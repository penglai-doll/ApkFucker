import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";
import { exportReport, getWorkspace, startExecution } from "../lib/api";
import { connectWorkspaceEvents } from "../lib/ws";

vi.mock("../lib/api", () => ({
  exportReport: vi.fn(),
  getWorkspace: vi.fn(),
  startExecution: vi.fn(),
}));

vi.mock("../lib/ws", () => ({
  connectWorkspaceEvents: vi.fn(),
}));

describe("CaseWorkspacePage", () => {
  beforeEach(() => {
    vi.mocked(exportReport).mockReset();
    vi.mocked(getWorkspace).mockReset();
    vi.mocked(startExecution).mockReset();
    vi.mocked(connectWorkspaceEvents).mockReset();
    vi.mocked(connectWorkspaceEvents).mockImplementation(({ onEvent }) => {
      onEvent({
        type: "execution.started",
        case_id: "case-001",
        status: "started",
        payload: { source: "test" },
      });
      return {
        close: vi.fn(),
      };
    });
  });

  it("loads workspace details by route param and renders all workspace panels", async () => {
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
    expect(screen.getByRole("heading", { name: "执行控制台" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "证据中心" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "报告与导出" })).toBeInTheDocument();
    expect(screen.getByText("execution.started")).toBeInTheDocument();
    expect(vi.mocked(connectWorkspaceEvents)).toHaveBeenCalled();
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

  it("starts an execution from the execution console", async () => {
    vi.mocked(getWorkspace).mockResolvedValue({
      case_id: "case-001",
      title: "Alpha 样本",
      view: "workspace",
    });
    vi.mocked(startExecution).mockResolvedValue({
      case_id: "case-001",
      status: "started",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-001"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "启动执行" }));

    await waitFor(() => {
      expect(vi.mocked(startExecution)).toHaveBeenCalledWith("case-001");
    });
    expect(await screen.findByText("当前状态：started")).toBeInTheDocument();
  });

  it("exports a report from the reports panel", async () => {
    vi.mocked(getWorkspace).mockResolvedValue({
      case_id: "case-001",
      title: "Alpha 样本",
      view: "workspace",
    });
    vi.mocked(exportReport).mockResolvedValue({
      case_id: "case-001",
      report_path: "/tmp/workspaces/case-001/reports/case-001-report.md",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-001"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "导出报告" }));

    await waitFor(() => {
      expect(vi.mocked(exportReport)).toHaveBeenCalledWith("case-001");
    });
    expect(
      await screen.findByText((content) => content.includes("/tmp/workspaces/case-001/reports/case-001-report.md")),
    ).toBeInTheDocument();
  });
});
