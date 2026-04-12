import type { EnvironmentPresetStatus, EnvironmentToolStatus, WorkspaceEvent } from "../../lib/types";

type ExecutionConsolePanelProps = {
  environmentError: string | null;
  environmentSummary: string | null;
  executionPresets: EnvironmentPresetStatus[];
  events: WorkspaceEvent[];
  isLoadingEnvironment: boolean;
  isStarting: boolean;
  onExecutionModeChange: (value: string) => void;
  onStart: () => void;
  recommendedExecutionMode: string | null;
  selectedExecutionMode: string;
  startDisabled: boolean;
  statusText: string;
  tools: EnvironmentToolStatus[];
};

function localizeExecutionStatus(statusText: string): string {
  switch (statusText) {
    case "idle":
      return "待执行";
    case "started":
      return "已启动";
    case "error":
      return "执行失败";
    default:
      return statusText;
  }
}

function localizeEventType(type: string): string {
  switch (type) {
    case "execution.started":
      return "执行已启动";
    case "workspace.events.error":
      return "事件流异常";
    default:
      return type;
  }
}

function localizeEnvironmentSummary(summary: string | null, tools: EnvironmentToolStatus[]): string {
  if (!summary) {
    return "暂无环境信息";
  }

  const readyCount = tools.filter((tool) => tool.available).length;
  const missingCount = tools.length - readyCount;
  return `已就绪 ${readyCount} 项，缺失 ${missingCount} 项`;
}

function localizePresetLabel(key: string, fallback: string): string {
  switch (key) {
    case "fake_backend":
      return "模拟执行";
    case "real_device":
      return "真实设备";
    case "real_adb_probe":
      return "ADB 探测";
    case "real_frida_bootstrap":
      return "Frida 自举";
    case "real_frida_probe":
      return "Frida 探测";
    case "real_frida_inject":
      return "Frida 注入";
    case "real_frida_session":
      return "Frida 会话";
    default:
      return fallback;
  }
}

function localizePresetDetail(detail: string): string {
  if (detail === "ready") {
    return "就绪";
  }

  const readyMatch = /^ready \((.+)\)$/.exec(detail);
  if (readyMatch) {
    return `就绪（${localizePresetLabelFromEnglish(readyMatch[1])}）`;
  }

  const missingMatch = /^unavailable \(missing (.+)\)$/.exec(detail);
  if (missingMatch) {
    return `不可用（缺少 ${missingMatch[1]}）`;
  }

  if (detail === "unavailable (not configured)") {
    return "不可用（未配置）";
  }

  if (detail === "unavailable (no ready backend)") {
    return "不可用（没有可用后端）";
  }

  return detail;
}

function localizePresetLabelFromEnglish(label: string): string {
  switch (label) {
    case "Fake Backend":
      return "模拟执行";
    case "Real Device":
      return "真实设备";
    case "ADB Probe":
      return "ADB 探测";
    case "Frida Bootstrap":
      return "Frida 自举";
    case "Frida Probe":
      return "Frida 探测";
    case "Frida Inject":
      return "Frida 注入";
    case "Frida Session":
      return "Frida 会话";
    default:
      return label;
  }
}

function localizeRecommendedPreset(key: string | null): string {
  if (!key) {
    return "暂无";
  }

  return localizePresetLabel(key, key);
}

export function ExecutionConsolePanel({
  environmentError,
  environmentSummary,
  executionPresets,
  events,
  isLoadingEnvironment,
  isStarting,
  onExecutionModeChange,
  onStart,
  recommendedExecutionMode,
  selectedExecutionMode,
  startDisabled,
  statusText,
  tools,
}: ExecutionConsolePanelProps): JSX.Element {
  return (
    <section aria-labelledby="execution-console-title">
      <h3 id="execution-console-title">执行控制台</h3>
      <p>触发案件执行，并查看最小实时事件流。</p>
      {isLoadingEnvironment ? <p>正在检查执行环境...</p> : null}
      {environmentError ? <p>执行环境暂时不可用，请稍后重试。</p> : null}
      {!isLoadingEnvironment && !environmentError ? (
        <>
          <p>环境概览：{localizeEnvironmentSummary(environmentSummary, tools)}</p>
          <p>推荐预设：{localizeRecommendedPreset(recommendedExecutionMode)}</p>
          <label>
            执行预设
            <select
              aria-label="执行预设"
              value={selectedExecutionMode}
              onChange={(event) => onExecutionModeChange(event.target.value)}
            >
              {executionPresets.map((preset) => (
                <option key={preset.key} value={preset.key} disabled={!preset.available}>
                  {localizePresetLabel(preset.key, preset.label)} · {localizePresetDetail(preset.detail)}
                </option>
              ))}
            </select>
          </label>
          <ul aria-label="执行预设状态">
            {executionPresets.length === 0 ? <li>暂无执行预设信息。</li> : null}
            {executionPresets.map((preset) => (
              <li key={preset.key}>
                {localizePresetLabel(preset.key, preset.label)}：{localizePresetDetail(preset.detail)}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <p>当前状态：{localizeExecutionStatus(statusText)}</p>
      <button type="button" onClick={onStart} disabled={startDisabled}>
        {isStarting ? "正在启动..." : "启动执行"}
      </button>
      <ul aria-label="执行事件流">
        {events.length === 0 ? <li>暂无执行事件。</li> : null}
        {events.map((event, index) => (
          <li key={`${event.type}-${event.timestamp ?? "no-ts"}-${index}`}>
            <strong>{localizeEventType(event.type)}</strong>
            {event.status ? ` · ${localizeExecutionStatus(event.status)}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
