import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { HookStudioPanel } from "../components/workspace/HookStudioPanel";
import { StaticBriefPanel } from "../components/workspace/StaticBriefPanel";
import { getWorkspace } from "../lib/api";
import type { WorkspaceSummary } from "../lib/types";

export function CaseWorkspacePage(): JSX.Element {
  const { caseId } = useParams<{ caseId: string }>();
  const [workspace, setWorkspace] = useState<WorkspaceSummary | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(caseId));
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
    </section>
  );
}
