import type {
  ExecutionStartResponse,
  HookPlanResponse,
  TrafficCaptureResponse,
  WorkspaceEvent,
  WorkspaceSummary,
} from "../../lib/types";
import { localizeExecutionFailureCode } from "../../lib/executionDiagnostics";

type EvidencePanelProps = {
  caseId: string | null;
  events: WorkspaceEvent[];
  executionResponse: ExecutionStartResponse | null;
  hookPlan: HookPlanResponse | null;
  isOpeningPath: boolean;
  onInspectHookContext: (event: WorkspaceEvent) => void;
  onOpenPath: (path: string) => void;
  openPathError: string | null;
  openPathMessage: string | null;
  trafficCapture: TrafficCaptureResponse | null;
  workspace: WorkspaceSummary | null;
};

function localizeEventType(type: string | undefined): string {
  switch (type) {
    case "execution.started":
      return "执行已启动";
    case "execution.completed":
      return "执行已完成";
    case "execution.failed":
      return "执行失败";
    case "execution.event":
      return "执行日志";
    case "workspace.events.error":
      return "事件流异常";
    case undefined:
      return "暂无";
    default:
      return type;
  }
}

function localizeStatus(status: string | undefined): string {
  switch (status) {
    case "completed":
      return "已完成";
    case "started":
      return "已启动";
    case "error":
      return "失败";
    case undefined:
      return "暂无";
    default:
      return status;
  }
}

function localizeExecutionPreset(key: string | undefined): string {
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
    case undefined:
      return "暂无";
    default:
      return key;
  }
}

function renderPath(
  label: string,
  value: string | null | undefined,
  options: {
    isOpening: boolean;
    onOpenPath: (path: string) => void;
  },
): JSX.Element {
  const { isOpening, onOpenPath } = options;
  return (
    <li>
      <strong>{label}</strong>
      <span>{value ? `：${value}` : "：暂无"}</span>
      {value ? (
        <button type="button" onClick={() => onOpenPath(value)} disabled={isOpening}>
          {isOpening ? `正在打开${label}...` : `打开${label}`}
        </button>
      ) : null}
    </li>
  );
}

function hasExecutionMethodRef(event: WorkspaceEvent): boolean {
  const className = event.payload?.class_name;
  const methodName = event.payload?.method_name;
  return typeof className === "string" && className.length > 0 && typeof methodName === "string" && methodName.length > 0;
}

export function EvidencePanel({
  caseId,
  events,
  executionResponse,
  hookPlan,
  isOpeningPath,
  onInspectHookContext,
  onOpenPath,
  openPathError,
  openPathMessage,
  trafficCapture,
  workspace,
}: EvidencePanelProps): JSX.Element {
  const latestEvent = events.length > 0 ? events[events.length - 1] : null;
  const recentEvents = events.slice(-5).reverse();
  const latestFailureCode =
    (latestEvent?.type === "execution.failed" ? latestEvent.error_code : null) ??
    executionResponse?.error_code ??
    hookPlan?.last_execution_error_code ??
    null;
  const latestFailureMessage =
    (latestEvent?.type === "execution.failed" ? latestEvent.message : null) ??
    executionResponse?.message ??
    hookPlan?.last_execution_error_message ??
    null;

  return (
    <section className="workspace-panel evidence-panel" aria-labelledby="evidence-panel-title">
      <h3 id="evidence-panel-title">证据中心</h3>
      <p>集中查看最近一次执行产物、最近事件和案件证据路径，便于直接回溯排障。</p>
      <p>案件编号：{caseId ?? "未选择"}</p>
      <p>案件标题：{workspace?.title ?? "未加载"}</p>
      <p>最近事件：{localizeEventType(latestEvent?.type)}</p>
      <p>最近执行状态：{localizeStatus(executionResponse?.status ?? hookPlan?.last_execution_status ?? latestEvent?.status)}</p>
      <p>最近请求模式：{localizeExecutionPreset(executionResponse?.execution_mode ?? hookPlan?.last_execution_mode ?? undefined)}</p>
      <p>
        最近实际后端：
        {executionResponse?.executed_backend_label ??
          localizeExecutionPreset(executionResponse?.executed_backend_key ?? hookPlan?.last_executed_backend_key ?? undefined)}
      </p>
      <p>最近执行事件数：{executionResponse?.event_count ?? hookPlan?.last_execution_event_count ?? 0}</p>
      <p>最近失败分类：{latestFailureCode ? localizeExecutionFailureCode(latestFailureCode) : "暂无"}</p>
      <p>最近失败原因：{latestFailureMessage ?? "暂无"}</p>
      <p>流量证据：{trafficCapture ? "已加载" : "暂无"}</p>
      <p>流量来源类型：{trafficCapture?.provenance.label ?? "暂无"}</p>
      <p>流量来源：{trafficCapture?.source_path ?? "暂无"}</p>
      <p>
        流量概览：
        {trafficCapture ? `${trafficCapture.flow_count} 条，总计 ${trafficCapture.suspicious_count} 条可疑` : "暂无"}
      </p>
      {openPathMessage ? <p role="status">{openPathMessage}</p> : null}
      {openPathError ? <p role="alert">{openPathError}</p> : null}
      <ul aria-label="证据路径">
        {renderPath("运行数据库", executionResponse?.db_path ?? hookPlan?.last_execution_db_path, {
          isOpening: isOpeningPath,
          onOpenPath,
        })}
        {renderPath("运行包目录", executionResponse?.bundle_path ?? hookPlan?.last_execution_bundle_path, {
          isOpening: isOpeningPath,
          onOpenPath,
        })}
        {renderPath("最近报告", hookPlan?.last_report_path, {
          isOpening: isOpeningPath,
          onOpenPath,
        })}
      </ul>
      <div aria-label="最近事件列表">
        <h4>最近事件</h4>
        <ul>
          {recentEvents.length === 0 ? <li>暂无实时事件。</li> : null}
          {recentEvents.map((event, index) => (
            <li key={`${event.type}-${event.run_id ?? "no-run"}-${index}`}>
              <strong>{localizeEventType(event.type)}</strong>
              <span>{event.status ? ` · ${localizeStatus(event.status)}` : ""}</span>
              <span>{event.executed_backend_label ? ` · ${event.executed_backend_label}` : ""}</span>
              <span>{event.message ? ` · ${event.message}` : ""}</span>
              {hasExecutionMethodRef(event) ? (
                <button type="button" className="button-ghost" onClick={() => onInspectHookContext(event)}>
                  在 Hook 工作台定位函数
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
