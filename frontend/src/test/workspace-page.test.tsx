import "@testing-library/jest-dom/vitest";

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from "react-router-dom";

import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";
import {
  exportReport,
  getEnvironmentStatus,
  getWorkspaceDetail,
  getWorkspaceMethods,
  getWorkspaceRecommendations,
  openWorkspaceInJadx,
  startExecution,
} from "../lib/api";
import { connectWorkspaceEvents } from "../lib/ws";

vi.mock("../lib/api", () => ({
  exportReport: vi.fn(),
  getEnvironmentStatus: vi.fn(),
  getWorkspaceDetail: vi.fn(),
  getWorkspaceMethods: vi.fn(),
  getWorkspaceRecommendations: vi.fn(),
  openWorkspaceInJadx: vi.fn(),
  startExecution: vi.fn(),
}));

vi.mock("../lib/ws", () => ({
  connectWorkspaceEvents: vi.fn(),
}));

describe("CaseWorkspacePage", () => {
  beforeEach(() => {
    vi.mocked(exportReport).mockReset();
    vi.mocked(getEnvironmentStatus).mockReset();
    vi.mocked(getWorkspaceDetail).mockReset();
    vi.mocked(getWorkspaceMethods).mockReset();
    vi.mocked(getWorkspaceRecommendations).mockReset();
    vi.mocked(openWorkspaceInJadx).mockReset();
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
    vi.mocked(getEnvironmentStatus).mockResolvedValue({
      summary: "4 available, 2 missing",
      recommended_execution_mode: "real_frida_session",
      tools: [
        { name: "jadx", label: "jadx", available: true, path: "/usr/bin/jadx" },
        { name: "jadx-gui", label: "jadx-gui", available: true, path: "/usr/bin/jadx-gui" },
        { name: "apktool", label: "apktool", available: false, path: null },
        { name: "adb", label: "adb", available: true, path: "/usr/bin/adb" },
        { name: "frida", label: "frida", available: false, path: null },
        { name: "python-frida", label: "python-frida", available: true, path: "module:frida" },
      ],
      execution_presets: [
        { key: "fake_backend", label: "Fake Backend", available: true, detail: "ready" },
        {
          key: "real_device",
          label: "Real Device",
          available: true,
          detail: "ready (Frida Session)",
        },
        { key: "real_adb_probe", label: "ADB Probe", available: true, detail: "ready" },
        {
          key: "real_frida_probe",
          label: "Frida Probe",
          available: false,
          detail: "unavailable (missing frida)",
        },
        {
          key: "real_frida_session",
          label: "Frida Session",
          available: true,
          detail: "ready",
        },
      ],
    });
  });

  function createDeferred<T>(): {
    promise: Promise<T>;
    resolve: (value: T) => void;
    reject: (reason?: unknown) => void;
  } {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((nextResolve, nextReject) => {
      resolve = nextResolve;
      reject = nextReject;
    });
    return { promise, resolve, reject };
  }

  it("loads the workspace inspection data and renders the Chinese workspace browser", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-001",
      title: "Alpha 样本",
      package_name: "com.example.alpha",
      technical_tags: ["okhttp3", "uniapp"],
      dangerous_permissions: ["READ_SMS", "CAMERA"],
      callback_endpoints: ["https://c2.example.com/api"],
      callback_clues: ["动态拼接 URL", "硬编码鉴权头"],
      crypto_signals: ["AES/CBC", "MD5"],
      packer_hints: ["腾讯乐固"],
      limitations: ["样本缺少完整 method index"],
      custom_scripts: [
        {
          script_id: "script-1",
          name: "日志脱敏脚本",
          script_path: "/workspace/case-001/scripts/log-mask.js",
        },
      ],
      can_open_in_jadx: true,
      has_method_index: true,
      method_count: 2,
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [
        {
          class_name: "com.example.alpha.net.ApiClient",
          method_name: "sendPayload",
          parameter_types: ["java.lang.String", "java.util.Map"],
          return_type: "void",
          is_constructor: false,
          overload_count: 2,
          source_path: "com/example/alpha/net/ApiClient.java",
          line_hint: 142,
          tags: ["回连", "加密前"],
          evidence: ["命中 callback clue"],
        },
      ],
      total: 1,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [
        {
          recommendation_id: "rec-1",
          kind: "method",
          title: "优先 Hook 回连方法",
          reason: "命中回连线索和网络类标签",
          score: 92,
          matched_terms: ["回连", "okhttp3"],
          method: {
            class_name: "com.example.alpha.net.ApiClient",
            method_name: "sendPayload",
            parameter_types: ["java.lang.String", "java.util.Map"],
            return_type: "void",
            is_constructor: false,
            overload_count: 2,
            source_path: "com/example/alpha/net/ApiClient.java",
            line_hint: 142,
            tags: ["回连", "加密前"],
            evidence: ["命中 callback clue"],
          },
          template_id: "template-okhttp",
          template_name: "okhttp3_unpin.js",
          plugin_id: "network",
        },
        {
          recommendation_id: "rec-2",
          kind: "template",
          title: "建议启用 AES 监控模板",
          reason: "检测到 AES/CBC 信号",
          score: 80,
          matched_terms: ["AES", "CBC"],
          method: null,
          template_id: "template-cipher",
          template_name: "cipher_monitor.js",
          plugin_id: null,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-001"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("案件工作台")).toBeInTheDocument();
    expect(await screen.findByText("当前案件：Alpha 样本")).toBeInTheDocument();
    expect(screen.getByText("com.example.alpha")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hook 工作台" })).toBeInTheDocument();
    expect(screen.getByText("技术标签")).toBeInTheDocument();
    expect(screen.getByText("危险权限")).toBeInTheDocument();
    expect(screen.getByText("回连端点")).toBeInTheDocument();
    expect(screen.getByText("回连线索")).toBeInTheDocument();
    expect(screen.getByText("加密信号")).toBeInTheDocument();
    expect(screen.getByText("加固线索")).toBeInTheDocument();
    expect(screen.getByText("限制说明")).toBeInTheDocument();
    expect(screen.getByText("自定义脚本")).toBeInTheDocument();
    expect(screen.getByText("方法索引状态")).toBeInTheDocument();
    expect(screen.getByText("已建立")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "执行控制台" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "证据中心" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "报告与导出" })).toBeInTheDocument();
    expect(screen.getByText("执行已启动")).toBeInTheDocument();
    expect(screen.getByText("环境概览：已就绪 4 项，缺失 2 项")).toBeInTheDocument();
    expect(screen.getByText("推荐预设：Frida 会话")).toBeInTheDocument();
    expect(screen.getByText("真实设备：就绪（Frida 会话）")).toBeInTheDocument();
    expect(screen.getByText("Frida 会话：就绪")).toBeInTheDocument();
    expect(screen.getByText("Frida 探测：不可用（缺少 frida）")).toBeInTheDocument();

    expect(screen.getByRole("textbox", { name: "搜索方法" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "搜索方法" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "在 JADX 中打开" })).toBeInTheDocument();

    expect(await screen.findByText("类名：com.example.alpha.net.ApiClient")).toBeInTheDocument();
    expect(screen.getByText("方法名：sendPayload")).toBeInTheDocument();
    expect(screen.getByText("参数：java.lang.String, java.util.Map")).toBeInTheDocument();
    expect(screen.getByText("签名：sendPayload(java.lang.String, java.util.Map)")).toBeInTheDocument();
    expect(screen.getByText("返回类型：void")).toBeInTheDocument();
    expect(screen.getByText("回连")).toBeInTheDocument();
    expect(screen.getByText("加密前")).toBeInTheDocument();

    expect(await screen.findByText("优先 Hook 回连方法")).toBeInTheDocument();
    expect(screen.getByText("建议启用 AES 监控模板")).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes("okhttp3_unpin.js"))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes("cipher_monitor.js"))).toBeInTheDocument();

    expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-001");
    expect(vi.mocked(getEnvironmentStatus)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getWorkspaceMethods)).toHaveBeenCalledWith("case-001", { query: "", limit: 12 });
    expect(vi.mocked(getWorkspaceRecommendations)).toHaveBeenCalledWith("case-001", { limit: 6 });
    expect(vi.mocked(connectWorkspaceEvents)).toHaveBeenCalled();
  });

  it("shows a Chinese fallback when the workspace has no method index", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-002",
      title: "Beta 样本",
      package_name: "com.example.beta",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: ["未生成 method index，暂时无法浏览方法列表。"],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [],
      total: 0,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-002"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("当前案件：Beta 样本")).toBeInTheDocument();
    expect(screen.getByText("当前没有可用的方法索引，无法浏览方法列表。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "在 JADX 中打开" })).toBeDisabled();
  });

  it("opens JADX from the hook studio and shows the Chinese success state", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-003",
      title: "Gamma 样本",
      package_name: "com.example.gamma",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: true,
      has_method_index: true,
      method_count: 0,
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [],
      total: 0,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [],
    });
    vi.mocked(openWorkspaceInJadx).mockResolvedValue({
      case_id: "case-003",
      status: "opened",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-003"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "在 JADX 中打开" }));

    await waitFor(() => {
      expect(vi.mocked(openWorkspaceInJadx)).toHaveBeenCalledWith("case-003");
    });
    expect(await screen.findByText("已尝试在本机打开 JADX。")).toBeInTheDocument();
  });

  it("shows a Chinese error state when workspace inspection fails", async () => {
    vi.mocked(getWorkspaceDetail).mockRejectedValue(new Error("boom"));

    render(
      <MemoryRouter initialEntries={["/workspace/case-missing"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("案件工作台暂时不可用。");
  });

  it("shows a Chinese execution environment fallback when environment inspection fails", async () => {
    vi.mocked(getEnvironmentStatus).mockRejectedValue(new Error("no tools"));
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-err",
      title: "环境错误样本",
      package_name: "com.example.err",
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

    render(
      <MemoryRouter initialEntries={["/workspace/case-err"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("当前案件：环境错误样本")).toBeInTheDocument();
    expect(screen.getByText("执行环境暂时不可用，请稍后重试。")).toBeInTheDocument();
  });

  it("starts an execution and exports a report from the workspace page", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-004",
      title: "Delta 样本",
      package_name: "com.example.delta",
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
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [],
      total: 0,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [],
    });
    vi.mocked(startExecution).mockResolvedValue({
      case_id: "case-004",
      status: "started",
    });
    vi.mocked(exportReport).mockResolvedValue({
      case_id: "case-004",
      report_path: "/tmp/workspaces/case-004/reports/case-004-report.md",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-004"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "启动执行" }));
    await waitFor(() => {
      expect(vi.mocked(startExecution)).toHaveBeenCalledWith("case-004");
    });
    expect(await screen.findByText("当前状态：已启动")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "导出报告" }));
    await waitFor(() => {
      expect(vi.mocked(exportReport)).toHaveBeenCalledWith("case-004");
    });
    expect(
      await screen.findByText((content) => content.includes("/tmp/workspaces/case-004/reports/case-004-report.md")),
    ).toBeInTheDocument();
  });

  it("does not leak in-flight action results into the next case workspace", async () => {
    const executionDeferred = createDeferred<{ case_id: string; status: string }>();
    const reportDeferred = createDeferred<{ case_id: string; report_path: string }>();
    const openDeferred = createDeferred<{ case_id: string; status: string }>();
    vi.mocked(startExecution).mockImplementation(() => executionDeferred.promise);
    vi.mocked(exportReport).mockImplementation(() => reportDeferred.promise);
    vi.mocked(openWorkspaceInJadx).mockImplementation(() => openDeferred.promise);
    vi.mocked(getWorkspaceDetail).mockImplementation(async (caseId) => ({
      case_id: caseId,
      title: caseId === "case-001" ? "Alpha 样本" : "Beta 样本",
      package_name: caseId === "case-001" ? "com.example.alpha" : "com.example.beta",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: true,
      has_method_index: false,
      method_count: 0,
    }));
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(connectWorkspaceEvents).mockImplementation(() => ({ close: vi.fn() }));

    const router = createMemoryRouter(
      [{ path: "/workspace/:caseId", element: <CaseWorkspacePage /> }],
      { initialEntries: ["/workspace/case-001"] },
    );

    render(<RouterProvider router={router} />);

    expect(await screen.findByText("当前案件：Alpha 样本")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "启动执行" }));
    fireEvent.click(screen.getByRole("button", { name: "导出报告" }));
    fireEvent.click(screen.getByRole("button", { name: "在 JADX 中打开" }));

    await act(async () => {
      await router.navigate("/workspace/case-002");
    });
    expect(await screen.findByText("当前案件：Beta 样本")).toBeInTheDocument();

    await act(async () => {
      executionDeferred.resolve({ case_id: "case-001", status: "started" });
      reportDeferred.resolve({
        case_id: "case-001",
        report_path: "/tmp/workspaces/case-001/reports/case-001-report.md",
      });
      openDeferred.resolve({ case_id: "case-001", status: "opened" });
    });

    await waitFor(() => {
      expect(screen.queryByText("当前状态：已启动")).not.toBeInTheDocument();
      expect(screen.queryByText("已尝试在本机打开 JADX。")).not.toBeInTheDocument();
      expect(
        screen.queryByText((content) => content.includes("/tmp/workspaces/case-001/reports/case-001-report.md")),
      ).not.toBeInTheDocument();
    });
  });
});
