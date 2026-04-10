import type { CaseQueueItem } from "../../lib/types";

type CaseQueueTableProps = {
  items: CaseQueueItem[];
};

export function CaseQueueTable({ items }: CaseQueueTableProps): JSX.Element {
  return (
    <table aria-label="案件列表">
      <thead>
        <tr>
          <th scope="col">案件</th>
          <th scope="col">编号</th>
          <th scope="col">工作目录</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.case_id}>
            <td>{item.title}</td>
            <td>{item.case_id}</td>
            <td>{item.workspace_root}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
