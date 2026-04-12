type ReportsPanelProps = {
  isExporting: boolean;
  onExport: () => void;
  reportPath: string | null;
};

export function ReportsPanel({ isExporting, onExport, reportPath }: ReportsPanelProps): JSX.Element {
  return (
    <section aria-labelledby="reports-panel-title">
      <h3 id="reports-panel-title">报告与导出</h3>
      <p>导出案件报告，并显示最近一次导出产物路径。</p>
      <button type="button" onClick={onExport} disabled={isExporting}>
        {isExporting ? "正在导出..." : "导出报告"}
      </button>
      <p>最近导出：{reportPath ?? "尚未导出"}</p>
    </section>
  );
}
