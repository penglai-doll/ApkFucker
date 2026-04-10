import { useEffect, useState } from "react";

import { CaseQueueTable } from "../components/queue/CaseQueueTable";
import { listCases } from "../lib/api";
import type { CaseQueueItem } from "../lib/types";

export function CaseQueuePage(): JSX.Element {
  const [items, setItems] = useState<CaseQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void listCases()
      .then((response) => {
        if (!active) {
          return;
        }
        setItems(response.items);
        setErrorMessage(null);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setErrorMessage("案件队列暂时不可用。");
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section aria-labelledby="case-queue-title">
      <h2 id="case-queue-title">案件队列</h2>
      <p>管理导入样本、批量状态和案件筛选。</p>
      {isLoading ? <p>正在加载案件队列...</p> : null}
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      {!isLoading && !errorMessage && items.length > 0 ? <CaseQueueTable items={items} /> : null}
      {!isLoading && !errorMessage && items.length === 0 ? <p>当前还没有案件，请先导入样本。</p> : null}
    </section>
  );
}
