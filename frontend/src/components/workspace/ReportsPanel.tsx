import type { HookPlanResponse, ReportExportResponse, TrafficCaptureResponse } from "../../lib/types";
import { localizeExecutionFailureCode } from "../../lib/executionDiagnostics";

type ReportsPanelProps = {
  exportError: string | null;
  isExporting: boolean;
  isOpeningPath: boolean;
  onExport: () => void;
  onOpenPath: (path: string) => void;
  openPathError: string | null;
  openPathMessage: string | null;
  hookPlan: HookPlanResponse | null;
  report: ReportExportResponse | null;
  trafficCapture: TrafficCaptureResponse | null;
};

function renderPathRow(
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

export function ReportsPanel({
  exportError,
  isExporting,
  isOpeningPath,
  onExport,
  onOpenPath,
  openPathError,
  openPathMessage,
  hookPlan,
  report,
  trafficCapture,
}: ReportsPanelProps): JSX.Element {
  const latestReportPath = report?.report_path ?? hookPlan?.last_report_path ?? null;
  const staticReportPath = report?.static_report_path ?? null;
  const executionDbPath = report?.last_execution_db_path ?? hookPlan?.last_execution_db_path ?? null;
  const executionBundlePath = report?.last_execution_bundle_path ?? hookPlan?.last_execution_bundle_path ?? null;
  const failureCode = hookPlan?.last_execution_error_code ?? null;
  const failureMessage = hookPlan?.last_execution_error_message ?? null;
  const trafficSummary = trafficCapture
    ? `${trafficCapture.flow_count} 条，总计 ${trafficCapture.suspicious_count} 条可疑`
    : "暂无";

  return (
    <section className="workspace-panel reports-panel" aria-labelledby="reports-panel-title">
      <h3 id="reports-panel-title">报告与导出</h3>
      <p>导出案件报告，并保留静态报告、最近一次运行数据库和执行目录的路径。</p>
      <button type="button" onClick={onExport} disabled={isExporting}>
        {isExporting ? "正在导出..." : "导出报告"}
      </button>
      {exportError ? <p role="alert">{exportError}</p> : null}
      {openPathMessage ? <p role="status">{openPathMessage}</p> : null}
      {openPathError ? <p role="alert">{openPathError}</p> : null}
      <div className="metric-grid metric-grid--four" aria-label="报告摘要">
        <div className="stat-tile">
          <span>最近导出</span>
          <strong>{latestReportPath ? "已生成" : "暂无"}</strong>
        </div>
        <div className="stat-tile">
          <span>静态报告</span>
          <strong>{staticReportPath ? "可用" : "暂无"}</strong>
        </div>
        <div className="stat-tile">
          <span>失败摘要</span>
          <strong>{failureCode ? localizeExecutionFailureCode(failureCode) : "暂无"}</strong>
        </div>
        <div className="stat-tile">
          <span>流量概览</span>
          <strong>{trafficCapture ? `${trafficCapture.flow_count} 条` : "暂无"}</strong>
        </div>
      </div>
      <div className="brief-disclosure-list">
        <details className="brief-disclosure" open>
          <summary>路径与产物 · 最近导出 {latestReportPath ? "可用" : "暂无"} · 执行目录 {executionBundlePath ? "可用" : "暂无"}</summary>
          <div className="brief-disclosure__content">
            <ul aria-label="报告路径">
              {renderPathRow("最近导出", latestReportPath, { isOpening: isOpeningPath, onOpenPath })}
              {renderPathRow("静态报告", staticReportPath, { isOpening: isOpeningPath, onOpenPath })}
              {renderPathRow("运行数据库", executionDbPath, { isOpening: isOpeningPath, onOpenPath })}
              {renderPathRow("执行目录", executionBundlePath, { isOpening: isOpeningPath, onOpenPath })}
              {renderPathRow("流量证据", trafficCapture?.source_path, { isOpening: isOpeningPath, onOpenPath })}
            </ul>
          </div>
        </details>
        <details className="brief-disclosure">
          <summary>执行与流量摘要 · 失败 {failureCode ? localizeExecutionFailureCode(failureCode) : "暂无"} · 流量 {trafficSummary}</summary>
          <div className="brief-disclosure__content">
            <div className="detail-card">
              <p>报告摘要中的失败分类：{failureCode ? localizeExecutionFailureCode(failureCode) : "暂无"}</p>
              <p>报告摘要中的失败原因：{failureMessage ?? "暂无"}</p>
              <p>流量来源类型：{trafficCapture?.provenance.label ?? "暂无"}</p>
              <p>流量概览：{trafficSummary}</p>
            </div>
          </div>
        </details>
      </div>
    </section>
  );
}
