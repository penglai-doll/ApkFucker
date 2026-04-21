import { afterEach, describe, expect, it, vi } from "vitest";

import {
  addTemplateToHookPlan,
  cancelExecution,
  deleteWorkspaceCustomScript,
  exportReport,
  getEnvironmentStatus,
  getExecutionHistory,
  getExecutionHistoryEvents,
  getExecutionPreflight,
  getHookPlan,
  getLiveTrafficCapture,
  getLiveTrafficPreview,
  getWorkspaceDetail,
  getWorkspaceCustomScript,
  getWorkspaceTraffic,
  moveHookPlanItem,
  setHookPlanItemEnabled,
  startExecution,
  startLiveTrafficCapture,
  stopLiveTrafficCapture,
  updateWorkspaceCustomScript,
  normalizeConnectedDevices,
  resolvePreferredDeviceSerial,
  resolveRecommendedDeviceSerial,
} from "../lib/api";
import type { EnvironmentStatus } from "../lib/types";

describe("API adapters", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps hook plan payloads from the backend contract into workspace-friendly items", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-001",
        updated_at: "2026-04-13T12:00:00Z",
        selected_hook_sources: [
          {
            source_id: "source-1",
            kind: "method_hook",
            method: {
              class_name: "com.demo.Api",
              method_name: "upload",
              parameter_types: ["java.lang.String"],
              return_type: "void",
              is_constructor: false,
              overload_count: 1,
              source_path: "com/demo/Api.java",
              line_hint: 12,
              tags: ["回连"],
              evidence: ["命中 clue"],
            },
          },
          {
            source_id: "source-2",
            kind: "template_hook",
            template_name: "OkHttp3 SSL Unpinning",
          },
          {
            source_id: "source-3",
            kind: "custom_script",
            script_name: "trace_login",
            script_path: "/tmp/workspaces/case-001/scripts/trace_login.js",
          },
        ],
        items: [
          {
            item_id: "hook-1",
            kind: "method_hook",
            inject_order: 1,
            enabled: true,
            plugin_id: "builtin.method-hook",
            source: {
              source_id: "source-1",
              kind: "method_hook",
              method: {
                class_name: "com.demo.Api",
                method_name: "upload",
                parameter_types: ["java.lang.String"],
                return_type: "void",
                is_constructor: false,
                overload_count: 1,
                source_path: "com/demo/Api.java",
                line_hint: 12,
                tags: ["回连"],
                evidence: ["命中 clue"],
              },
            },
            render_context: { rendered_script: "send('method');" },
          },
          {
            item_id: "hook-2",
            kind: "template_hook",
            inject_order: 2,
            enabled: true,
            plugin_id: "builtin.ssl",
            source: {
              source_id: "source-2",
              kind: "template_hook",
              template_name: "OkHttp3 SSL Unpinning",
            },
            render_context: {
              rendered_script: "send('template');",
              template_name: "ignored fallback",
            },
          },
          {
            item_id: "hook-3",
            kind: "custom_script",
            inject_order: 3,
            enabled: true,
            plugin_id: "custom.local-script",
            source: {
              source_id: "source-3",
              kind: "custom_script",
              script_name: "trace_login",
              script_path: "/tmp/workspaces/case-001/scripts/trace_login.js",
            },
            render_context: {
              rendered_script: "send('custom');",
              script_name: "ignored-script-name",
            },
          },
        ],
        execution_count: 2,
        last_execution_run_id: "run-2",
        last_execution_mode: "real_frida_session",
        last_executed_backend_key: "real_frida_session",
        last_execution_status: "completed",
        last_execution_stage: "completed",
        last_execution_event_count: 8,
        last_execution_result_path: "/tmp/workspaces/case-001/executions/run-2",
        last_execution_db_path: "/tmp/workspaces/case-001/executions/run-2/hook-events.sqlite3",
        last_execution_bundle_path: "/tmp/workspaces/case-001/executions/run-2",
        last_report_path: "/tmp/workspaces/case-001/reports/case-001-report.md",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await getHookPlan("case-001");

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-001/hook-plan");
    expect(response.items).toHaveLength(3);
    expect(response.items[0].method?.method_name).toBe("upload");
    expect(response.items[0].rendered_script).toBe("send('method');");
    expect(response.items[1].template_name).toBe("OkHttp3 SSL Unpinning");
    expect(response.items[2].script_name).toBe("trace_login");
    expect(response.items[2].script_path).toBe("/tmp/workspaces/case-001/scripts/trace_login.js");
    expect(response.last_execution_db_path).toBe(
      "/tmp/workspaces/case-001/executions/run-2/hook-events.sqlite3",
    );
    expect(response.last_executed_backend_key).toBe("real_frida_session");
    expect(response.last_execution_stage).toBe("completed");
  });

  it("preserves exported report side-channel paths", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-001",
        report_path: "/tmp/workspaces/case-001/reports/case-001-report.md",
        static_report_path: "/tmp/workspaces/case-001/static/report.md",
        last_execution_db_path: "/tmp/workspaces/case-001/executions/run-2/hook-events.sqlite3",
        last_execution_bundle_path: "/tmp/workspaces/case-001/executions/run-2",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await exportReport("case-001");

    expect(response.report_path).toBe("/tmp/workspaces/case-001/reports/case-001-report.md");
    expect(response.static_report_path).toBe("/tmp/workspaces/case-001/static/report.md");
    expect(response.last_execution_db_path).toBe(
      "/tmp/workspaces/case-001/executions/run-2/hook-events.sqlite3",
    );
    expect(response.last_execution_bundle_path).toBe("/tmp/workspaces/case-001/executions/run-2");
  });

  it("prefers per-item source summaries over positional selected_hook_sources matching", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-002",
        updated_at: "2026-04-13T12:30:00Z",
        selected_hook_sources: [
          {
            source_id: "source-other",
            kind: "template_hook",
            template_name: "Should not be used positionally",
          },
        ],
        items: [
          {
            item_id: "hook-1",
            kind: "custom_script",
            inject_order: 1,
            enabled: true,
            plugin_id: "custom.local-script",
            source: {
              source_id: "source-real",
              kind: "custom_script",
              script_name: "trace-login",
              script_path: "/tmp/workspaces/case-002/scripts/trace-login.js",
            },
            render_context: {
              rendered_script: "send('custom');",
            },
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await getHookPlan("case-002");

    expect(response.items).toHaveLength(1);
    expect(response.items[0].script_name).toBe("trace-login");
    expect(response.items[0].script_path).toBe("/tmp/workspaces/case-002/scripts/trace-login.js");
    expect(response.items[0].template_name).toBeNull();
  });

  it("preserves traffic provenance when loading workspace traffic evidence", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-traffic",
        capture: {
          case_id: "case-traffic",
          source_path: "/tmp/workspaces/case-traffic/evidence/traffic/live/live-001.har",
          provenance: {
            kind: "live_capture",
            label: "实时抓包自动导入",
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
          flows: [],
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await getWorkspaceTraffic("case-traffic");

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-traffic/traffic");
    expect(response?.provenance.kind).toBe("live_capture");
    expect(response?.provenance.label).toBe("实时抓包自动导入");
    expect(response?.summary?.https_flow_count).toBe(2);
    expect(response?.summary?.top_hosts[0]?.host).toBe("demo-c2.example");
  });

  it("normalizes ssl hook guidance template entries from the environment payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        summary: "5 available, 4 missing",
        recommended_execution_mode: "real_frida_session",
        tools: [],
        live_capture: {
          available: true,
          source: "builtin_mitmdump",
          detail: "ready",
          listen_host: "0.0.0.0",
          listen_port: 8080,
          help_text: null,
          proxy_address_hint: "分析机局域网 IP:8080",
          install_url: "http://mitm.it",
          certificate_path: null,
          certificate_directory_path: null,
          certificate_exists: false,
          certificate_help_text: null,
          setup_steps: ["先配置代理"],
          proxy_steps: ["代理到分析机局域网 IP:8080"],
          certificate_steps: ["安装 mitm 证书"],
          recommended_actions: ["优先启用 SSL 建议"],
          ssl_hook_guidance: {
            recommended: true,
            summary: "HTTPS 明文仍缺失，建议补 SSL Hook",
            reason: "代理和证书已配置，但关键请求仍然握手失败。",
            suggested_templates: ["okhttp3_unpin.js", "trustmanager_hook.js"],
            suggested_template_entries: [
              {
                source_id: "template:builtin.ssl:okhttp3_unpin",
                template_id: "okhttp3_unpin",
                template_name: "OkHttp3 SSL Unpinning",
                plugin_id: "builtin.ssl",
                label: "OkHttp3 SSL Unpinning",
              },
              {
                source_id: "",
                template_id: "trustmanager_hook",
                template_name: "TrustManager Hook",
                plugin_id: "builtin.ssl",
                label: "TrustManager Hook",
              },
              {
                source_id: "broken",
                kind: "template_hook",
                template_id: null,
                template_name: null,
                plugin_id: null,
              },
            ],
            suggested_terms: ["https", "ssl", "certificate"],
          },
        },
        execution_presets: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await getEnvironmentStatus();

    expect(fetchMock).toHaveBeenCalledWith("/api/settings/environment");
    expect(response.live_capture.ssl_hook_guidance?.suggested_template_entries).toEqual([
      {
        source_id: "template:builtin.ssl:okhttp3_unpin",
        template_id: "okhttp3_unpin",
        template_name: "OkHttp3 SSL Unpinning",
        plugin_id: "builtin.ssl",
        label: "OkHttp3 SSL Unpinning",
      },
      {
        source_id: "template:builtin.ssl:trustmanager_hook",
        template_id: "trustmanager_hook",
        template_name: "TrustManager Hook",
        plugin_id: "builtin.ssl",
        label: "TrustManager Hook",
      },
    ]);
  });

  it("adds the refresh query parameter when reloading workspace detail", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-refresh",
        title: "刷新案件",
        package_name: "com.example.refresh",
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
        method_count: 12,
        runtime: {
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
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await getWorkspaceDetail("case-refresh", { refresh: true });

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-refresh/workspace/detail?refresh=true");
  });

  it("targets the custom script detail, update, and delete endpoints with encoded script ids", async () => {
    const scriptId = "custom_script:/tmp/workspaces/case-traffic/scripts/trace_login.js";
    const encodedScriptId = encodeURIComponent(scriptId);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          script_id: scriptId,
          name: "trace_login",
          script_path: "/tmp/workspaces/case-traffic/scripts/trace_login.js",
          content: "send('v1');\n",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          script_id: "custom_script:/tmp/workspaces/case-traffic/scripts/trace_login_v2.js",
          name: "trace_login_v2",
          script_path: "/tmp/workspaces/case-traffic/scripts/trace_login_v2.js",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => {
          throw new Error("should not parse");
        },
      });
    vi.stubGlobal("fetch", fetchMock);

    const detail = await getWorkspaceCustomScript("case-traffic", scriptId);
    const updated = await updateWorkspaceCustomScript("case-traffic", scriptId, {
      name: "trace_login_v2",
      content: "send('v2');\n",
    });
    await deleteWorkspaceCustomScript("case-traffic", updated.script_id);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `/api/cases/case-traffic/custom-scripts/${encodedScriptId}`,
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, `/api/cases/case-traffic/custom-scripts/${encodedScriptId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: "trace_login_v2",
        content: "send('v2');\n",
      }),
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `/api/cases/case-traffic/custom-scripts/${encodeURIComponent(updated.script_id)}`,
      {
        method: "DELETE",
      },
    );
    expect(detail.content).toBe("send('v1');\n");
    expect(updated.name).toBe("trace_login_v2");
  });

  it("updates hook plan item enabled state through the item patch endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-toggle",
        updated_at: "2026-04-18T10:00:00Z",
        items: [
          {
            item_id: "hook-1",
            kind: "method_hook",
            inject_order: 1,
            enabled: false,
            plugin_id: "builtin.method-hook",
            source: {
              source_id: "source-1",
              kind: "method_hook",
              method: {
                class_name: "com.demo.Api",
                method_name: "upload",
                parameter_types: ["java.lang.String"],
                return_type: "void",
                is_constructor: false,
                overload_count: 1,
                source_path: "com/demo/Api.java",
                line_hint: 12,
                tags: [],
                evidence: [],
              },
            },
            render_context: { rendered_script: "send('method');" },
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await setHookPlanItemEnabled("case-toggle", "hook-1", false);

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-toggle/hook-plan/items/hook-1", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ enabled: false }),
    });
    expect(response.items).toHaveLength(1);
    expect(response.items[0].enabled).toBe(false);
  });

  it("posts template guidance entries to the hook plan template endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-template",
        updated_at: "2026-04-19T20:00:00Z",
        items: [
          {
            item_id: "hook-template-1",
            kind: "template_hook",
            inject_order: 1,
            enabled: true,
            plugin_id: "builtin.ssl",
            source: {
              source_id: "template:builtin.ssl:okhttp3_unpin",
              kind: "template_hook",
              template_id: "okhttp3_unpin",
              template_name: "OkHttp3 SSL Unpinning",
              plugin_id: "builtin.ssl",
            },
            render_context: {
              rendered_script: "send('template');",
            },
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await addTemplateToHookPlan("case-template", {
      template_id: "okhttp3_unpin",
      template_name: "OkHttp3 SSL Unpinning",
      plugin_id: "builtin.ssl",
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-template/hook-plan/templates", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        template_id: "okhttp3_unpin",
        template_name: "OkHttp3 SSL Unpinning",
        plugin_id: "builtin.ssl",
      }),
    });
    expect(response.items[0].template_name).toBe("OkHttp3 SSL Unpinning");
  });

  it("moves hook plan items through the move endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-move",
        updated_at: "2026-04-18T10:05:00Z",
        items: [
          {
            item_id: "hook-2",
            kind: "template_hook",
            inject_order: 1,
            enabled: true,
            plugin_id: "builtin.ssl",
            source: {
              source_id: "source-2",
              kind: "template_hook",
              template_name: "OkHttp3 SSL Unpinning",
            },
            render_context: { rendered_script: "send('template');" },
          },
          {
            item_id: "hook-1",
            kind: "method_hook",
            inject_order: 2,
            enabled: true,
            plugin_id: "builtin.method-hook",
            source: {
              source_id: "source-1",
              kind: "method_hook",
              method: {
                class_name: "com.demo.Api",
                method_name: "upload",
                parameter_types: ["java.lang.String"],
                return_type: "void",
                is_constructor: false,
                overload_count: 1,
                source_path: "com/demo/Api.java",
                line_hint: 12,
                tags: [],
                evidence: [],
              },
            },
            render_context: { rendered_script: "send('method');" },
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await moveHookPlanItem("case-move", "hook-2", "up");

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-move/hook-plan/items/hook-2/move", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ direction: "up" }),
    });
    expect(response.items).toHaveLength(2);
    expect(response.items[0].item_id).toBe("hook-2");
    expect(response.items[0].inject_order).toBe(1);
    expect(response.items[1].item_id).toBe("hook-1");
    expect(response.items[1].inject_order).toBe(2);
  });

  it("surfaces backend detail messages for failed execution starts", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        detail: "Execution is already running for this case.",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(startExecution("case-003", { executionMode: "fake_backend" })).rejects.toThrow(
      "启动执行失败：Execution is already running for this case.",
    );
  });

  it("calls the cancel execution endpoint and returns the cancellation snapshot", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        case_id: "case-004",
        status: "cancelling",
        execution_mode: "real_frida_session",
        stage: "cancelling",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await cancelExecution("case-004");

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-004/executions/cancel", {
      method: "POST",
    });
    expect(response).toEqual({
      case_id: "case-004",
      status: "cancelling",
      execution_mode: "real_frida_session",
      stage: "cancelling",
    });
  });

  it("calls the live traffic capture endpoints and preserves status snapshots", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          case_id: "case-traffic",
          status: "running",
          artifact_path: null,
          message: "实时抓包进行中。",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          case_id: "case-traffic",
          status: "running",
          artifact_path: null,
          message: "已开始实时抓包。",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          case_id: "case-traffic",
          status: "stopped",
          artifact_path: "/tmp/workspaces/case-traffic/traffic/live-001.har",
          message: "已停止实时抓包，产物已保存。",
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const current = await getLiveTrafficCapture("case-traffic");
    const started = await startLiveTrafficCapture("case-traffic");
    const stopped = await stopLiveTrafficCapture("case-traffic");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/cases/case-traffic/traffic/live");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/cases/case-traffic/traffic/live/start", {
      method: "POST",
    });
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/cases/case-traffic/traffic/live/stop", {
      method: "POST",
    });
    expect(current).toEqual({
      case_id: "case-traffic",
      status: "running",
      artifact_path: null,
      message: "实时抓包进行中。",
    });
    expect(started.message).toBe("已开始实时抓包。");
    expect(stopped.artifact_path).toBe("/tmp/workspaces/case-traffic/traffic/live-001.har");
  });

  it("loads the live traffic preview endpoint while capture is running", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        case_id: "case-traffic",
        status: "running",
        preview_path: "/tmp/workspaces/case-traffic/evidence/traffic/live/live-001.ndjson",
        truncated: false,
        items: [
          {
            flow_id: "preview-1",
            timestamp: "2026-04-19T10:00:00Z",
            method: "GET",
            url: "https://cdn.example.org/app.js",
            status_code: 200,
            matched_indicators: [],
            suspicious: false,
          },
          {
            flow_id: "preview-2",
            timestamp: "2026-04-19T10:00:02Z",
            method: "POST",
            url: "https://demo-c2.example/api/upload",
            status_code: 202,
            matched_indicators: ["demo-c2.example"],
            suspicious: true,
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await getLiveTrafficPreview("case-traffic");

    expect(fetchMock).toHaveBeenCalledWith("/api/cases/case-traffic/traffic/live/preview");
    expect(response.status).toBe("running");
    expect(response.items).toHaveLength(2);
    expect(response.items[1].url).toBe("https://demo-c2.example/api/upload");
  });

  it("loads execution preflight and history from the execution APIs", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          case_id: "case-001",
          ready: true,
          execution_mode: "real_frida_session",
          executed_backend_key: "real_frida_session",
          executed_backend_label: "Frida Session",
          detail: "ready",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          case_id: "case-001",
          items: [
            {
              history_id: "exec-1",
              run_id: "run-1",
              execution_mode: "fake_backend",
              executed_backend_key: "fake_backend",
              status: "completed",
              stage: "completed",
              error_code: null,
              error_message: null,
              event_count: 3,
              db_path: "/tmp/run-1/hook-events.sqlite3",
              bundle_path: "/tmp/run-1",
              started_at: "2026-04-18T00:00:00Z",
              updated_at: "2026-04-18T00:00:01Z",
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          case_id: "case-001",
          items: [
            {
              type: "execution.event",
              case_id: "case-001",
              timestamp: "2026-04-18T00:00:01Z",
              message: "com.demo.Api.upload",
              payload: {
                event_type: "method",
                source: "fake",
                class_name: "com.demo.Api",
                method_name: "upload",
                arguments: ["hello"],
                return_value: null,
                stacktrace: "",
                raw_payload: {},
              },
            },
          ],
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const preflight = await getExecutionPreflight("case-001", {
      executionMode: "real_frida_session",
      fridaSessionSeconds: "5",
    });
    const history = await getExecutionHistory("case-001");
    const events = await getExecutionHistoryEvents("case-001", "exec-1", { limit: 5 });

    expect(preflight.ready).toBe(true);
    expect(history[0].history_id).toBe("exec-1");
    expect(events[0].type).toBe("execution.event");
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/cases/case-001/executions/preflight", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        execution_mode: "real_frida_session",
        device_serial: "",
        frida_server_binary_path: "",
        frida_server_remote_path: "",
        frida_session_seconds: "5",
      }),
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/cases/case-001/executions/history");
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/cases/case-001/executions/history/exec-1/events?limit=5",
    );
  });

  it("normalizes connected device payloads and picks the preferred serial", () => {
    const environment = {
      summary: "2 available, 1 missing",
      recommended_execution_mode: "real_device",
      tools: [],
      live_capture: {
        available: true,
        source: "builtin_mitmdump",
        detail: "ready",
        listen_host: "0.0.0.0",
        listen_port: 8080,
        help_text: null,
        proxy_address_hint: null,
        install_url: null,
        certificate_path: null,
        certificate_directory_path: null,
        certificate_exists: false,
        certificate_help_text: null,
        setup_steps: ["先配置代理"],
        proxy_steps: ["代理到分析机局域网 IP:8080"],
        certificate_steps: ["安装 mitm 证书"],
        recommended_actions: ["优先启用 SSL 建议"],
      },
      execution_presets: [],
      connected_devices: [
        "emulator-5554",
        {
          device_serial: "usb-serial-1",
          label: "Pixel 8",
          status: "online",
          detail: "USB 连接",
          model: "Pixel 8",
          recommended: true,
        },
        {
          serial: "usb-serial-1",
          name: "重复项",
          status: "offline",
        },
      ],
      recommended_device_serial: "usb-serial-1",
    } as unknown as EnvironmentStatus;

    const devices = normalizeConnectedDevices(environment);

    expect(devices).toEqual([
      {
        serial: "emulator-5554",
        label: "emulator-5554",
        status: null,
        detail: null,
        model: null,
        transport: null,
        recommended: false,
      },
      {
        serial: "usb-serial-1",
        label: "Pixel 8",
        status: "online",
        detail: "USB 连接",
        model: "Pixel 8",
        transport: null,
        recommended: true,
      },
    ]);
    expect(resolveRecommendedDeviceSerial(environment, devices)).toBe("usb-serial-1");
    expect(resolvePreferredDeviceSerial({ device_serial: "" }, devices, "usb-serial-1")).toBe("usb-serial-1");
    expect(resolvePreferredDeviceSerial({ device_serial: "manual-999" }, devices, "usb-serial-1")).toBe(
      "manual-999",
    );
  });
});
