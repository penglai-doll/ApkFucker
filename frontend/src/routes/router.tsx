import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppFrame } from "../components/layout/AppFrame";
import { CaseQueuePage } from "../pages/CaseQueuePage";
import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";

export function createAppRouter() {
  return createBrowserRouter([
    {
      path: "/",
      element: <AppFrame />,
      children: [
        { index: true, element: <CaseQueuePage /> },
        { path: "queue", element: <CaseQueuePage /> },
        { path: "workspace", element: <CaseWorkspacePage /> },
        { path: "workspace/:caseId", element: <CaseWorkspacePage /> },
        { path: "*", element: <Navigate replace to="/queue" /> },
      ],
    },
  ]);
}
