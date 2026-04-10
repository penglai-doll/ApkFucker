import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";

describe("CaseWorkspacePage", () => {
  it("renders the static brief and hook studio panels", () => {
    render(<CaseWorkspacePage />);

    expect(screen.getByText("案件工作台")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "静态简报" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hook Studio" })).toBeInTheDocument();
  });
});
