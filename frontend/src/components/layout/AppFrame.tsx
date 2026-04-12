import { useEffect } from "react";
import { useRef } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { getStartupSettings } from "../../lib/api";
import type { AppMode } from "../../lib/types";
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
