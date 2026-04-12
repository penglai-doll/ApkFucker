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

function getModeFromPath(pathname: string): AppMode {
  return pathname.startsWith("/workspace") ? "workspace" : "queue";
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
    const isStartupEligibleRoute = pathname === "/";

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
        navigate("/queue", { replace: true });
      })
      .catch(() => {
        if (active) {
          navigate("/queue", { replace: true });
        }
      });

    return () => {
      active = false;
    };
  }, [navigate, pathname]);

  return (
    <div>
      <header>
        <p>安卓 APK 动态分析工具</p>
        <h1>APKHacker</h1>
        <p aria-label="当前模式">{modeTitles[currentMode]}</p>
        <p>
          {apiHealthStatus === "checking" ? "本地后端：检查中" : null}
          {apiHealthStatus === "ready" ? "本地后端：已连接" : null}
          {apiHealthStatus === "unavailable" ? "本地后端：未就绪" : null}
        </p>
        {apiHealthStatus === "ready" && apiHealth ? (
          <p>默认工作目录：{apiHealth.default_workspace_root}</p>
        ) : null}
        <nav aria-label="工作台主导航">
          <NavLink to="/queue">案件队列</NavLink>
          <NavLink to="/workspace">案件工作台</NavLink>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
