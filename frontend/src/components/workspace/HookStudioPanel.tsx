import type { HookRecommendationSummary, WorkspaceMethodSummary } from "../../lib/types";

type HookStudioPanelProps = {
  canOpenInJadx: boolean;
  hasMethodIndex: boolean;
  isLoadingMethods: boolean;
  isLoadingRecommendations: boolean;
  isOpeningInJadx: boolean;
  methodTotal: number;
  methods: WorkspaceMethodSummary[];
  openJadxMessage: string | null;
  openJadxError: string | null;
  recommendations: HookRecommendationSummary[];
  recommendationsError: string | null;
  searchError: string | null;
  searchValue: string;
  onMethodQueryChange: (value: string) => void;
  onMethodSearch: () => void;
  onOpenInJadx: () => void;
};

function formatMethodSignature(method: WorkspaceMethodSummary): string {
  const parameters = method.parameter_types.length > 0 ? method.parameter_types.join(", ") : "无参数";
  const methodName = method.is_constructor ? "构造方法" : method.method_name;
  return `${methodName}(${parameters}) : ${method.return_type}`;
}

function formatMethodParameters(method: WorkspaceMethodSummary): string {
  return method.parameter_types.length > 0 ? method.parameter_types.join(", ") : "无参数";
}

function renderMethodTags(method: WorkspaceMethodSummary): JSX.Element {
  if (method.tags.length === 0) {
    return <span>暂无标签</span>;
  }

  return (
    <>
      {method.tags.map((tag) => (
        <span key={tag}>{tag}</span>
      ))}
    </>
  );
}

export function HookStudioPanel({
  canOpenInJadx,
  hasMethodIndex,
  isLoadingMethods,
  isLoadingRecommendations,
  isOpeningInJadx,
  methodTotal,
  methods,
  openJadxError,
  openJadxMessage,
  onMethodQueryChange,
  onMethodSearch,
  onOpenInJadx,
  recommendations,
  recommendationsError,
  searchError,
  searchValue,
}: HookStudioPanelProps): JSX.Element {
  return (
    <section aria-labelledby="hook-studio-title">
      <h3 id="hook-studio-title">Hook Studio</h3>
      <p>这里整合方法搜索、离线推荐和 Open in JADX，方便快速浏览样本。</p>

      <section aria-labelledby="method-browser-title">
        <h4 id="method-browser-title">方法浏览</h4>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onMethodSearch();
          }}
        >
          <label>
            搜索方法
            <input
              aria-label="搜索方法"
              value={searchValue}
              onChange={(event) => onMethodQueryChange(event.target.value)}
              type="text"
              disabled={!hasMethodIndex}
              placeholder={hasMethodIndex ? "输入类名、方法名、签名或标签" : "没有方法索引可搜索"}
            />
          </label>
          <button type="submit" disabled={!hasMethodIndex}>
            搜索方法
          </button>
        </form>

        {!hasMethodIndex ? <p>当前没有可用的方法索引，无法浏览方法列表。</p> : null}
        {searchError ? <p role="alert">{searchError}</p> : null}
        {isLoadingMethods ? <p>正在加载方法索引...</p> : null}
        <p>方法总数：{methodTotal}</p>

        <ul aria-label="方法列表">
          {!isLoadingMethods && methods.length === 0 ? <li>暂无方法结果。</li> : null}
          {methods.map((method) => (
            <li key={`${method.class_name}.${method.method_name}.${method.source_path}`}>
              <strong>{method.class_name}</strong>
              <p>类名：{method.class_name}</p>
              <p>方法名：{method.method_name}</p>
              <p>参数：{formatMethodParameters(method)}</p>
              <p>签名：{method.method_name}({formatMethodParameters(method)})</p>
              <p>返回类型：{method.return_type}</p>
              <p>
                来源：{method.source_path}
                {method.line_hint ? ` · 第 ${method.line_hint} 行` : ""}
              </p>
              <p>
                标签：
                {renderMethodTags(method)}
              </p>
              {method.evidence.length > 0 ? <p>线索：{method.evidence.join("；")}</p> : null}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="recommendations-title">
        <h4 id="recommendations-title">离线推荐</h4>
        <p>方法推荐和模板推荐会一起显示在这里。</p>
        {recommendationsError ? <p role="alert">{recommendationsError}</p> : null}
        {isLoadingRecommendations ? <p>正在加载离线推荐...</p> : null}
        <ul aria-label="离线推荐列表">
          {!isLoadingRecommendations && recommendations.length === 0 ? <li>暂无离线推荐。</li> : null}
          {recommendations.map((item) => (
            <li key={item.recommendation_id}>
              <strong>{item.title}</strong>
              <p>类型：{item.kind} · 评分：{item.score}</p>
              <p>{item.reason}</p>
              {item.method ? (
                <p>
                  方法：{item.method.class_name}.{item.method.method_name} · {formatMethodSignature(item.method)}
                </p>
              ) : null}
              {item.template_name ? <p>模板：{item.template_name}</p> : null}
              {item.matched_terms.length > 0 ? <p>命中词：{item.matched_terms.join("、")}</p> : null}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="jadx-open-title">
        <h4 id="jadx-open-title">JADX</h4>
        <p>需要深入代码时，直接打开本地 JADX。</p>
        <button type="button" onClick={onOpenInJadx} disabled={!canOpenInJadx || isOpeningInJadx}>
          {isOpeningInJadx ? "正在打开..." : "Open in JADX"}
        </button>
        {!canOpenInJadx ? <p>当前无法打开 JADX，请先确认本机配置。</p> : null}
        {openJadxMessage ? <p>{openJadxMessage}</p> : null}
        {openJadxError ? <p role="alert">{openJadxError}</p> : null}
      </section>
    </section>
  );
}
