import { Link } from "react-router-dom";

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
          <th scope="col">操作</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.case_id}>
            <td>{item.title}</td>
            <td>{item.case_id}</td>
            <td>{item.workspace_root}</td>
            <td>
              <Link to={`/workspace/${item.case_id}`}>进入 {item.title} 工作台</Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
