import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { CaseQueueTable } from "../components/queue/CaseQueueTable";
import { importCase, listCases } from "../lib/api";
import type { CaseQueueItem } from "../lib/types";

export function CaseQueuePage(): JSX.Element {
  const navigate = useNavigate();
  const [items, setItems] = useState<CaseQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isImporting, setIsImporting] = useState(false);
  const [samplePath, setSamplePath] = useState("");
  const [workspaceRoot, setWorkspaceRoot] = useState("");
  const [title, setTitle] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadCases = async (): Promise<void> => {
    const response = await listCases();
    setItems(response.items);
  };

  useEffect(() => {
    let active = true;

    void loadCases()
      .then(() => {
        if (!active) {
          return;
        }
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

  async function handleImportSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsImporting(true);
    setErrorMessage(null);

    try {
      const response = await importCase({
        sample_path: samplePath,
        workspace_root: workspaceRoot,
        title: title || null,
      });
      await loadCases();
      navigate(`/workspace/${response.case_id}`);
    } catch {
      setErrorMessage("导入案件失败，请检查样本路径和工作目录。");
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <section aria-labelledby="case-queue-title">
      <h2 id="case-queue-title">案件队列</h2>
      <p>管理导入样本、批量状态和案件筛选。</p>
      <form onSubmit={handleImportSubmit}>
        <fieldset disabled={isImporting}>
          <legend>导入案件</legend>
          <label>
            样本路径
            <input
              aria-label="样本路径"
              value={samplePath}
              onChange={(event) => setSamplePath(event.target.value)}
              type="text"
            />
          </label>
          <label>
            workspace 根目录
            <input
              aria-label="workspace 根目录"
              value={workspaceRoot}
              onChange={(event) => setWorkspaceRoot(event.target.value)}
              type="text"
            />
          </label>
          <label>
            案件标题
            <input
              aria-label="案件标题"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              type="text"
            />
          </label>
          <button type="submit">{isImporting ? "导入中..." : "导入样本"}</button>
        </fieldset>
      </form>
      {isLoading ? <p>正在加载案件队列...</p> : null}
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      {!isLoading && !errorMessage && items.length > 0 ? <CaseQueueTable items={items} /> : null}
      {!isLoading && !errorMessage && items.length === 0 ? <p>当前还没有案件，请先导入样本。</p> : null}
    </section>
  );
}
