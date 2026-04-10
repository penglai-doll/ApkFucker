import { useMemo } from "react";
import { RouterProvider } from "react-router-dom";

import { createAppRouter } from "./routes/router";

export default function App(): JSX.Element {
  const router = useMemo(() => createAppRouter(), []);

  return <RouterProvider router={router} />;
}
