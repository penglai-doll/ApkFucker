import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import {
  getApiHealth,
  getEnvironmentStatus,
  getStartupSettings,
  getWorkspaceDetail,
  getWorkspaceMethods,
  getWorkspaceRecommendations,
  listCases,
} from "../lib/api";
import { connectWorkspaceEvents } from "../lib/ws";

vi.mock("../lib/api", () => ({
  getApiHealth: vi.fn(),
  getEnvironmentStatus: vi.fn(),
  getStartupSettings: vi.fn(),
  getWorkspaceDetail: vi.fn(),
  getWorkspaceMethods: vi.fn(),
  getWorkspaceRecommendations: vi.fn(),
  listCases: vi.fn(),
}));

vi.mock("../lib/ws", () => ({
  connectWorkspaceEvents: vi.fn(),
}));

describe("App shell", () => {
  beforeEach(() => {
    vi.mocked(getStartupSettings).mockReset();
    vi.mocked(getApiHealth).mockReset();
    vi.mocked(getEnvironmentStatus).mockReset();
    vi.mocked(listCases).mockReset();
    vi.mocked(getWorkspaceDetail).mockReset();
    vi.mocked(getWorkspaceMethods).mockReset();
    vi.mocked(getWorkspaceRecommendations).mockReset();
    vi.mocked(connectWorkspaceEvents).mockReset();
    vi.mocked(getStartupSettings).mockResolvedValue({
      launch_view: "queue",
      last_workspace_root: null,
      case_id: null,
      title: null,
    });
    vi.mocked(getApiHealth).mockResolvedValue({
      status: "ok",
      service: "local-api",
      default_workspace_root: "/tmp/workspaces",
    });
    vi.mocked(getEnvironmentStatus).mockResolvedValue({
      summary: "4 available, 2 missing",
      recommended_execution_mode: "real_frida_session",
      tools: [],
      execution_presets: [],
    });
    vi.mocked(listCases).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-default",
      title: "默认案件",
      package_name: "com.example.default",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(connectWorkspaceEvents).mockImplementation(() => ({
      close: vi.fn(),
    }));
  });

  it("renders the Chinese dual-mode app frame", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "案件队列" })).toHaveAttribute("href", "/queue");
    expect(screen.getByRole("link", { name: "案件工作台" })).toHaveAttribute("href", "/workspace");
    expect(await screen.findByText("本地后端：已连接")).toBeInTheDocument();
    expect(screen.getByText("默认工作目录：/tmp/workspaces")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "案件队列" })).toBeInTheDocument();
  });

  it("shows an unavailable status when the local API health check fails", async () => {
    vi.mocked(getApiHealth).mockRejectedValue(new Error("connection refused"));

    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(await screen.findByText("本地后端：未就绪")).toBeInTheDocument();
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
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-009",
      title: "Recovered 样本",
      package_name: "com.example.recovered",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
    });

    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(await screen.findByText("当前案件：Recovered 样本")).toBeInTheDocument();
    expect(vi.mocked(getStartupSettings)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-009");
  });

  it("does not override a concrete workspace route during startup restore", async () => {
    vi.mocked(getStartupSettings).mockResolvedValue({
      launch_view: "workspace",
      last_workspace_root: "/tmp/workspaces/case-009",
      case_id: "case-009",
      title: "Recovered 样本",
    });
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-001",
      title: "Pinned 样本",
      package_name: "com.example.pinned",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
    });

    window.history.replaceState({}, "", "/workspace/case-001");
    render(<App />);

    expect(await screen.findByText("当前案件：Pinned 样本")).toBeInTheDocument();
    expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-001");
    expect(vi.mocked(getWorkspaceDetail)).not.toHaveBeenCalledWith("case-009");
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
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-001",
      title: "Alpha 样本",
      package_name: "com.example.alpha",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
    });

    window.history.replaceState({}, "", "/queue");
    render(<App />);

    const link = await screen.findByRole("link", { name: "进入 Alpha 样本 工作台" });
    fireEvent.click(link);

    expect(await screen.findByText("当前案件：Alpha 样本")).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件工作台");
    expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-001");
  });
});
