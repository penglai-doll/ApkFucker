import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { EvidencePanel } from "../components/workspace/EvidencePanel";
import { ExecutionConsolePanel } from "../components/workspace/ExecutionConsolePanel";
import { HookStudioPanel } from "../components/workspace/HookStudioPanel";
import { ReportsPanel } from "../components/workspace/ReportsPanel";
import { StaticBriefPanel } from "../components/workspace/StaticBriefPanel";
import {
  exportReport,
  getEnvironmentStatus,
  getWorkspaceDetail,
  getWorkspaceMethods,
  getWorkspaceRecommendations,
  openWorkspaceInJadx,
  startExecution,
} from "../lib/api";
import type {
  ExecutionStartResponse,
  EnvironmentPresetStatus,
  EnvironmentToolStatus,
  HookRecommendationSummary,
  ReportExportResponse,
  WorkspaceDetailResponse,
  WorkspaceEvent,
  WorkspaceMethodSummary,
  WorkspaceSummary,
} from "../lib/types";
import { connectWorkspaceEvents } from "../lib/ws";

const METHOD_LIMIT = 12;
const RECOMMENDATION_LIMIT = 6;

export function CaseWorkspacePage(): JSX.Element {
  const { caseId } = useParams<{ caseId: string }>();
  const activeCaseIdRef = useRef<string | null>(caseId ?? null);
  const [detail, setDetail] = useState<WorkspaceDetailResponse | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(Boolean(caseId));
  const [searchValue, setSearchValue] = useState("");
  const [methodQuery, setMethodQuery] = useState("");
  const [methods, setMethods] = useState<WorkspaceMethodSummary[]>([]);
  const [methodTotal, setMethodTotal] = useState(0);
  const [isLoadingMethods, setIsLoadingMethods] = useState(false);
  const [methodsError, setMethodsError] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<HookRecommendationSummary[]>([]);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);
  const [isOpeningInJadx, setIsOpeningInJadx] = useState(false);
  const [openJadxMessage, setOpenJadxMessage] = useState<string | null>(null);
  const [openJadxError, setOpenJadxError] = useState<string | null>(null);
  const [events, setEvents] = useState<WorkspaceEvent[]>([]);
  const [environmentSummary, setEnvironmentSummary] = useState<string | null>(null);
  const [recommendedExecutionMode, setRecommendedExecutionMode] = useState<string | null>(null);
  const [executionPresets, setExecutionPresets] = useState<EnvironmentPresetStatus[]>([]);
  const [environmentTools, setEnvironmentTools] = useState<EnvironmentToolStatus[]>([]);
  const [isLoadingEnvironment, setIsLoadingEnvironment] = useState(Boolean(caseId));
  const [environmentError, setEnvironmentError] = useState<string | null>(null);
  const [executionResponse, setExecutionResponse] = useState<ExecutionStartResponse | null>(null);
  const [reportResponse, setReportResponse] = useState<ReportExportResponse | null>(null);
  const [isStartingExecution, setIsStartingExecution] = useState(false);
  const [isExportingReport, setIsExportingReport] = useState(false);

  useEffect(() => {
    activeCaseIdRef.current = caseId ?? null;
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setDetail(null);
      setDetailError(null);
      setIsLoadingDetail(false);
      setSearchValue("");
      setMethodQuery("");
      setMethods([]);
      setMethodTotal(0);
      setMethodsError(null);
      setRecommendations([]);
      setRecommendationsError(null);
      setOpenJadxMessage(null);
      setOpenJadxError(null);
      setEvents([]);
      setEnvironmentSummary(null);
      setRecommendedExecutionMode(null);
      setExecutionPresets([]);
      setEnvironmentTools([]);
      setIsLoadingEnvironment(false);
      setEnvironmentError(null);
      setExecutionResponse(null);
      setReportResponse(null);
      return;
    }

    let active = true;
    setIsLoadingDetail(true);
    setDetailError(null);
    setDetail(null);
    setSearchValue("");
    setMethodQuery("");
    setMethods([]);
    setMethodTotal(0);
    setMethodsError(null);
    setRecommendations([]);
    setRecommendationsError(null);
    setOpenJadxMessage(null);
    setOpenJadxError(null);
    setEvents([]);
    setEnvironmentSummary(null);
    setRecommendedExecutionMode(null);
    setExecutionPresets([]);
    setEnvironmentTools([]);
    setIsLoadingEnvironment(true);
    setEnvironmentError(null);
    setExecutionResponse(null);
    setReportResponse(null);

    void getWorkspaceDetail(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        setDetail(response);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setDetail(null);
        setDetailError("案件工作台暂时不可用。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingDetail(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setEnvironmentSummary(null);
      setRecommendedExecutionMode(null);
      setExecutionPresets([]);
      setEnvironmentTools([]);
      setIsLoadingEnvironment(false);
      setEnvironmentError(null);
      return;
    }

    let active = true;
    setIsLoadingEnvironment(true);
    setEnvironmentError(null);

    void getEnvironmentStatus()
      .then((response) => {
        if (!active) {
          return;
        }
        setEnvironmentSummary(response.summary);
        setRecommendedExecutionMode(response.recommended_execution_mode);
        setExecutionPresets(response.execution_presets);
        setEnvironmentTools(response.tools);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setEnvironmentSummary(null);
        setRecommendedExecutionMode(null);
        setExecutionPresets([]);
        setEnvironmentTools([]);
        setEnvironmentError("执行环境暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingEnvironment(false);
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

  useEffect(() => {
    if (!caseId || !detail) {
      return;
    }

    let active = true;
    setIsLoadingRecommendations(true);
    setRecommendationsError(null);

    void getWorkspaceRecommendations(caseId, { limit: RECOMMENDATION_LIMIT })
      .then((response) => {
        if (!active) {
          return;
        }
        setRecommendations(response.items);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setRecommendations([]);
        setRecommendationsError("离线推荐暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingRecommendations(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId, detail]);

  useEffect(() => {
    if (!caseId || !detail || !detail.has_method_index) {
      setMethods([]);
      setMethodTotal(0);
      setMethodsError(null);
      setIsLoadingMethods(false);
      return;
    }

    let active = true;
    setIsLoadingMethods(true);
    setMethodsError(null);

    void getWorkspaceMethods(caseId, { query: methodQuery.trim(), limit: METHOD_LIMIT })
      .then((response) => {
        if (!active) {
          return;
        }
        setMethods(response.items);
        setMethodTotal(response.total);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setMethods([]);
        setMethodTotal(0);
        setMethodsError("方法索引暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingMethods(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId, detail, methodQuery]);

  async function handleOpenInJadx(): Promise<void> {
    if (!caseId || !detail?.can_open_in_jadx) {
      return;
    }

    const requestCaseId = caseId;
    setIsOpeningInJadx(true);
    setOpenJadxMessage(null);
    setOpenJadxError(null);

    try {
      await openWorkspaceInJadx(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setOpenJadxMessage("已尝试在本机打开 JADX。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setOpenJadxError("打开 JADX 失败，请检查本机配置。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsOpeningInJadx(false);
      }
    }
  }

  async function handleStartExecution(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setIsStartingExecution(true);
    try {
      const response = await startExecution(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setExecutionResponse(response);
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setExecutionResponse({
        case_id: requestCaseId,
        status: "error",
      });
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsStartingExecution(false);
      }
    }
  }

  async function handleExportReport(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setIsExportingReport(true);
    try {
      const response = await exportReport(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setReportResponse(response);
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setReportResponse({
        case_id: requestCaseId,
        report_path: "报告导出失败，请稍后重试。",
      });
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsExportingReport(false);
      }
    }
  }

  function handleMethodSearch(): void {
    if (!detail?.has_method_index) {
      return;
    }

    setMethodQuery(searchValue.trim());
  }

  const latestEvent = events.length > 0 ? events[events.length - 1] : null;
  const executionStatusText = executionResponse?.status ?? latestEvent?.status ?? "idle";
  const workspaceSummary: WorkspaceSummary | null = detail
    ? {
        case_id: detail.case_id,
        title: detail.title,
        view: "workspace",
      }
    : null;

  return (
    <section aria-labelledby="case-workspace-title">
      <h2 id="case-workspace-title">案件工作台</h2>
      <p>浏览静态简报、方法索引和离线 Hook 推荐，必要时可以直接打开本地 JADX。</p>
      {caseId ? <p>案件编号：{caseId}</p> : <p>请先从案件队列选择一个案件进入工作台。</p>}
      {isLoadingDetail ? <p>正在加载工作区数据...</p> : null}
      {!isLoadingDetail && detail ? <p>当前案件：{detail.title}</p> : null}
      <StaticBriefPanel detail={detail} errorMessage={detailError} isLoading={isLoadingDetail} />
      <HookStudioPanel
        canOpenInJadx={Boolean(detail?.can_open_in_jadx)}
        hasMethodIndex={Boolean(detail?.has_method_index)}
        isLoadingMethods={isLoadingMethods}
        isLoadingRecommendations={isLoadingRecommendations}
        isOpeningInJadx={isOpeningInJadx}
        methodTotal={methodTotal}
        methods={methods}
        openJadxError={openJadxError}
        openJadxMessage={openJadxMessage}
        onMethodQueryChange={setSearchValue}
        onMethodSearch={handleMethodSearch}
        onOpenInJadx={() => {
          void handleOpenInJadx();
        }}
        recommendations={recommendations}
        recommendationsError={recommendationsError}
        searchError={methodsError}
        searchValue={searchValue}
      />
      <ExecutionConsolePanel
        environmentError={environmentError}
        environmentSummary={environmentSummary}
        executionPresets={executionPresets}
        events={events}
        isLoadingEnvironment={isLoadingEnvironment}
        isStarting={isStartingExecution}
        onStart={() => {
          void handleStartExecution();
        }}
        recommendedExecutionMode={recommendedExecutionMode}
        startDisabled={!caseId || isStartingExecution}
        statusText={executionStatusText}
        tools={environmentTools}
      />
      <EvidencePanel caseId={caseId ?? null} latestEvent={latestEvent} workspace={workspaceSummary} />
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
