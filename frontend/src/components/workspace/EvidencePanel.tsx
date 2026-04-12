import type { WorkspaceEvent, WorkspaceSummary } from "../../lib/types";

type EvidencePanelProps = {
  caseId: string | null;
  latestEvent: WorkspaceEvent | null;
  workspace: WorkspaceSummary | null;
};

export function EvidencePanel({ caseId, latestEvent, workspace }: EvidencePanelProps): JSX.Element {
  return (
    <section aria-labelledby="evidence-panel-title">
      <h3 id="evidence-panel-title">证据中心</h3>
      <p>汇总当前案件的基础上下文，并预留动态证据归集入口。</p>
      <p>案件编号：{caseId ?? "未选择"}</p>
      <p>案件标题：{workspace?.title ?? "未加载"}</p>
      <p>最近事件：{latestEvent?.type ?? "暂无"}</p>
    </section>
  );
}
