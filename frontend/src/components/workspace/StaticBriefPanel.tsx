import type { WorkspaceDetailResponse } from "../../lib/types";

type StaticBriefPanelProps = {
  detail: WorkspaceDetailResponse | null;
  errorMessage: string | null;
  isLoading: boolean;
};

function renderItems(items: string[], emptyLabel: string): JSX.Element {
  if (items.length === 0) {
    return <li>{emptyLabel}</li>;
  }

  return (
    <>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </>
  );
}

function summarizeItems(items: string[], emptyLabel: string): string {
  if (items.length === 0) {
    return emptyLabel;
  }
  if (items.length === 1) {
    return items[0];
  }
  return `${items[0]} 等 ${items.length} 项`;
}

function detailSummary(label: string, items: string[]): string {
  if (items.length === 0) {
    return `${label} · 暂无`;
  }
  return `${label} · ${items.length} 项`;
}

export function StaticBriefPanel({
  detail,
  errorMessage,
  isLoading,
}: StaticBriefPanelProps): JSX.Element {
  const technicalTags = detail?.technical_tags ?? [];
  const dangerousPermissions = detail?.dangerous_permissions ?? [];
  const callbackEndpoints = detail?.callback_endpoints ?? [];
  const callbackClues = detail?.callback_clues ?? [];
  const cryptoSignals = detail?.crypto_signals ?? [];
  const packerHints = detail?.packer_hints ?? [];
  const limitations = detail?.limitations ?? [];
  const customScripts = detail?.custom_scripts ?? [];

  return (
    <section className="workspace-panel static-brief-panel" aria-labelledby="static-brief-title">
      <h3 id="static-brief-title">静态简报</h3>
      <p>先看摘要，需要时再展开明细，避免首屏被静态信息堆满。</p>

      {isLoading ? <p>正在加载静态简报...</p> : null}
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}

      <div className="metric-grid metric-grid--four">
        <div className="app-banner__metric">
          <span>包名</span>
          <strong>{detail?.package_name ?? "未加载"}</strong>
        </div>
        <div className="app-banner__metric">
          <span>技术标签</span>
          <strong>{summarizeItems(technicalTags, "暂无")}</strong>
        </div>
        <div className="app-banner__metric">
          <span>危险权限</span>
          <strong>{dangerousPermissions.length > 0 ? `${dangerousPermissions.length} 项` : "暂无"}</strong>
        </div>
        <div className="app-banner__metric">
          <span>回连端点</span>
          <strong>{callbackEndpoints.length > 0 ? `${callbackEndpoints.length} 条` : "暂无"}</strong>
        </div>
        <div className="app-banner__metric">
          <span>加密信号</span>
          <strong>{cryptoSignals.length > 0 ? `${cryptoSignals.length} 项` : "暂无"}</strong>
        </div>
        <div className="app-banner__metric">
          <span>加固线索</span>
          <strong>{packerHints.length > 0 ? `${packerHints.length} 项` : "暂无"}</strong>
        </div>
        <div className="app-banner__metric">
          <span>自定义脚本</span>
          <strong>{customScripts.length > 0 ? `${customScripts.length} 个` : "暂无"}</strong>
        </div>
        <div className="app-banner__metric">
          <span>方法索引状态</span>
          <strong>{detail?.has_method_index ? `已建立 · ${detail.method_count} 个函数` : "未建立"}</strong>
        </div>
      </div>

      <div className="brief-disclosure-list">
        <details className="brief-disclosure">
          <summary>{detailSummary("技术标签", technicalTags)}</summary>
          <ul>{renderItems(technicalTags, "暂无技术标签。")}</ul>
        </details>
        <details className="brief-disclosure">
          <summary>{detailSummary("危险权限", dangerousPermissions)}</summary>
          <ul>{renderItems(dangerousPermissions, "暂无危险权限。")}</ul>
        </details>
        <details className="brief-disclosure">
          <summary>{detailSummary("回连端点", callbackEndpoints)}</summary>
          <ul>{renderItems(callbackEndpoints, "暂无回连端点。")}</ul>
        </details>
        <details className="brief-disclosure">
          <summary>{detailSummary("回连线索", callbackClues)}</summary>
          <ul>{renderItems(callbackClues, "暂无回连线索。")}</ul>
        </details>
        <details className="brief-disclosure">
          <summary>{detailSummary("加密信号", cryptoSignals)}</summary>
          <ul>{renderItems(cryptoSignals, "暂无加密信号。")}</ul>
        </details>
        <details className="brief-disclosure">
          <summary>{detailSummary("加固线索", packerHints)}</summary>
          <ul>{renderItems(packerHints, "暂无加固线索。")}</ul>
        </details>
        <details className="brief-disclosure">
          <summary>{detailSummary("限制说明", limitations)}</summary>
          <ul>{renderItems(limitations, "暂无限制说明。")}</ul>
        </details>
        <details className="brief-disclosure">
          <summary>{customScripts.length > 0 ? `自定义脚本 · ${customScripts.length} 个` : "自定义脚本 · 暂无"}</summary>
          {customScripts.length > 0 ? (
            <ul>
              {customScripts.map((script) => (
                <li key={script.script_id}>
                  <strong>{script.name}</strong>
                  <span> · {script.script_path}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>暂无自定义脚本。</p>
          )}
        </details>
        <details className="brief-disclosure">
          <summary>{detail?.has_method_index ? "方法索引状态 · 已建立" : "方法索引状态 · 未建立"}</summary>
          <p>{detail?.has_method_index ? "当前案件已支持方法搜索和类导航。" : "当前案件尚未建立方法索引。"}</p>
          <p>方法总数：{detail?.method_count ?? 0}</p>
        </details>
      </div>
    </section>
  );
}
