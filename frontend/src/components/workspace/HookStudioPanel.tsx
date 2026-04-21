import { useEffect, useMemo, useState } from "react";

import type {
  HookPlanMoveDirection,
  CustomScriptSummary,
  HookMethodInsightSummary,
  HookPlanItemSummary,
  HookRecommendationSummary,
  HookStudioExternalContext,
  WorkspaceMethodScope,
  WorkspaceMethodSummary,
} from "../../lib/types";
import { localizeExecutionFailureCode } from "../../lib/executionDiagnostics";

type HookStudioPanelProps = {
  customScripts: CustomScriptSummary[];
  customScriptsError: string | null;
  draftScriptContent: string;
  draftScriptName: string;
  externalContext: HookStudioExternalContext | null;
  hasMethodIndex: boolean;
  hookPlanError: string | null;
  hookPlanItems: HookPlanItemSummary[];
  hookStudioError: string | null;
  hookStudioMessage: string | null;
  isLoadingHookPlan: boolean;
  isLoadingMethods: boolean;
  isLoadingRecommendations: boolean;
  isLoadingCustomScript: boolean;
  isDeletingCustomScript: boolean;
  isRefreshingMethodIndex: boolean;
  isSavingCustomScript: boolean;
  methodIndexProgress: number;
  methodIndexStageLabel: string | null;
  methodScope: WorkspaceMethodScope;
  availableMethodScopes: WorkspaceMethodScope[];
  methodTotal: number;
  methods: WorkspaceMethodSummary[];
  methodIndexMessage: string | null;
  methodInsight: HookMethodInsightSummary | null;
  selectedMethod: WorkspaceMethodSummary | null;
  onAddCustomScriptToPlan: (scriptId: string) => void;
  onAddMethodToPlan: (method: WorkspaceMethodSummary) => void;
  onAddRecommendationToPlan: (recommendationId: string) => void;
  onInspectExecutionContext: (payload: { class_name: string; method_name: string }) => void;
  onInspectTrafficContext: (payload: {
    hint: string;
    recommendationId: string | null;
    recommendationTitle: string | null;
  }) => void;
  onClearHookPlan: () => void;
  onClearExternalContext: () => void;
  onCreateCustomScriptDraft: () => void;
  onDeleteCustomScript: (scriptId: string) => void;
  onDraftScriptContentChange: (value: string) => void;
  onDraftScriptNameChange: (value: string) => void;
  onLoadCustomScript: (scriptId: string) => void;
  onMethodQueryChange: (value: string) => void;
  onMethodSearch: () => void;
  onMethodScopeChange: (value: WorkspaceMethodScope) => void;
  onRefreshMethodIndex: () => void;
  onSelectMethod: (method: WorkspaceMethodSummary) => void;
  onMoveHookPlanItem: (itemId: string, direction: HookPlanMoveDirection) => void;
  onRemoveHookPlanItem: (itemId: string) => void;
  onSaveCustomScript: () => void;
  onSetHookPlanItemEnabled: (itemId: string, enabled: boolean) => void;
  recommendations: HookRecommendationSummary[];
  recommendationsError: string | null;
  searchError: string | null;
  searchValue: string;
  selectedCustomScriptId: string | null;
};

type ClassBucket = {
  className: string;
  count: number;
  methods: WorkspaceMethodSummary[];
};

type NamespaceBucket = {
  namespace: string;
  classes: ClassBucket[];
};

type MethodGroup = {
  methodName: string;
  count: number;
  methods: WorkspaceMethodSummary[];
};

function formatMethodSignature(method: WorkspaceMethodSummary): string {
  const parameters = method.parameter_types.length > 0 ? method.parameter_types.join(", ") : "无参数";
  const methodName = method.is_constructor ? "构造方法" : method.method_name;
  return `${methodName}(${parameters}) : ${method.return_type}`;
}

function methodKey(method: WorkspaceMethodSummary): string {
  return [
    method.class_name,
    method.method_name,
    method.source_path,
    method.line_hint ?? "",
    method.parameter_types.join(","),
  ].join("|");
}

function methodGroupKey(method: WorkspaceMethodSummary): string {
  return `${method.class_name}:${method.is_constructor ? "<constructor>" : method.method_name}`;
}

function simpleClassName(className: string): string {
  const withoutInner = className.split("$").at(-1) ?? className;
  return withoutInner.split(".").at(-1) ?? withoutInner;
}

function namespaceName(className: string): string {
  const lastDot = className.lastIndexOf(".");
  if (lastDot < 0) {
    return "默认包";
  }
  return className.slice(0, lastDot);
}

function buildClassBuckets(methods: WorkspaceMethodSummary[]): ClassBucket[] {
  const buckets = new Map<string, WorkspaceMethodSummary[]>();
  for (const method of methods) {
    const existing = buckets.get(method.class_name);
    if (existing) {
      existing.push(method);
      continue;
    }
    buckets.set(method.class_name, [method]);
  }

  return Array.from(buckets.entries())
    .map(([className, classMethods]) => ({
      className,
      count: classMethods.length,
      methods: [...classMethods].sort((left, right) => {
        if (left.method_name !== right.method_name) {
          return left.method_name.localeCompare(right.method_name);
        }
        return (left.line_hint ?? 0) - (right.line_hint ?? 0);
      }),
    }))
    .sort((left, right) => left.className.localeCompare(right.className));
}

function buildNamespaceBuckets(classBuckets: ClassBucket[]): NamespaceBucket[] {
  const buckets = new Map<string, ClassBucket[]>();
  for (const classBucket of classBuckets) {
    const namespace = namespaceName(classBucket.className);
    const existing = buckets.get(namespace);
    if (existing) {
      existing.push(classBucket);
      continue;
    }
    buckets.set(namespace, [classBucket]);
  }

  return Array.from(buckets.entries())
    .map(([namespace, classes]) => ({
      namespace,
      classes: [...classes].sort((left, right) => left.className.localeCompare(right.className)),
    }))
    .sort((left, right) => left.namespace.localeCompare(right.namespace));
}

function buildMethodGroups(methods: WorkspaceMethodSummary[]): MethodGroup[] {
  const groups = new Map<string, WorkspaceMethodSummary[]>();
  for (const method of methods) {
    const groupKey = method.is_constructor ? "<constructor>" : method.method_name;
    const existing = groups.get(groupKey);
    if (existing) {
      existing.push(method);
      continue;
    }
    groups.set(groupKey, [method]);
  }

  return Array.from(groups.entries())
    .map(([methodName, groupedMethods]) => ({
      methodName,
      count: groupedMethods.length,
      methods: [...groupedMethods].sort((left, right) => {
        const leftLine = left.line_hint ?? Number.MAX_SAFE_INTEGER;
        const rightLine = right.line_hint ?? Number.MAX_SAFE_INTEGER;
        return leftLine - rightLine;
      }),
    }))
    .sort((left, right) => left.methodName.localeCompare(right.methodName));
}

function localizeRecommendationKind(kind: string): string {
  switch (kind) {
    case "method":
      return "方法推荐";
    case "template":
    case "template_hook":
      return "模板推荐";
    default:
      return kind;
  }
}

function localizePlanKind(kind: string): string {
  switch (kind) {
    case "method_hook":
      return "方法 Hook";
    case "template_hook":
      return "模板 Hook";
    case "custom_script":
      return "自定义脚本";
    default:
      return kind;
  }
}

function planTitle(item: HookPlanItemSummary): string {
  return `${item.kind} #${item.inject_order}`;
}

function localizePlanStatus(enabled: boolean): string {
  return enabled ? "已启用" : "已禁用";
}

function localizeMethodScope(scope: WorkspaceMethodScope): string {
  switch (scope) {
    case "all":
      return "全部方法";
    case "related_candidates":
      return "相关候选";
    case "first_party":
    default:
      return "一方代码";
  }
}

function localizeExecutionInsightStatus(status: string | null, eventType: string | null): string {
  if (status === "started") {
    return "已启动";
  }
  if (status === "completed") {
    return "已完成";
  }
  if (status === "cancelled") {
    return "已取消";
  }
  if (status === "error") {
    return "执行失败";
  }
  if (eventType === "execution.event") {
    return "已记录日志";
  }
  if (eventType === "execution.failed") {
    return "执行失败";
  }
  if (eventType === "execution.completed") {
    return "已完成";
  }
  return "暂无";
}

function scopeDescription(scope: WorkspaceMethodScope): string {
  switch (scope) {
    case "all":
      return "包含一方代码与反编译后的全部依赖方法，适合做兜底排查。";
    case "related_candidates":
      return "优先保留一方代码，同时补入命中线索、标签或推荐的候选方法。";
    case "first_party":
    default:
      return "仅展示样本自身包名下的方法入口，适合先快速定位核心逻辑。";
  }
}

function buildTrafficHaystack(parts: string[]): string {
  return parts.join(" ").toLowerCase();
}

function isTrafficLinkedMethod(method: WorkspaceMethodSummary | null): boolean {
  if (!method) {
    return false;
  }
  const haystack = buildTrafficHaystack([
    method.class_name,
    method.method_name,
    method.declaration ?? "",
    method.source_preview ?? "",
    ...method.tags,
    ...method.evidence,
  ]);
  return [
    "ssl",
    "https",
    "http",
    "network",
    "okhttp",
    "retrofit",
    "webview",
    "proxy",
    "tls",
    "trustmanager",
    "hostname",
    "socket",
    "pin",
    "流量",
    "网络",
    "证书",
  ].some((keyword) => haystack.includes(keyword));
}

function isTrafficLinkedRecommendation(item: HookRecommendationSummary): boolean {
  const haystack = buildTrafficHaystack([
    item.title,
    item.reason,
    item.template_id ?? "",
    item.template_name ?? "",
    item.plugin_id ?? "",
    ...item.matched_terms,
    ...(item.method?.tags ?? []),
    ...(item.method?.evidence ?? []),
    item.method?.class_name ?? "",
    item.method?.method_name ?? "",
  ]);
  return [
    "ssl",
    "https",
    "http",
    "network",
    "okhttp",
    "retrofit",
    "webview",
    "proxy",
    "tls",
    "trustmanager",
    "hostname",
    "socket",
    "pin",
    "流量",
    "网络",
    "证书",
  ].some((keyword) => haystack.includes(keyword));
}

export function HookStudioPanel({
  customScripts,
  customScriptsError,
  draftScriptContent,
  draftScriptName,
  externalContext,
  hasMethodIndex,
  hookPlanError,
  hookPlanItems,
  hookStudioError,
  hookStudioMessage,
  isLoadingHookPlan,
  isLoadingMethods,
  isLoadingRecommendations,
  isLoadingCustomScript,
  isDeletingCustomScript,
  isRefreshingMethodIndex,
  isSavingCustomScript,
  methodIndexProgress,
  methodIndexStageLabel,
  methodScope,
  availableMethodScopes,
  methodTotal,
  methods,
  methodIndexMessage,
  methodInsight,
  selectedMethod,
  onAddCustomScriptToPlan,
  onAddMethodToPlan,
  onAddRecommendationToPlan,
  onInspectExecutionContext,
  onInspectTrafficContext,
  onClearHookPlan,
  onClearExternalContext,
  onCreateCustomScriptDraft,
  onDeleteCustomScript,
  onDraftScriptContentChange,
  onDraftScriptNameChange,
  onLoadCustomScript,
  onMethodQueryChange,
  onMethodSearch,
  onMethodScopeChange,
  onRefreshMethodIndex,
  onSelectMethod,
  onMoveHookPlanItem,
  onRemoveHookPlanItem,
  onSaveCustomScript,
  onSetHookPlanItemEnabled,
  recommendations,
  recommendationsError,
  searchError,
  searchValue,
  selectedCustomScriptId,
}: HookStudioPanelProps): JSX.Element {
  const [expandedRecommendationId, setExpandedRecommendationId] = useState<string | null>(null);
  const [expandedPlanItemId, setExpandedPlanItemId] = useState<string | null>(null);
  const [expandedScriptId, setExpandedScriptId] = useState<string | null>(null);
  const [expandedMethodGroupKey, setExpandedMethodGroupKey] = useState<string | null>(null);
  const [isHookPlanSectionOpen, setIsHookPlanSectionOpen] = useState<boolean>(hookPlanItems.length > 0);
  const [isCustomScriptSectionOpen, setIsCustomScriptSectionOpen] = useState<boolean>(
    customScripts.length > 0 || draftScriptName.trim().length > 0 || draftScriptContent.trim().length > 0,
  );

  const classBuckets = useMemo(() => buildClassBuckets(methods), [methods]);
  const namespaceBuckets = useMemo(() => buildNamespaceBuckets(classBuckets), [classBuckets]);
  const activeClassName = selectedMethod?.class_name ?? classBuckets[0]?.className ?? null;
  const activeClassMethods =
    classBuckets.find((bucket) => bucket.className === activeClassName)?.methods ?? methods;
  const activeMethodGroups = useMemo(() => buildMethodGroups(activeClassMethods), [activeClassMethods]);
  const overloadGroupCount = activeMethodGroups.filter((group) => group.count > 1).length;
  const activeMethodGroupKey = selectedMethod ? methodGroupKey(selectedMethod) : null;

  useEffect(() => {
    if (activeMethodGroupKey) {
      setExpandedMethodGroupKey(activeMethodGroupKey);
      return;
    }
    if (activeMethodGroups.length === 0) {
      setExpandedMethodGroupKey(null);
      return;
    }
    setExpandedMethodGroupKey((current) => current ?? methodGroupKey(activeMethodGroups[0].methods[0]));
  }, [activeMethodGroupKey, activeMethodGroups]);

  useEffect(() => {
    if (hookPlanItems.length > 0) {
      setIsHookPlanSectionOpen(true);
    }
  }, [hookPlanItems.length]);

  useEffect(() => {
    if (customScripts.length > 0 || draftScriptName.trim().length > 0 || draftScriptContent.trim().length > 0) {
      setIsCustomScriptSectionOpen(true);
    }
  }, [customScripts.length, draftScriptName, draftScriptContent]);

  useEffect(() => {
    if (!externalContext?.recommendation_id) {
      return;
    }
    if (recommendations.some((item) => item.recommendation_id === externalContext.recommendation_id)) {
      setExpandedRecommendationId(externalContext.recommendation_id);
    }
  }, [externalContext?.recommendation_id, recommendations]);

  return (
    <section className="workspace-panel hook-studio-panel" aria-labelledby="hook-studio-title">
      <div className="workspace-panel__hero">
        <div>
          <h3 id="hook-studio-title">Hook 工作台</h3>
          <p>先定位类与函数，再在右侧查看详情并决定是否加入 Hook 计划。</p>
        </div>
        <div className="workspace-panel__actions">
          <button type="button" onClick={onClearHookPlan} disabled={hookPlanItems.length === 0}>
            清空 Hook 计划
          </button>
        </div>
      </div>
      {hookStudioMessage ? <p>{hookStudioMessage}</p> : null}
      {hookStudioError ? <p role="alert">{hookStudioError}</p> : null}
      {externalContext ? (
        <div className="detail-card hook-context-banner" aria-live="polite">
          <div>
            <strong>{externalContext.title}</strong>
            <p>{externalContext.summary}</p>
            <p>
              {externalContext.keywords.length > 0
                ? `已带入 ${localizeMethodScope(externalContext.suggested_scope)} 范围，关键词：${externalContext.keywords.join("、")}`
                : `已带入 ${localizeMethodScope(externalContext.suggested_scope)} 范围。`}
            </p>
            {externalContext.focused_method ? (
              <p>{`焦点函数：${externalContext.focused_method.class_name}.${externalContext.focused_method.method_name}`}</p>
            ) : null}
            {externalContext.recommendation_title ? <p>{`焦点推荐：${externalContext.recommendation_title}`}</p> : null}
          </div>
          <button type="button" className="button-ghost" onClick={onClearExternalContext}>
            收起提示
          </button>
        </div>
      ) : null}
      {methodIndexMessage ? <p>{methodIndexMessage}</p> : null}
      {isRefreshingMethodIndex ? (
        <section className="subsurface subsurface--nested" aria-label="方法索引重建状态">
          <div className="progress-card" aria-live="polite">
            <div className="progress-card__header">
              <strong>方法索引重建中</strong>
              <span>{Math.max(0, Math.min(100, Math.round(methodIndexProgress)))}%</span>
            </div>
            <div
              className="progress-card__track"
              aria-label="方法索引重建进度"
              aria-valuemax={100}
              aria-valuemin={0}
              aria-valuenow={Math.max(0, Math.min(100, Math.round(methodIndexProgress)))}
              role="progressbar"
            >
              <span
                className="progress-card__fill"
                style={{ width: `${Math.max(4, Math.min(100, methodIndexProgress))}%` }}
              />
            </div>
            <p>{methodIndexStageLabel ?? "正在整理可浏览的方法列表，请稍候。"}</p>
            <p className="progress-card__hint">如果超过 30 秒仍未完成，页面会自动提示你改用 JADX 或稍后再试。</p>
          </div>
        </section>
      ) : null}

      <div className="hook-studio__overview">
        <div className="stat-tile">
          <span>索引范围</span>
          <strong>{localizeMethodScope(methodScope)}</strong>
        </div>
        <div className="stat-tile">
          <span>类结果</span>
          <strong>{classBuckets.length} 个类</strong>
        </div>
        <div className="stat-tile">
          <span>方法命中</span>
          <strong>{methodTotal} 个</strong>
        </div>
        <div className="stat-tile">
          <span>当前类重载组</span>
          <strong>{activeClassName ? `${overloadGroupCount} 组` : "暂无"}</strong>
        </div>
      </div>

      <div className="hook-studio-workbench">
        <section className="subsurface hook-studio-pane hook-studio-pane--rail" aria-labelledby="method-browser-title">
          <div className="hook-studio-pane__header">
            <div>
              <h4 id="method-browser-title">函数导航</h4>
              <p>左侧只保留范围、检索和类树，减少首屏干扰。</p>
            </div>
          </div>
          <div className="scope-switch" aria-label="方法索引范围">
            {availableMethodScopes.map((scope) => (
              <button
                key={scope}
                type="button"
                className="scope-switch__item"
                aria-pressed={methodScope === scope}
                data-active={methodScope === scope ? "true" : undefined}
                onClick={() => onMethodScopeChange(scope)}
              >
                {localizeMethodScope(scope)}
              </button>
            ))}
          </div>
          <p className="compact-list__muted">{scopeDescription(methodScope)}</p>
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
                placeholder={hasMethodIndex ? "输入类名、方法名、签名、参数、标签或源码片段" : "没有方法索引可搜索"}
              />
            </label>
            <button type="submit" disabled={!hasMethodIndex}>
              搜索方法
            </button>
          </form>

          {!hasMethodIndex ? (
            <div className="empty-state">
              <p>当前没有可用的方法索引，无法浏览方法列表。</p>
              <p>
                旧案件在升级后可能仍未补出 JADX 源码，可先尝试重新构建一次方法索引；若要直接看源码，请到上方静态简报区打开 JADX。
              </p>
              <div className="button-row">
                <button type="button" className="button-secondary" onClick={onRefreshMethodIndex} disabled={isRefreshingMethodIndex}>
                  {isRefreshingMethodIndex ? "正在重建方法索引..." : "重新构建方法索引"}
                </button>
              </div>
            </div>
          ) : null}
          {searchError ? <p role="alert">{searchError}</p> : null}
          {isLoadingMethods ? <p>正在加载方法索引...</p> : null}
          <p className="compact-list__muted">
            当前范围：{localizeMethodScope(methodScope)} · 匹配 {methodTotal} 个方法
            {methodTotal > methods.length ? `，当前展示前 ${methods.length} 条` : ""}
          </p>
          <section className="class-browser class-browser--tree" aria-labelledby="class-browser-title">
            <div className="class-browser__header">
              <h5 id="class-browser-title">类树</h5>
              <span>{classBuckets.length} 个类</span>
            </div>
            {!isLoadingMethods && namespaceBuckets.length === 0 ? <p>暂无类结果。</p> : null}
            <div className="class-tree" role="tree" aria-label="类导航树">
              {namespaceBuckets.map((bucket) => {
                const containsActiveClass = bucket.classes.some((entry) => entry.className === activeClassName);
                return (
                  <details
                    key={bucket.namespace}
                    className="class-tree__section"
                    open={containsActiveClass || namespaceBuckets.length <= 4}
                  >
                    <summary className="class-tree__summary">
                      <strong>{bucket.namespace}</strong>
                      <span>{bucket.classes.length} 个类</span>
                    </summary>
                    <div className="class-tree__items">
                      {bucket.classes.map((classBucket) => (
                        <button
                          key={classBucket.className}
                          type="button"
                          className="class-browser__chip class-browser__chip--tree"
                          data-active={classBucket.className === activeClassName ? "true" : undefined}
                          onClick={() => onSelectMethod(classBucket.methods[0])}
                        >
                          <strong>{simpleClassName(classBucket.className)}</strong>
                          <span>{classBucket.count} 个方法</span>
                        </button>
                      ))}
                    </div>
                  </details>
                );
              })}
            </div>
          </section>
        </section>

        <section className="subsurface hook-studio-pane hook-studio-pane--main" aria-labelledby="method-groups-title">
          <div className="class-browser__summary" aria-label="当前类摘要">
            {activeClassName ? (
              <>
                <strong>{`当前类：${activeClassName}`}</strong>
                <span>{`当前类下共 ${activeClassMethods.length} 个方法入口，${overloadGroupCount} 组同名函数。`}</span>
              </>
            ) : (
              <>
                <strong>当前类：暂无</strong>
                <span>请先从左侧类树或搜索结果中选择一个类。</span>
              </>
            )}
          </div>

          <div className="method-groups" aria-labelledby="method-groups-title">
            <div className="method-groups__header">
              <div>
                <h4 id="method-groups-title">方法组</h4>
                <p>先看函数组摘要，再按需展开重载并选择具体函数。</p>
              </div>
              <span>{activeMethodGroups.length} 组结果</span>
            </div>
            {!isLoadingMethods && activeMethodGroups.length === 0 ? <p>暂无方法结果。</p> : null}
            {activeMethodGroups.map((group) => {
              const groupKey = methodGroupKey(group.methods[0]);
              return (
                <div
                  key={`${activeClassName ?? "all"}:${group.methodName}`}
                  className="method-group method-group--collapsible"
                  data-active={expandedMethodGroupKey === groupKey ? "true" : undefined}
                  aria-label={`${group.methodName} 方法组`}
                >
                  <div className="method-group__summary">
                    <div className="method-group__summary-copy">
                      <strong>{`${group.methods[0]?.is_constructor ? "构造方法" : group.methodName} · ${group.count} 个重载`}</strong>
                      <span>{group.methods[0]?.class_name}</span>
                    </div>
                    <button
                      type="button"
                      className="button-ghost"
                      aria-expanded={expandedMethodGroupKey === groupKey}
                      onClick={() => setExpandedMethodGroupKey((current) => (current === groupKey ? null : groupKey))}
                    >
                      {expandedMethodGroupKey === groupKey ? "收起重载" : "展开重载"}
                    </button>
                  </div>
                  {expandedMethodGroupKey === groupKey ? (
                    <ul className="compact-list compact-list--cards compact-list--narrow">
                      {group.methods.map((method, index) => (
                        <li
                          key={methodKey(method)}
                          data-selected={selectedMethod ? methodKey(selectedMethod) === methodKey(method) : undefined}
                        >
                          <strong>{formatMethodSignature(method)}</strong>
                          <span className="compact-list__muted">
                            {method.is_constructor ? "构造路径" : "函数入口"}
                            {group.count > 1 ? ` · 第 ${index + 1} 个重载` : ""}
                            {method.tags.length > 0 ? ` · ${method.tags[0]}` : ""}
                          </span>
                          <button type="button" onClick={() => onSelectMethod(method)}>
                            查看此函数
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>

        <section className="subsurface hook-studio-pane hook-studio-pane--detail" aria-labelledby="selected-method-title">
          <h4 id="selected-method-title">函数详情</h4>
          {!selectedMethod ? <p>先在中间的重载列表里选择一个函数，右侧才会展开完整声明、源码片段和 Hook 动作。</p> : null}
          {selectedMethod ? (
            <div className="method-detail" aria-label="选中函数详情">
              <div className="method-detail__hero">
                <strong>{selectedMethod.method_name}</strong>
                <span>{selectedMethod.class_name}</span>
              </div>
              <div className="button-row">
                <button type="button" onClick={() => onAddMethodToPlan(selectedMethod)}>
                  将当前函数加入 Hook 计划
                </button>
                <button
                  type="button"
                  className="button-ghost"
                  onClick={() =>
                    onInspectExecutionContext({
                      class_name: selectedMethod.class_name,
                      method_name: selectedMethod.method_name,
                    })
                  }
                >
                  查看相关执行事件
                </button>
                {isTrafficLinkedMethod(selectedMethod) ? (
                  <button
                    type="button"
                    className="button-ghost"
                    onClick={() =>
                      onInspectTrafficContext({
                        hint: `已根据 ${selectedMethod.class_name}.${selectedMethod.method_name} 回到流量证据，可继续核对 HTTPS 请求、证书状态和网络建议。`,
                        recommendationId: null,
                        recommendationTitle: null,
                      })
                    }
                  >
                    在流量证据查看网络摘要
                  </button>
                ) : null}
              </div>
              <dl className="method-detail__grid">
                <div>
                  <dt>完整类名</dt>
                  <dd>{selectedMethod.class_name}</dd>
                </div>
                <div>
                  <dt>函数名</dt>
                  <dd>{selectedMethod.method_name}</dd>
                </div>
                <div>
                  <dt>函数签名</dt>
                  <dd>{formatMethodSignature(selectedMethod)}</dd>
                </div>
                {selectedMethod.declaration ? (
                  <div>
                    <dt>反编译声明</dt>
                    <dd>
                      <code>{`反编译声明：${selectedMethod.declaration}`}</code>
                    </dd>
                  </div>
                ) : null}
                <div>
                  <dt>源码位置</dt>
                  <dd>
                    {selectedMethod.source_path}
                    {selectedMethod.line_hint ? ` · 第 ${selectedMethod.line_hint} 行` : ""}
                  </dd>
                </div>
                {selectedMethod.tags.length > 0 ? (
                  <div>
                    <dt>标签</dt>
                    <dd>{selectedMethod.tags.join("、")}</dd>
                  </div>
                ) : null}
                {selectedMethod.evidence.length > 0 ? (
                  <div>
                    <dt>线索</dt>
                    <dd>{selectedMethod.evidence.join("；")}</dd>
                  </div>
                ) : null}
                {selectedMethod.source_preview ? (
                  <div className="method-detail__preview">
                    <dt>源码片段</dt>
                    <dd>
                      <pre>{selectedMethod.source_preview}</pre>
                    </dd>
                  </div>
                ) : null}
              </dl>

              <section className="subsurface subsurface--nested method-detail__insight" aria-labelledby="method-insight-title">
                <h5 id="method-insight-title">联动摘要</h5>
                <div className="method-detail__insight-grid">
                  <article className="detail-card" aria-label="执行联动摘要">
                    <strong>执行结果</strong>
                    {methodInsight?.execution ? (
                      <>
                        <p>{`关联事件：${methodInsight.execution.related_event_count} 条`}</p>
                        <p>
                          {`最近状态：${localizeExecutionInsightStatus(
                            methodInsight.execution.latest_status,
                            methodInsight.execution.latest_event_type,
                          )}`}
                        </p>
                        {methodInsight.execution.latest_timestamp ? (
                          <p>{`最近时间：${methodInsight.execution.latest_timestamp}`}</p>
                        ) : null}
                        {methodInsight.execution.latest_message ? (
                          <p>{`最近说明：${methodInsight.execution.latest_message}`}</p>
                        ) : null}
                        {methodInsight.execution.latest_arguments.length > 0 ? (
                          <p>{`最近参数：${methodInsight.execution.latest_arguments.join("、")}`}</p>
                        ) : null}
                        {methodInsight.execution.latest_return_value ? (
                          <p>{`最近返回：${methodInsight.execution.latest_return_value}`}</p>
                        ) : null}
                        {methodInsight.execution.latest_stack_preview ? (
                          <p>{`堆栈摘要：${methodInsight.execution.latest_stack_preview}`}</p>
                        ) : null}
                        {methodInsight.execution.failure_code ? (
                          <p>{`最近失败分类：${localizeExecutionFailureCode(methodInsight.execution.failure_code)}`}</p>
                        ) : null}
                        {methodInsight.execution.failure_message ? (
                          <p>{`最近失败原因：${methodInsight.execution.failure_message}`}</p>
                        ) : null}
                      </>
                    ) : (
                      <p>当前还没有命中这一个函数的执行事件。可以先运行 Hook，再回到这里核对参数、返回值和堆栈。</p>
                    )}
                  </article>

                  <article className="detail-card" aria-label="流量联动摘要">
                    <strong>流量摘要</strong>
                    {methodInsight?.traffic ? (
                      <>
                        <p>{`流量来源：${methodInsight.traffic.source_label ?? "暂无"}`}</p>
                        <p>
                          {`当前流量：${methodInsight.traffic.flow_count} 条，可疑 ${methodInsight.traffic.suspicious_count} 条${
                            methodInsight.traffic.https_flow_count !== null
                              ? `，HTTPS ${methodInsight.traffic.https_flow_count} 条`
                              : ""
                          }`}
                        </p>
                        {methodInsight.traffic.preview_count !== null ? (
                          <p>{`实时预览：${methodInsight.traffic.preview_count} 条`}</p>
                        ) : null}
                        {methodInsight.traffic.top_host_summary ? (
                          <p>{`主机摘要：${methodInsight.traffic.top_host_summary}`}</p>
                        ) : null}
                        {methodInsight.traffic.suspicious_host_summary ? (
                          <p>{`可疑主机：${methodInsight.traffic.suspicious_host_summary}`}</p>
                        ) : null}
                        {methodInsight.traffic.matched_flow_label ? (
                          <p>{`命中流量：${methodInsight.traffic.matched_flow_label}`}</p>
                        ) : null}
                        {methodInsight.traffic.matched_flow_reason ? (
                          <p>{`对照理由：${methodInsight.traffic.matched_flow_reason}`}</p>
                        ) : null}
                        {methodInsight.traffic.guidance_summary ? (
                          <p>{`SSL 建议：${methodInsight.traffic.guidance_summary}`}</p>
                        ) : null}
                      </>
                    ) : (
                      <p>当前还没有可用于对照的流量摘要。可先导入 HAR 或启动实时抓包，再回来对照函数行为。</p>
                    )}
                  </article>
                </div>
              </section>
            </div>
          ) : null}

          <section className="subsurface subsurface--nested" aria-labelledby="recommendations-title">
            <h5 id="recommendations-title">离线推荐</h5>
            <p>推荐区现在只做辅助，不再压过函数浏览主线。</p>
            {recommendationsError ? <p role="alert">{recommendationsError}</p> : null}
            {isLoadingRecommendations ? <p>正在加载离线推荐...</p> : null}
            <ul className="compact-list compact-list--cards" aria-label="离线推荐列表">
              {!isLoadingRecommendations && recommendations.length === 0 ? <li>暂无离线推荐。</li> : null}
              {recommendations.map((item) => (
                <li
                  key={item.recommendation_id}
                  data-active={externalContext?.recommendation_id === item.recommendation_id ? "true" : undefined}
                >
                  <strong>{item.title}</strong>
                  <span>类型：{localizeRecommendationKind(item.kind)} · 评分：{item.score}</span>
                  <span>{item.method ? `${item.method.method_name} · ${item.method.class_name}` : item.template_name ?? "点击查看推荐详情"}</span>
                  <div className="button-row">
                    <button
                      type="button"
                      className="button-ghost"
                      aria-expanded={expandedRecommendationId === item.recommendation_id}
                      onClick={() =>
                        setExpandedRecommendationId((current) =>
                          current === item.recommendation_id ? null : item.recommendation_id,
                        )
                      }
                    >
                      {expandedRecommendationId === item.recommendation_id ? "收起详情" : "查看推荐详情"}
                    </button>
                    <button type="button" onClick={() => onAddRecommendationToPlan(item.recommendation_id)}>
                      接受推荐并加入 Hook 计划
                    </button>
                    {isTrafficLinkedRecommendation(item) ? (
                      <button
                        type="button"
                        className="button-ghost"
                        onClick={() =>
                          onInspectTrafficContext({
                            hint: `已根据 ${item.title} 回到流量证据，可继续核对当前抓包摘要、代理/证书准备度和 SSL 联动建议。`,
                            recommendationId: item.recommendation_id,
                            recommendationTitle: item.title,
                          })
                        }
                      >
                        在流量证据查看网络摘要
                      </button>
                    ) : null}
                  </div>
                  {expandedRecommendationId === item.recommendation_id ? (
                    <div className="detail-card">
                      <p>{item.reason}</p>
                      {item.method ? (
                        <p>
                          方法：{item.method.class_name}.{item.method.method_name} · {formatMethodSignature(item.method)}
                        </p>
                      ) : null}
                      {item.template_name ? <p>模板：{item.template_name}</p> : null}
                      {item.matched_terms.length > 0 ? <p>命中词：{item.matched_terms.join("、")}</p> : null}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        </section>
      </div>

      <div className="panel-grid panel-grid--balanced">
        <details
          className="brief-disclosure"
          open={isHookPlanSectionOpen}
          onToggle={(event) => setIsHookPlanSectionOpen((event.currentTarget as HTMLDetailsElement).open)}
        >
          <summary id="hook-plan-title">Hook 计划与渲染脚本</summary>
          <div className="brief-disclosure__content">
            <p>主舞台先负责找函数，这里再集中处理注入顺序、启停与渲染脚本预览。</p>
            {hookPlanError ? <p role="alert">{hookPlanError}</p> : null}
            {isLoadingHookPlan ? <p>正在加载 Hook 计划...</p> : null}
            <ul className="compact-list compact-list--cards" aria-label="Hook 计划列表">
              {!isLoadingHookPlan && hookPlanItems.length === 0 ? <li>当前还没有 Hook 计划项。</li> : null}
              {hookPlanItems.map((item, index) => (
                <li key={item.item_id}>
                  <strong>{planTitle(item)}</strong>
                  <span>类型：{localizePlanKind(item.kind)}</span>
                  <span>状态：{localizePlanStatus(item.enabled)}</span>
                  <span>
                    {item.method
                      ? `${item.method.method_name} · ${item.method.class_name}`
                      : item.template_name
                        ? `模板 · ${item.template_name}`
                        : item.script_name
                          ? `脚本 · ${item.script_name}`
                          : "点击查看详情"}
                  </span>
                  <div className="button-row">
                    <button
                      type="button"
                      className="button-ghost"
                      aria-expanded={expandedPlanItemId === item.item_id}
                      onClick={() => setExpandedPlanItemId((current) => (current === item.item_id ? null : item.item_id))}
                    >
                      {expandedPlanItemId === item.item_id ? "收起详情" : "查看详情"}
                    </button>
                    <button
                      type="button"
                      aria-label={`上移 ${planTitle(item)}`}
                      onClick={() => onMoveHookPlanItem(item.item_id, "up")}
                      disabled={index === 0}
                    >
                      上移
                    </button>
                    <button
                      type="button"
                      aria-label={`下移 ${planTitle(item)}`}
                      onClick={() => onMoveHookPlanItem(item.item_id, "down")}
                      disabled={index === hookPlanItems.length - 1}
                    >
                      下移
                    </button>
                    <button
                      type="button"
                      aria-label={`${item.enabled ? "禁用" : "启用"} ${planTitle(item)}`}
                      onClick={() => onSetHookPlanItemEnabled(item.item_id, !item.enabled)}
                    >
                      {item.enabled ? "禁用" : "启用"}
                    </button>
                    <button type="button" onClick={() => onRemoveHookPlanItem(item.item_id)}>
                      移除计划项
                    </button>
                  </div>
                  {expandedPlanItemId === item.item_id ? (
                    <div className="detail-card">
                      {item.method ? (
                        <p>
                          目标方法：{item.method.class_name}.{item.method.method_name} · {formatMethodSignature(item.method)}
                        </p>
                      ) : null}
                      {item.template_name ? <p>模板：{item.template_name}</p> : null}
                      {item.script_name ? <p>脚本：{item.script_name}</p> : null}
                      {item.plugin_id ? <p>来源：{item.plugin_id}</p> : null}
                      <details>
                        <summary>查看渲染脚本预览</summary>
                        <pre>{item.rendered_script}</pre>
                      </details>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        </details>

        <details
          className="brief-disclosure"
          open={isCustomScriptSectionOpen}
          onToggle={(event) => setIsCustomScriptSectionOpen((event.currentTarget as HTMLDetailsElement).open)}
        >
          <summary id="custom-script-title">自定义脚本资产</summary>
          <div className="brief-disclosure__content">
            <p>当自动推荐不够时，再进入这里编写、保存、切换并插入自己的 Frida 脚本。</p>
            {customScriptsError ? <p role="alert">{customScriptsError}</p> : null}
            <div className="panel-grid panel-grid--balanced">
              <section className="subsurface subsurface--nested" aria-labelledby="custom-script-editor-title">
                <h5 id="custom-script-editor-title">脚本编辑器</h5>
                <div className="button-row">
                  <button type="button" onClick={onCreateCustomScriptDraft}>
                    新建空白脚本
                  </button>
                  <button type="button" onClick={onSaveCustomScript} disabled={isSavingCustomScript}>
                    {isSavingCustomScript ? "正在保存..." : selectedCustomScriptId ? "更新脚本" : "保存脚本"}
                  </button>
                </div>
                <label>
                  脚本名称
                  <input
                    aria-label="脚本名称"
                    type="text"
                    value={draftScriptName}
                    onChange={(event) => onDraftScriptNameChange(event.target.value)}
                    placeholder="例如：登录口令旁路监控"
                  />
                </label>
                <label>
                  脚本内容
                  <textarea
                    aria-label="脚本内容"
                    value={draftScriptContent}
                    onChange={(event) => onDraftScriptContentChange(event.target.value)}
                    rows={8}
                    placeholder="输入自定义 Frida 脚本内容"
                  />
                </label>
              </section>

              <section className="subsurface subsurface--nested" aria-labelledby="custom-script-library-title">
                <h5 id="custom-script-library-title">脚本库</h5>
                <ul className="compact-list compact-list--cards" aria-label="自定义脚本列表">
                  {customScripts.length === 0 ? <li>当前还没有自定义脚本。</li> : null}
                  {customScripts.map((script) => (
                    <li key={script.script_id}>
                      <strong>{script.name}</strong>
                      <span>{script.script_path}</span>
                      <div className="button-row">
                        <button
                          type="button"
                          className="button-ghost"
                          aria-expanded={expandedScriptId === script.script_id}
                          onClick={() => setExpandedScriptId((current) => (current === script.script_id ? null : script.script_id))}
                        >
                          {expandedScriptId === script.script_id ? "收起详情" : "查看详情"}
                        </button>
                        <button type="button" onClick={() => onLoadCustomScript(script.script_id)} disabled={isLoadingCustomScript}>
                          {isLoadingCustomScript && selectedCustomScriptId === script.script_id ? "正在加载..." : "加载到编辑器"}
                        </button>
                      </div>
                      {expandedScriptId === script.script_id ? (
                        <div className="detail-card">
                          {selectedCustomScriptId === script.script_id ? <p>当前正在编辑该脚本。</p> : null}
                          <div className="button-row">
                            <button type="button" onClick={() => onAddCustomScriptToPlan(script.script_id)}>
                              将脚本加入 Hook 计划
                            </button>
                            <button
                              type="button"
                              onClick={() => onDeleteCustomScript(script.script_id)}
                              disabled={isDeletingCustomScript}
                            >
                              {isDeletingCustomScript && selectedCustomScriptId === script.script_id ? "正在删除..." : "删除脚本"}
                            </button>
                          </div>
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        </details>
      </div>
    </section>
  );
}
