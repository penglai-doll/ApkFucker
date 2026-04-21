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
    } catch (error) {
      const detail = error instanceof Error ? error.message.trim() : "";
      setActionErrorMessage(
        detail.length > 0
          ? detail.startsWith("导入案件失败")
            ? detail
            : `导入案件失败：${detail}`
          : "导入案件失败，请检查样本路径和工作目录。",
      );
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
    <section className="page-shell" aria-labelledby="case-queue-title">
      <header className="page-header">
        <div>
          <p className="eyebrow">Case Queue</p>
          <h2 id="case-queue-title" className="page-title">
            案件队列
          </h2>
          <p className="page-description">
            这里负责把样本导入本地工作目录、建立案件，并把需要深挖的 APK 快速送进案件工作台。
          </p>
        </div>
        <aside className="page-header__aside" aria-label="案件队列摘要">
          <div className="stat-tile">
            <span>当前案件数</span>
            <strong>{items.length}</strong>
          </div>
          <div className="stat-tile">
            <span>默认策略</span>
            <strong>复制样本到独立 Workspace</strong>
          </div>
        </aside>
      </header>

      <div className="queue-layout">
        <section className="surface surface--strong" aria-labelledby="case-import-title">
          <div className="surface__head">
            <div>
              <h3 id="case-import-title">导入案件</h3>
              <p>支持选择样本文件与工作目录；导入后会复制样本进入独立 workspace。</p>
            </div>
          </div>

          <div className="queue-flow" aria-label="导入流程">
            <div className="queue-flow__step">
              <span>1</span>
              <strong>选择样本</strong>
              <p>支持 APK、APKS、XAPK、ZIP。</p>
            </div>
            <div className="queue-flow__step">
              <span>2</span>
              <strong>确认目录</strong>
              <p>每个案件使用独立工作目录。</p>
            </div>
            <div className="queue-flow__step">
              <span>3</span>
              <strong>进入工作台</strong>
              <p>导入完成后直接跳转到案件工作台。</p>
            </div>
          </div>

          <form className="form-grid" onSubmit={handleImportSubmit}>
            <fieldset disabled={isImporting}>
              <legend>导入配置</legend>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="case-queue-sample-path">样本路径</label>
                  <div className="input-row">
                    <button className="button-secondary" type="button" onClick={() => void handlePickSampleFile()}>
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

                <div className="field">
                  <label htmlFor="case-queue-workspace-root">工作目录</label>
                  <div className="input-row">
                    <button className="button-secondary" type="button" onClick={() => void handlePickWorkspaceDirectory()}>
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

                <div className="field">
                  <label htmlFor="case-queue-title-input">案件标题</label>
                  <input
                    id="case-queue-title-input"
                    aria-label="案件标题"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    type="text"
                    placeholder="可选，默认会用样本文件名生成标题"
                  />
                </div>
              </div>

              <div className="button-row">
                <button className="button-primary" type="submit">
                  {isImporting ? "导入中..." : "导入样本"}
                </button>
                <button
                  className="button-ghost"
                  type="button"
                  onClick={() => {
                    setSamplePath("");
                    setTitle("");
                    setActionErrorMessage(null);
                    setChooserMessage(null);
                  }}
                >
                  清空样本输入
                </button>
              </div>
            </fieldset>
          </form>

          {chooserMessage ? <p className="message-inline" role="status">{chooserMessage}</p> : null}
          {actionErrorMessage ? <p className="message-inline" role="alert">{actionErrorMessage}</p> : null}
        </section>

        <aside className="surface" aria-labelledby="queue-overview-title">
          <div className="surface__head">
            <div>
              <h3 id="queue-overview-title">队列概览</h3>
              <p>先确认样本复制位置，再决定要不要立即进入深度工作台。</p>
            </div>
          </div>

          <div className="queue-stats">
            <div className="stat-grid">
              <div className="stat-tile">
                <span>当前案件数</span>
                <strong>{items.length}</strong>
              </div>
              <div className="stat-tile">
                <span>导入策略</span>
                <strong>复制样本</strong>
              </div>
            </div>
            <div className="stat-tile">
              <span>默认工作目录</span>
              <strong>{workspaceRoot || "等待本地后端返回默认目录"}</strong>
            </div>
            <div className="stat-tile">
              <span>建议路径</span>
              <strong>先导入样本，再进入案件工作台做静态与动态分析。</strong>
            </div>
          </div>
        </aside>
      </div>

      <section className="surface" aria-labelledby="case-queue-list-title">
        <div className="surface__head">
          <div>
            <h3 id="case-queue-list-title">案件列表</h3>
            <p>已经导入的案件会在这里集中展示，并可直接进入对应工作台。</p>
          </div>
        </div>

        {isLoading ? <p>正在加载案件队列...</p> : null}
        {queueErrorMessage ? <p className="message-inline" role="alert">{queueErrorMessage}</p> : null}

        {!isLoading && !queueErrorMessage && items.length > 0 ? (
          <CaseQueueTable items={items} />
        ) : null}

        {!isLoading && !queueErrorMessage && items.length === 0 ? (
          <div className="empty-state">
            当前还没有案件。你可以先选择一个 APK/APKS/XAPK/ZIP 样本，然后在上方直接导入。
          </div>
        ) : null}
      </section>
    </section>
  );
}
