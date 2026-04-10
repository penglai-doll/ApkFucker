import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";

describe("CaseWorkspacePage", () => {
  it("renders the workspace heading in Chinese", () => {
    render(<CaseWorkspacePage />);

    expect(screen.getByText("案件工作台")).toBeInTheDocument();
  });
});
