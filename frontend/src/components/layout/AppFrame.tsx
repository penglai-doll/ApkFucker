import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAppStore } from "../../store/app-store";

const modeTitles = {
  queue: "案件队列",
  workspace: "案件工作台",
} as const;

export function AppFrame(): JSX.Element {
  const { pathname } = useLocation();
  const currentMode = useAppStore((state) => state.currentMode);
  const setCurrentMode = useAppStore((state) => state.setCurrentMode);

  useEffect(() => {
    setCurrentMode(pathname.startsWith("/workspace") ? "workspace" : "queue");
  }, [pathname, setCurrentMode]);

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
