import type { WorkspaceEvent } from "../../lib/types";

type ExecutionConsolePanelProps = {
  events: WorkspaceEvent[];
  isStarting: boolean;
  onStart: () => void;
  startDisabled: boolean;
  statusText: string;
};

export function ExecutionConsolePanel({
  events,
  isStarting,
  onStart,
  startDisabled,
  statusText,
}: ExecutionConsolePanelProps): JSX.Element {
  return (
    <section aria-labelledby="execution-console-title">
      <h3 id="execution-console-title">执行控制台</h3>
      <p>触发案件执行，并查看最小实时事件流。</p>
      <p>当前状态：{statusText}</p>
      <button type="button" onClick={onStart} disabled={startDisabled}>
        {isStarting ? "正在启动..." : "启动执行"}
      </button>
      <ul aria-label="执行事件流">
        {events.length === 0 ? <li>暂无执行事件。</li> : null}
        {events.map((event, index) => (
          <li key={`${event.type}-${event.timestamp ?? "no-ts"}-${index}`}>
            <strong>{event.type}</strong>
            {event.status ? ` · ${event.status}` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}
