import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

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
  const setCurrentMode = useAppStore((state) => state.setCurrentMode);
  const currentMode = getModeFromPath(pathname);

  useEffect(() => {
    setCurrentMode(currentMode);
  }, [currentMode, setCurrentMode]);

  return (
    <div>
      <header>
        <p>安卓 APK 动态分析工具</p>
        <h1>APKHacker</h1>
        <p>{modeTitles[currentMode]}</p>
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
