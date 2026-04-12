import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { EvidencePanel } from "../components/workspace/EvidencePanel";
import { ExecutionConsolePanel } from "../components/workspace/ExecutionConsolePanel";
import { HookStudioPanel } from "../components/workspace/HookStudioPanel";
import { ReportsPanel } from "../components/workspace/ReportsPanel";
import { StaticBriefPanel } from "../components/workspace/StaticBriefPanel";
import { exportReport, getWorkspace, startExecution } from "../lib/api";
import type { ExecutionStartResponse, ReportExportResponse, WorkspaceEvent, WorkspaceSummary } from "../lib/types";
import { connectWorkspaceEvents } from "../lib/ws";

export function CaseWorkspacePage(): JSX.Element {
  const { caseId } = useParams<{ caseId: string }>();
  const [workspace, setWorkspace] = useState<WorkspaceSummary | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(caseId));
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [events, setEvents] = useState<WorkspaceEvent[]>([]);
  const [executionResponse, setExecutionResponse] = useState<ExecutionStartResponse | null>(null);
  const [reportResponse, setReportResponse] = useState<ReportExportResponse | null>(null);
  const [isStartingExecution, setIsStartingExecution] = useState(false);
  const [isExportingReport, setIsExportingReport] = useState(false);

  useEffect(() => {
    if (!caseId) {
      setWorkspace(null);
      setErrorMessage(null);
      setIsLoading(false);
      return;
    }

    let active = true;
    setIsLoading(true);

    void getWorkspace(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        setWorkspace(response);
        setErrorMessage(null);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setWorkspace(null);
        setErrorMessage("案件工作台暂时不可用。");
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setEvents([]);
      return;
    }

    const connection = connectWorkspaceEvents({
      caseId,
      onEvent: (event) => {
        setEvents((current) => [...current, event].slice(-20));
      },
      onError: () => {
        setEvents((current) => [
          ...current,
          {
            type: "workspace.events.error",
            case_id: caseId,
          },
        ]);
      },
    });

    return () => {
      connection.close();
    };
  }, [caseId]);

  async function handleStartExecution(): Promise<void> {
    if (!caseId) {
      return;
    }

    setIsStartingExecution(true);
    try {
      const response = await startExecution(caseId);
      setExecutionResponse(response);
    } catch {
      setExecutionResponse({
        case_id: caseId,
        status: "error",
      });
    } finally {
      setIsStartingExecution(false);
    }
  }

  async function handleExportReport(): Promise<void> {
    if (!caseId) {
      return;
    }

    setIsExportingReport(true);
    try {
      const response = await exportReport(caseId);
      setReportResponse(response);
    } catch {
      setReportResponse({
        case_id: caseId,
        report_path: "报告导出失败，请稍后重试。",
      });
    } finally {
      setIsExportingReport(false);
    }
  }

  const latestEvent = events.length > 0 ? events[events.length - 1] : null;
  const executionStatusText = executionResponse?.status ?? latestEvent?.status ?? "idle";

  return (
    <section aria-labelledby="case-workspace-title">
      <h2 id="case-workspace-title">案件工作台</h2>
      <p>查看静态简报与 Hook Studio，继续串起案件工作台的第一步数据流。</p>
      {caseId ? <p>案件编号：{caseId}</p> : <p>请先从案件队列选择一个案件进入工作台。</p>}
      {isLoading ? <p>正在加载案件工作台...</p> : null}
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      {!isLoading && !errorMessage && workspace ? <p>当前案件：{workspace.title}</p> : null}
      <StaticBriefPanel />
      <HookStudioPanel />
      <ExecutionConsolePanel
        events={events}
        isStarting={isStartingExecution}
        onStart={() => {
          void handleStartExecution();
        }}
        startDisabled={!caseId || isStartingExecution}
        statusText={executionStatusText}
      />
      <EvidencePanel caseId={caseId ?? null} latestEvent={latestEvent} workspace={workspace} />
      <ReportsPanel
        isExporting={isExportingReport}
        onExport={() => {
          void handleExportReport();
        }}
        reportPath={reportResponse?.report_path ?? null}
      />
    </section>
  );
}
