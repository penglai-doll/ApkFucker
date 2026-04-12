import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { CaseQueueTable } from "../components/queue/CaseQueueTable";
import { getApiHealth, importCase, listCases } from "../lib/api";
import { pickSampleFile, pickWorkspaceDirectory } from "../lib/desktop";
import type { CaseQueueItem } from "../lib/types";

export function CaseQueuePage(): JSX.Element {
  const navigate = useNavigate();
  const [items, setItems] = useState<CaseQueueItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isImporting, setIsImporting] = useState(false);
  const [samplePath, setSamplePath] = useState("");
  const [workspaceRoot, setWorkspaceRoot] = useState("");
  const [title, setTitle] = useState("");
  const [queueErrorMessage, setQueueErrorMessage] = useState<string | null>(null);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);
  const [chooserMessage, setChooserMessage] = useState<string | null>(null);

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
        setQueueErrorMessage(null);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setQueueErrorMessage("案件队列暂时不可用。");
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

  useEffect(() => {
    let active = true;

    void getApiHealth()
      .then((response) => {
        if (!active) {
          return;
        }
        setWorkspaceRoot((current) => current || response.default_workspace_root || "");
      })
      .catch(() => {
        if (!active) {
          return;
        }
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleImportSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsImporting(true);
    setActionErrorMessage(null);
    setChooserMessage(null);

    try {
      const response = await importCase({
        sample_path: samplePath,
        workspace_root: workspaceRoot,
        title: title || null,
      });
      await loadCases();
      navigate(`/workspace/${response.case_id}`);
    } catch {
      setActionErrorMessage("导入案件失败，请检查样本路径和工作目录。");
    } finally {
      setIsImporting(false);
    }
  }

  async function handlePickSampleFile(): Promise<void> {
    setActionErrorMessage(null);
    setChooserMessage(null);

    try {
      const selected = await pickSampleFile();
      if (!selected) {
        return;
      }
      setSamplePath(selected);
    } catch {
      setChooserMessage("当前环境暂时无法使用原生选择器，请直接填写路径。");
    }
  }

  async function handlePickWorkspaceDirectory(): Promise<void> {
    setActionErrorMessage(null);
    setChooserMessage(null);

    try {
      const selected = await pickWorkspaceDirectory();
      if (!selected) {
        return;
      }
      setWorkspaceRoot(selected);
    } catch {
      setChooserMessage("当前环境暂时无法使用原生选择器，请直接填写路径。");
    }
  }

  return (
    <section aria-labelledby="case-queue-title">
      <h2 id="case-queue-title">案件队列</h2>
      <p>管理导入样本、批量状态和案件筛选。</p>
      <form onSubmit={handleImportSubmit}>
        <fieldset disabled={isImporting}>
          <legend>导入案件</legend>
          <div>
            <label htmlFor="case-queue-sample-path">样本路径</label>
            <div>
              <button type="button" onClick={() => void handlePickSampleFile()}>
                选择样本文件
              </button>
              <input
                id="case-queue-sample-path"
                aria-label="样本路径"
                value={samplePath}
                onChange={(event) => {
                  setSamplePath(event.target.value);
                  setChooserMessage(null);
                }}
                type="text"
              />
            </div>
          </div>
          <div>
            <label htmlFor="case-queue-workspace-root">工作目录</label>
            <div>
              <button type="button" onClick={() => void handlePickWorkspaceDirectory()}>
                选择工作目录
              </button>
              <input
                id="case-queue-workspace-root"
                aria-label="工作目录"
                value={workspaceRoot}
                onChange={(event) => {
                  setWorkspaceRoot(event.target.value);
                  setChooserMessage(null);
                }}
                type="text"
              />
            </div>
          </div>
          <div>
            <label htmlFor="case-queue-title-input">案件标题</label>
            <input
              id="case-queue-title-input"
              aria-label="案件标题"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              type="text"
            />
          </div>
          <button type="submit">{isImporting ? "导入中..." : "导入样本"}</button>
        </fieldset>
      </form>
      {chooserMessage ? <p role="status">{chooserMessage}</p> : null}
      {isLoading ? <p>正在加载案件队列...</p> : null}
      {actionErrorMessage ? <p role="alert">{actionErrorMessage}</p> : null}
      {queueErrorMessage ? <p role="alert">{queueErrorMessage}</p> : null}
      {!isLoading && !queueErrorMessage && items.length > 0 ? <CaseQueueTable items={items} /> : null}
      {!isLoading && !queueErrorMessage && items.length === 0 ? <p>当前还没有案件，请先导入样本。</p> : null}
    </section>
  );
}
