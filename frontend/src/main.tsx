import React from "react";
import ReactDOM from "react-dom/client";

import AppRouter from "./routes/router";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element #root not found");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <AppRouter />
  </React.StrictMode>,
);
