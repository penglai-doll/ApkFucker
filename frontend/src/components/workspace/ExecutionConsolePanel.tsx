import type {
  ConnectedDeviceSummary,
  ExecutionConsoleExternalContext,
  EnvironmentPresetStatus,
  EnvironmentToolStatus,
  ExecutionHistoryEntry,
  RuntimeSettings,
  WorkspaceEvent,
} from "../../lib/types";
import { localizeExecutionFailureCode } from "../../lib/executionDiagnostics";

type ExecutionConsolePanelProps = {
  cancelDisabled: boolean;
  executedBackendKey: string | null;
  environmentError: string | null;
  environmentSummary: string | null;
  externalContext: ExecutionConsoleExternalContext | null;
  executionHistory: ExecutionHistoryEntry[];
  executionPresets: EnvironmentPresetStatus[];
  executionPreflightDetail: string | null;
  executionPreflightReady: boolean | null;
  events: WorkspaceEvent[];
  executionStageText: string | null;
  failureCode: string | null;
  failureMessage: string | null;
  historyReplayMessage: string | null;
  isLoadingEnvironment: boolean;
  isLoadingExecutionHistory: boolean;
  isLoadingExecutionPreflight: boolean;
  isCancelling: boolean;
  isStarting: boolean;
  isSavingRuntimeSettings: boolean;
  onCancel: () => void;
  onClearExternalContext: () => void;
  onExecutionModeChange: (value: string) => void;
  onInspectHookContext: (event: WorkspaceEvent) => void;
  onPickFridaServerBinary: () => void;
  onReplayExecutionHistory: (historyId: string) => void;
  onRuntimeSettingChange: (field: keyof RuntimeSettings, value: string) => void;
  onSaveRuntimeSettings: () => void;
  onStart: () => void;
  requestedExecutionMode: string | null;
  recommendedExecutionMode: string | null;
  runtimeSettings: RuntimeSettings;
  runtimeSettingsError: string | null;
  runtimeSettingsMessage: string | null;
  selectedExecutionMode: string;
  startBlockedReason: string | null;
  startDisabled: boolean;
  statusText: string;
  connectedDevices: ConnectedDeviceSummary[];
  recommendedDeviceSerial: string | null;
  tools: EnvironmentToolStatus[];
};

function localizeExecutionStatus(statusText: string): string {
  switch (statusText) {
    case "idle":
      return "待执行";
    case "started":
      return "已启动";
    case "cancelling":
      return "正在取消";
    case "completed":
      return "已完成";
    case "cancelled":
      return "已取消";
    case "error":
      return "执行失败";
    default:
      return statusText;
  }
}

function localizeExecutionStage(stageText: string | null): string {
  switch (stageText) {
    case null:
    case "":
      return "暂无";
    case "queued":
      return "已排队";
    case "executing":
      return "执行中";
    case "persisting":
      return "正在落盘";
    case "cancelling":
      return "正在取消";
    case "cancelled":
      return "已取消";
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    default:
      return stageText;
  }
}

function localizeEventType(type: string): string {
  switch (type) {
    case "execution.started":
      return "执行已启动";
    case "execution.progress":
      return "执行进度";
    case "execution.cancelling":
      return "执行正在取消";
    case "execution.cancelled":
      return "执行已取消";
    case "execution.completed":
      return "执行已完成";
    case "execution.failed":
      return "执行失败";
    case "execution.event":
      return "执行日志";
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

function formatEventTimestamp(timestamp: string | undefined): string | null {
  if (!timestamp) {
    return null;
  }

  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) {
    return timestamp;
  }

  return parsed.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function extractExecutionMethodRef(event: WorkspaceEvent): { class_name: string; method_name: string } | null {
  const className = event.payload?.class_name;
  const methodName = event.payload?.method_name;
  if (typeof className !== "string" || typeof methodName !== "string") {
    return null;
  }
  if (className.trim().length === 0 || methodName.trim().length === 0) {
    return null;
  }
  return {
    class_name: className,
    method_name: methodName,
  };
}

function matchesExecutionContext(
  event: WorkspaceEvent,
  externalContext: ExecutionConsoleExternalContext | null,
): boolean {
  if (!externalContext) {
    return false;
  }
  const methodRef = extractExecutionMethodRef(event);
  if (!methodRef) {
    return false;
  }
  return (
    methodRef.class_name === externalContext.class_name && methodRef.method_name === externalContext.method_name
  );
}

function summarizeExecutionPreflight(
  ready: boolean | null,
  detail: string | null,
  isLoading: boolean,
): string {
  if (isLoading) {
    return "正在检查";
  }
  if (ready === null) {
    return "暂无检查结果";
  }
  if (ready) {
    return detail && detail.length > 0 ? `已就绪 · ${detail}` : "已就绪";
  }
  return detail && detail.length > 0 ? `未就绪 · ${detail}` : "未就绪";
}

function summarizeRuntimeSettings(runtimeSettings: RuntimeSettings): string {
  const configured: string[] = [];
  if (runtimeSettings.device_serial.trim()) {
    configured.push("设备序列号");
  }
  if (runtimeSettings.frida_server_binary_path.trim()) {
    configured.push("Frida Server");
  }
  if (runtimeSettings.frida_server_remote_path.trim()) {
    configured.push("远端路径");
  }
  if (runtimeSettings.frida_session_seconds.trim()) {
    configured.push("会话时长");
  }

  if (configured.length === 0) {
    return "暂未配置";
  }
  if (configured.length === 1) {
    return `已配置 · ${configured[0]}`;
  }
  return `已配置 · ${configured[0]} 等 ${configured.length} 项`;
}

function localizeDeviceStatus(status: string | null | undefined): string {
  switch (status) {
    case null:
    case undefined:
    case "":
      return "未提供状态";
    case "ready":
    case "available":
    case "connected":
    case "online":
      return "已连接";
    case "selected":
      return "已选中";
    case "unauthorized":
      return "未授权";
    case "offline":
      return "已离线";
    case "bootloader":
      return "引导模式";
    case "recovery":
      return "恢复模式";
    default:
      return status;
  }
}

function formatConnectedDevice(device: ConnectedDeviceSummary): string {
  const pieces = [device.label, device.serial];
  if (device.model && device.model !== device.label) {
    pieces.push(device.model);
  }
  return pieces.filter(Boolean).join(" · ");
}

function summarizeSelectedDevice(
  deviceSerial: string,
  connectedDevices: ConnectedDeviceSummary[],
  recommendedDeviceSerial: string | null,
): string {
  const trimmedSerial = deviceSerial.trim();
  if (!trimmedSerial) {
    if (recommendedDeviceSerial) {
      const recommendedDevice = connectedDevices.find((device) => device.serial === recommendedDeviceSerial);
      return recommendedDevice ? `已预选 ${recommendedDevice.label}` : `已预选 ${recommendedDeviceSerial}`;
    }
    return "未选设备";
  }

  const selectedDevice = connectedDevices.find((device) => device.serial === trimmedSerial);
  if (selectedDevice) {
    return `当前设备：${selectedDevice.label}`;
  }

  return `手动序列号：${trimmedSerial}`;
}

export function ExecutionConsolePanel({
  cancelDisabled,
  executedBackendKey,
  environmentError,
  environmentSummary,
  externalContext,
  executionHistory,
  executionPresets,
  executionPreflightDetail,
  executionPreflightReady,
  events,
  executionStageText,
  failureCode,
  failureMessage,
  historyReplayMessage,
  isLoadingEnvironment,
  isLoadingExecutionHistory,
  isLoadingExecutionPreflight,
  isCancelling,
  isStarting,
  isSavingRuntimeSettings,
  onCancel,
  onClearExternalContext,
  onExecutionModeChange,
  onInspectHookContext,
  onPickFridaServerBinary,
  onReplayExecutionHistory,
  onRuntimeSettingChange,
  onSaveRuntimeSettings,
  onStart,
  requestedExecutionMode,
  recommendedExecutionMode,
  runtimeSettings,
  runtimeSettingsError,
  runtimeSettingsMessage,
  selectedExecutionMode,
  startBlockedReason,
  startDisabled,
  statusText,
  connectedDevices,
  recommendedDeviceSerial,
  tools,
}: ExecutionConsolePanelProps): JSX.Element {
  const localizedStatus = localizeExecutionStatus(statusText);
  const localizedStage = localizeExecutionStage(executionStageText);
  const localizedRequestedMode = requestedExecutionMode
    ? localizePresetLabel(requestedExecutionMode, requestedExecutionMode)
    : "暂无";
  const localizedExecutedBackend = executedBackendKey
    ? localizePresetLabel(executedBackendKey, executedBackendKey)
    : "暂无";
  const readyPresetCount = executionPresets.filter((preset) => preset.available).length;
  const executionHistoryCount = executionHistory.length;
  const eventCount = events.length;
  const failureSummary = failureCode ? localizeExecutionFailureCode(failureCode) : "暂无";
  const preflightSummary = summarizeExecutionPreflight(
    executionPreflightReady,
    executionPreflightDetail,
    isLoadingExecutionPreflight,
  );
  const runtimeSettingsSummary = summarizeRuntimeSettings(runtimeSettings);
  const effectiveDeviceSerial =
    runtimeSettings.device_serial.trim() || recommendedDeviceSerial || connectedDevices[0]?.serial || "";
  const selectedConnectedDevice = connectedDevices.find((device) => device.serial === effectiveDeviceSerial);
  const selectedDeviceSummary = summarizeSelectedDevice(
    effectiveDeviceSerial,
    connectedDevices,
    recommendedDeviceSerial,
  );
  const deviceSelectionPrompt =
    connectedDevices.length > 0
      ? "可以从下拉列表选择已连接设备，或者保留下面的手动序列号兜底。"
      : "当前还没有可用设备列表，请先手动填写设备序列号。";

  return (
    <section className="workspace-panel execution-console-panel" aria-labelledby="execution-console-title">
      <div className="workspace-panel__hero">
        <div>
          <h3 id="execution-console-title">执行控制台</h3>
          <p>触发案件执行、检查环境，并在同一视图里追踪当前阶段与最近历史。</p>
        </div>
        <div className="workspace-panel__actions">
          <button type="button" className="button-primary" onClick={onStart} disabled={startDisabled}>
            {isStarting ? "正在启动..." : "启动执行"}
          </button>
          <button type="button" className="button-secondary" onClick={onCancel} disabled={cancelDisabled}>
            {isCancelling ? "正在取消..." : "取消执行"}
          </button>
        </div>
      </div>
      {startBlockedReason ? (
        <div className="execution-console__notice" role="status">
          <strong>当前无法启动执行</strong>
          <p>{startBlockedReason}</p>
          {startBlockedReason.includes("Hook 计划") ? (
            <a className="button-ghost" href="#hook-studio-section">
              前往 Hook 工作台添加计划项
            </a>
          ) : null}
        </div>
      ) : null}
      {externalContext ? (
        <div className="detail-card hook-context-banner" aria-live="polite">
          <div>
            <strong>{externalContext.title}</strong>
            <p>{externalContext.summary}</p>
            <p>{`焦点函数：${externalContext.class_name}.${externalContext.method_name}`}</p>
          </div>
          <button type="button" className="button-ghost" onClick={onClearExternalContext}>
            收起提示
          </button>
        </div>
      ) : null}

      <div className="metric-grid metric-grid--four" aria-label="执行概览">
        <div className="stat-tile">
          <span>当前状态</span>
          <strong>{localizedStatus}</strong>
        </div>
        <div className="stat-tile">
          <span>当前阶段</span>
          <strong>{localizedStage}</strong>
        </div>
        <div className="stat-tile">
          <span>请求模式</span>
          <strong>{localizedRequestedMode}</strong>
        </div>
        <div className="stat-tile">
          <span>实际后端</span>
          <strong>{localizedExecutedBackend}</strong>
        </div>
      </div>
      <div className="execution-console__summary-row" aria-label="执行控制台摘要">
        <span>执行前检查：{preflightSummary}</span>
        <span>执行预设：可用 {readyPresetCount} 个</span>
        <span>执行历史：{executionHistoryCount} 次</span>
        <span>最近失败：{failureSummary}</span>
      </div>

      {isLoadingEnvironment ? <p>正在检查执行环境...</p> : null}
      {environmentError ? <p>执行环境暂时不可用，请稍后重试。</p> : null}
      <div className="brief-disclosure-list">
        {!isLoadingEnvironment && !environmentError ? (
          <details className="brief-disclosure" open>
            <summary>环境与预设 · {localizeEnvironmentSummary(environmentSummary, tools)} · 推荐 {localizeRecommendedPreset(recommendedExecutionMode)}</summary>
            <div className="brief-disclosure__content">
              <div className="panel-grid panel-grid--balanced">
                <section className="subsurface subsurface--nested" aria-labelledby="execution-environment-title">
                  <h4 id="execution-environment-title">环境与预设</h4>
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
                  <ul className="compact-list" aria-label="执行预设状态">
                    {executionPresets.length === 0 ? <li>暂无执行预设信息。</li> : null}
                    {executionPresets.map((preset) => (
                      <li key={preset.key}>
                        <strong>{localizePresetLabel(preset.key, preset.label)}</strong>
                        <span>{localizePresetDetail(preset.detail)}</span>
                      </li>
                    ))}
                  </ul>
                </section>
                <section className="subsurface subsurface--nested" aria-labelledby="execution-preflight-title">
                  <h4 id="execution-preflight-title">执行前检查</h4>
                  <p>{preflightSummary}</p>
                  {failureCode ? <p>失败分类：{localizeExecutionFailureCode(failureCode)}</p> : <p>失败分类：暂无</p>}
                  {failureMessage ? <p>失败原因：{failureMessage}</p> : <p>失败原因：暂无</p>}
                </section>
              </div>
            </div>
          </details>
        ) : null}

        <details className="brief-disclosure">
          <summary>真实设备运行参数 · {runtimeSettingsSummary} · {selectedDeviceSummary}</summary>
          <div className="brief-disclosure__content">
            <div className="detail-card">
              <strong>当前设备摘要</strong>
              <p>{selectedDeviceSummary}</p>
              <p>状态：{selectedConnectedDevice ? localizeDeviceStatus(selectedConnectedDevice.status) : "未选设备"}</p>
              <p>设备列表：{connectedDevices.length > 0 ? `已识别 ${connectedDevices.length} 台` : "暂无可用设备"}</p>
              {selectedConnectedDevice?.detail ? <p>说明：{selectedConnectedDevice.detail}</p> : null}
              <p>{deviceSelectionPrompt}</p>
            </div>
            <fieldset className="workspace-panel__fieldset workspace-panel__fieldset--compact">
              <legend>真实设备运行参数</legend>
              <p>这些参数会用于下一次真实设备执行，也可以单独保存到本地。</p>
              <div className="form-grid form-grid--two">
                <label>
                  真实设备列表
                  <select
                    aria-label="真实设备列表"
                    value={effectiveDeviceSerial}
                    onChange={(event) => onRuntimeSettingChange("device_serial", event.target.value)}
                    disabled={connectedDevices.length === 0}
                  >
                    <option value="">{connectedDevices.length > 0 ? "请选择真实设备" : "暂无可用设备"}</option>
                    {connectedDevices.map((device) => (
                      <option key={device.serial} value={device.serial}>
                        {formatConnectedDevice(device)}
                        {device.status ? ` · ${localizeDeviceStatus(device.status)}` : ""}
                      </option>
                    ))}
                    {runtimeSettings.device_serial.trim() &&
                    !connectedDevices.some((device) => device.serial === runtimeSettings.device_serial.trim()) ? (
                      <option value={runtimeSettings.device_serial.trim()}>
                        手动输入 · {runtimeSettings.device_serial.trim()}
                      </option>
                    ) : null}
                  </select>
                </label>
                <label>
                  设备序列号
                  <input
                    aria-label="设备序列号"
                    type="text"
                    value={runtimeSettings.device_serial}
                    placeholder="例如：emulator-5554（兜底）"
                    onChange={(event) => onRuntimeSettingChange("device_serial", event.target.value)}
                  />
                </label>
                <label>
                  远端路径
                  <input
                    aria-label="远端路径"
                    type="text"
                    value={runtimeSettings.frida_server_remote_path}
                    placeholder="例如：/data/local/tmp/frida-server"
                    onChange={(event) => onRuntimeSettingChange("frida_server_remote_path", event.target.value)}
                  />
                </label>
                <label>
                  Frida Server 文件
                  <input
                    aria-label="Frida Server 文件"
                    type="text"
                    value={runtimeSettings.frida_server_binary_path}
                    placeholder="例如：/opt/frida-server"
                    onChange={(event) => onRuntimeSettingChange("frida_server_binary_path", event.target.value)}
                  />
                </label>
                <label>
                  会话时长（秒）
                  <input
                    aria-label="会话时长（秒）"
                    type="text"
                    value={runtimeSettings.frida_session_seconds}
                    placeholder="例如：3.5"
                    onChange={(event) => onRuntimeSettingChange("frida_session_seconds", event.target.value)}
                  />
                </label>
              </div>
              <div className="button-row">
                <button type="button" onClick={onPickFridaServerBinary}>
                  选择 Frida Server 文件
                </button>
                <button type="button" onClick={onSaveRuntimeSettings} disabled={isSavingRuntimeSettings}>
                  {isSavingRuntimeSettings ? "正在保存..." : "保存运行参数"}
                </button>
              </div>
              {runtimeSettingsMessage ? <p>{runtimeSettingsMessage}</p> : null}
              {runtimeSettingsError ? <p>{runtimeSettingsError}</p> : null}
            </fieldset>
          </div>
        </details>

        <details className="brief-disclosure">
          <summary>执行历史与事件 · 历史 {executionHistoryCount} 次 · 最近 {eventCount} 条事件</summary>
          <div className="brief-disclosure__content">
            <div className="panel-grid panel-grid--balanced">
              <section className="subsurface subsurface--nested" aria-labelledby="execution-history-title">
                <h4 id="execution-history-title">执行历史</h4>
                {historyReplayMessage ? <p>{historyReplayMessage}</p> : null}
                {isLoadingExecutionHistory ? <p>正在加载执行历史...</p> : null}
                <ul className="compact-list compact-list--cards" aria-label="执行历史列表">
                  {!isLoadingExecutionHistory && executionHistory.length === 0 ? <li>暂无执行历史。</li> : null}
                  {executionHistory.map((entry) => (
                    <li key={entry.history_id}>
                      <strong>
                        {entry.run_id ?? entry.history_id} · {localizeExecutionStatus(entry.status ?? "idle")}
                      </strong>
                      <span>
                        模式：
                        {entry.execution_mode
                          ? localizePresetLabel(entry.execution_mode, entry.execution_mode)
                          : "暂无"}
                        {" · "}
                        后端：
                        {entry.executed_backend_key
                          ? localizePresetLabel(entry.executed_backend_key, entry.executed_backend_key)
                          : "暂无"}
                      </span>
                      <span>阶段：{localizeExecutionStage(entry.stage)} · 事件数：{entry.event_count ?? 0}</span>
                      {entry.error_message ? <span>失败原因：{entry.error_message}</span> : null}
                      <button
                        type="button"
                        onClick={() => onReplayExecutionHistory(entry.history_id)}
                        disabled={!entry.db_path}
                      >
                        回放该次事件
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
              <section className="subsurface subsurface--nested" aria-labelledby="execution-events-title">
                <h4 id="execution-events-title">执行事件流</h4>
                <ul className="compact-list compact-list--timeline" aria-label="执行事件流">
                  {events.length === 0 ? <li>暂无执行事件。</li> : null}
                  {events.map((event, index) => (
                    <li
                      key={`${event.type}-${event.timestamp ?? "no-ts"}-${index}`}
                      data-active={matchesExecutionContext(event, externalContext) ? "true" : undefined}
                    >
                      <strong>{localizeEventType(event.type)}</strong>
                      {formatEventTimestamp(event.timestamp) ? (
                        <span className="timeline-meta">时间：{formatEventTimestamp(event.timestamp)}</span>
                      ) : null}
                      <span>
                        {event.status ? `${localizeExecutionStatus(event.status)} · ` : ""}
                        {event.stage ? `${localizeExecutionStage(event.stage)} · ` : ""}
                        {event.executed_backend_label ? `${event.executed_backend_label} · ` : ""}
                        {event.event_count ? `事件 ${event.event_count} 条 · ` : ""}
                        {event.message ?? "无附加消息"}
                      </span>
                      {extractExecutionMethodRef(event) ? (
                        <button type="button" className="button-ghost" onClick={() => onInspectHookContext(event)}>
                          在 Hook 工作台定位函数
                        </button>
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
