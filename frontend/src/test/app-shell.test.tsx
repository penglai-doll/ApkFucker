import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { getStartupSettings, getWorkspace, listCases } from "../lib/api";

vi.mock("../lib/api", () => ({
  getStartupSettings: vi.fn(),
  getWorkspace: vi.fn(),
  listCases: vi.fn(),
}));

describe("App shell", () => {
  beforeEach(() => {
    vi.mocked(getStartupSettings).mockReset();
    vi.mocked(listCases).mockReset();
    vi.mocked(getWorkspace).mockReset();
    vi.mocked(getStartupSettings).mockResolvedValue({
      launch_view: "queue",
      last_workspace_root: null,
      case_id: null,
      title: null,
    });
    vi.mocked(listCases).mockResolvedValue({ items: [] });
  });

  it("renders the Chinese dual-mode app frame", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "案件队列" })).toHaveAttribute("href", "/queue");
    expect(screen.getByRole("link", { name: "案件工作台" })).toHaveAttribute("href", "/workspace");
    expect(await screen.findByRole("heading", { name: "案件队列" })).toBeInTheDocument();
  });

  it("shows the workspace mode title when entering /workspace directly", async () => {
    window.history.replaceState({}, "", "/workspace");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "案件工作台" })).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件工作台");
  });

  it("restores the last workspace from startup settings when booting into root", async () => {
    vi.mocked(getStartupSettings).mockResolvedValue({
      launch_view: "workspace",
      last_workspace_root: "/tmp/workspaces/case-009",
      case_id: "case-009",
      title: "Recovered 样本",
    });
    vi.mocked(getWorkspace).mockResolvedValue({
      case_id: "case-009",
      title: "Recovered 样本",
      view: "workspace",
    });

    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(await screen.findByText("当前案件：Recovered 样本")).toBeInTheDocument();
    expect(vi.mocked(getStartupSettings)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getWorkspace)).toHaveBeenCalledWith("case-009");
  });

  it("does not override a concrete workspace route during startup restore", async () => {
    vi.mocked(getStartupSettings).mockResolvedValue({
      launch_view: "workspace",
      last_workspace_root: "/tmp/workspaces/case-009",
      case_id: "case-009",
      title: "Recovered 样本",
    });
    vi.mocked(getWorkspace).mockResolvedValue({
      case_id: "case-001",
      title: "Pinned 样本",
      view: "workspace",
    });

    window.history.replaceState({}, "", "/workspace/case-001");
    render(<App />);

    expect(await screen.findByText("当前案件：Pinned 样本")).toBeInTheDocument();
    expect(vi.mocked(getWorkspace)).toHaveBeenCalledWith("case-001");
    expect(vi.mocked(getWorkspace)).not.toHaveBeenCalledWith("case-009");
  });

  it("keeps the Chinese shell for unknown routes", async () => {
    window.history.replaceState({}, "", "/not-found");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "案件队列" })).toBeInTheDocument();
    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件队列");
    expect(screen.queryByText("Unexpected Application Error!")).not.toBeInTheDocument();
  });

  it("navigates from queue to a concrete workspace and loads workspace details", async () => {
    vi.mocked(listCases).mockResolvedValue({
      items: [
        {
          case_id: "case-001",
          title: "Alpha 样本",
          workspace_root: "/tmp/workspaces/case-001",
        },
      ],
    });
    vi.mocked(getWorkspace).mockResolvedValue({
      case_id: "case-001",
      title: "Alpha 样本",
      view: "workspace",
    });

    window.history.replaceState({}, "", "/queue");
    render(<App />);

    const link = await screen.findByRole("link", { name: "进入 Alpha 样本 工作台" });
    fireEvent.click(link);

    expect(await screen.findByText("当前案件：Alpha 样本")).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件工作台");
    expect(vi.mocked(getWorkspace)).toHaveBeenCalledWith("case-001");
  });
});
