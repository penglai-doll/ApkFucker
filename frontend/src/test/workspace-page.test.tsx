import "@testing-library/jest-dom/vitest";

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from "react-router-dom";

import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";
import {
  addCustomScriptToHookPlan,
  addMethodToHookPlan,
  addRecommendationToHookPlan,
  addTemplateToHookPlan,
  cancelExecution,
  clearHookPlan,
  exportReport,
  getEnvironmentStatus,
  getExecutionHistory,
  getExecutionHistoryEvents,
  getExecutionPreflight,
  getHookPlan,
  getLiveTrafficCapture,
  getLiveTrafficPreview,
  getRuntimeSettings,
  getWorkspaceEvents,
  getWorkspaceCustomScript,
  getWorkspaceDetail,
  getWorkspaceMethods,
  getWorkspaceRecommendations,
  getWorkspaceTraffic,
  importWorkspaceTraffic,
  listWorkspaceCustomScripts,
  moveHookPlanItem,
  openWorkspacePath,
  openWorkspaceInJadx,
  removeHookPlanItem,
  saveRuntimeSettings,
  setHookPlanItemEnabled,
  saveWorkspaceCustomScript,
  startLiveTrafficCapture,
  startExecution,
  stopLiveTrafficCapture,
  updateWorkspaceCustomScript,
  deleteWorkspaceCustomScript,
} from "../lib/api";
import type { WorkspaceRuntimeSummary } from "../lib/types";
import { copyTextToClipboard } from "../lib/clipboard";
import { connectWorkspaceEvents } from "../lib/ws";

vi.mock("../lib/api", () => ({
  addCustomScriptToHookPlan: vi.fn(),
  addMethodToHookPlan: vi.fn(),
  addRecommendationToHookPlan: vi.fn(),
  addTemplateToHookPlan: vi.fn(),
  cancelExecution: vi.fn(),
  clearHookPlan: vi.fn(),
  exportReport: vi.fn(),
  getEnvironmentStatus: vi.fn(),
  getExecutionHistory: vi.fn(),
  getExecutionHistoryEvents: vi.fn(),
  getExecutionPreflight: vi.fn(),
  getHookPlan: vi.fn(),
  getLiveTrafficCapture: vi.fn(),
  getLiveTrafficPreview: vi.fn(),
  getRuntimeSettings: vi.fn(),
  getWorkspaceEvents: vi.fn(),
  getWorkspaceCustomScript: vi.fn(),
  getWorkspaceDetail: vi.fn(),
  getWorkspaceMethods: vi.fn(),
  getWorkspaceRecommendations: vi.fn(),
  getWorkspaceTraffic: vi.fn(),
  normalizeConnectedDevices: vi.fn((environment: { connected_devices?: unknown[] }) =>
    Array.isArray(environment.connected_devices)
      ? environment.connected_devices
          .map((entry) => {
            if (typeof entry === "string") {
              const serial = entry.trim();
              return serial
                ? {
                    serial,
                    label: serial,
                    status: null,
                    detail: null,
                    model: null,
                    transport: null,
                    recommended: false,
                  }
                : null;
            }
            if (!entry || typeof entry !== "object") {
              return null;
            }
            const record = entry as Record<string, unknown>;
            const serial =
              typeof record.serial === "string"
                ? record.serial
                : typeof record.device_serial === "string"
                  ? record.device_serial
                  : typeof record.id === "string"
                    ? record.id
                    : typeof record.value === "string"
                      ? record.value
                      : "";
            if (!serial) {
              return null;
            }
            const label =
              typeof record.label === "string"
                ? record.label
                : typeof record.name === "string"
                  ? record.name
                  : typeof record.title === "string"
                    ? record.title
                    : serial;
            return {
              serial,
              label,
              status:
                typeof record.status === "string"
                  ? record.status
                  : typeof record.state === "string"
                    ? record.state
                    : typeof record.device_status === "string"
                      ? record.device_status
                      : null,
              detail: typeof record.detail === "string" ? record.detail : typeof record.message === "string" ? record.message : null,
              model:
                typeof record.model === "string"
                  ? record.model
                  : typeof record.device_model === "string"
                    ? record.device_model
                    : null,
              transport:
                typeof record.transport === "string"
                  ? record.transport
                  : typeof record.connection_type === "string"
                    ? record.connection_type
                    : typeof record.connection === "string"
                      ? record.connection
                      : null,
              recommended:
                record.recommended === true ||
                record.is_recommended === true ||
                record.selected === true ||
                record.is_selected === true,
            };
          })
          .filter((device): device is {
            serial: string;
            label: string;
            status: string | null;
            detail: string | null;
            model: string | null;
            transport: string | null;
            recommended: boolean;
          } => device !== null)
          .filter((device, index, devices) => devices.findIndex((candidate) => candidate.serial === device.serial) === index)
      : [],
  ),
  resolveRecommendedDeviceSerial: vi.fn((environment: { recommended_device_serial?: unknown; connected_devices?: unknown[] }) => {
    if (typeof environment.recommended_device_serial === "string" && environment.recommended_device_serial.trim()) {
      return environment.recommended_device_serial.trim();
    }
    const devices = Array.isArray(environment.connected_devices)
      ? environment.connected_devices
          .map((entry) => (typeof entry === "string" ? entry.trim() : typeof entry === "object" && entry !== null ? (entry as { serial?: unknown; device_serial?: unknown; recommended?: unknown }).serial ?? (entry as { serial?: unknown; device_serial?: unknown; recommended?: unknown }).device_serial : ""))
          .filter((serial): serial is string => typeof serial === "string" && serial.length > 0)
      : [];
    return devices[0] ?? null;
  }),
  resolvePreferredDeviceSerial: vi.fn(
    (
      runtimeSettings: { device_serial: string },
      connectedDevices: { serial: string }[],
      recommendedDeviceSerial: string | null,
    ) => runtimeSettings.device_serial.trim() || recommendedDeviceSerial || connectedDevices[0]?.serial || "",
  ),
  importWorkspaceTraffic: vi.fn(),
  listWorkspaceCustomScripts: vi.fn(),
  moveHookPlanItem: vi.fn(),
  openWorkspacePath: vi.fn(),
  openWorkspaceInJadx: vi.fn(),
  removeHookPlanItem: vi.fn(),
  saveRuntimeSettings: vi.fn(),
  setHookPlanItemEnabled: vi.fn(),
  saveWorkspaceCustomScript: vi.fn(),
  startLiveTrafficCapture: vi.fn(),
  startExecution: vi.fn(),
  stopLiveTrafficCapture: vi.fn(),
  updateWorkspaceCustomScript: vi.fn(),
  deleteWorkspaceCustomScript: vi.fn(),
}));

vi.mock("../lib/ws", () => ({
  connectWorkspaceEvents: vi.fn(),
}));

vi.mock("../lib/clipboard", () => ({
  copyTextToClipboard: vi.fn(),
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

function hasExactTextContent(expected: string): (_: string, element: Element | null) => boolean {
  return (_content: string, element: Element | null) => element?.textContent === expected;
}

describe("CaseWorkspacePage", () => {
  beforeEach(() => {
    vi.mocked(addCustomScriptToHookPlan).mockReset();
    vi.mocked(addMethodToHookPlan).mockReset();
    vi.mocked(addRecommendationToHookPlan).mockReset();
    vi.mocked(cancelExecution).mockReset();
    vi.mocked(clearHookPlan).mockReset();
    vi.mocked(exportReport).mockReset();
    vi.mocked(getEnvironmentStatus).mockReset();
    vi.mocked(getExecutionHistory).mockReset();
    vi.mocked(getExecutionHistoryEvents).mockReset();
    vi.mocked(getExecutionPreflight).mockReset();
    vi.mocked(getHookPlan).mockReset();
    vi.mocked(getLiveTrafficCapture).mockReset();
    vi.mocked(getLiveTrafficPreview).mockReset();
    vi.mocked(getRuntimeSettings).mockReset();
    vi.mocked(getWorkspaceEvents).mockReset();
    vi.mocked(getWorkspaceCustomScript).mockReset();
    vi.mocked(getWorkspaceDetail).mockReset();
    vi.mocked(getWorkspaceMethods).mockReset();
    vi.mocked(getWorkspaceRecommendations).mockReset();
    vi.mocked(getWorkspaceTraffic).mockReset();
    vi.mocked(importWorkspaceTraffic).mockReset();
    vi.mocked(listWorkspaceCustomScripts).mockReset();
    vi.mocked(moveHookPlanItem).mockReset();
    vi.mocked(openWorkspacePath).mockReset();
    vi.mocked(openWorkspaceInJadx).mockReset();
    vi.mocked(removeHookPlanItem).mockReset();
    vi.mocked(saveRuntimeSettings).mockReset();
    vi.mocked(setHookPlanItemEnabled).mockReset();
    vi.mocked(saveWorkspaceCustomScript).mockReset();
    vi.mocked(startLiveTrafficCapture).mockReset();
    vi.mocked(startExecution).mockReset();
    vi.mocked(stopLiveTrafficCapture).mockReset();
    vi.mocked(updateWorkspaceCustomScript).mockReset();
    vi.mocked(deleteWorkspaceCustomScript).mockReset();
    vi.mocked(copyTextToClipboard).mockReset();
    vi.mocked(connectWorkspaceEvents).mockReset();
    vi.mocked(openWorkspacePath).mockResolvedValue({
      path: "/tmp/demo",
      status: "opened",
    });
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
    vi.mocked(copyTextToClipboard).mockResolvedValue();
    vi.mocked(getEnvironmentStatus).mockResolvedValue({
      summary: "5 available, 4 missing",
      recommended_execution_mode: "real_frida_session",
      tools: [
        { name: "jadx", label: "jadx", available: true, path: "/usr/bin/jadx" },
        { name: "jadx-gui", label: "jadx-gui", available: true, path: "/usr/bin/jadx-gui" },
        { name: "apktool", label: "apktool", available: false, path: null },
        { name: "adb", label: "adb", available: true, path: "/usr/bin/adb" },
        { name: "frida", label: "frida", available: false, path: null },
        { name: "mitmdump", label: "mitmdump", available: true, path: "/usr/bin/mitmdump" },
        { name: "mitmproxy", label: "mitmproxy", available: false, path: null },
        { name: "tcpdump", label: "tcpdump", available: false, path: null },
        { name: "python-frida", label: "python-frida", available: true, path: "module:frida" },
      ],
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
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-001",
      updated_at: "2026-04-13T12:00:00Z",
      items: [],
    });
    vi.mocked(getExecutionHistory).mockResolvedValue([]);
    vi.mocked(getExecutionHistoryEvents).mockResolvedValue([]);
    vi.mocked(getExecutionPreflight).mockResolvedValue({
      case_id: "case-001",
      ready: true,
      execution_mode: "real_frida_session",
      executed_backend_key: "real_frida_session",
      executed_backend_label: "Frida Session",
      detail: "ready",
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
    vi.mocked(getWorkspaceEvents).mockResolvedValue([]);
    vi.mocked(getWorkspaceTraffic).mockResolvedValue(null);
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-001",
      status: "idle",
      artifact_path: null,
      message: null,
    });
    vi.mocked(getLiveTrafficPreview).mockResolvedValue({
      case_id: "case-001",
      status: "idle",
      preview_path: null,
      truncated: false,
      items: [],
    });
    vi.mocked(listWorkspaceCustomScripts).mockResolvedValue({ items: [] });
    vi.mocked(saveRuntimeSettings).mockResolvedValue({
      execution_mode: "real_frida_session",
      device_serial: "",
      frida_server_binary_path: "",
      frida_server_remote_path: "",
      frida_session_seconds: "",
      live_capture_listen_host: "0.0.0.0",
      live_capture_listen_port: "8080",
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
      runtime: createRuntimeSummary(),
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
          declaration:
            "public void sendPayload(java.lang.String endpoint, java.util.Map<java.lang.String, java.lang.String> headers)",
          source_preview: "public void sendPayload(...) {\\n    encryptPayload(body);\\n    post(endpoint, headers);\\n}",
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
    expect(screen.getAllByText("com.example.alpha").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Hook 工作台" })).toBeInTheDocument();
    expect(screen.getAllByText(/技术标签/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/危险权限/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/回连端点/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/回连线索/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/加密信号/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/加固线索/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/限制说明/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/自定义脚本/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/方法索引状态/).length).toBeGreaterThan(0);
    expect(screen.getByText("已建立")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "执行控制台" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "证据中心" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "报告与导出" })).toBeInTheDocument();
    expect(screen.getAllByText("执行已启动").length).toBeGreaterThan(0);
    expect(screen.getByText("环境概览：已就绪 5 项，缺失 4 项")).toBeInTheDocument();
    expect(screen.getByText("推荐预设：Frida 会话")).toBeInTheDocument();
    expect(screen.getByText(hasExactTextContent("真实设备就绪（Frida 会话）"))).toBeInTheDocument();
    expect(screen.getByText(hasExactTextContent("Frida 会话就绪"))).toBeInTheDocument();
    expect(screen.getByText(hasExactTextContent("Frida 探测不可用（缺少 frida）"))).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "执行预设" })).toHaveValue("real_frida_session");

    expect(screen.getByRole("textbox", { name: "搜索方法" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "搜索方法" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "在 JADX 中打开" })).toBeInTheDocument();

    expect(await screen.findByText("完整类名")).toBeInTheDocument();
    expect(screen.getAllByText("com.example.alpha.net.ApiClient").length).toBeGreaterThan(0);
    expect(screen.getByText("函数名")).toBeInTheDocument();
    expect(screen.getByText("函数签名")).toBeInTheDocument();
    expect(screen.getByText("回连、加密前")).toBeInTheDocument();

    expect((await screen.findAllByText("优先 Hook 回连方法")).length).toBeGreaterThan(0);
    expect(screen.getByText("建议启用 AES 监控模板")).toBeInTheDocument();
    const recommendationButtons = screen.getAllByRole("button", { name: "查看推荐详情" });
    fireEvent.click(recommendationButtons[0]);
    expect(screen.getAllByText(/模板：okhttp3_unpin\.js/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "收起详情" }));
    fireEvent.click(screen.getAllByRole("button", { name: "查看推荐详情" })[1]);
    expect(screen.getByText(/模板：cipher_monitor\.js/)).toBeInTheDocument();

    expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-001");
    expect(vi.mocked(getEnvironmentStatus)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(getWorkspaceMethods)).toHaveBeenCalledWith("case-001", {
      query: "",
      limit: 120,
      scope: "first_party",
    });
    expect(vi.mocked(getWorkspaceRecommendations)).toHaveBeenCalledWith("case-001", { limit: 6 });
    expect(vi.mocked(getHookPlan)).toHaveBeenCalledWith("case-001");
    expect(vi.mocked(connectWorkspaceEvents)).toHaveBeenCalled();
  });

  it("allows adding methods and recommendations into the hook plan", async () => {
    const method = {
      class_name: "com.example.alpha.net.ApiClient",
      method_name: "sendPayload",
      parameter_types: ["java.lang.String", "java.util.Map"],
      return_type: "void",
      is_constructor: false,
      overload_count: 2,
      source_path: "com/example/alpha/net/ApiClient.java",
      line_hint: 142,
      declaration:
        "public void sendPayload(java.lang.String endpoint, java.util.Map<java.lang.String, java.lang.String> headers)",
      source_preview: "public void sendPayload(...) {\n    encryptPayload(body);\n    post(endpoint, headers);\n}",
      tags: ["回连", "加密前"],
      evidence: ["命中 callback clue"],
    };
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-010",
      title: "Hook 计划样本",
      package_name: "com.example.alpha",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: true,
      has_method_index: true,
      method_count: 1,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [method],
      total: 1,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [
        {
          recommendation_id: "rec-10",
          kind: "method",
          title: "优先 Hook sendPayload",
          reason: "命中回连链路",
          score: 90,
          matched_terms: ["回连"],
          method,
          template_id: null,
          template_name: null,
          plugin_id: null,
        },
      ],
    });
    vi.mocked(addMethodToHookPlan).mockResolvedValue({
      case_id: "case-010",
      updated_at: "2026-04-13T12:10:00Z",
      items: [
        {
          item_id: "item-method",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "Java.perform(function() { /* sendPayload */ });",
          method,
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(addRecommendationToHookPlan).mockResolvedValue({
      case_id: "case-010",
      updated_at: "2026-04-13T12:11:00Z",
      items: [
        {
          item_id: "item-method",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "Java.perform(function() { /* sendPayload */ });",
          method,
          template_name: null,
          script_name: null,
          script_path: null,
        },
        {
          item_id: "item-template",
          kind: "template_hook",
          inject_order: 2,
          enabled: true,
          plugin_id: "builtin.network",
          rendered_script: "Java.perform(function() { /* recommendation */ });",
          method: null,
          template_name: "okhttp3_unpin.js",
          script_name: null,
          script_path: null,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-010"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("函数详情")).toBeInTheDocument();
    const initialToggle = await screen.findByRole("button", { name: /重载$/ });
    if (initialToggle.textContent?.includes("展开")) {
      fireEvent.click(initialToggle);
    }
    fireEvent.click(await screen.findByRole("button", { name: "查看此函数" }));
    expect(
      await screen.findByText(
        (content) =>
          content.includes(
            "反编译声明：public void sendPayload(java.lang.String endpoint, java.util.Map<java.lang.String, java.lang.String> headers)",
          ),
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/encryptPayload\(body\)/)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "将当前函数加入 Hook 计划" }));
    await waitFor(() => {
      expect(vi.mocked(addMethodToHookPlan)).toHaveBeenCalledWith("case-010", method);
    });
    expect(await screen.findByText("method_hook #1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看详情" }));
    fireEvent.click(screen.getByText("查看渲染脚本预览"));
    expect(screen.getByText("Java.perform(function() { /* sendPayload */ });")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "接受推荐并加入 Hook 计划" }));
    await waitFor(() => {
      expect(vi.mocked(addRecommendationToHookPlan)).toHaveBeenCalledWith("case-010", "rec-10");
    });
    expect(await screen.findByText("template_hook #2")).toBeInTheDocument();
  });

  it("supports class-oriented method browsing in the hook studio", async () => {
    const sendPayloadMethod = {
      class_name: "com.example.alpha.net.ApiClient",
      method_name: "sendPayload",
      parameter_types: ["java.lang.String"],
      return_type: "void",
      is_constructor: false,
      overload_count: 1,
      source_path: "com/example/alpha/net/ApiClient.java",
      line_hint: 41,
      declaration: "public void sendPayload(java.lang.String endpoint)",
      source_preview: "public void sendPayload(...) {\n    post(endpoint);\n}",
      tags: ["回连"],
      evidence: ["命中 callback clue"],
    };
    const sendPayloadWithHeadersMethod = {
      class_name: "com.example.alpha.net.ApiClient",
      method_name: "sendPayload",
      parameter_types: ["java.lang.String", "java.util.Map<java.lang.String, java.lang.String>"],
      return_type: "void",
      is_constructor: false,
      overload_count: 2,
      source_path: "com/example/alpha/net/ApiClient.java",
      line_hint: 57,
      declaration:
        "public void sendPayload(java.lang.String endpoint, java.util.Map<java.lang.String, java.lang.String> headers)",
      source_preview: "public void sendPayload(...) {\n    applyHeaders(headers);\n    post(endpoint, headers);\n}",
      tags: ["回连", "请求头"],
      evidence: ["命中网络线索"],
    };
    const collectFingerprintMethod = {
      class_name: "com.example.alpha.collect.DeviceCollector",
      method_name: "collectFingerprint",
      parameter_types: [],
      return_type: "java.lang.String",
      is_constructor: false,
      overload_count: 1,
      source_path: "com/example/alpha/collect/DeviceCollector.java",
      line_hint: 88,
      declaration: "public java.lang.String collectFingerprint()",
      source_preview: "public String collectFingerprint() {\n    return androidId + imei;\n}",
      tags: ["设备指纹"],
      evidence: ["命中敏感数据线索"],
    };

    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-012",
      title: "类导航样本",
      package_name: "com.example.alpha",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: true,
      has_method_index: true,
      method_count: 2,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [sendPayloadMethod, sendPayloadWithHeadersMethod, collectFingerprintMethod],
      total: 3,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });

    render(
      <MemoryRouter initialEntries={["/workspace/case-012"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("button", { name: /ApiClient/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /DeviceCollector/ })).toBeInTheDocument();
    expect(screen.getByText("当前类：com.example.alpha.net.ApiClient")).toBeInTheDocument();
    expect(screen.getByText("当前类下共 2 个方法入口，1 组同名函数。")).toBeInTheDocument();
    expect(screen.getByText("sendPayload · 2 个重载")).toBeInTheDocument();
    const activeGroupToggle = screen.getByRole("button", { name: /重载$/ });
    if (activeGroupToggle.textContent?.includes("展开")) {
      fireEvent.click(activeGroupToggle);
    }
    fireEvent.click(screen.getAllByRole("button", { name: "查看此函数" })[0]);
    expect(screen.getByText(/反编译声明：public void sendPayload\(java\.lang\.String endpoint\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /DeviceCollector/ }));

    expect(await screen.findByText("当前类：com.example.alpha.collect.DeviceCollector")).toBeInTheDocument();
    const collectorToggle = screen.getByRole("button", { name: /重载$/ });
    if (collectorToggle.textContent?.includes("展开")) {
      fireEvent.click(collectorToggle);
    }
    fireEvent.click(screen.getByRole("button", { name: "查看此函数" }));
    expect(await screen.findByText(/反编译声明：public java\.lang\.String collectFingerprint\(\)/)).toBeInTheDocument();
    expect(screen.getByText(/androidId \+ imei/)).toBeInTheDocument();
  });

  it("switches the method browser between first-party and all-method scopes", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-012a",
      title: "范围切换样本",
      package_name: "com.example.alpha",
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
      method_count: 25,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods)
      .mockResolvedValueOnce({
        items: [],
        total: 25,
        scope: "first_party",
        available_scopes: ["first_party", "related_candidates", "all"],
      })
      .mockResolvedValueOnce({
        items: [
          {
            class_name: "com.example.traffic.inspect.UploadClient",
            method_name: "send",
            parameter_types: ["java.lang.String"],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/traffic/inspect/UploadClient.java",
            line_hint: 21,
            declaration: "public void send(java.lang.String payload)",
            source_preview: "public void send(String payload) { return; }",
            tags: ["first-party"],
            evidence: [],
          },
          {
            class_name: "okhttp3.internal.tls.CertificateChainCleaner",
            method_name: "clean",
            parameter_types: ["java.util.List", "java.lang.String"],
            return_type: "java.util.List",
            is_constructor: false,
            overload_count: 1,
            source_path: "okhttp3/internal/tls/CertificateChainCleaner.java",
            line_hint: 48,
            declaration:
              "public java.util.List clean(java.util.List chain, java.lang.String hostname)",
            source_preview:
              "public java.util.List clean(...) {\\n    return clean(chain, hostname, certificatePinner);\\n}",
            tags: ["相关候选", "ssl"],
            evidence: ["命中 callback clue", "命中 ssl"],
          },
        ],
        total: 438,
        scope: "related_candidates",
        available_scopes: ["first_party", "related_candidates", "all"],
      })
      .mockResolvedValueOnce({
        items: [],
        total: 20418,
        scope: "all",
        available_scopes: ["first_party", "related_candidates", "all"],
      });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });

    render(
      <MemoryRouter initialEntries={["/workspace/case-012a"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Hook 工作台" })).toBeInTheDocument();
    expect(
      await screen.findByText((content) => content.includes("当前范围：一方代码") && content.includes("25 个方法")),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "相关候选" }));

    await waitFor(() => {
      expect(vi.mocked(getWorkspaceMethods)).toHaveBeenLastCalledWith("case-012a", {
        query: "",
        limit: 120,
        scope: "related_candidates",
      });
    });
    expect(
      await screen.findByText((content) => content.includes("当前范围：相关候选") && content.includes("438 个方法")),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "相关候选" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("button", { name: /CertificateChainCleaner/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "全部方法" }));

    await waitFor(() => {
      expect(vi.mocked(getWorkspaceMethods)).toHaveBeenLastCalledWith("case-012a", {
        query: "",
        limit: 120,
        scope: "all",
      });
    });
    expect(
      await screen.findByText((content) => content.includes("当前范围：全部方法") && content.includes("20418 个方法")),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "全部方法" })).toHaveAttribute("aria-pressed", "true");
  });

  it("supports saving a custom script and adding it into the hook plan", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-011",
      title: "自定义脚本样本",
      package_name: "com.example.custom",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(saveWorkspaceCustomScript).mockResolvedValue({
      script_id: "script-local",
      name: "本地脚本",
      script_path: "/tmp/workspaces/case-011/hooks/custom/local.js",
    });
    vi.mocked(addCustomScriptToHookPlan).mockResolvedValue({
      case_id: "case-011",
      updated_at: "2026-04-13T12:12:00Z",
      items: [
        {
          item_id: "item-script",
          kind: "custom_script",
          inject_order: 1,
          enabled: true,
          plugin_id: "custom.local-script",
          rendered_script: "send({ type: 'custom' });",
          method: null,
          template_name: null,
          script_name: "本地脚本",
          script_path: "/tmp/workspaces/case-011/hooks/custom/local.js",
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-011"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByRole("textbox", { name: "脚本名称" }), {
      target: { value: "本地脚本" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "脚本内容" }), {
      target: { value: "send({ type: 'custom' });" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存脚本" }));

    await waitFor(() => {
      expect(vi.mocked(saveWorkspaceCustomScript)).toHaveBeenCalledWith("case-011", {
        name: "本地脚本",
        content: "send({ type: 'custom' });",
      });
    });

    fireEvent.click(await screen.findByRole("button", { name: "查看详情" }));
    fireEvent.click(await screen.findByRole("button", { name: "将脚本加入 Hook 计划" }));
    await waitFor(() => {
      expect(vi.mocked(addCustomScriptToHookPlan)).toHaveBeenCalledWith("case-011", "script-local");
    });
    expect(await screen.findByText("custom_script #1")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "查看详情" })[0]);
    fireEvent.click(screen.getByText("查看渲染脚本预览"));
    expect(screen.getAllByText("send({ type: 'custom' });")).toHaveLength(2);
  });

  it("loads, updates, and deletes a custom script from the hook studio", async () => {
    const originalScriptId = "custom_script:/tmp/workspaces/case-011c/hooks/custom/trace_login.js";
    const updatedScriptId = "custom_script:/tmp/workspaces/case-011c/hooks/custom/trace_login_v2.js";

    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-011c",
      title: "自定义脚本 CRUD 样本",
      package_name: "com.example.custom.crud",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [
        {
          script_id: originalScriptId,
          name: "trace_login",
          script_path: "/tmp/workspaces/case-011c/hooks/custom/trace_login.js",
        },
      ],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(listWorkspaceCustomScripts).mockResolvedValue({
      items: [
        {
          script_id: originalScriptId,
          name: "trace_login",
          script_path: "/tmp/workspaces/case-011c/hooks/custom/trace_login.js",
        },
      ],
    });
    vi.mocked(getWorkspaceCustomScript).mockResolvedValue({
      script_id: originalScriptId,
      name: "trace_login",
      script_path: "/tmp/workspaces/case-011c/hooks/custom/trace_login.js",
      content: "send('v1');\n",
    });
    vi.mocked(updateWorkspaceCustomScript).mockResolvedValue({
      script_id: updatedScriptId,
      name: "trace_login_v2",
      script_path: "/tmp/workspaces/case-011c/hooks/custom/trace_login_v2.js",
    });
    vi.mocked(deleteWorkspaceCustomScript).mockResolvedValue();

    render(
      <MemoryRouter initialEntries={["/workspace/case-011c"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "加载到编辑器" }));

    await waitFor(() => {
      expect(vi.mocked(getWorkspaceCustomScript)).toHaveBeenCalledWith("case-011c", originalScriptId);
    });
    expect(screen.getByRole("textbox", { name: "脚本名称" })).toHaveValue("trace_login");
    expect(screen.getByRole("textbox", { name: "脚本内容" })).toHaveValue("send('v1');\n");
    expect(screen.getByRole("button", { name: "更新脚本" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "脚本名称" }), {
      target: { value: "trace_login_v2" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "脚本内容" }), {
      target: { value: "send('v2');\n" },
    });
    fireEvent.click(screen.getByRole("button", { name: "更新脚本" }));

    await waitFor(() => {
      expect(vi.mocked(updateWorkspaceCustomScript)).toHaveBeenCalledWith("case-011c", originalScriptId, {
        name: "trace_login_v2",
        content: "send('v2');\n",
      });
    });
    expect(await screen.findByText("已更新脚本 trace_login_v2。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看详情" }));
    fireEvent.click(screen.getByRole("button", { name: "删除脚本" }));

    await waitFor(() => {
      expect(vi.mocked(deleteWorkspaceCustomScript)).toHaveBeenCalledWith("case-011c", updatedScriptId);
    });
    expect(await screen.findByText("已删除脚本 trace_login_v2。")).toBeInTheDocument();
    expect(screen.getByText("当前还没有自定义脚本。")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "脚本名称" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "脚本内容" })).toHaveValue("");
  });

  it("shows the backend validation message when saving a custom script fails", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-011b",
      title: "自定义脚本错误样本",
      package_name: "com.example.custom.error",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(saveWorkspaceCustomScript).mockRejectedValue(
      new Error("保存自定义脚本失败：Script name can only contain letters, numbers, dot, dash, and underscore."),
    );

    render(
      <MemoryRouter initialEntries={["/workspace/case-011b"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByRole("textbox", { name: "脚本名称" }), {
      target: { value: "bad script name" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "脚本内容" }), {
      target: { value: "send({ type: 'custom' });" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存脚本" }));

    expect(
      await screen.findByText("保存自定义脚本失败：Script name can only contain letters, numbers, dot, dash, and underscore."),
    ).toBeInTheDocument();
  });

  it("clears the hook plan in Chinese workspace flow", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-012",
      title: "清空计划样本",
      package_name: "com.example.clear",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-012",
      updated_at: "2026-04-13T12:15:00Z",
      items: [
        {
          item_id: "item-existing",
          kind: "template_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.network",
          rendered_script: "Java.perform(function() { /* okhttp */ });",
          method: null,
          template_name: "okhttp3_unpin.js",
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(clearHookPlan).mockResolvedValue({
      case_id: "case-012",
      updated_at: "2026-04-13T12:16:00Z",
      items: [],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-012"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("template_hook #1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "清空 Hook 计划" }));

    await waitFor(() => {
      expect(vi.mocked(clearHookPlan)).toHaveBeenCalledWith("case-012");
    });
    expect(await screen.findByText("当前还没有 Hook 计划项。")).toBeInTheDocument();
  });

  it("toggles a hook plan item between enabled and disabled", async () => {
    const method = {
      class_name: "com.example.ToggleHooks",
      method_name: "upload",
      parameter_types: ["java.lang.String"],
      return_type: "void",
      is_constructor: false,
      overload_count: 1,
      source_path: "sources/com/example/ToggleHooks.java",
      line_hint: 21,
      tags: ["回连"],
      evidence: ["命中上传链路"],
    };

    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-013",
      title: "启停计划样本",
      package_name: "com.example.toggle",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-013",
      updated_at: "2026-04-18T10:10:00Z",
      items: [
        {
          item_id: "item-toggle",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "send('enabled');",
          method,
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(setHookPlanItemEnabled).mockResolvedValue({
      case_id: "case-013",
      updated_at: "2026-04-18T10:11:00Z",
      items: [
        {
          item_id: "item-toggle",
          kind: "method_hook",
          inject_order: 1,
          enabled: false,
          plugin_id: "builtin.method-hook",
          rendered_script: "send('enabled');",
          method,
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-013"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("状态：已启用")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "禁用 method_hook #1" }));

    await waitFor(() => {
      expect(vi.mocked(setHookPlanItemEnabled)).toHaveBeenCalledWith("case-013", "item-toggle", false);
    });
    expect(await screen.findByText("状态：已禁用")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "启用 method_hook #1" })).toBeInTheDocument();
  });

  it("moves hook plan items up and down from the workspace hook studio", async () => {
    const method = {
      class_name: "com.example.OrderHooks",
      method_name: "upload",
      parameter_types: ["java.lang.String"],
      return_type: "void",
      is_constructor: false,
      overload_count: 1,
      source_path: "sources/com/example/OrderHooks.java",
      line_hint: 34,
      tags: ["网络"],
      evidence: ["命中上传调用"],
    };

    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-014",
      title: "排序计划样本",
      package_name: "com.example.move",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-014",
      updated_at: "2026-04-18T10:15:00Z",
      items: [
        {
          item_id: "item-method",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "send('method');",
          method,
          template_name: null,
          script_name: null,
          script_path: null,
        },
        {
          item_id: "item-template",
          kind: "template_hook",
          inject_order: 2,
          enabled: true,
          plugin_id: "builtin.ssl",
          rendered_script: "send('template');",
          method: null,
          template_name: "okhttp3_unpin.js",
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(moveHookPlanItem)
      .mockResolvedValueOnce({
        case_id: "case-014",
        updated_at: "2026-04-18T10:16:00Z",
        items: [
          {
            item_id: "item-template",
            kind: "template_hook",
            inject_order: 1,
            enabled: true,
            plugin_id: "builtin.ssl",
            rendered_script: "send('template');",
            method: null,
            template_name: "okhttp3_unpin.js",
            script_name: null,
            script_path: null,
          },
          {
            item_id: "item-method",
            kind: "method_hook",
            inject_order: 2,
            enabled: true,
            plugin_id: "builtin.method-hook",
            rendered_script: "send('method');",
            method,
            template_name: null,
            script_name: null,
            script_path: null,
          },
        ],
      })
      .mockResolvedValueOnce({
        case_id: "case-014",
        updated_at: "2026-04-18T10:17:00Z",
        items: [
          {
            item_id: "item-method",
            kind: "method_hook",
            inject_order: 1,
            enabled: true,
            plugin_id: "builtin.method-hook",
            rendered_script: "send('method');",
            method,
            template_name: null,
            script_name: null,
            script_path: null,
          },
          {
            item_id: "item-template",
            kind: "template_hook",
            inject_order: 2,
            enabled: true,
            plugin_id: "builtin.ssl",
            rendered_script: "send('template');",
            method: null,
            template_name: "okhttp3_unpin.js",
            script_name: null,
            script_path: null,
          },
        ],
      });

    render(
      <MemoryRouter initialEntries={["/workspace/case-014"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("method_hook #1")).toBeInTheDocument();
    expect(screen.getByText("template_hook #2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "上移 template_hook #2" }));

    await waitFor(() => {
      expect(vi.mocked(moveHookPlanItem)).toHaveBeenCalledWith("case-014", "item-template", "up");
    });
    expect(await screen.findByText("template_hook #1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "下移 template_hook #1" }));
    await waitFor(() => {
      expect(vi.mocked(moveHookPlanItem)).toHaveBeenCalledWith("case-014", "item-template", "down");
    });
    expect(await screen.findByText("method_hook #1")).toBeInTheDocument();
    expect(screen.getByText("template_hook #2")).toBeInTheDocument();
  });

  it("shows a Chinese fallback when the workspace has no method index", async () => {
    const refreshDeferred = createDeferred<Awaited<ReturnType<typeof getWorkspaceDetail>>>();

    vi.mocked(getWorkspaceDetail)
      .mockResolvedValueOnce({
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
        runtime: createRuntimeSummary(),
      })
      .mockImplementationOnce(() => refreshDeferred.promise);

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
    await waitFor(() => {
      expect(vi.mocked(getWorkspaceDetail)).toHaveBeenCalledWith("case-002", {
        refresh: true,
        timeoutMs: 30000,
      });
    });
    expect(screen.getByLabelText("方法索引重建状态")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "方法索引重建进度" })).toBeInTheDocument();
    expect(screen.getByText("方法索引重建中")).toBeInTheDocument();

    await act(async () => {
      refreshDeferred.resolve({
        case_id: "case-002",
        title: "Beta 样本",
        package_name: "com.example.beta",
        technical_tags: [],
        dangerous_permissions: [],
        callback_endpoints: [],
        callback_clues: [],
        crypto_signals: [],
        packer_hints: [],
        limitations: [],
        custom_scripts: [],
        can_open_in_jadx: false,
        has_method_index: true,
        method_count: 3,
        runtime: createRuntimeSummary(),
      });
      await refreshDeferred.promise;
    });

    expect(await screen.findByText("方法索引已刷新，共发现 3 个函数入口。")).toBeInTheDocument();
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
      runtime: createRuntimeSummary(),
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

  it("loads and forwards runtime settings when starting execution", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-001",
      title: "Alpha 样本",
      package_name: "com.example.alpha",
      technical_tags: ["okhttp3", "uniapp"],
      dangerous_permissions: ["READ_SMS", "CAMERA"],
      callback_endpoints: ["https://c2.example.com/api"],
      callback_clues: ["动态拼接 URL", "硬编码鉴权头"],
      crypto_signals: ["AES/CBC", "Base64"],
      packer_hints: ["无明显加固"],
      limitations: ["未连接真实设备"],
      custom_scripts: [],
      can_open_in_jadx: true,
      has_method_index: true,
      method_count: 12,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [],
      total: 0,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-001",
      updated_at: "2026-04-13T12:00:00Z",
      items: [
        {
          item_id: "plan-1",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: null,
          rendered_script: "Java.perform(function() { /* ready */ });",
          method: {
            class_name: "com.example.alpha.Login",
            method_name: "submit",
            parameter_types: ["java.lang.String"],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/alpha/Login.java",
            line_hint: 12,
            tags: [],
            evidence: [],
          },
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(getRuntimeSettings).mockResolvedValue({
      execution_mode: "real_frida_session",
      device_serial: "emulator-5554",
      frida_server_binary_path: "/tmp/frida-server",
      frida_server_remote_path: "/data/local/tmp/frida-server",
      frida_session_seconds: "3.5",
      live_capture_listen_host: "0.0.0.0",
      live_capture_listen_port: "8080",
    });
    vi.mocked(connectWorkspaceEvents).mockImplementation(() => ({
      close: vi.fn(),
    }));
    vi.mocked(startExecution).mockResolvedValue({
      case_id: "case-001",
      status: "started",
      execution_mode: "real_frida_session",
      executed_backend_key: "real_frida_session",
      stage: "queued",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-001"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByDisplayValue("emulator-5554")).toBeInTheDocument();
    expect(screen.getByDisplayValue("/tmp/frida-server")).toBeInTheDocument();
    expect(screen.getByDisplayValue("/data/local/tmp/frida-server")).toBeInTheDocument();
    expect(screen.getByDisplayValue("3.5")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("设备序列号"), { target: { value: "usb-serial-1" } });
    fireEvent.change(screen.getByLabelText("Frida Server 文件"), { target: { value: "/opt/frida-server" } });
    fireEvent.change(screen.getByLabelText("远端路径"), { target: { value: "/data/local/tmp/fs" } });
    fireEvent.change(screen.getByLabelText("会话时长（秒）"), { target: { value: "5.0" } });
    fireEvent.click(screen.getByRole("button", { name: "启动执行" }));

    await waitFor(() =>
      expect(vi.mocked(startExecution)).toHaveBeenCalledWith("case-001", {
        executionMode: "real_frida_session",
        deviceSerial: "usb-serial-1",
        fridaServerBinaryPath: "/opt/frida-server",
        fridaServerRemotePath: "/data/local/tmp/fs",
        fridaSessionSeconds: "5.0",
      }),
    );
    await waitFor(() =>
      expect(vi.mocked(saveRuntimeSettings)).toHaveBeenCalledWith({
        execution_mode: "real_frida_session",
        device_serial: "usb-serial-1",
        frida_server_binary_path: "/opt/frida-server",
        frida_server_remote_path: "/data/local/tmp/fs",
        frida_session_seconds: "5.0",
        live_capture_listen_host: "0.0.0.0",
        live_capture_listen_port: "8080",
      }),
    );
  });

  it("prefers connected device selection in the execution console and keeps manual fallback available", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-device-picker",
      title: "设备选择样本",
      package_name: "com.example.devicepicker",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-device-picker",
      updated_at: "2026-04-13T12:00:00Z",
      items: [
        {
          item_id: "item-device-picker",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "Java.perform(function() { /* ready */ });",
          method: {
            class_name: "com.example.devicepicker.Entry",
            method_name: "run",
            parameter_types: [],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/devicepicker/Entry.java",
            line_hint: 10,
            tags: [],
            evidence: [],
          },
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
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
    vi.mocked(getEnvironmentStatus).mockResolvedValue({
      summary: "6 available, 3 missing",
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
          key: "real_frida_session",
          label: "Frida Session",
          available: true,
          detail: "ready",
        },
      ],
      connected_devices: [
        {
          device_serial: "usb-serial-1",
          label: "Pixel 8",
          status: "online",
          detail: "USB 已连接",
          model: "Pixel 8",
          recommended: true,
        },
        {
          serial: "usb-serial-2",
          name: "Pixel 8 Pro",
          status: "online",
          detail: "USB 已连接",
          model: "Pixel 8 Pro",
        },
      ],
      recommended_device_serial: "usb-serial-1",
    });
    vi.mocked(startExecution).mockResolvedValue({
      case_id: "case-device-picker",
      status: "started",
      execution_mode: "real_frida_session",
      executed_backend_key: "real_frida_session",
      stage: "queued",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-device-picker"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("当前设备：Pixel 8")).toBeInTheDocument();
    const deviceSelect = await screen.findByRole("combobox", { name: "真实设备列表" });
    expect(deviceSelect).toHaveValue("usb-serial-1");
    expect(screen.getByRole("textbox", { name: "设备序列号" })).toHaveValue("usb-serial-1");
    expect(screen.getByText("状态：已连接")).toBeInTheDocument();
    expect(screen.getByText("设备列表：已识别 2 台")).toBeInTheDocument();

    fireEvent.change(deviceSelect, { target: { value: "usb-serial-2" } });
    expect(await screen.findByText("当前设备：Pixel 8 Pro")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "启动执行" }));

    await waitFor(() =>
      expect(vi.mocked(saveRuntimeSettings)).toHaveBeenCalledWith({
        execution_mode: "real_frida_session",
        device_serial: "usb-serial-2",
        frida_server_binary_path: "",
        frida_server_remote_path: "",
        frida_session_seconds: "",
        live_capture_listen_host: "0.0.0.0",
        live_capture_listen_port: "8080",
      }),
    );
    await waitFor(() =>
      expect(vi.mocked(startExecution)).toHaveBeenCalledWith("case-device-picker", {
        executionMode: "real_frida_session",
        deviceSerial: "usb-serial-2",
        fridaServerBinaryPath: "",
        fridaServerRemotePath: "",
        fridaSessionSeconds: "",
      }),
    );
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

    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((node) => node.textContent?.includes("案件工作台暂时不可用。"))).toBe(true);
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
      runtime: createRuntimeSummary(),
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

  it("shows a Chinese blocked reason when execution preflight is not ready", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-preflight",
      title: "预检样本",
      package_name: "com.example.preflight",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-preflight",
      updated_at: "2026-04-13T12:00:00Z",
      items: [
        {
          item_id: "item-preflight",
          kind: "template_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.ssl",
          rendered_script: "send('template');",
          method: null,
          template_name: "okhttp3_unpin.js",
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(getExecutionPreflight).mockResolvedValue({
      case_id: "case-preflight",
      ready: false,
      execution_mode: "fake_backend",
      executed_backend_key: "fake_backend",
      executed_backend_label: "Fake Backend",
      detail: "Add at least one hook plan item first.",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-preflight"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("当前无法启动执行")).toBeInTheDocument();
    expect(
      await screen.findByText((content) => content.includes("请先添加至少一个 Hook 计划项。")),
    ).toBeInTheDocument();
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
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [],
      total: 0,
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [],
    });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-004",
      updated_at: "2026-04-13T12:20:00Z",
      items: [
        {
          item_id: "item-existing",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "Java.perform(function() { /* ready */ });",
          method: {
            class_name: "com.example.delta.Entry",
            method_name: "run",
            parameter_types: [],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/delta/Entry.java",
            line_hint: 10,
            tags: [],
            evidence: [],
          },
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(startExecution).mockResolvedValue({
      case_id: "case-004",
      status: "started",
      stage: "queued",
      execution_mode: "real_adb_probe",
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

    fireEvent.change(await screen.findByRole("combobox", { name: "执行预设" }), {
      target: { value: "real_adb_probe" },
    });
    const startButton = await screen.findByRole("button", { name: "启动执行" });
    await waitFor(() => {
      expect(startButton).toBeEnabled();
    });

    fireEvent.click(startButton);
    await waitFor(() => {
      expect(vi.mocked(startExecution)).toHaveBeenCalledWith("case-004", {
        executionMode: "real_adb_probe",
        deviceSerial: "",
        fridaServerBinaryPath: "",
        fridaServerRemotePath: "",
        fridaSessionSeconds: "",
      });
    });
    expect(await screen.findByText(hasExactTextContent("当前状态已启动"))).toBeInTheDocument();
    expect(screen.getByText(hasExactTextContent("当前阶段已排队"))).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "导出报告" }));
    await waitFor(() => {
      expect(vi.mocked(exportReport)).toHaveBeenCalledWith("case-004");
    });
    expect(
      (
        await screen.findAllByText((content) =>
          content.includes("/tmp/workspaces/case-004/reports/case-004-report.md"),
        )
      ).length,
    ).toBeGreaterThan(0);
  });

  it("shows a Chinese export error without treating it as a report path", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-report-error",
      title: "导出失败样本",
      package_name: "com.example.report.error",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-report-error",
      updated_at: "2026-04-13T12:26:00Z",
      items: [],
    });
    vi.mocked(exportReport).mockRejectedValue(new Error("boom"));

    render(
      <MemoryRouter initialEntries={["/workspace/case-report-error"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "导出报告" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("报告导出失败，请稍后重试。");
    expect(screen.queryByRole("button", { name: "打开最近导出" })).not.toBeInTheDocument();
  });

  it("shows the backend failure reason when execution start is rejected", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-exec-error",
      title: "执行失败样本",
      package_name: "com.example.error",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-exec-error",
      updated_at: "2026-04-13T12:25:00Z",
      items: [
        {
          item_id: "item-existing",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "Java.perform(function() { /* ready */ });",
          method: {
            class_name: "com.example.error.Entry",
            method_name: "run",
            parameter_types: [],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/error/Entry.java",
            line_hint: 10,
            tags: [],
            evidence: [],
          },
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(connectWorkspaceEvents).mockImplementation(() => ({ close: vi.fn() }));
    vi.mocked(startExecution).mockRejectedValue(
      new Error("启动执行失败：Execution is already running for this case."),
    );

    render(
      <MemoryRouter initialEntries={["/workspace/case-exec-error"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const startButton = await screen.findByRole("button", { name: "启动执行" });
    await waitFor(() => {
      expect(startButton).toBeEnabled();
    });

    fireEvent.click(startButton);

    const failureNodes = await screen.findAllByText((content) =>
      content.includes("当前案件已有执行任务在运行。"),
    );
    expect(failureNodes.length).toBeGreaterThan(0);
  });

  it("shows the latest execution failure reason in Chinese panels", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-failure",
      title: "失败诊断样本",
      package_name: "com.example.failure",
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
      runtime: {
        ...createRuntimeSummary(),
        last_execution_status: "error",
        last_execution_stage: "failed",
        last_execution_mode: "real_frida_session",
        last_executed_backend_key: "real_frida_session",
        last_execution_error_code: "app_install_error",
        last_execution_error_message: "安装样本失败，请检查设备可用空间。",
      },
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-failure",
      updated_at: "2026-04-17T14:00:00Z",
      items: [],
      last_execution_status: "error",
      last_execution_stage: "failed",
      last_execution_mode: "real_frida_session",
      last_executed_backend_key: "real_frida_session",
      last_execution_error_code: "app_install_error",
      last_execution_error_message: "安装样本失败，请检查设备可用空间。",
    });
    vi.mocked(connectWorkspaceEvents).mockImplementation(() => ({ close: vi.fn() }));

    render(
      <MemoryRouter initialEntries={["/workspace/case-failure"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("最近失败原因：安装样本失败，请检查设备可用空间。")).toBeInTheDocument();
    expect(screen.getByText("最近失败分类：安装样本失败")).toBeInTheDocument();
  });

  it("cancels an in-flight execution and shows Chinese cancellation state", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-cancel",
      title: "取消样本",
      package_name: "com.example.cancel",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-cancel",
      updated_at: "2026-04-17T12:00:00Z",
      items: [
        {
          item_id: "item-existing",
          kind: "method_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.method-hook",
          rendered_script: "Java.perform(function() { /* ready */ });",
          method: {
            class_name: "com.example.cancel.Entry",
            method_name: "run",
            parameter_types: [],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/cancel/Entry.java",
            line_hint: 10,
            tags: [],
            evidence: [],
          },
          template_name: null,
          script_name: null,
          script_path: null,
        },
      ],
      last_execution_status: "started",
      last_execution_stage: "executing",
      last_execution_mode: "fake_backend",
      last_executed_backend_key: "fake_backend",
    });
    vi.mocked(connectWorkspaceEvents).mockImplementation(() => ({ close: vi.fn() }));
    vi.mocked(cancelExecution).mockResolvedValue({
      case_id: "case-cancel",
      status: "cancelling",
      execution_mode: "fake_backend",
      executed_backend_key: "fake_backend",
      stage: "cancelling",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-cancel"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText(hasExactTextContent("当前状态已启动"))).toBeInTheDocument();
    expect(screen.getByText(hasExactTextContent("当前阶段执行中"))).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "取消执行" }));

    await waitFor(() => {
      expect(vi.mocked(cancelExecution)).toHaveBeenCalledWith("case-cancel");
    });
    expect(await screen.findByText(hasExactTextContent("当前状态正在取消"))).toBeInTheDocument();
    expect(screen.getByText(hasExactTextContent("当前阶段正在取消"))).toBeInTheDocument();
  });

  it("imports HAR capture and renders traffic evidence in Chinese workspace flow", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-traffic",
      title: "流量样本",
      package_name: "com.example.traffic",
      technical_tags: ["network-callback"],
      dangerous_permissions: [],
      callback_endpoints: ["https://demo-c2.example/api/upload"],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceTraffic).mockResolvedValue(null);
    vi.mocked(importWorkspaceTraffic).mockResolvedValue({
      case_id: "case-traffic",
      source_path: "/tmp/captures/sample.har",
      provenance: {
        kind: "manual_har",
        label: "手工 HAR 导入",
      },
      flow_count: 2,
      suspicious_count: 1,
      https_flow_count: 2,
      matched_indicator_count: 1,
      top_hosts: [
        {
          host: "demo-c2.example",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      suspicious_hosts: [
        {
          host: "demo-c2.example",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      summary: {
        https_flow_count: 2,
        matched_indicator_count: 1,
        top_hosts: [
          {
            host: "demo-c2.example",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
        suspicious_hosts: [
          {
            host: "demo-c2.example",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
      },
      flows: [
        {
          flow_id: "flow-1",
          method: "POST",
          url: "https://demo-c2.example/api/upload",
          status_code: 200,
          mime_type: "application/json",
          request_preview: "{\"device_id\":\"abc\"}",
          response_preview: "{\"ok\":true}",
          matched_indicators: ["demo-c2.example"],
          suspicious: true,
        },
        {
          flow_id: "flow-2",
          method: "GET",
          url: "https://cdn.example.com/ping",
          status_code: 204,
          mime_type: null,
          request_preview: "",
          response_preview: "",
          matched_indicators: [],
          suspicious: false,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-traffic"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "流量证据" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "HAR 文件路径" }), {
      target: { value: "/tmp/captures/sample.har" },
    });
    fireEvent.click(screen.getByRole("button", { name: "导入 HAR" }));

    await waitFor(() => {
      expect(vi.mocked(importWorkspaceTraffic)).toHaveBeenCalledWith("case-traffic", {
        harPath: "/tmp/captures/sample.har",
      });
    });
    expect(await screen.findByText("已加载流量证据")).toBeInTheDocument();
    expect(screen.getByText("来源类型：手工 HAR 导入")).toBeInTheDocument();
    expect(screen.getByText("来源路径：/tmp/captures/sample.har")).toBeInTheDocument();
    expect(screen.getByText("总流量：2")).toBeInTheDocument();
    expect(screen.getByText("可疑流量：1")).toBeInTheDocument();
    expect(screen.getAllByText("HTTPS 请求：2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("命中线索：1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("https://demo-c2.example/api/upload").length).toBeGreaterThan(0);
    expect(screen.getByText("命中线索：demo-c2.example")).toBeInTheDocument();
    expect(screen.getByText("主机摘要：demo-c2.example（1）")).toBeInTheDocument();
    expect(screen.getByText("流量证据：已加载")).toBeInTheDocument();
    expect(screen.getAllByText("流量来源类型：手工 HAR 导入").length).toBeGreaterThan(0);
    expect(screen.getByText("流量来源：/tmp/captures/sample.har")).toBeInTheDocument();
    expect(screen.getAllByText("流量概览：2 条，总计 1 条可疑").length).toBeGreaterThan(0);
  });

  it("shows the live traffic capture status from runtime and api snapshot", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-live",
      title: "实时抓包样本",
      package_name: "com.example.live",
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
      runtime: {
        ...createRuntimeSummary(),
        live_traffic_status: "running",
        live_traffic_artifact_path: "/tmp/workspaces/case-live/traffic/live-last.har",
        live_traffic_message: "实时抓包进行中。",
      },
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live",
      status: "running",
      artifact_path: "/tmp/workspaces/case-live/traffic/live-last.har",
      message: "实时抓包进行中。",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-live"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("实时抓包状态：抓包中")).toBeInTheDocument();
    expect(screen.getByText("最近产物路径：/tmp/workspaces/case-live/traffic/live-last.har")).toBeInTheDocument();
    expect(screen.getByText("实时抓包进行中。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始实时抓包" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "停止实时抓包" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "导入 HAR" })).toBeEnabled();
    expect(screen.getByText("抓包引擎：内置 Mitmdump 已就绪（监听 0.0.0.0:8080）")).toBeInTheDocument();
    expect(
      screen.getByText("请把设备 HTTP/HTTPS 代理指向分析机 IP 的 8080 端口，停止后会自动导入 HAR。"),
    ).toBeInTheDocument();
    expect(screen.getByText("代理地址：分析机局域网 IP:8080")).toBeInTheDocument();
    expect(screen.getByText("安装地址：http://mitm.it")).toBeInTheDocument();
    expect(screen.getByText("证书路径：/Users/demo/.mitmproxy/mitmproxy-ca-cert.cer")).toBeInTheDocument();
    expect(screen.getByText("可直接把该证书安装到测试设备，或在设备浏览器访问 http://mitm.it。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "打开证书文件" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "打开证书目录" })).toBeEnabled();
  });

  it("disables live traffic start when the capture runtime is unavailable", async () => {
    vi.mocked(getEnvironmentStatus).mockResolvedValue({
      summary: "4 available, 4 missing",
      recommended_execution_mode: "real_frida_session",
      tools: [
        { name: "jadx", label: "jadx", available: true, path: "/usr/bin/jadx" },
        { name: "jadx-gui", label: "jadx-gui", available: true, path: "/usr/bin/jadx-gui" },
        { name: "apktool", label: "apktool", available: false, path: null },
        { name: "adb", label: "adb", available: true, path: "/usr/bin/adb" },
        { name: "frida", label: "frida", available: false, path: null },
        { name: "mitmdump", label: "mitmdump", available: false, path: null },
        { name: "mitmproxy", label: "mitmproxy", available: false, path: null },
        { name: "tcpdump", label: "tcpdump", available: false, path: null },
        { name: "python-frida", label: "python-frida", available: true, path: "module:frida" },
      ],
      live_capture: {
        available: false,
        source: "unavailable",
        detail: "未配置抓包命令，且未检测到 mitmdump。",
        listen_host: "0.0.0.0",
        listen_port: 8080,
        help_text: "可以先设置 APKHACKER_TRAFFIC_CAPTURE_COMMAND，或在本机安装 mitmdump 后重试。",
        proxy_address_hint: null,
        install_url: null,
        certificate_path: null,
        certificate_directory_path: null,
        certificate_exists: false,
        certificate_help_text: null,
        setup_steps: ["先安装 mitmdump"],
        proxy_steps: [],
        certificate_steps: [],
        recommended_actions: ["先使用 HAR 导入"],
      },
      execution_presets: [
        { key: "fake_backend", label: "Fake Backend", available: true, detail: "ready" },
        {
          key: "real_device",
          label: "Real Device",
          available: true,
          detail: "ready (Frida Session)",
        },
      ],
    });
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-live-disabled",
      title: "抓包不可用样本",
      package_name: "com.example.live.disabled",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-disabled",
      status: "unavailable",
      artifact_path: null,
      message: "未配置实时抓包命令，请设置 APKHACKER_TRAFFIC_CAPTURE_COMMAND。",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-live-disabled"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("抓包引擎：未配置抓包命令，且未检测到 mitmdump。")).toBeInTheDocument();
    expect(
      screen.getByText("可以先设置 APKHACKER_TRAFFIC_CAPTURE_COMMAND，或在本机安装 mitmdump 后重试。"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始实时抓包" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "停止实时抓包" })).toBeDisabled();
  });

  it("opens the live capture certificate file and directory through the local bridge", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-live-cert",
      title: "抓包证书样本",
      package_name: "com.example.live.cert",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-cert",
      status: "idle",
      artifact_path: null,
      message: null,
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
        ssl_hook_guidance: {
          recommended: true,
          summary: "建议优先启用 SSL / HTTPS 相关 Hook。",
          reason: "当前已具备抓包与设备注入基础，优先启用 SSL Hook 更容易拿到 HTTPS 明文与协议细节。",
          suggested_templates: ["OkHttp3 SSL Unpinning"],
          suggested_template_entries: [
            {
              source_id: "template:builtin.ssl-okhttp3-unpin:ssl.okhttp3_unpin",
              template_id: "ssl.okhttp3_unpin",
              template_name: "OkHttp3 SSL Unpinning",
              plugin_id: "builtin.ssl-okhttp3-unpin",
              label: "OkHttp3 SSL Unpinning",
            },
          ],
          suggested_terms: ["https", "ssl", "certificate", "network"],
        },
      },
      execution_presets: [],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-live-cert"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "打开证书文件" }));
    fireEvent.click(screen.getByRole("button", { name: "打开证书目录" }));

    await waitFor(() => {
      expect(vi.mocked(openWorkspacePath)).toHaveBeenNthCalledWith(1, "/Users/demo/.mitmproxy/mitmproxy-ca-cert.cer");
      expect(vi.mocked(openWorkspacePath)).toHaveBeenNthCalledWith(2, "/Users/demo/.mitmproxy");
    });
  });

  it("copies live capture setup values from the workspace panel", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-live-copy",
      title: "抓包复制样本",
      package_name: "com.example.live.copy",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [], });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-copy",
      status: "idle",
      artifact_path: null,
      message: null,
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

    render(
      <MemoryRouter initialEntries={["/workspace/case-live-copy"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "复制代理地址" }));
    fireEvent.click(screen.getByRole("button", { name: "复制安装地址" }));
    fireEvent.click(screen.getByRole("button", { name: "复制证书路径" }));

    await waitFor(() => {
      expect(vi.mocked(copyTextToClipboard)).toHaveBeenNthCalledWith(1, "分析机局域网 IP:8080");
      expect(vi.mocked(copyTextToClipboard)).toHaveBeenNthCalledWith(2, "http://mitm.it");
      expect(vi.mocked(copyTextToClipboard)).toHaveBeenNthCalledWith(
        3,
        "/Users/demo/.mitmproxy/mitmproxy-ca-cert.cer",
      );
    });
    expect(screen.getByText("已复制到剪贴板。")).toBeInTheDocument();
  });

  it("saves live capture runtime settings from the traffic panel and refreshes the effective runtime", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-live-settings",
      title: "抓包设置样本",
      package_name: "com.example.live.settings",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-settings",
      status: "idle",
      artifact_path: null,
      message: null,
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
    vi.mocked(getEnvironmentStatus)
      .mockResolvedValueOnce({
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
      })
      .mockResolvedValueOnce({
        summary: "5 available, 4 missing",
        recommended_execution_mode: "real_frida_session",
        tools: [],
        live_capture: {
          available: true,
          source: "builtin_mitmdump",
          detail: "内置 Mitmdump 已就绪（监听 127.0.0.1:9091）",
          listen_host: "127.0.0.1",
          listen_port: 9091,
          help_text: "请把设备 HTTP/HTTPS 代理指向分析机 IP 的 9091 端口，停止后会自动导入 HAR。",
          proxy_address_hint: "分析机局域网 IP:9091",
          install_url: "http://mitm.it",
          certificate_path: "/Users/demo/.mitmproxy/mitmproxy-ca-cert.cer",
          certificate_directory_path: "/Users/demo/.mitmproxy",
          certificate_exists: true,
          certificate_help_text: "可直接把该证书安装到测试设备，或在设备浏览器访问 http://mitm.it。",
          setup_steps: ["先配置代理", "安装证书", "复现关键请求"],
          proxy_steps: ["代理到分析机局域网 IP:9091"],
          certificate_steps: ["安装 mitm 证书", "若仍失败则启用 SSL Hook"],
          recommended_actions: ["优先启用 SSL 建议"],
        },
        execution_presets: [],
      });
    vi.mocked(saveRuntimeSettings).mockResolvedValue({
      execution_mode: "real_frida_session",
      device_serial: "",
      frida_server_binary_path: "",
      frida_server_remote_path: "",
      frida_session_seconds: "",
      live_capture_listen_host: "127.0.0.1",
      live_capture_listen_port: "9091",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-live-settings"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(await screen.findByLabelText("抓包监听地址"), { target: { value: "127.0.0.1" } });
    fireEvent.change(screen.getByLabelText("抓包监听端口"), { target: { value: "9091" } });
    fireEvent.click(screen.getByRole("button", { name: "保存抓包参数" }));

    await waitFor(() =>
      expect(vi.mocked(saveRuntimeSettings)).toHaveBeenCalledWith({
        execution_mode: "real_frida_session",
        device_serial: "",
        frida_server_binary_path: "",
        frida_server_remote_path: "",
        frida_session_seconds: "",
        live_capture_listen_host: "127.0.0.1",
        live_capture_listen_port: "9091",
      }),
    );
    expect(await screen.findByText("当前生效：127.0.0.1:9091")).toBeInTheDocument();
    expect(screen.getByText("代理地址：分析机局域网 IP:9091")).toBeInTheDocument();
    expect(screen.getByText("已保存运行参数。")).toBeInTheDocument();
  });

  it("starts and stops live traffic capture while keeping HAR import available", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-live-toggle",
      title: "抓包切换样本",
      package_name: "com.example.live.toggle",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-toggle",
      status: "idle",
      artifact_path: null,
      message: null,
    });
    vi.mocked(startLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-toggle",
      status: "running",
      artifact_path: null,
      message: "已开始实时抓包。",
    });
    vi.mocked(stopLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-toggle",
      status: "stopped",
      artifact_path: "/tmp/workspaces/case-live-toggle/traffic/live-001.har",
      message: "已停止实时抓包，产物已保存。",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-live-toggle"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("实时抓包状态：未启动")).toBeInTheDocument();
    expect(screen.getByText("最近产物路径：暂无")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始实时抓包" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "停止实时抓包" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "开始实时抓包" }));

    await waitFor(() => {
      expect(vi.mocked(startLiveTrafficCapture)).toHaveBeenCalledWith("case-live-toggle");
    });
    expect(await screen.findByText("实时抓包状态：抓包中")).toBeInTheDocument();
    expect(screen.getByText("已开始实时抓包。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始实时抓包" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "停止实时抓包" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "导入 HAR" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "停止实时抓包" }));

    await waitFor(() => {
      expect(vi.mocked(stopLiveTrafficCapture)).toHaveBeenCalledWith("case-live-toggle");
    });
    expect(await screen.findByText("实时抓包状态：已停止")).toBeInTheDocument();
    expect(screen.getByText("最近产物路径：/tmp/workspaces/case-live-toggle/traffic/live-001.har")).toBeInTheDocument();
    expect(screen.getByText("已停止实时抓包，产物已保存。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始实时抓包" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "停止实时抓包" })).toBeDisabled();
  });

  it("shows recent live traffic preview entries while capture is running", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-live-preview",
      title: "实时预览样本",
      package_name: "com.example.live.preview",
      technical_tags: [],
      dangerous_permissions: [],
      callback_endpoints: ["https://demo-c2.example/api/upload"],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
      runtime: {
        ...createRuntimeSummary(),
        live_traffic_status: "running",
        live_traffic_message: "实时抓包进行中。",
      },
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-live-preview",
      status: "running",
      artifact_path: "/tmp/workspaces/case-live-preview/evidence/traffic/live/live-001.har",
      message: "实时抓包进行中。",
    });
    vi.mocked(getLiveTrafficPreview).mockResolvedValue({
      case_id: "case-live-preview",
      status: "running",
      preview_path: "/tmp/workspaces/case-live-preview/evidence/traffic/live/live-001.ndjson",
      truncated: false,
      items: [
        {
          schema_version: "traffic-flow.v1",
          capture_id: "capture-preview",
          flow_id: "preview-1",
          timestamp: "2026-04-19T10:00:00Z",
          method: "GET",
          url: "https://cdn.example.org/app.js",
          status_code: 200,
          mime_type: null,
          request_preview: "",
          response_preview: "",
          matched_indicators: [],
          suspicious: false,
        },
        {
          schema_version: "traffic-flow.v1",
          capture_id: "capture-preview",
          flow_id: "preview-2",
          timestamp: "2026-04-19T10:00:02Z",
          method: "POST",
          url: "https://demo-c2.example/api/upload",
          status_code: 202,
          mime_type: null,
          request_preview: "",
          response_preview: "",
          matched_indicators: ["demo-c2.example"],
          suspicious: true,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-live-preview"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("最近请求预览")).toBeInTheDocument();
    expect(screen.getByText("POST · 202 · https://demo-c2.example/api/upload")).toBeInTheDocument();
    expect(screen.getByText("命中线索：demo-c2.example")).toBeInTheDocument();
    expect(screen.getByText("预览文件：/tmp/workspaces/case-live-preview/evidence/traffic/live/live-001.ndjson")).toBeInTheDocument();
    expect(vi.mocked(getLiveTrafficPreview)).toHaveBeenCalledWith("case-live-preview");
  });

  it("surfaces the traffic readiness checklist and lets network recommendations join the hook plan", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-traffic-workflow",
      title: "流量工作流样本",
      package_name: "com.example.traffic.workflow",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: ["https://relay.example.net/upload"],
      callback_clues: ["https 上报"],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
      runtime: {
        ...createRuntimeSummary(),
        traffic_capture_source_path: "/tmp/workspaces/case-traffic-workflow/evidence/traffic/imported.har",
        traffic_capture_flow_count: 4,
        traffic_capture_suspicious_count: 1,
      },
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [
        {
          recommendation_id: "rec-traffic-ssl",
          kind: "template",
          title: "优先处理 OkHttp SSL Pinning",
          reason: "命中 okhttp3 / SSL 证书校验链路",
          score: 92,
          matched_terms: ["okhttp3", "ssl", "https"],
          method: null,
          template_id: "okhttp3_unpin",
          template_name: "okhttp3_unpin.js",
          plugin_id: "builtin.network",
        },
      ],
    });
    vi.mocked(getWorkspaceTraffic).mockResolvedValue({
      case_id: "case-traffic-workflow",
      source_path: "/tmp/workspaces/case-traffic-workflow/evidence/traffic/imported.har",
      provenance: {
        kind: "imported_har",
        label: "导入 HAR",
      },
      flow_count: 4,
      suspicious_count: 1,
      https_flow_count: 4,
      matched_indicator_count: 1,
      top_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
        {
          host: "cdn.example.net",
          flow_count: 1,
          suspicious_count: 0,
          https_flow_count: 1,
        },
      ],
      suspicious_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      summary: {
        https_flow_count: 4,
        matched_indicator_count: 1,
        top_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
          {
            host: "cdn.example.net",
            flow_count: 1,
            suspicious_count: 0,
            https_flow_count: 1,
          },
        ],
        suspicious_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
      },
      flows: [
        {
          flow_id: "flow-hot",
          method: "POST",
          url: "https://relay.example.net/upload",
          status_code: 202,
          mime_type: "application/json",
          request_preview: "{\"device_id\":\"abc\"}",
          response_preview: "{\"ok\":true}",
          matched_indicators: ["relay.example.net"],
          suspicious: true,
        },
        {
          flow_id: "flow-cdn",
          method: "GET",
          url: "https://cdn.example.net/app.js",
          status_code: 200,
          mime_type: "application/javascript",
          request_preview: "",
          response_preview: "",
          matched_indicators: [],
          suspicious: false,
        },
      ],
    });
    vi.mocked(addRecommendationToHookPlan).mockResolvedValue({
      case_id: "case-traffic-workflow",
      updated_at: "2026-04-19T10:15:00Z",
      items: [
        {
          item_id: "item-traffic-template",
          kind: "template_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.network",
          rendered_script: "Java.perform(function() { /* okhttp ssl */ });",
          method: null,
          template_name: "okhttp3_unpin.js",
          script_name: null,
          script_path: null,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-traffic-workflow"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("抓包准备清单")).toBeInTheDocument();
    expect(screen.getByText("代理地址")).toBeInTheDocument();
    expect(screen.getByText("分析机局域网 IP:8080")).toBeInTheDocument();
    const trafficPanel = screen.getByRole("heading", { name: "流量证据" }).closest("section");
    expect(trafficPanel).not.toBeNull();
    expect(await within(trafficPanel as HTMLElement).findByText("优先处理 OkHttp SSL Pinning")).toBeInTheDocument();
    expect(within(trafficPanel as HTMLElement).getByText("主机摘要：relay.example.net（1）、cdn.example.net（1）")).toBeInTheDocument();
    expect(within(trafficPanel as HTMLElement).getByText("HTTPS 请求：4 条；命中线索：1 次。")).toBeInTheDocument();

    fireEvent.click(await within(trafficPanel as HTMLElement).findByRole("button", { name: "加入 Hook 计划" }));

    await waitFor(() => {
      expect(vi.mocked(addRecommendationToHookPlan)).toHaveBeenCalledWith("case-traffic-workflow", "rec-traffic-ssl");
    });
    expect(await screen.findByText("template_hook #1")).toBeInTheDocument();
  });

  it("shows action cards that explain proxy, certificate, and ssl hook timing", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-traffic-steps",
      title: "流量引导样本",
      package_name: "com.example.traffic.steps",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: ["https://api.example.net/login"],
      callback_clues: ["https 登录链路"],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [
        {
          recommendation_id: "rec-ssl-step",
          kind: "template",
          title: "优先处理 OkHttp SSL Pinning",
          reason: "命中 okhttp3 / SSL 证书校验链路",
          score: 92,
          matched_terms: ["okhttp3", "ssl", "https"],
          method: null,
          template_id: "okhttp3_unpin",
          template_name: "okhttp3_unpin.js",
          plugin_id: "builtin.network",
        },
      ],
    });
    vi.mocked(addRecommendationToHookPlan).mockResolvedValue({
      case_id: "case-traffic-steps",
      updated_at: "2026-04-19T11:10:00Z",
      items: [
        {
          item_id: "item-ssl-step",
          kind: "template_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.network",
          rendered_script: "Java.perform(function() { /* okhttp ssl */ });",
          method: null,
          template_name: "okhttp3_unpin.js",
          script_name: null,
          script_path: null,
        },
      ],
    });
    vi.mocked(getWorkspaceTraffic).mockResolvedValue(null);
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-traffic-steps",
      status: "idle",
      artifact_path: null,
      message: null,
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
        certificate_exists: false,
        certificate_help_text: "可直接把该证书安装到测试设备，或在设备浏览器访问 http://mitm.it。",
        setup_steps: ["先配置代理", "安装证书", "复现关键请求"],
        proxy_steps: ["代理到分析机局域网 IP:8080"],
        certificate_steps: ["安装 mitm 证书", "若仍失败则启用 SSL Hook"],
        recommended_actions: ["优先启用 SSL 建议"],
      },
      execution_presets: [],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-traffic-steps"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const trafficPanel = screen.getByRole("heading", { name: "流量证据" }).closest("section");
    expect(trafficPanel).not.toBeNull();

    expect(await within(trafficPanel as HTMLElement).findByText("下一步操作卡片")).toBeInTheDocument();
    expect(within(trafficPanel as HTMLElement).getByText("1. 配置代理")).toBeInTheDocument();
    expect(
      within(trafficPanel as HTMLElement).getByText(
        "把测试设备 HTTP/HTTPS 代理改为手动，并填入 分析机局域网 IP:8080。",
      ),
    ).toBeInTheDocument();
    expect(within(trafficPanel as HTMLElement).getByText("2. 安装证书")).toBeInTheDocument();
    expect(
      within(trafficPanel as HTMLElement).getByText(
        "优先在设备浏览器访问 http://mitm.it；没有浏览器时再直接安装导出的 mitm 证书。",
      ),
    ).toBeInTheDocument();
    expect(within(trafficPanel as HTMLElement).getByText("3. 评估 SSL / 网络 Hook")).toBeInTheDocument();
    expect(
      await within(trafficPanel as HTMLElement).findByText("优先处理 OkHttp SSL Pinning"),
    ).toBeInTheDocument();
    expect(
      within(trafficPanel as HTMLElement).getByText(
        "先完成代理和证书；如果 HTTPS 仍报证书错误、握手失败或没有明文，再把当前 SSL 建议加入 Hook 计划。",
      ),
    ).toBeInTheDocument();

    fireEvent.click(
      await within(trafficPanel as HTMLElement).findByRole("button", { name: "将当前 SSL 建议加入计划" }),
    );

    await waitFor(() => {
      expect(vi.mocked(addRecommendationToHookPlan)).toHaveBeenCalledWith("case-traffic-steps", "rec-ssl-step");
    });
  });

  it("adds ssl template suggestions directly from the traffic panel when no traffic recommendation is available", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-traffic-template-link",
      title: "流量模板联动样本",
      package_name: "com.example.traffic.template",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: ["https://api.example.net/login"],
      callback_clues: ["https 登录链路"],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: false,
      method_count: 0,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceTraffic).mockResolvedValue(null);
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-traffic-template-link",
      status: "idle",
      artifact_path: null,
      message: null,
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
        ssl_hook_guidance: {
          recommended: true,
          summary: "建议优先启用 SSL / HTTPS 相关 Hook。",
          reason: "当前已具备抓包与设备注入基础，优先启用 SSL Hook 更容易拿到 HTTPS 明文与协议细节。",
          suggested_templates: ["OkHttp3 SSL Unpinning"],
          suggested_template_entries: [
            {
              source_id: "template:builtin.ssl-okhttp3-unpin:ssl.okhttp3_unpin",
              template_id: "ssl.okhttp3_unpin",
              template_name: "OkHttp3 SSL Unpinning",
              plugin_id: "builtin.ssl-okhttp3-unpin",
              label: "OkHttp3 SSL Unpinning",
            },
          ],
          suggested_terms: ["https", "ssl", "certificate", "network"],
        },
      },
      execution_presets: [],
    });
    vi.mocked(addTemplateToHookPlan).mockResolvedValue({
      case_id: "case-traffic-template-link",
      updated_at: "2026-04-19T12:00:00Z",
      items: [
        {
          item_id: "item-template-direct",
          kind: "template_hook",
          inject_order: 1,
          enabled: true,
          plugin_id: "builtin.ssl-okhttp3-unpin",
          rendered_script: "Java.perform(function() { /* okhttp ssl */ });",
          method: null,
          template_name: "OkHttp3 SSL Unpinning",
          script_name: null,
          script_path: null,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-traffic-template-link"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const trafficPanel = screen.getByRole("heading", { name: "流量证据" }).closest("section");
    expect(trafficPanel).not.toBeNull();
    expect(
      await within(trafficPanel as HTMLElement).findByText("1 条 SSL 模板建议可直接加入计划"),
    ).toBeInTheDocument();
    expect(within(trafficPanel as HTMLElement).getByText("当前候选：OkHttp3 SSL Unpinning")).toBeInTheDocument();

    fireEvent.click(
      await within(trafficPanel as HTMLElement).findByRole("button", { name: "将 OkHttp3 SSL Unpinning 加入计划" }),
    );

    await waitFor(() => {
      expect(vi.mocked(addTemplateToHookPlan)).toHaveBeenCalledWith("case-traffic-template-link", {
        template_id: "ssl.okhttp3_unpin",
        template_name: "OkHttp3 SSL Unpinning",
        plugin_id: "builtin.ssl-okhttp3-unpin",
      });
    });
    expect(await screen.findByText("已将 OkHttp3 SSL Unpinning 加入 Hook 计划。")).toBeInTheDocument();
  });

  it("jumps from the traffic panel into the hook studio with related candidate scope and ssl query", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-traffic-inspect",
      title: "流量跳转样本",
      package_name: "com.example.traffic.inspect",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: ["https://relay.example.net/upload"],
      callback_clues: ["https 上报"],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: true,
      method_count: 438,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods)
      .mockResolvedValueOnce({
        items: [
          {
            class_name: "com.example.traffic.inspect.UploadClient",
            method_name: "send",
            parameter_types: ["java.lang.String"],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/traffic/inspect/UploadClient.java",
            line_hint: 21,
            declaration: "public void send(java.lang.String payload)",
            source_preview: "public void send(String payload) { return; }",
            tags: ["first-party"],
            evidence: [],
          },
        ],
        total: 25,
        scope: "first_party",
        available_scopes: ["first_party", "related_candidates", "all"],
      })
      .mockResolvedValueOnce({
        items: [
          {
            class_name: "okhttp3.internal.tls.CertificateChainCleaner",
            method_name: "clean",
            parameter_types: ["java.util.List", "java.lang.String"],
            return_type: "java.util.List",
            is_constructor: false,
            overload_count: 1,
            source_path: "okhttp3/internal/tls/CertificateChainCleaner.java",
            line_hint: 48,
            declaration:
              "public java.util.List clean(java.util.List chain, java.lang.String hostname)",
            source_preview:
              "public java.util.List clean(...) { return clean(chain, hostname, certificatePinner); }",
            tags: ["相关候选", "ssl"],
            evidence: ["命中 ssl", "命中 okhttp3"],
          },
        ],
        total: 438,
        scope: "related_candidates",
        available_scopes: ["first_party", "related_candidates", "all"],
      });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [
        {
          recommendation_id: "rec-traffic-focus",
          kind: "template",
          title: "优先处理 OkHttp SSL Pinning",
          reason: "命中 okhttp3 / SSL 证书校验链路",
          score: 92,
          matched_terms: ["okhttp3", "ssl", "https"],
          method: null,
          template_id: "okhttp3_unpin",
          template_name: "okhttp3_unpin.js",
          plugin_id: "builtin.network",
        },
      ],
    });
    vi.mocked(getWorkspaceTraffic).mockResolvedValue({
      case_id: "case-traffic-inspect",
      source_path: "/tmp/workspaces/case-traffic-inspect/evidence/traffic/imported.har",
      provenance: {
        kind: "imported_har",
        label: "导入 HAR",
      },
      flow_count: 4,
      suspicious_count: 1,
      https_flow_count: 4,
      matched_indicator_count: 1,
      top_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      suspicious_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      summary: {
        https_flow_count: 4,
        matched_indicator_count: 1,
        top_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
        suspicious_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
      },
      flows: [
        {
          flow_id: "flow-hot",
          method: "POST",
          url: "https://relay.example.net/upload",
          status_code: 202,
          mime_type: "application/json",
          request_preview: "{\"device_id\":\"abc\"}",
          response_preview: "{\"ok\":true}",
          matched_indicators: ["relay.example.net"],
          suspicious: true,
        },
      ],
    });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-traffic-inspect",
      status: "idle",
      artifact_path: null,
      message: null,
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
        ssl_hook_guidance: {
          recommended: true,
          summary: "建议优先启用 SSL / HTTPS 相关 Hook。",
          reason: "当前已具备抓包与设备注入基础，优先启用 SSL Hook 更容易拿到 HTTPS 明文与协议细节。",
          suggested_templates: ["OkHttp3 SSL Unpinning"],
          suggested_template_entries: [
            {
              source_id: "template:builtin.ssl-okhttp3-unpin:ssl.okhttp3_unpin",
              template_id: "ssl.okhttp3_unpin",
              template_name: "OkHttp3 SSL Unpinning",
              plugin_id: "builtin.ssl-okhttp3-unpin",
              label: "OkHttp3 SSL Unpinning",
            },
          ],
          suggested_terms: ["okhttp3", "ssl", "https"],
        },
      },
      execution_presets: [],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-traffic-inspect"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const trafficPanel = screen.getByRole("heading", { name: "流量证据" }).closest("section");
    expect(trafficPanel).not.toBeNull();
    await within(trafficPanel as HTMLElement).findByText("优先处理 OkHttp SSL Pinning");

    fireEvent.click(
      await within(trafficPanel as HTMLElement).findByRole("button", { name: "在 Hook 工作台中查看 SSL/网络线索" }),
    );

    await waitFor(() => {
      expect(vi.mocked(getWorkspaceMethods)).toHaveBeenLastCalledWith("case-traffic-inspect", {
        query: "okhttp3 ssl https",
        limit: 120,
        scope: "related_candidates",
      });
    });
    expect(await screen.findByText("来自流量证据的线索")).toBeInTheDocument();
    expect(
      await screen.findByText(
        hasExactTextContent("已根据 优先处理 OkHttp SSL Pinning 切到 Hook 工作台，并预填关键词：okhttp3 ssl https。"),
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("焦点推荐：优先处理 OkHttp SSL Pinning")).toBeInTheDocument();
    expect(screen.getAllByText("命中 okhttp3 / SSL 证书校验链路")).not.toHaveLength(0);
    expect(screen.getByRole("button", { name: "相关候选" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("link", { name: "Hook 工作台" })).toHaveAttribute("aria-current", "location");
    expect(screen.getByRole("textbox", { name: "搜索方法" })).toHaveValue("okhttp3 ssl https");
    expect(
      await screen.findByText(
        (content) => content.includes("当前类：") && content.includes("okhttp3.internal.tls.CertificateChainCleaner"),
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "函数详情" }).closest("section")).toHaveTextContent(
      "okhttp3.internal.tls.CertificateChainCleaner",
    );
    expect(screen.getByText("反编译声明：public java.util.List clean(java.util.List chain, java.lang.String hostname)")).toBeInTheDocument();
  });

  it("jumps back to traffic evidence from a traffic-linked hook recommendation", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-hook-to-traffic",
      title: "Hook 回看样本",
      package_name: "com.example.hook.traffic",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: ["https://relay.example.net/upload"],
      callback_clues: ["https 上报"],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: true,
      method_count: 25,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [
        {
          class_name: "com.example.hook.traffic.UploadClient",
          method_name: "send",
          parameter_types: ["java.lang.String"],
          return_type: "void",
          is_constructor: false,
          overload_count: 1,
          source_path: "com/example/hook/traffic/UploadClient.java",
          line_hint: 21,
          declaration: "public void send(java.lang.String payload)",
          source_preview: "public void send(String payload) { return; }",
          tags: ["first-party"],
          evidence: [],
        },
      ],
      total: 25,
      scope: "first_party",
      available_scopes: ["first_party", "related_candidates", "all"],
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({
      items: [
        {
          recommendation_id: "rec-hook-traffic",
          kind: "template",
          title: "优先处理 OkHttp SSL Pinning",
          reason: "命中 okhttp3 / SSL 证书校验链路",
          score: 92,
          matched_terms: ["okhttp3", "ssl", "https"],
          method: null,
          template_id: "okhttp3_unpin",
          template_name: "okhttp3_unpin.js",
          plugin_id: "builtin.network",
        },
      ],
    });
    vi.mocked(getWorkspaceTraffic).mockResolvedValue({
      case_id: "case-hook-to-traffic",
      source_path: "/tmp/workspaces/case-hook-to-traffic/evidence/traffic/imported.har",
      provenance: {
        kind: "imported_har",
        label: "导入 HAR",
      },
      flow_count: 3,
      suspicious_count: 1,
      https_flow_count: 3,
      matched_indicator_count: 1,
      top_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      suspicious_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      summary: {
        https_flow_count: 3,
        matched_indicator_count: 1,
        top_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
        suspicious_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
      },
      flows: [
        {
          flow_id: "flow-hot",
          method: "POST",
          url: "https://relay.example.net/upload",
          status_code: 202,
          mime_type: "application/json",
          request_preview: "{\"device_id\":\"abc\"}",
          response_preview: "{\"ok\":true}",
          matched_indicators: ["relay.example.net"],
          suspicious: true,
        },
      ],
    });
    vi.mocked(getLiveTrafficCapture).mockResolvedValue({
      case_id: "case-hook-to-traffic",
      status: "idle",
      artifact_path: null,
      message: null,
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
        ssl_hook_guidance: {
          recommended: true,
          summary: "建议优先启用 SSL / HTTPS 相关 Hook。",
          reason: "当前已具备抓包与设备注入基础，优先启用 SSL Hook 更容易拿到 HTTPS 明文与协议细节。",
          suggested_templates: ["OkHttp3 SSL Unpinning"],
          suggested_template_entries: [
            {
              source_id: "template:builtin.ssl-okhttp3-unpin:ssl.okhttp3_unpin",
              template_id: "ssl.okhttp3_unpin",
              template_name: "OkHttp3 SSL Unpinning",
              plugin_id: "builtin.ssl-okhttp3-unpin",
              label: "OkHttp3 SSL Unpinning",
            },
          ],
          suggested_terms: ["okhttp3", "ssl", "https"],
        },
      },
      execution_presets: [],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-hook-to-traffic"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    const hookStudio = await screen.findByRole("heading", { name: "Hook 工作台" });
    expect(hookStudio).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "在流量证据查看网络摘要" }));

    expect(await screen.findByText("来自 Hook 工作台的回看")).toBeInTheDocument();
    expect(
      screen.getByText("已根据 优先处理 OkHttp SSL Pinning 回到流量证据，可继续核对当前抓包摘要、代理/证书准备度和 SSL 联动建议。"),
    ).toBeInTheDocument();
    expect(screen.getByText("焦点推荐：优先处理 OkHttp SSL Pinning")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "流量证据" })).toHaveAttribute("aria-current", "location");
  });

  it("jumps from execution events into the hook studio and locates the related function", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-execution-to-hook",
      title: "执行回跳样本",
      package_name: "com.example.execution.hook",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: true,
      method_count: 64,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods)
      .mockResolvedValueOnce({
        items: [
          {
            class_name: "com.example.execution.hook.UploadClient",
            method_name: "send",
            parameter_types: ["java.lang.String"],
            return_type: "void",
            is_constructor: false,
            overload_count: 1,
            source_path: "com/example/execution/hook/UploadClient.java",
            line_hint: 21,
            declaration: "public void send(java.lang.String payload)",
            source_preview: "public void send(String payload) { return; }",
            tags: ["first-party"],
            evidence: [],
          },
        ],
        total: 64,
        scope: "first_party",
        available_scopes: ["first_party", "related_candidates", "all"],
      })
      .mockResolvedValueOnce({
        items: [
          {
            class_name: "okhttp3.internal.tls.CertificateChainCleaner",
            method_name: "clean",
            parameter_types: ["java.util.List", "java.lang.String"],
            return_type: "java.util.List",
            is_constructor: false,
            overload_count: 1,
            source_path: "okhttp3/internal/tls/CertificateChainCleaner.java",
            line_hint: 48,
            declaration:
              "public java.util.List clean(java.util.List chain, java.lang.String hostname)",
            source_preview:
              "public java.util.List clean(...) { return clean(chain, hostname, certificatePinner); }",
            tags: ["相关候选", "ssl"],
            evidence: ["命中 ssl", "命中 okhttp3"],
          },
        ],
        total: 20418,
        scope: "all",
        available_scopes: ["first_party", "related_candidates", "all"],
      });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceEvents).mockResolvedValue([
      {
        type: "execution.event",
        case_id: "case-execution-to-hook",
        timestamp: "2026-04-19T12:00:00Z",
        message: "okhttp3.internal.tls.CertificateChainCleaner.clean · [hook]",
        payload: {
          event_type: "method",
          source: "ssl.okhttp3_unpin",
          class_name: "okhttp3.internal.tls.CertificateChainCleaner",
          method_name: "clean",
          arguments: ["chain", "hostname"],
          return_value: null,
          stacktrace: "okhttp3.internal.tls.CertificateChainCleaner.clean",
          raw_payload: {},
        },
      },
    ]);

    render(
      <MemoryRouter initialEntries={["/workspace/case-execution-to-hook"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByText(/执行历史与事件/));
    const executionConsoleSection = screen.getByRole("heading", { name: "执行控制台" }).closest("section");
    expect(executionConsoleSection).not.toBeNull();
    fireEvent.click(await within(executionConsoleSection as HTMLElement).findByRole("button", { name: "在 Hook 工作台定位函数" }));

    await waitFor(() => {
      expect(vi.mocked(getWorkspaceMethods)).toHaveBeenLastCalledWith("case-execution-to-hook", {
        query: "okhttp3.internal.tls.CertificateChainCleaner clean",
        limit: 120,
        scope: "all",
      });
    });
    expect(await screen.findByText("来自执行控制台的定位")).toBeInTheDocument();
    expect(
      screen.getByText("已根据 okhttp3.internal.tls.CertificateChainCleaner.clean 切到 Hook 工作台，并尝试定位对应函数。"),
    ).toBeInTheDocument();
    expect(screen.getByText("焦点函数：okhttp3.internal.tls.CertificateChainCleaner.clean")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "全部方法" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "函数详情" }).closest("section")).toHaveTextContent(
      "okhttp3.internal.tls.CertificateChainCleaner",
    );
  });

  it("jumps back to execution console from the selected hook method", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-hook-to-execution",
      title: "Hook 回看执行样本",
      package_name: "com.example.hook.execution",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: true,
      method_count: 1,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [
        {
          class_name: "okhttp3.internal.tls.CertificateChainCleaner",
          method_name: "clean",
          parameter_types: ["java.util.List", "java.lang.String"],
          return_type: "java.util.List",
          is_constructor: false,
          overload_count: 1,
          source_path: "okhttp3/internal/tls/CertificateChainCleaner.java",
          line_hint: 48,
          declaration:
            "public java.util.List clean(java.util.List chain, java.lang.String hostname)",
          source_preview:
            "public java.util.List clean(...) { return clean(chain, hostname, certificatePinner); }",
          tags: ["相关候选", "ssl"],
          evidence: ["命中 ssl", "命中 okhttp3"],
        },
      ],
      total: 1,
      scope: "all",
      available_scopes: ["first_party", "related_candidates", "all"],
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceEvents).mockResolvedValue([
      {
        type: "execution.event",
        case_id: "case-hook-to-execution",
        timestamp: "2026-04-19T12:00:00Z",
        message: "okhttp3.internal.tls.CertificateChainCleaner.clean · [hook]",
        payload: {
          event_type: "method",
          source: "ssl.okhttp3_unpin",
          class_name: "okhttp3.internal.tls.CertificateChainCleaner",
          method_name: "clean",
          arguments: ["chain", "hostname"],
          return_value: null,
          stacktrace: "okhttp3.internal.tls.CertificateChainCleaner.clean",
          raw_payload: {},
        },
      },
    ]);

    render(
      <MemoryRouter initialEntries={["/workspace/case-hook-to-execution"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "查看相关执行事件" }));

    expect(await screen.findByText("来自 Hook 工作台的回看")).toBeInTheDocument();
    expect(
      screen.getByText("已根据 okhttp3.internal.tls.CertificateChainCleaner.clean 回到执行控制台，可继续核对相关事件、返回值与堆栈。"),
    ).toBeInTheDocument();
    expect(screen.getByText("焦点函数：okhttp3.internal.tls.CertificateChainCleaner.clean")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "执行控制台" })).toHaveAttribute("aria-current", "location");
  });

  it("shows linked execution and traffic summaries for the selected method", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-method-insight",
      title: "函数联动摘要样本",
      package_name: "com.example.method.insight",
      technical_tags: ["okhttp3"],
      dangerous_permissions: [],
      callback_endpoints: [],
      callback_clues: [],
      crypto_signals: [],
      packer_hints: [],
      limitations: [],
      custom_scripts: [],
      can_open_in_jadx: false,
      has_method_index: true,
      method_count: 1,
      runtime: createRuntimeSummary(),
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({
      items: [
        {
          class_name: "okhttp3.internal.tls.CertificateChainCleaner",
          method_name: "clean",
          parameter_types: ["java.util.List", "java.lang.String"],
          return_type: "java.util.List",
          is_constructor: false,
          overload_count: 1,
          source_path: "okhttp3/internal/tls/CertificateChainCleaner.java",
          line_hint: 48,
          declaration:
            "public java.util.List clean(java.util.List chain, java.lang.String hostname)",
          source_preview:
            "public java.util.List clean(...) { return clean(chain, hostname, certificatePinner); }",
          tags: ["相关候选", "ssl"],
          evidence: ["命中 ssl", "命中 okhttp3"],
        },
      ],
      total: 1,
      scope: "all",
      available_scopes: ["first_party", "related_candidates", "all"],
    });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getWorkspaceEvents).mockResolvedValue([
      {
        type: "execution.event",
        case_id: "case-method-insight",
        timestamp: "2026-04-19T12:00:00Z",
        status: "started",
        message: "命中 CertificateChainCleaner.clean",
        payload: {
          event_type: "method",
          source: "ssl.okhttp3_unpin",
          class_name: "okhttp3.internal.tls.CertificateChainCleaner",
          method_name: "clean",
          arguments: ["chain", "hostname"],
          return_value: "cleaned-chain",
          stacktrace:
            "okhttp3.internal.tls.CertificateChainCleaner.clean\nokhttp3.CertificatePinner.check",
          raw_payload: {},
        },
      },
    ]);
    vi.mocked(getWorkspaceTraffic).mockResolvedValue({
      case_id: "case-method-insight",
      source_path: "/tmp/workspaces/case-method-insight/evidence/traffic/imported.har",
      provenance: {
        kind: "imported_har",
        label: "导入 HAR",
      },
      flow_count: 3,
      suspicious_count: 1,
      https_flow_count: 3,
      matched_indicator_count: 2,
      top_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      suspicious_hosts: [
        {
          host: "relay.example.net",
          flow_count: 1,
          suspicious_count: 1,
          https_flow_count: 1,
        },
      ],
      summary: {
        https_flow_count: 3,
        matched_indicator_count: 2,
        top_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
        suspicious_hosts: [
          {
            host: "relay.example.net",
            flow_count: 1,
            suspicious_count: 1,
            https_flow_count: 1,
          },
        ],
      },
      flows: [
        {
          flow_id: "flow-method-insight",
          method: "POST",
          url: "https://relay.example.net/certificate/clean",
          status_code: 202,
          mime_type: "application/json",
          request_preview: "{\"hostname\":\"relay.example.net\"}",
          response_preview: "{\"ok\":true}",
          matched_indicators: ["certificate", "clean"],
          suspicious: true,
        },
      ],
    });
    vi.mocked(getEnvironmentStatus).mockResolvedValue({
      summary: "5 available, 4 missing",
      recommended_execution_mode: "real_frida_session",
      tools: [
        { name: "jadx", label: "jadx", available: true, path: "/usr/bin/jadx" },
        { name: "adb", label: "adb", available: true, path: "/usr/bin/adb" },
      ],
      live_capture: {
        available: true,
        source: "builtin_mitmdump",
        detail: "内置 Mitmdump 已就绪（监听 0.0.0.0:8080）",
        listen_host: "0.0.0.0",
        listen_port: 8080,
        help_text: "请把设备 HTTP/HTTPS 代理指向分析机 IP 的 8080 端口。",
        proxy_address_hint: "分析机局域网 IP:8080",
        install_url: "http://mitm.it",
        certificate_path: "/Users/demo/.mitmproxy/mitmproxy-ca-cert.cer",
        certificate_directory_path: "/Users/demo/.mitmproxy",
        certificate_exists: true,
        certificate_help_text: "可直接把该证书安装到测试设备。",
        setup_steps: [],
        proxy_steps: [],
        certificate_steps: [],
        recommended_actions: [],
        ssl_hook_guidance: {
          recommended: true,
          summary: "建议先启用 OkHttp3 SSL Unpinning，再复现证书校验流量。",
          reason: "命中 okhttp3/ssl 线索",
          suggested_templates: ["okhttp3_unpin"],
          suggested_terms: ["okhttp3", "ssl", "https"],
        },
      },
      execution_presets: [
        { key: "fake_backend", label: "Fake Backend", available: true, detail: "ready" },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-method-insight"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "联动摘要" })).toBeInTheDocument();
    expect(screen.getByText("关联事件：1 条")).toBeInTheDocument();
    expect(screen.getByText("最近参数：chain、hostname")).toBeInTheDocument();
    expect(screen.getByText("最近返回：cleaned-chain")).toBeInTheDocument();
    expect(screen.getByText(/堆栈摘要：okhttp3\.internal\.tls\.CertificateChainCleaner\.clean/)).toBeInTheDocument();
    expect(screen.getByText("流量来源：导入 HAR")).toBeInTheDocument();
    expect(screen.getByText("主机摘要：relay.example.net（1 条）")).toBeInTheDocument();
    expect(screen.getByText("命中流量：POST https://relay.example.net/certificate/clean")).toBeInTheDocument();
    expect(screen.getByText("SSL 建议：建议先启用 OkHttp3 SSL Unpinning，再复现证书校验流量。")).toBeInTheDocument();
  });

  it("opens evidence paths through the local desktop bridge", async () => {
    vi.mocked(getWorkspaceDetail).mockResolvedValue({
      case_id: "case-open",
      title: "打开路径样本",
      package_name: "com.example.open",
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
    });
    vi.mocked(getWorkspaceMethods).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(getWorkspaceRecommendations).mockResolvedValue({ items: [] });
    vi.mocked(getHookPlan).mockResolvedValue({
      case_id: "case-open",
      updated_at: "2026-04-17T10:00:00Z",
      items: [],
      last_execution_db_path: "/tmp/workspaces/case-open/executions/run-1/hook-events.sqlite3",
      last_execution_bundle_path: "/tmp/workspaces/case-open/executions/run-1",
      last_report_path: "/tmp/workspaces/case-open/reports/case-open-report.md",
    });

    render(
      <MemoryRouter initialEntries={["/workspace/case-open"]}>
        <Routes>
          <Route path="/workspace/:caseId" element={<CaseWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click((await screen.findAllByRole("button", { name: "打开运行数据库" }))[0]);

    await waitFor(() => {
      expect(vi.mocked(openWorkspacePath)).toHaveBeenCalledWith(
        "/tmp/workspaces/case-open/executions/run-1/hook-events.sqlite3",
      );
    });
    expect(await screen.findAllByText("已在本机打开所选路径。")).not.toHaveLength(0);
  });

  it("does not leak in-flight action results into the next case workspace", async () => {
    const executionDeferred = createDeferred<{
      case_id: string;
      status: string;
      execution_mode: string | null;
    }>();
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
      runtime: createRuntimeSummary(),
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
      executionDeferred.resolve({ case_id: "case-001", status: "started", execution_mode: "fake_backend" });
      reportDeferred.resolve({
        case_id: "case-001",
        report_path: "/tmp/workspaces/case-001/reports/case-001-report.md",
      });
      openDeferred.resolve({ case_id: "case-001", status: "opened" });
    });

    await waitFor(() => {
      expect(screen.queryByText(hasExactTextContent("当前状态已启动"))).not.toBeInTheDocument();
      expect(screen.queryByText("已尝试在本机打开 JADX。")).not.toBeInTheDocument();
      expect(
        screen.queryByText((content) => content.includes("/tmp/workspaces/case-001/reports/case-001-report.md")),
      ).not.toBeInTheDocument();
    });
  });
});
