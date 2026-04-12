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

export function StaticBriefPanel({ detail, errorMessage, isLoading }: StaticBriefPanelProps): JSX.Element {
  return (
    <section aria-labelledby="static-brief-title">
      <h3 id="static-brief-title">静态简报</h3>
      <p>这里展示工作区静态检查返回的真实静态概览。</p>

      {isLoading ? <p>正在加载静态简报...</p> : null}
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}

      <dl>
        <div>
          <dt>包名</dt>
          <dd>{detail?.package_name ?? "未加载"}</dd>
        </div>
        <div>
          <dt>技术标签</dt>
          <dd>
            <ul>{renderItems(detail?.technical_tags ?? [], "暂无技术标签。")}</ul>
          </dd>
        </div>
        <div>
          <dt>危险权限</dt>
          <dd>
            <ul>{renderItems(detail?.dangerous_permissions ?? [], "暂无危险权限。")}</ul>
          </dd>
        </div>
        <div>
          <dt>回连端点</dt>
          <dd>
            <ul>{renderItems(detail?.callback_endpoints ?? [], "暂无回连端点。")}</ul>
          </dd>
        </div>
        <div>
          <dt>回连线索</dt>
          <dd>
            <ul>{renderItems(detail?.callback_clues ?? [], "暂无回连线索。")}</ul>
          </dd>
        </div>
        <div>
          <dt>加密信号</dt>
          <dd>
            <ul>{renderItems(detail?.crypto_signals ?? [], "暂无加密信号。")}</ul>
          </dd>
        </div>
        <div>
          <dt>加固线索</dt>
          <dd>
            <ul>{renderItems(detail?.packer_hints ?? [], "暂无加固线索。")}</ul>
          </dd>
        </div>
        <div>
          <dt>限制说明</dt>
          <dd>
            <ul>{renderItems(detail?.limitations ?? [], "暂无限制说明。")}</ul>
          </dd>
        </div>
        <div>
          <dt>自定义脚本</dt>
          <dd>
            {detail?.custom_scripts && detail.custom_scripts.length > 0 ? (
              <ul>
                {detail.custom_scripts.map((script) => (
                  <li key={script.script_id}>
                    <strong>{script.name}</strong>
                    <span> · {script.script_path}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>暂无自定义脚本。</p>
            )}
          </dd>
        </div>
        <div>
          <dt>方法索引状态</dt>
          <dd>
            <p>{detail?.has_method_index ? "已建立" : "未建立"}</p>
            <p>方法总数：{detail?.method_count ?? 0}</p>
          </dd>
        </div>
      </dl>
    </section>
  );
}
