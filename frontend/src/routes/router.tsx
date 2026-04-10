import { HashRouter, Navigate, Route, Routes } from "react-router-dom";

import App from "../App";

export default function AppRouter(): JSX.Element {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="*" element={<Navigate replace to="/" />} />
      </Routes>
    </HashRouter>
  );
}
