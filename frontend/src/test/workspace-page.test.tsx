import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";
import { getWorkspace } from "../lib/api";

vi.mock("../lib/api", () => ({
  getWorkspace: vi.fn(),
}));

describe("CaseWorkspacePage", () => {
  beforeEach(() => {
    vi.mocked(getWorkspace).mockReset();
  });

  it("loads workspace details by route param and renders the first panels", async () => {
    vi.mocked(getWorkspace).mockResolvedValue({
      case_id: "case-001",
      title: "Alpha 样本",
      view: "workspace",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-001"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("当前案件：Alpha 样本")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "静态简报" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hook Studio" })).toBeInTheDocument();
  });

  it("shows a Chinese error state when workspace loading fails", async () => {
    vi.mocked(getWorkspace).mockRejectedValue(new Error("boom"));

    render(
      <MemoryRouter initialEntries={["/workspace/case-missing"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("案件工作台暂时不可用。");
  });
});
