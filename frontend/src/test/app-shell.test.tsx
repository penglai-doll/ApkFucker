import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AppRouter from "../routes/router";

describe("App shell", () => {
  it("renders the routed Chinese workspace shell", () => {
    render(<AppRouter />);

    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByText("案件队列")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "案件工作台" })).toBeInTheDocument();
  });
});
