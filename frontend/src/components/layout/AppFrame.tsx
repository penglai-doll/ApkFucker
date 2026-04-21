import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { getApiHealth } from "../../lib/api";
import { getStartupSettings } from "../../lib/api";
import type { AppMode } from "../../lib/types";
import type { ApiHealth } from "../../lib/types";
import { useAppStore } from "../../store/app-store";

const modeTitles: Record<AppMode, string> = {
  queue: "案件队列",
  workspace: "案件工作台",
};

const modeDescriptions: Record<AppMode, string> = {
  queue: "导入样本并整理案件，再把需要深挖的样本送进工作台。",
  workspace: "围绕单个样本查看静态、Hook、执行和证据。",
};

const modeSecondaryLabels: Record<AppMode, string> = {
  queue: "Case Queue",
  workspace: "Case Workspace",
};

const navItems: Array<{
  description: string;
  icon: string;
  label: string;
  tag: string;
  to: string;
}> = [
  {
    to: "/queue",
    label: "案件队列",
    description: "导入样本并快速进入工作台。",
    icon: "案",
    tag: "Queue",
  },
  {
    to: "/workspace",
    label: "案件工作台",
    description: "围绕当前样本查看函数、Hook、执行与证据。",
    icon: "台",
    tag: "Workspace",
  },
];

function getModeFromPath(pathname: string): AppMode {
  return pathname.startsWith("/workspace") ? "workspace" : "queue";
}

function summarizePath(path: string | null | undefined): string {
  if (!path) {
    return "等待后端返回";
  }

  const segments = path.split("/").filter(Boolean);
  if (segments.length <= 3) {
    return path;
  }

  return `…/${segments.slice(-3).join("/")}`;
}

export function AppFrame(): JSX.Element {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const setCurrentMode = useAppStore((state) => state.setCurrentMode);
  const currentMode = getModeFromPath(pathname);
  const hasResolvedStartup = useRef(false);
  const [apiHealth, setApiHealth] = useState<ApiHealth | null>(null);
  const [apiHealthStatus, setApiHealthStatus] = useState<"checking" | "ready" | "unavailable">(
    "checking",
  );

  const apiHealthValue =
    apiHealthStatus === "checking" ? "检查中" : apiHealthStatus === "ready" ? "已连接" : "未就绪";

  const apiHealthClassName =
    apiHealthStatus === "ready"
      ? "status-pill status-pill--ready"
      : apiHealthStatus === "unavailable"
        ? "status-pill status-pill--down"
        : "status-pill";
  const workspaceRootLabel = summarizePath(apiHealth?.default_workspace_root);
  const workspaceModeLabel = currentMode === "queue" ? "队列优先" : "状态先行";

  useEffect(() => {
    let active = true;
    let timerId: number | null = null;

    const scheduleNextProbe = (delayMs: number): void => {
      timerId = window.setTimeout(() => {
        void probeHealth();
      }, delayMs);
    };

    const probeHealth = async (): Promise<void> => {
      try {
        const response = await getApiHealth();
        if (!active) {
          return;
        }

        setApiHealth(response);
        setApiHealthStatus(response.status === "ok" ? "ready" : "unavailable");
        scheduleNextProbe(response.status === "ok" ? 15000 : 3000);
      } catch {
        if (!active) {
          return;
        }

        setApiHealth(null);
        setApiHealthStatus("unavailable");
        scheduleNextProbe(3000);
      }
    };

    setApiHealthStatus("checking");
    void probeHealth();

    return () => {
      active = false;
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
    };
  }, []);

  useEffect(() => {
    setCurrentMode(currentMode);
  }, [currentMode, setCurrentMode]);

  useEffect(() => {
    const isConcreteWorkspaceRoute = /^\/workspace\/[^/]+$/.test(pathname);
    const isWorkspaceLandingRoute = pathname === "/workspace";
    const isStartupEligibleRoute = pathname === "/" || isWorkspaceLandingRoute;

    if (hasResolvedStartup.current || isConcreteWorkspaceRoute || !isStartupEligibleRoute) {
      if (!isConcreteWorkspaceRoute && !isStartupEligibleRoute) {
        hasResolvedStartup.current = true;
      }
      return;
    }

    hasResolvedStartup.current = true;
    let active = true;

    void getStartupSettings()
      .then((settings) => {
        if (!active) {
          return;
        }
        if (settings.launch_view === "workspace" && settings.case_id) {
          navigate(`/workspace/${settings.case_id}`, { replace: true });
          return;
        }
        if (!isWorkspaceLandingRoute) {
          navigate("/queue", { replace: true });
        }
      })
      .catch(() => {
        if (active && !isWorkspaceLandingRoute) {
          navigate("/queue", { replace: true });
        }
      });

    return () => {
      active = false;
    };
  }, [navigate, pathname]);

  return (
    <div className="app-shell">
      <aside className="app-shell__sidebar" aria-label="工作台侧边导航">
        <div className="app-shell__sidebar-topline">
          <span>桌面版</span>
          <span>中文工作台</span>
        </div>
        <div className="app-shell__brand">
          <div className="app-shell__brand-mark" aria-hidden="true" />
          <div className="app-shell__brand-copy">
            <p className="eyebrow">Android APK 动态分析</p>
            <strong>APKHacker</strong>
            <span>面向案件的 APK 动态分析工作台</span>
          </div>
        </div>

        <div className="app-shell__nav-title">
          <p className="eyebrow">主导航</p>
        </div>
        <nav className="app-shell__nav" aria-label="工作台主导航">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              aria-label={item.label}
              className={({ isActive }) =>
                `app-shell__nav-link${isActive ? " app-shell__nav-link--active" : ""}`
              }
            >
              <span className="app-shell__nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span className="app-shell__nav-copy">
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </span>
              <span className="app-shell__nav-tag" aria-hidden="true">
                {item.tag}
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="app-shell__sidebar-footer">
          <span className={apiHealthClassName} aria-label={`本地后端：${apiHealthValue}`}>
            <span>本地后端</span>
            <strong>{apiHealthValue}</strong>
          </span>
          <div className="app-shell__sidebar-summary">
            <div>
              <span>当前模式</span>
              <strong aria-label="当前模式">{modeTitles[currentMode]}</strong>
            </div>
            <div>
              <span>工作方式</span>
              <strong>{currentMode === "queue" ? "先管理，再深挖" : "先看状态，再进入模块"}</strong>
            </div>
          </div>
          <p>{modeDescriptions[currentMode]}</p>
          <p>
            默认工作目录：
            <strong
              className="app-banner__metric-value--path"
              title={apiHealth?.default_workspace_root ?? "等待本地后端返回"}
            >
              {workspaceRootLabel}
            </strong>
          </p>
        </div>
      </aside>

      <div className="app-shell__main">
        <header className="app-banner">
          <div className="app-banner__headline">
            <div className="app-banner__headline-top">
              <p className="eyebrow">{modeSecondaryLabels[currentMode]}</p>
              <span className="app-banner__ribbon">{currentMode === "queue" ? "案件管理" : "深度分析"}</span>
            </div>
            <h1>APKHacker</h1>
            <p className="app-banner__description">{modeDescriptions[currentMode]}</p>
            <div className="app-banner__summary-row" aria-hidden="true">
              <span>本地优先</span>
              <span>实时状态</span>
              <span>证据导向</span>
            </div>
          </div>

          <div className="app-banner__meta">
            <div className="app-banner__metric">
              <span>当前模式</span>
              <strong>{modeTitles[currentMode]}</strong>
            </div>
            <div className="app-banner__metric">
              <span>本地后端</span>
              <strong aria-label={`本地后端状态：${apiHealthValue}`}>{apiHealthValue}</strong>
            </div>
            <div className="app-banner__metric">
              <span>默认工作目录</span>
              <strong className="app-banner__metric-value--path" title={apiHealth?.default_workspace_root ?? "等待后端返回"}>
                {workspaceRootLabel}
              </strong>
            </div>
            <div className="app-banner__metric">
              <span>工作方式</span>
              <strong title={currentMode === "queue" ? "先管理案件，再进入深度分析。" : "先看案件状态，再进入具体模块。"}>
                {workspaceModeLabel}
              </strong>
            </div>
          </div>
        </header>

        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
