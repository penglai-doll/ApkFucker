import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import {
  getExecutionHistory,
  getExecutionPreflight,
  getHookPlan,
  getApiHealth,
  getEnvironmentStatus,
  getLiveTrafficCapture,
  getRuntimeSettings,
  getStartupSettings,
  getWorkspaceDetail,
  getWorkspaceEvents,
  getWorkspaceMethods,
  getWorkspaceRecommendations,
  getWorkspaceTraffic,
  listWorkspaceCustomScripts,
  listCases,
} from "../lib/api";
import type { WorkspaceDetailResponse, WorkspaceRuntimeSummary } from "../lib/types";
import { connectWorkspaceEvents } from "../lib/ws";

vi.mock("../lib/api", () => ({
  getExecutionHistory: vi.fn(),
  getExecutionPreflight: vi.fn(),
  getHookPlan: vi.fn(),
  getApiHealth: vi.fn(),
  getEnvironmentStatus: vi.fn(),
  getLiveTrafficCapture: vi.fn(),
  getRuntimeSettings: vi.fn(),
  getStartupSettings: vi.fn(),
  getWorkspaceDetail: vi.fn(),
  getWorkspaceEvents: vi.fn(),
  getWorkspaceMethods: vi.fn(),
  getWorkspaceRecommendations: vi.fn(),
  getWorkspaceTraffic: vi.fn(),
  listWorkspaceCustomScripts: vi.fn(),
  listCases: vi.fn(),
  normalizeConnectedDevices: vi.fn((environment: { connected_devices?: unknown[] }) =>
    Array.isArray(environment.connected_devices)
      ? environment.connected_devices
          .map((entry) =>
            entry && typeof entry === "object" && typeof (entry as { serial?: unknown }).serial === "string"
              ? {
                  serial: (entry as { serial: string }).serial,
                  label: typeof (entry as { model?: unknown }).model === "string" ? (entry as { model: string }).model : (entry as { serial: string }).serial,
                  status: typeof (entry as { state?: unknown }).state === "string" ? (entry as { state: string }).state : null,
                  detail: null,
                  model: typeof (entry as { model?: unknown }).model === "string" ? (entry as { model: string }).model : null,
                  transport: null,
                  recommended: false,
                }
              : null,
          )
          .filter((device): device is {
            serial: string;
            label: string;
            status: string | null;
            detail: null;
            model: string | null;
            transport: null;
            recommended: boolean;
          } => device !== null)
      : [],
  ),
  resolveRecommendedDeviceSerial: vi.fn((environment: { recommended_device_serial?: unknown; connected_devices?: unknown[] }) => {
    if (typeof environment.recommended_device_serial === "string" && environment.recommended_device_serial.trim()) {
      return environment.recommended_device_serial.trim();
    }
    const first = Array.isArray(environment.connected_devices)
      ? environment.connected_devices.find(
          (entry) => entry && typeof entry === "object" && typeof (entry as { serial?: unknown }).serial === "string",
        )
      : null;
    return first && typeof (first as { serial?: unknown }).serial === "string" ? (first as { serial: string }).serial : null;
  }),
  resolvePreferredDeviceSerial: vi.fn(
    (
      runtimeSettings: { device_serial: string },
      connectedDevices: { serial: string }[],
      recommendedDeviceSerial: string | null,
    ) => runtimeSettings.device_serial.trim() || recommendedDeviceSerial || connectedDevices[0]?.serial || "",
  ),
}));

vi.mock("../lib/ws", () => ({
  connectWorkspaceEvents: vi.fn(),
}));

function createRuntimeSummary(): WorkspaceRuntimeSummary {
  return {
    execution_count: 0,
    last_execution_run_id: null,
    last_execution_mode: null,
    last_executed_backend_key: null,
    last_execution_status: null,
    last_execution_stage: null,
    last_execution_error_code: null,
    last_execution_error_message: null,
    last_execution_event_count: null,
    last_execution_result_path: null,
    last_execution_db_path: null,
    last_execution_bundle_path: null,
    last_report_path: null,
    traffic_capture_source_path: null,
    traffic_capture_summary_path: null,
    traffic_capture_flow_count: null,
    traffic_capture_suspicious_count: null,
    live_traffic_status: null,
    live_traffic_artifact_path: null,
    live_traffic_message: null,
  };
}

function createWorkspaceDetail(
  overrides: Partial<WorkspaceDetailResponse> & Pick<WorkspaceDetailResponse, "case_id" | "title" | "package_name">,
): WorkspaceDetailResponse {
  const { case_id, title, package_name, ...rest } = overrides;
  return {
    case_id,
    title,
    package_name,
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
    runtime: createRuntimeSummary(),
    ...rest,
  };
}

describe("App shell", () => {
  beforeEach(() => {
    vi.mocked(getStartupSettings).mockReset();
    vi.mocked(getExecutionHistory).mockReset();
    vi.mocked(getExecutionPreflight).mockReset();
    vi.mocked(getHookPlan).mockReset();
    vi.mocked(getApiHealth).mockReset();
    vi.mocked(getEnvironmentStatus).mockReset();
    vi.mocked(getLiveTrafficCapture).mockReset();
    vi.mocked(getRuntimeSettings).mockReset();
    vi.mocked(listCases).mockReset();
    vi.mocked(getWorkspaceDetail).mockReset();
    vi.mocked(getWorkspaceEvents).mockReset();
    vi.mocked(getWorkspaceMethods).mockReset();
    vi.mocked(getWorkspaceRecommendations).mockReset();
    vi.mocked(getWorkspaceTraffic).mockReset();
    vi.mocked(listWorkspaceCustomScripts).mockReset();
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
      summary: "5 available, 4 missing",
      recommended_execution_mode: "real_frida_session",
      tools: [],
      live_capture: {
        available: true,
        source: "builtin_mitmdump",
        detail: "内置 Mitmdump 已就绪（监听 0.0.0.0:8080）",
        listen_host: "0.0.0.0",
        listen_port: 8080,
        help_text: "请把设备 HTTP/HTTPS 代理指向分析机 IP 的 8080 端口，停止后会自动导入 HAR。",
        proxy_address_hint: "分析机局域网 IP:8080",
        install_url: "http://mitm.it",
        certificate_path: "/Users/demo/.mitmproxy/mitmproxy-ca-cert.cer",
        certificate_directory_path: "/Users/demo/.mitmproxy",
        certificate_exists: true,
        certificate_help_text: "可直接把该证书安装到测试设备，或在设备浏览器访问 http://mitm.it。",
        setup_steps: ["先配置代理", "安装证书", "复现关键请求"],
        proxy_steps: ["代理到分析机局域网 IP:8080"],
        certificate_steps: ["安装 mitm 证书", "若仍失败则启用 SSL Hook"],
        recommended_actions: ["优先启用 SSL 建议"],
      },
      execution_presets: [],
    });
    vi.mocked(getRuntimeSettings).mockResolvedValue({
      execution_mode: "real_frida_session",
      device_serial: "",
      frida_server_binary_path: "",
      frida_server_remote_path: "",
      frida_session_seconds: "",
      live_capture_listen_host: "0.0.0.0",
      live_capture_listen_port: "8080",
    });
    vi.mocked(listCases).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceDetail).mockResolvedValue(createWorkspaceDetail({
      case_id: "case-default",
      title: "默认案件",
      package_name: "com.example.default",
    }));
    vi.mocked(getWorkspaceEvents).mockResolvedValue([]);
    vi.mocked(getExecutionHistory).mockResolvedValue([]);
    vi.mocked(getExecutionPreflight).mockResolvedValue({
      case_id: "case-default",
      ready: true,
      execution_mode: "real_frida_session",
      executed_backend_key: "real_frida_session",
      executed_backend_label: "Frida Session",
      detail: "ready",
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceTraffic).mockResolvedValue(null);
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-default",
      status: "idle",
      artifact_path: null,
      message: null,
    });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-default",
      updated_at: "2026-04-13T12:00:00Z",
      items: [],
    });
    vi.mocked(listWorkspaceCustomScripts).mockResolvedValue({ items: [] });
    vi.mocked(connectWorkspaceEvents).mockImplementation(() => ({
      close: vi.fn(),
    }));
  });

  it("renders the Chinese dual-mode app frame", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(screen.getByRole("heading", { name: "APKHacker" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "案件队列" })).toHaveAttribute("href", "/queue");
    expect(screen.getByRole("link", { name: "案件工作台" })).toHaveAttribute("href", "/workspace");
    expect(await screen.findByLabelText("本地后端：已连接")).toBeInTheDocument();
    expect(
      screen.getByText((_content, element) => element?.textContent === "默认工作目录：/tmp/workspaces"),
    ).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "案件队列" })).toBeInTheDocument();
  });

  it("shows an unavailable status when the local API health check fails", async () => {
    vi.mocked(getApiHealth).mockRejectedValue(new Error("connection refused"));

    window.history.replaceState({}, "", "/");
    render(<App />);

    expect(await screen.findByLabelText("本地后端：未就绪")).toBeInTheDocument();
  });

  it("shows the workspace mode title when entering /workspace directly", async () => {
    window.history.replaceState({}, "", "/workspace");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "案件工作台" })).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件工作台");
  });

  it("restores the last workspace when entering /workspace without a concrete case id", async () => {
    vi.mocked(getStartupSettings).mockResolvedValue({
      launch_view: "workspace",
      last_workspace_root: "/tmp/workspaces/case-010",
      case_id: "case-010",
      title: "恢复样本",
    });
    vi.mocked(getWorkspaceDetail).mockResolvedValue(
      createWorkspaceDetail({
        case_id: "case-010",
        title: "恢复样本",
        package_name: "com.example.restore",
      }),
    );

    window.history.replaceState({}, "", "/workspace");
    render(<App />);

    expect(await screen.findByText("当前案件：恢复样本")).toBeInTheDocument();
    expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-010");
  });

  it("restores the last workspace from startup settings when booting into root", async () => {
    vi.mocked(getStartupSettings).mockResolvedValue({
      launch_view: "workspace",
      last_workspace_root: "/tmp/workspaces/case-009",
      case_id: "case-009",
      title: "Recovered 样本",
    });
    vi.mocked(getWorkspaceDetail).mockResolvedValue(createWorkspaceDetail({
      case_id: "case-009",
      title: "Recovered 样本",
      package_name: "com.example.recovered",
    }));

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
    vi.mocked(getWorkspaceDetail).mockResolvedValue(createWorkspaceDetail({
      case_id: "case-001",
      title: "Pinned 样本",
      package_name: "com.example.pinned",
    }));

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
    expect(screen.getByRole("heading", { name: "APKHacker" })).toBeInTheDocument();
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
    vi.mocked(getWorkspaceDetail).mockResolvedValue(createWorkspaceDetail({
      case_id: "case-001",
      title: "Alpha 样本",
      package_name: "com.example.alpha",
    }));

    window.history.replaceState({}, "", "/queue");
    render(<App />);

    const link = await screen.findByRole("link", { name: "进入 Alpha 样本 工作台" });
    fireEvent.click(link);

    expect(await screen.findByText("当前案件：Alpha 样本")).toBeInTheDocument();
    expect(screen.getByLabelText("当前模式")).toHaveTextContent("案件工作台");
    expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-001");
  });
});
