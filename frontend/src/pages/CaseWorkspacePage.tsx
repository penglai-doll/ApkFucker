import { HookStudioPanel } from "../components/workspace/HookStudioPanel";
import { StaticBriefPanel } from "../components/workspace/StaticBriefPanel";

export function CaseWorkspacePage(): JSX.Element {
  return (
    <section aria-labelledby="case-workspace-title">
      <h2 id="case-workspace-title">案件工作台</h2>
      <p>查看静态简报与 Hook Studio，继续串起案件工作台的第一步数据流。</p>
      <StaticBriefPanel />
      <HookStudioPanel />
    </section>
  );
}
