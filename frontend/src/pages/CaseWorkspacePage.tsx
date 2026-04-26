import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { EvidencePanel } from "../components/workspace/EvidencePanel";
import { ExecutionConsolePanel } from "../components/workspace/ExecutionConsolePanel";
import { HookStudioPanel } from "../components/workspace/HookStudioPanel";
import { ReportsPanel } from "../components/workspace/ReportsPanel";
import { StaticBriefPanel } from "../components/workspace/StaticBriefPanel";
import { TrafficEvidencePanel } from "../components/workspace/TrafficEvidencePanel";
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
  getWorkspaceCustomScript,
  getWorkspaceDetail,
  getWorkspaceEvents,
  getWorkspaceMethods,
  getWorkspaceRecommendations,
  getWorkspaceTraffic,
  importWorkspaceTraffic,
  listWorkspaceCustomScripts,
  moveHookPlanItem,
  openWorkspacePath,
  openWorkspaceInJadx,
  removeHookPlanItem,
  normalizeConnectedDevices,
  resolvePreferredDeviceSerial,
  resolveRecommendedDeviceSerial,
  saveRuntimeSettings,
  setHookPlanItemEnabled,
  saveWorkspaceCustomScript,
  startLiveTrafficCapture,
  startExecution,
  stopLiveTrafficCapture,
  updateWorkspaceCustomScript,
  deleteWorkspaceCustomScript,
} from "../lib/api";
import type {
  CustomScriptSummary,
  ConnectedDeviceSummary,
  ExecutionHistoryEntry,
  ExecutionConsoleExternalContext,
  ExecutionPreflightResponse,
  ExecutionStartResponse,
  HookMethodInsightSummary,
  LiveCaptureRuntimeStatus,
  EnvironmentPresetStatus,
  EnvironmentToolStatus,
  EnvironmentStatus,
  HookPlanMoveDirection,
  HookPlanResponse,
  HookPlanItemSummary,
  HookRecommendationSummary,
  HookStudioExternalContext,
  TrafficEvidenceExternalContext,
  LiveTrafficCaptureResponse,
  LiveTrafficPreviewResponse,
  ReportExportResponse,
  RuntimeSettings,
  TrafficCaptureResponse,
  WorkspaceDetailResponse,
  WorkspaceEvent,
  WorkspaceMethodSummary,
  WorkspaceMethodScope,
  WorkspaceSummary,
} from "../lib/types";
import { localizeExecutionFailureCode } from "../lib/executionDiagnostics";
import { connectWorkspaceEvents } from "../lib/ws";
import { pickFridaServerBinary } from "../lib/desktop";

const METHOD_LIMIT = 120;
const RECOMMENDATION_LIMIT = 6;
const LIVE_TRAFFIC_PREVIEW_POLL_INTERVAL_MS = 1500;
const METHOD_INDEX_REFRESH_TIMEOUT_MS = 30000;
const METHOD_INDEX_PROGRESS_STEPS = [
  { afterMs: 0, progress: 8, label: "准备工作区产物…" },
  { afterMs: 1200, progress: 22, label: "检查静态输出与 JADX 源码…" },
  { afterMs: 3500, progress: 46, label: "扫描反编译源码中的一方代码…" },
  { afterMs: 8000, progress: 70, label: "正在建立函数索引…" },
  { afterMs: 16000, progress: 86, label: "正在整理函数摘要…" },
  { afterMs: 24000, progress: 94, label: "当前案件较大，仍在继续处理…" },
] as const;
const WORKSPACE_SECTIONS = [
  { id: "static-brief-section", label: "静态简报" },
  { id: "hook-studio-section", label: "Hook 工作台" },
  { id: "execution-console-section", label: "执行控制台" },
  { id: "traffic-evidence-section", label: "流量证据" },
  { id: "evidence-center-section", label: "证据中心" },
  { id: "reports-section", label: "报告导出" },
] as const;

const DEFAULT_RUNTIME_SETTINGS: RuntimeSettings = {
  execution_mode: "fake_backend",
  device_serial: "",
  frida_server_binary_path: "",
  frida_server_remote_path: "",
  frida_session_seconds: "",
  live_capture_listen_host: "0.0.0.0",
  live_capture_listen_port: "8080",
};

function localizeDeviceStatus(status: string | null | undefined): string {
  switch (status) {
    case null:
    case undefined:
    case "":
      return "未提供状态";
    case "ready":
    case "available":
    case "connected":
    case "online":
      return "已连接";
    case "selected":
      return "已选中";
    case "unauthorized":
      return "未授权";
    case "offline":
      return "已离线";
    case "bootloader":
      return "引导模式";
    case "recovery":
      return "恢复模式";
    default:
      return status;
  }
}

function summarizeSelectedDevice(
  deviceSerial: string,
  connectedDevices: ConnectedDeviceSummary[],
  recommendedDeviceSerial: string | null,
): string {
  const trimmedSerial = deviceSerial.trim();
  if (!trimmedSerial) {
    if (recommendedDeviceSerial) {
      const recommendedDevice = connectedDevices.find((device) => device.serial === recommendedDeviceSerial);
      return recommendedDevice
        ? `已预选 ${recommendedDevice.label}`
        : `已预选 ${recommendedDeviceSerial}`;
    }
    return "未选设备";
  }

  const selectedDevice = connectedDevices.find((device) => device.serial === trimmedSerial);
  if (selectedDevice) {
    return `当前设备：${selectedDevice.label}`;
  }
  return `手动序列号：${trimmedSerial}`;
}

function workspaceMethodKey(method: WorkspaceMethodSummary): string {
  return [
    method.class_name,
    method.method_name,
    method.source_path,
    method.line_hint ?? "",
    method.parameter_types.join(","),
  ].join("|");
}

function normalizeExecutionStatus(status: string | null | undefined, eventType?: string): string {
  if (status && status.length > 0) {
    return status;
  }
  switch (eventType) {
    case "execution.started":
      return "started";
    case "execution.cancelling":
      return "cancelling";
    case "execution.cancelled":
      return "cancelled";
    case "execution.completed":
      return "completed";
    case "execution.failed":
      return "error";
    case "execution.progress":
      return "started";
    default:
      return "idle";
  }
}

function isExecutionBusy(status: string): boolean {
  return status === "started" || status === "running" || status === "queued" || status === "cancelling";
}

function deriveExecutionSnapshot(detail: WorkspaceDetailResponse | null): ExecutionStartResponse | null {
  const runtime = detail?.runtime;
  if (!detail || !runtime) {
    return null;
  }
  if (
    !runtime.last_execution_status &&
    !runtime.last_execution_stage &&
    !runtime.last_execution_run_id &&
    !runtime.last_execution_mode
  ) {
    return null;
  }
  return {
    case_id: detail.case_id,
    status: runtime.last_execution_status ?? "idle",
    stage: runtime.last_execution_stage,
    execution_mode: runtime.last_execution_mode,
    executed_backend_key: runtime.last_executed_backend_key,
    run_id: runtime.last_execution_run_id,
    event_count: runtime.last_execution_event_count,
    db_path: runtime.last_execution_db_path,
    bundle_path: runtime.last_execution_bundle_path,
    error_code: runtime.last_execution_error_code,
    message: runtime.last_execution_error_message,
  };
}

function deriveLiveTrafficSnapshot(detail: WorkspaceDetailResponse | null): LiveTrafficCaptureResponse | null {
  const runtime = detail?.runtime;
  if (!detail || !runtime) {
    return null;
  }
  if (
    !runtime.live_traffic_status &&
    !runtime.live_traffic_artifact_path &&
    !runtime.live_traffic_preview_path &&
    !runtime.live_traffic_message
  ) {
    return null;
  }
  return {
    case_id: detail.case_id,
    status: runtime.live_traffic_status ?? "idle",
    session_id: runtime.live_traffic_session_id ?? null,
    artifact_path: runtime.live_traffic_artifact_path ?? null,
    output_path: runtime.live_traffic_output_path ?? runtime.live_traffic_artifact_path ?? null,
    preview_path: runtime.live_traffic_preview_path ?? null,
    message: runtime.live_traffic_message ?? null,
  };
}

function hasLiveTrafficArtifact(snapshot: LiveTrafficCaptureResponse): boolean {
  return Boolean(snapshot.artifact_path ?? snapshot.output_path ?? snapshot.preview_path);
}

function isEmptyIdleLiveTrafficSnapshot(snapshot: LiveTrafficCaptureResponse): boolean {
  return (
    snapshot.status === "idle" &&
    snapshot.session_id == null &&
    !hasLiveTrafficArtifact(snapshot) &&
    snapshot.message == null
  );
}

function shouldApplyLiveTrafficCaptureSnapshot(
  current: LiveTrafficCaptureResponse | null,
  next: LiveTrafficCaptureResponse | null,
): boolean {
  if (!current) {
    return true;
  }
  if (!next) {
    return current.status === "idle" || current.status === "unavailable";
  }
  if (current.case_id !== next.case_id) {
    return true;
  }
  if (isEmptyIdleLiveTrafficSnapshot(next)) {
    return !["running", "starting", "stopping", "stopped"].includes(current.status) && !hasLiveTrafficArtifact(current);
  }
  return true;
}

function buildEmptyLiveTrafficPreview(caseId: string, status: string): LiveTrafficPreviewResponse {
  return {
    case_id: caseId,
    status,
    preview_path: null,
    truncated: false,
    items: [],
  };
}

function normalizeLiveTrafficStatus(status: string | null | undefined): string {
  switch (status) {
    case "unavailable":
      return "环境未就绪";
    case "running":
      return "抓包中";
    case "starting":
      return "正在启动";
    case "stopping":
      return "正在停止";
    case "stopped":
      return "已停止";
    case "error":
    case "failed":
      return "抓包异常";
    case "idle":
    case null:
    case undefined:
    case "":
      return "未启动";
    default:
      return status;
  }
}

function isTrafficLinkedRecommendation(entry: HookRecommendationSummary): boolean {
  const haystacks = [
    entry.title,
    entry.reason,
    entry.template_id,
    entry.template_name,
    entry.plugin_id,
    ...entry.matched_terms,
    ...(entry.method?.tags ?? []),
    ...(entry.method?.evidence ?? []),
    entry.method?.class_name ?? "",
    entry.method?.method_name ?? "",
  ]
    .join(" ")
    .toLowerCase();

  return [
    "ssl",
    "https",
    "http",
    "network",
    "okhttp",
    "retrofit",
    "webview",
    "proxy",
    "tls",
    "trustmanager",
    "hostname",
    "socket",
    "pin",
    "流量",
    "网络",
    "证书",
  ].some((keyword) => haystacks.includes(keyword));
}

function scoreTrafficRecommendationForPanel(entry: HookRecommendationSummary): number {
  const haystacks = [
    entry.title,
    entry.reason,
    entry.template_id,
    entry.template_name,
    entry.plugin_id,
    ...entry.matched_terms,
    ...(entry.method?.tags ?? []),
    ...(entry.method?.evidence ?? []),
    entry.method?.class_name ?? "",
    entry.method?.method_name ?? "",
  ]
    .join(" ")
    .toLowerCase();

  let priority = entry.score;
  if (["ssl", "tls", "pin", "trustmanager", "hostname", "证书"].some((keyword) => haystacks.includes(keyword))) {
    priority += 100;
  }
  if (["https", "okhttp", "retrofit", "webview"].some((keyword) => haystacks.includes(keyword))) {
    priority += 40;
  }
  if (["network", "http", "proxy", "socket", "流量", "网络"].some((keyword) => haystacks.includes(keyword))) {
    priority += 10;
  }
  return priority;
}

function readEventPayloadString(event: WorkspaceEvent, key: string): string | null {
  const value = event.payload?.[key];
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function readEventPayloadStringArray(event: WorkspaceEvent, key: string): string[] {
  const value = event.payload?.[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0);
}

function buildExecutionEventMethodRef(
  event: WorkspaceEvent,
): { class_name: string; method_name: string } | null {
  const className = readEventPayloadString(event, "class_name");
  const methodName = readEventPayloadString(event, "method_name");
  if (!className || !methodName) {
    return null;
  }
  return {
    class_name: className,
    method_name: methodName,
  };
}

function buildTrafficMethodHaystack(method: WorkspaceMethodSummary): string {
  return [
    method.class_name,
    method.method_name,
    method.declaration ?? "",
    method.source_preview ?? "",
    ...method.tags,
    ...method.evidence,
  ]
    .join(" ")
    .toLowerCase();
}

function methodMatchesRecommendation(
  method: WorkspaceMethodSummary,
  recommendationMethod: WorkspaceMethodSummary | null,
): boolean {
  if (!recommendationMethod) {
    return false;
  }
  return (
    method.class_name === recommendationMethod.class_name &&
    method.method_name === recommendationMethod.method_name &&
    method.parameter_types.join(",") === recommendationMethod.parameter_types.join(",")
  );
}

function scoreTrafficMethodForContext(method: WorkspaceMethodSummary, keywords: string[]): number {
  const haystack = buildTrafficMethodHaystack(method);
  let score = 0;

  for (const keyword of keywords) {
    const normalized = keyword.trim().toLowerCase();
    if (normalized.length > 0 && haystack.includes(normalized)) {
      score += 45;
    }
  }

  if (["ssl", "tls", "pin", "trustmanager", "hostname", "证书"].some((keyword) => haystack.includes(keyword))) {
    score += 100;
  }
  if (["https", "okhttp", "retrofit", "webview"].some((keyword) => haystack.includes(keyword))) {
    score += 40;
  }
  if (["network", "http", "proxy", "socket", "流量", "网络"].some((keyword) => haystack.includes(keyword))) {
    score += 10;
  }

  return score;
}

function pickTrafficFocusedMethod(options: {
  methods: WorkspaceMethodSummary[];
  externalContext: HookStudioExternalContext | null;
  recommendations: HookRecommendationSummary[];
}): WorkspaceMethodSummary | null {
  const { methods, externalContext, recommendations } = options;
  if (!externalContext || methods.length === 0) {
    return null;
  }

  if (externalContext.focused_method) {
    const directMatch =
      methods.find(
        (method) =>
          method.class_name === externalContext.focused_method?.class_name &&
          method.method_name === externalContext.focused_method?.method_name,
      ) ?? null;
    if (directMatch) {
      return directMatch;
    }
  }

  const focusRecommendation =
    (externalContext.recommendation_id
      ? recommendations.find((item) => item.recommendation_id === externalContext.recommendation_id) ?? null
      : null) ??
    [...recommendations]
      .filter(isTrafficLinkedRecommendation)
      .sort((left, right) => scoreTrafficRecommendationForPanel(right) - scoreTrafficRecommendationForPanel(left))[0] ??
    null;

  const exactRecommendationMethod = focusRecommendation?.method
    ? methods.find((method) => methodMatchesRecommendation(method, focusRecommendation.method)) ?? null
    : null;

  if (exactRecommendationMethod) {
    return exactRecommendationMethod;
  }

  const keywords = externalContext.keywords.length > 0 ? externalContext.keywords : ["ssl", "https", "network"];
  return (
    [...methods]
      .sort((left, right) => scoreTrafficMethodForContext(right, keywords) - scoreTrafficMethodForContext(left, keywords))[0] ??
    null
  );
}

function isLiveTrafficRunning(status: string | null | undefined): boolean {
  return status === "running";
}

function formatWorkspaceTimestamp(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function splitMethodInsightKeywords(rawValue: string): string[] {
  return rawValue
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .split(/[^a-zA-Z0-9\u4e00-\u9fa5]+/)
    .map((part) => part.trim().toLowerCase())
    .filter(
      (part) =>
        part.length >= 3 &&
        !["com", "java", "lang", "android", "void", "string", "list", "internal", "null"].includes(part),
    );
}

function buildMethodInsightKeywords(method: WorkspaceMethodSummary): string[] {
  const uniqueKeywords = new Set<string>();
  const sources = [
    method.class_name,
    method.method_name,
    method.declaration ?? "",
    method.source_preview ?? "",
    ...method.tags,
    ...method.evidence,
  ];

  for (const source of sources) {
    for (const keyword of splitMethodInsightKeywords(source)) {
      uniqueKeywords.add(keyword);
    }
  }

  return Array.from(uniqueKeywords);
}

function summarizeTrafficHosts(hosts: { host: string; flow_count: number; suspicious_count: number; https_flow_count: number }[]): string | null {
  if (hosts.length === 0) {
    return null;
  }
  return hosts
    .slice(0, 2)
    .map((host) => `${host.host}（${host.flow_count} 条）`)
    .join("、");
}

function summarizeSuspiciousHosts(
  hosts: { host: string; flow_count: number; suspicious_count: number; https_flow_count: number }[],
): string | null {
  if (hosts.length === 0) {
    return null;
  }
  return hosts
    .slice(0, 2)
    .map((host) => `${host.host}（可疑 ${host.suspicious_count}，HTTPS ${host.https_flow_count}）`)
    .join("；");
}

function scoreTrafficFlowAgainstKeywords(
  haystack: string,
  keywords: string[],
  options: { suspicious: boolean; matchedIndicatorCount: number; unexpectedStatus: boolean },
): number {
  let score = 0;
  for (const keyword of keywords) {
    if (keyword.length > 0 && haystack.includes(keyword)) {
      score += 18;
    }
  }
  if (options.suspicious) {
    score += 20;
  }
  score += options.matchedIndicatorCount * 8;
  if (options.unexpectedStatus) {
    score += 5;
  }
  return score;
}

function buildRelatedTrafficInsight(options: {
  selectedMethod: WorkspaceMethodSummary;
  trafficCapture: TrafficCaptureResponse | null;
  liveTrafficPreview: LiveTrafficPreviewResponse | null;
  liveCaptureRuntime: LiveCaptureRuntimeStatus | null;
}): HookMethodInsightSummary["traffic"] {
  const { selectedMethod, trafficCapture, liveTrafficPreview, liveCaptureRuntime } = options;
  const keywords = buildMethodInsightKeywords(selectedMethod);
  const captureFlows = trafficCapture?.flows ?? [];
  const previewItems = liveTrafficPreview?.items ?? [];

  const bestCaptureFlow =
    [...captureFlows]
      .map((flow) => {
        const haystack = [
          flow.method,
          flow.url,
          flow.request_preview,
          flow.response_preview,
          ...flow.matched_indicators,
        ]
          .join(" ")
          .toLowerCase();
        return {
          flow,
          score: scoreTrafficFlowAgainstKeywords(haystack, keywords, {
            suspicious: flow.suspicious,
            matchedIndicatorCount: flow.matched_indicators.length,
            unexpectedStatus: flow.status_code !== null && (flow.status_code < 200 || flow.status_code >= 400),
          }),
        };
      })
      .sort((left, right) => right.score - left.score)[0] ?? null;

  const bestPreviewItem =
    [...previewItems]
      .map((item) => {
        const haystack = [item.method, item.url, ...item.matched_indicators].join(" ").toLowerCase();
        return {
          item,
          score: scoreTrafficFlowAgainstKeywords(haystack, keywords, {
            suspicious: item.suspicious,
            matchedIndicatorCount: item.matched_indicators.length,
            unexpectedStatus: item.status_code !== null && (item.status_code < 200 || item.status_code >= 400),
          }),
        };
      })
      .sort((left, right) => right.score - left.score)[0] ?? null;

  if (!trafficCapture && !liveTrafficPreview && !liveCaptureRuntime?.ssl_hook_guidance) {
    return null;
  }

  const captureSummary = trafficCapture?.summary;
  const topHosts = captureSummary?.top_hosts ?? trafficCapture?.top_hosts ?? [];
  const suspiciousHosts = captureSummary?.suspicious_hosts ?? trafficCapture?.suspicious_hosts ?? [];
  const matchedFlowLabel =
    (bestCaptureFlow && bestCaptureFlow.score > 0
      ? `${bestCaptureFlow.flow.method} ${bestCaptureFlow.flow.url}`
      : null) ??
    (bestPreviewItem && bestPreviewItem.score > 0 ? `${bestPreviewItem.item.method} ${bestPreviewItem.item.url}` : null);
  const matchedFlowReason =
    (bestCaptureFlow && bestCaptureFlow.score > 0
      ? bestCaptureFlow.flow.matched_indicators.length > 0
        ? `命中线索：${bestCaptureFlow.flow.matched_indicators.join("、")}`
        : bestCaptureFlow.flow.suspicious
          ? "该请求已被标记为可疑流量。"
          : null
      : null) ??
    (bestPreviewItem && bestPreviewItem.score > 0
      ? bestPreviewItem.item.matched_indicators.length > 0
        ? `命中线索：${bestPreviewItem.item.matched_indicators.join("、")}`
        : bestPreviewItem.item.suspicious
          ? "该实时请求已被标记为可疑。"
          : null
      : null);

  return {
    source_label: trafficCapture?.provenance.label ?? (liveTrafficPreview ? "实时抓包预览" : null),
    flow_count: trafficCapture?.flow_count ?? 0,
    suspicious_count: trafficCapture?.suspicious_count ?? 0,
    https_flow_count: captureSummary?.https_flow_count ?? trafficCapture?.https_flow_count ?? null,
    matched_indicator_count: captureSummary?.matched_indicator_count ?? trafficCapture?.matched_indicator_count ?? null,
    preview_count: liveTrafficPreview?.items.length ?? null,
    top_host_summary: summarizeTrafficHosts(topHosts),
    suspicious_host_summary: summarizeSuspiciousHosts(suspiciousHosts),
    matched_flow_label: matchedFlowLabel,
    matched_flow_reason: matchedFlowReason,
    guidance_summary: liveCaptureRuntime?.ssl_hook_guidance?.summary ?? null,
  };
}

function buildMethodInsightSummary(options: {
  selectedMethod: WorkspaceMethodSummary | null;
  events: WorkspaceEvent[];
  executionResponse: ExecutionStartResponse | null;
  hookPlanState: HookPlanResponse | null;
  trafficCapture: TrafficCaptureResponse | null;
  liveTrafficPreview: LiveTrafficPreviewResponse | null;
  liveCaptureRuntime: LiveCaptureRuntimeStatus | null;
}): HookMethodInsightSummary | null {
  const { selectedMethod, events, executionResponse, hookPlanState, trafficCapture, liveTrafficPreview, liveCaptureRuntime } =
    options;

  if (!selectedMethod) {
    return null;
  }

  const relatedEvents = events.filter((event) => {
    const methodRef = buildExecutionEventMethodRef(event);
    return (
      methodRef?.class_name === selectedMethod.class_name &&
      methodRef.method_name === selectedMethod.method_name
    );
  });
  const latestRelatedEvent = relatedEvents.at(-1) ?? null;
  const executionInsight =
    latestRelatedEvent || executionResponse?.error_code || hookPlanState?.last_execution_error_code
      ? {
          related_event_count: relatedEvents.length,
          latest_event_type: latestRelatedEvent?.type ?? null,
          latest_status: latestRelatedEvent?.status ?? null,
          latest_message: latestRelatedEvent?.message ?? null,
          latest_timestamp: formatWorkspaceTimestamp(latestRelatedEvent?.timestamp),
          latest_arguments: latestRelatedEvent ? readEventPayloadStringArray(latestRelatedEvent, "arguments") : [],
          latest_return_value: latestRelatedEvent ? readEventPayloadString(latestRelatedEvent, "return_value") : null,
          latest_stack_preview: latestRelatedEvent
            ? readEventPayloadString(latestRelatedEvent, "stacktrace")?.split("\n").slice(0, 2).join(" → ") ?? null
            : null,
          failure_code: executionResponse?.error_code ?? hookPlanState?.last_execution_error_code ?? null,
          failure_message: executionResponse?.message ?? hookPlanState?.last_execution_error_message ?? null,
        }
      : null;

  return {
    execution: executionInsight,
    traffic: buildRelatedTrafficInsight({
      selectedMethod,
      trafficCapture,
      liveTrafficPreview,
      liveCaptureRuntime,
    }),
  };
}

function workspaceEventKey(event: WorkspaceEvent): string {
  return [
    event.type,
    event.case_id ?? "",
    event.timestamp ?? "",
    event.run_id ?? "",
    event.stage ?? "",
    event.message ?? "",
  ].join("|");
}

function mergeWorkspaceEvents(current: WorkspaceEvent[], incoming: WorkspaceEvent[]): WorkspaceEvent[] {
  const merged: WorkspaceEvent[] = [];
  const seen = new Set<string>();
  for (const event of [...current, ...incoming]) {
    const key = workspaceEventKey(event);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push(event);
  }
  return merged.slice(-20);
}

function localizeWorkspaceStatus(status: string): string {
  switch (status) {
    case "idle":
      return "待执行";
    case "started":
      return "已启动";
    case "running":
      return "执行中";
    case "cancelling":
      return "正在取消";
    case "cancelled":
      return "已取消";
    case "completed":
      return "已完成";
    case "error":
      return "执行失败";
    default:
      return status;
  }
}

function localizeWorkspaceStage(stage: string | null): string {
  switch (stage) {
    case null:
    case "":
      return "暂无";
    case "queued":
      return "已排队";
    case "executing":
      return "执行中";
    case "persisting":
      return "正在落盘";
    case "cancelling":
      return "正在取消";
    case "cancelled":
      return "已取消";
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    default:
      return stage;
  }
}

function localizeWorkspaceExecutionMode(mode: string | null | undefined): string {
  switch (mode) {
    case "fake_backend":
      return "模拟执行";
    case "real_device":
      return "真实设备";
    case "real_adb_probe":
      return "ADB 探测";
    case "real_frida_bootstrap":
      return "Frida 自举";
    case "real_frida_probe":
      return "Frida 探测";
    case "real_frida_inject":
      return "Frida 注入";
    case "real_frida_session":
      return "Frida 会话";
    case null:
    case undefined:
    case "":
      return "暂无";
    default:
      return mode;
  }
}

function localizeExecutionDetail(detail: string | null | undefined): string | null {
  if (detail === null || detail === undefined || detail === "") {
    return null;
  }

  if (detail === "ready") {
    return "当前执行模式已就绪。";
  }

  const replacements: Array<[string, string]> = [
    ["Add at least one hook plan item first.", "请先添加至少一个 Hook 计划项。"],
    ["Execution is already running for this case.", "当前案件已有执行任务在运行。"],
  ];

  return replacements.reduce((current, [source, target]) => current.replaceAll(source, target), detail);
}

function normalizeRuntimeSettingsForEnvironment(
  runtimeSettings: RuntimeSettings,
  environment: EnvironmentStatus,
): {
  connectedDevices: ConnectedDeviceSummary[];
  recommendedDeviceSerial: string | null;
  runtimeSettings: RuntimeSettings;
} {
  const connectedDevices = normalizeConnectedDevices(environment);
  const recommendedDeviceSerial = resolveRecommendedDeviceSerial(environment, connectedDevices);
  const preferredDeviceSerial = resolvePreferredDeviceSerial(
    runtimeSettings,
    connectedDevices,
    recommendedDeviceSerial,
  );

  if (preferredDeviceSerial === runtimeSettings.device_serial) {
    return {
      connectedDevices,
      recommendedDeviceSerial,
      runtimeSettings,
    };
  }

  return {
    connectedDevices,
    recommendedDeviceSerial,
    runtimeSettings: {
      ...runtimeSettings,
      device_serial: preferredDeviceSerial,
    },
  };
}

export function CaseWorkspacePage(): JSX.Element {
  const { caseId } = useParams<{ caseId: string }>();
  const activeCaseIdRef = useRef<string | null>(caseId ?? null);
  const attemptedMethodIndexRefreshRef = useRef<Set<string>>(new Set());
  const [detail, setDetail] = useState<WorkspaceDetailResponse | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(Boolean(caseId));
  const [searchValue, setSearchValue] = useState("");
  const [methodQuery, setMethodQuery] = useState("");
  const [methodScope, setMethodScope] = useState<WorkspaceMethodScope>("first_party");
  const [availableMethodScopes, setAvailableMethodScopes] = useState<WorkspaceMethodScope[]>([
    "first_party",
    "related_candidates",
    "all",
  ]);
  const [methods, setMethods] = useState<WorkspaceMethodSummary[]>([]);
  const [selectedMethodKey, setSelectedMethodKey] = useState<string | null>(null);
  const [pendingHookStudioFocusNonce, setPendingHookStudioFocusNonce] = useState(0);
  const [hookStudioExternalContext, setHookStudioExternalContext] = useState<HookStudioExternalContext | null>(null);
  const [trafficEvidenceExternalContext, setTrafficEvidenceExternalContext] =
    useState<TrafficEvidenceExternalContext | null>(null);
  const [executionConsoleExternalContext, setExecutionConsoleExternalContext] =
    useState<ExecutionConsoleExternalContext | null>(null);
  const [methodTotal, setMethodTotal] = useState(0);
  const [isLoadingMethods, setIsLoadingMethods] = useState(false);
  const [methodsError, setMethodsError] = useState<string | null>(null);
  const [isRefreshingMethodIndex, setIsRefreshingMethodIndex] = useState(false);
  const [methodIndexMessage, setMethodIndexMessage] = useState<string | null>(null);
  const [methodIndexProgress, setMethodIndexProgress] = useState(0);
  const [methodIndexStageLabel, setMethodIndexStageLabel] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<HookRecommendationSummary[]>([]);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState(false);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);
  const [hookPlanState, setHookPlanState] = useState<HookPlanResponse | null>(null);
  const [hookPlanItems, setHookPlanItems] = useState<HookPlanItemSummary[]>([]);
  const [isLoadingHookPlan, setIsLoadingHookPlan] = useState(Boolean(caseId));
  const [hookPlanError, setHookPlanError] = useState<string | null>(null);
  const [customScripts, setCustomScripts] = useState<CustomScriptSummary[]>([]);
  const [customScriptsError, setCustomScriptsError] = useState<string | null>(null);
  const [selectedCustomScriptId, setSelectedCustomScriptId] = useState<string | null>(null);
  const [draftScriptName, setDraftScriptName] = useState("");
  const [draftScriptContent, setDraftScriptContent] = useState("");
  const [isLoadingCustomScript, setIsLoadingCustomScript] = useState(false);
  const [isDeletingCustomScript, setIsDeletingCustomScript] = useState(false);
  const [isSavingCustomScript, setIsSavingCustomScript] = useState(false);
  const [hookStudioMessage, setHookStudioMessage] = useState<string | null>(null);
  const [hookStudioError, setHookStudioError] = useState<string | null>(null);
  const [isOpeningInJadx, setIsOpeningInJadx] = useState(false);
  const [openJadxMessage, setOpenJadxMessage] = useState<string | null>(null);
  const [openJadxError, setOpenJadxError] = useState<string | null>(null);
  const [trafficCapture, setTrafficCapture] = useState<TrafficCaptureResponse | null>(null);
  const [trafficPath, setTrafficPath] = useState("");
  const [trafficImportMessage, setTrafficImportMessage] = useState<string | null>(null);
  const [trafficError, setTrafficError] = useState<string | null>(null);
  const [isImportingTraffic, setIsImportingTraffic] = useState(false);
  const [liveTrafficCapture, setLiveTrafficCapture] = useState<LiveTrafficCaptureResponse | null>(null);
  const [liveTrafficPreview, setLiveTrafficPreview] = useState<LiveTrafficPreviewResponse | null>(null);
  const [liveTrafficError, setLiveTrafficError] = useState<string | null>(null);
  const [isStartingLiveTraffic, setIsStartingLiveTraffic] = useState(false);
  const [isStoppingLiveTraffic, setIsStoppingLiveTraffic] = useState(false);
  const [events, setEvents] = useState<WorkspaceEvent[]>([]);
  const [environmentSummary, setEnvironmentSummary] = useState<string | null>(null);
  const [recommendedExecutionMode, setRecommendedExecutionMode] = useState<string | null>(null);
  const [executionPresets, setExecutionPresets] = useState<EnvironmentPresetStatus[]>([]);
  const [environmentTools, setEnvironmentTools] = useState<EnvironmentToolStatus[]>([]);
  const [connectedDevices, setConnectedDevices] = useState<ConnectedDeviceSummary[]>([]);
  const [recommendedDeviceSerial, setRecommendedDeviceSerial] = useState<string | null>(null);
  const [liveCaptureRuntime, setLiveCaptureRuntime] = useState<LiveCaptureRuntimeStatus | null>(null);
  const [isLoadingEnvironment, setIsLoadingEnvironment] = useState(Boolean(caseId));
  const [environmentError, setEnvironmentError] = useState<string | null>(null);
  const [selectedExecutionMode, setSelectedExecutionMode] = useState("fake_backend");
  const [runtimeSettings, setRuntimeSettings] = useState<RuntimeSettings>(DEFAULT_RUNTIME_SETTINGS);
  const [isSavingRuntimeSettings, setIsSavingRuntimeSettings] = useState(false);
  const [runtimeSettingsMessage, setRuntimeSettingsMessage] = useState<string | null>(null);
  const [runtimeSettingsError, setRuntimeSettingsError] = useState<string | null>(null);
  const [runtimeSettingsFeedbackTarget, setRuntimeSettingsFeedbackTarget] = useState<"execution" | "traffic" | null>(
    null,
  );
  const [executionPreflight, setExecutionPreflight] = useState<ExecutionPreflightResponse | null>(null);
  const [isLoadingExecutionPreflight, setIsLoadingExecutionPreflight] = useState(false);
  const [executionHistory, setExecutionHistory] = useState<ExecutionHistoryEntry[]>([]);
  const [isLoadingExecutionHistory, setIsLoadingExecutionHistory] = useState(Boolean(caseId));
  const [executionHistoryMessage, setExecutionHistoryMessage] = useState<string | null>(null);
  const [executionResponse, setExecutionResponse] = useState<ExecutionStartResponse | null>(null);
  const [reportResponse, setReportResponse] = useState<ReportExportResponse | null>(null);
  const [reportExportError, setReportExportError] = useState<string | null>(null);
  const [isStartingExecution, setIsStartingExecution] = useState(false);
  const [isCancellingExecution, setIsCancellingExecution] = useState(false);
  const [isExportingReport, setIsExportingReport] = useState(false);
  const [isOpeningWorkspacePath, setIsOpeningWorkspacePath] = useState(false);
  const [workspacePathMessage, setWorkspacePathMessage] = useState<string | null>(null);
  const [workspacePathError, setWorkspacePathError] = useState<string | null>(null);
  const [activeSectionId, setActiveSectionId] = useState<(typeof WORKSPACE_SECTIONS)[number]["id"]>(
    WORKSPACE_SECTIONS[0].id,
  );
  const [expandedWorkspaceMetricId, setExpandedWorkspaceMetricId] = useState<string | null>(null);
  const liveTrafficCaptureRef = useRef<LiveTrafficCaptureResponse | null>(null);

  function replaceLiveTrafficCapture(next: LiveTrafficCaptureResponse | null): void {
    liveTrafficCaptureRef.current = next;
    setLiveTrafficCapture(next);
  }

  function applyLiveTrafficCaptureSnapshot(next: LiveTrafficCaptureResponse | null): boolean {
    if (!shouldApplyLiveTrafficCaptureSnapshot(liveTrafficCaptureRef.current, next)) {
      return false;
    }
    replaceLiveTrafficCapture(next);
    return true;
  }

  function updateLiveTrafficCaptureSnapshot(
    updater: (current: LiveTrafficCaptureResponse | null) => LiveTrafficCaptureResponse | null,
  ): void {
    replaceLiveTrafficCapture(updater(liveTrafficCaptureRef.current));
  }

  async function refreshRuntimeSnapshots(requestCaseId: string): Promise<void> {
    try {
      const [nextDetail, nextHookPlan, nextTrafficCapture, nextLiveTrafficCapture] = await Promise.all([
        getWorkspaceDetail(requestCaseId),
        getHookPlan(requestCaseId),
        getWorkspaceTraffic(requestCaseId),
        getLiveTrafficCapture(requestCaseId),
      ]);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setDetail(nextDetail);
      setHookPlanState(nextHookPlan);
      setHookPlanItems(nextHookPlan.items);
      setTrafficCapture(nextTrafficCapture);
      applyLiveTrafficCaptureSnapshot(nextLiveTrafficCapture);
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanError("执行完成后刷新工作台失败，请手动刷新页面。");
    }
  }

  async function refreshExecutionHistory(requestCaseId: string): Promise<void> {
    setIsLoadingExecutionHistory(true);
    try {
      const items = await getExecutionHistory(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setExecutionHistory(items);
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setExecutionHistoryMessage("加载执行历史失败，请稍后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsLoadingExecutionHistory(false);
      }
    }
  }

  useEffect(() => {
    activeCaseIdRef.current = caseId ?? null;
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      return;
    }
    if (detail?.has_method_index || isLoadingDetail || isRefreshingMethodIndex) {
      return;
    }
    if (attemptedMethodIndexRefreshRef.current.has(caseId)) {
      return;
    }

    attemptedMethodIndexRefreshRef.current.add(caseId);
    setMethodIndexMessage("当前案件尚未建立方法索引，正在尝试自动重建一次。");
    void handleRefreshMethodIndex();
  }, [caseId, detail?.has_method_index, isLoadingDetail, isRefreshingMethodIndex]);

  useEffect(() => {
    setActiveSectionId(WORKSPACE_SECTIONS[0].id);
    setExpandedWorkspaceMetricId(null);
    setHookStudioExternalContext(null);
    setTrafficEvidenceExternalContext(null);
    setExecutionConsoleExternalContext(null);
    setPendingHookStudioFocusNonce(0);
  }, [caseId]);

  useEffect(() => {
    if (!caseId || typeof IntersectionObserver === "undefined") {
      return;
    }

    const sections = WORKSPACE_SECTIONS.map((section) => document.getElementById(section.id)).filter(
      (element): element is HTMLElement => element instanceof HTMLElement,
    );
    if (sections.length === 0) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio);

        if (visibleEntries.length > 0) {
          setActiveSectionId(visibleEntries[0].target.id as (typeof WORKSPACE_SECTIONS)[number]["id"]);
        }
      },
      {
        rootMargin: "-18% 0px -52% 0px",
        threshold: [0.2, 0.45, 0.7],
      },
    );

    sections.forEach((section) => observer.observe(section));

    return () => {
      observer.disconnect();
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setDetail(null);
      setDetailError(null);
      setIsLoadingDetail(false);
      setSearchValue("");
      setMethodQuery("");
      setMethodScope("first_party");
      setAvailableMethodScopes(["first_party", "all"]);
      setMethods([]);
      setSelectedMethodKey(null);
      setMethodTotal(0);
      setMethodsError(null);
      setIsRefreshingMethodIndex(false);
      setMethodIndexMessage(null);
      setMethodIndexProgress(0);
      setMethodIndexStageLabel(null);
      setRecommendations([]);
      setRecommendationsError(null);
      setHookPlanState(null);
      setHookPlanItems([]);
      setIsLoadingHookPlan(false);
      setHookPlanError(null);
      setCustomScripts([]);
      setCustomScriptsError(null);
      setSelectedCustomScriptId(null);
      setDraftScriptName("");
      setDraftScriptContent("");
      setIsLoadingCustomScript(false);
      setIsDeletingCustomScript(false);
      setIsSavingCustomScript(false);
      setHookStudioMessage(null);
      setHookStudioError(null);
      setHookStudioExternalContext(null);
      setTrafficEvidenceExternalContext(null);
      setExecutionConsoleExternalContext(null);
      setPendingHookStudioFocusNonce(0);
      setOpenJadxMessage(null);
      setOpenJadxError(null);
      setTrafficCapture(null);
      setTrafficPath("");
      setTrafficImportMessage(null);
      setTrafficError(null);
      setIsImportingTraffic(false);
      replaceLiveTrafficCapture(null);
      setLiveTrafficPreview(null);
      setLiveTrafficError(null);
      setIsStartingLiveTraffic(false);
      setIsStoppingLiveTraffic(false);
      setEvents([]);
      setEnvironmentSummary(null);
      setRecommendedExecutionMode(null);
      setExecutionPresets([]);
      setEnvironmentTools([]);
      setConnectedDevices([]);
      setRecommendedDeviceSerial(null);
      setIsLoadingEnvironment(false);
      setEnvironmentError(null);
      setSelectedExecutionMode("fake_backend");
      setRuntimeSettings(DEFAULT_RUNTIME_SETTINGS);
      setIsSavingRuntimeSettings(false);
      setRuntimeSettingsMessage(null);
      setRuntimeSettingsError(null);
      setRuntimeSettingsFeedbackTarget(null);
      setExecutionPreflight(null);
      setIsLoadingExecutionPreflight(false);
      setExecutionHistory([]);
      setIsLoadingExecutionHistory(false);
      setExecutionHistoryMessage(null);
      setExecutionResponse(null);
      setIsCancellingExecution(false);
      setReportResponse(null);
      setReportExportError(null);
      setIsOpeningWorkspacePath(false);
      setWorkspacePathMessage(null);
      setWorkspacePathError(null);
      return;
    }

    let active = true;
    setIsLoadingDetail(true);
    setDetailError(null);
    setDetail(null);
    setSearchValue("");
    setMethodQuery("");
    setMethodScope("first_party");
    setAvailableMethodScopes(["first_party", "all"]);
    setMethods([]);
    setMethodTotal(0);
    setMethodsError(null);
    setIsRefreshingMethodIndex(false);
    setMethodIndexMessage(null);
    setMethodIndexProgress(0);
    setMethodIndexStageLabel(null);
    setRecommendations([]);
    setRecommendationsError(null);
    setHookPlanState(null);
    setHookPlanItems([]);
    setIsLoadingHookPlan(true);
    setHookPlanError(null);
    setCustomScripts([]);
    setCustomScriptsError(null);
    setSelectedCustomScriptId(null);
    setDraftScriptName("");
    setDraftScriptContent("");
    setIsLoadingCustomScript(false);
    setIsDeletingCustomScript(false);
    setIsSavingCustomScript(false);
    setHookStudioMessage(null);
    setHookStudioError(null);
    setOpenJadxMessage(null);
    setOpenJadxError(null);
    setTrafficCapture(null);
    setTrafficPath("");
    setTrafficImportMessage(null);
    setTrafficError(null);
    setIsImportingTraffic(false);
    replaceLiveTrafficCapture(null);
    setLiveTrafficPreview(null);
    setLiveTrafficError(null);
    setIsStartingLiveTraffic(false);
    setIsStoppingLiveTraffic(false);
    setEvents([]);
    setEnvironmentSummary(null);
    setRecommendedExecutionMode(null);
    setExecutionPresets([]);
    setEnvironmentTools([]);
    setConnectedDevices([]);
    setRecommendedDeviceSerial(null);
    setIsLoadingEnvironment(true);
    setEnvironmentError(null);
    setSelectedExecutionMode("fake_backend");
    setRuntimeSettings(DEFAULT_RUNTIME_SETTINGS);
    setIsSavingRuntimeSettings(false);
    setRuntimeSettingsMessage(null);
    setRuntimeSettingsError(null);
    setRuntimeSettingsFeedbackTarget(null);
    setExecutionPreflight(null);
    setIsLoadingExecutionPreflight(false);
    setExecutionHistory([]);
    setIsLoadingExecutionHistory(true);
    setExecutionHistoryMessage(null);
    setExecutionResponse(null);
    setIsCancellingExecution(false);
    setReportResponse(null);
    setReportExportError(null);
    setIsOpeningWorkspacePath(false);
    setWorkspacePathMessage(null);
    setWorkspacePathError(null);

    void getWorkspaceDetail(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        setDetail(response);
        setCustomScripts(response.custom_scripts);
        setExecutionResponse(deriveExecutionSnapshot(response));
        applyLiveTrafficCaptureSnapshot(deriveLiveTrafficSnapshot(response));
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setDetail(null);
        setDetailError("案件工作台暂时不可用。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingDetail(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setEnvironmentSummary(null);
      setRecommendedExecutionMode(null);
      setExecutionPresets([]);
      setEnvironmentTools([]);
      setLiveCaptureRuntime(null);
      setIsLoadingEnvironment(false);
      setEnvironmentError(null);
      setRuntimeSettings(DEFAULT_RUNTIME_SETTINGS);
      setRuntimeSettingsMessage(null);
      setRuntimeSettingsError(null);
      setRuntimeSettingsFeedbackTarget(null);
      return;
    }

    let active = true;
    setIsLoadingEnvironment(true);
    setEnvironmentError(null);
    setRuntimeSettingsError(null);

    void Promise.allSettled([getEnvironmentStatus(), getRuntimeSettings()])
      .then(([environmentResult, runtimeSettingsResult]) => {
        if (!active) {
          return;
        }

        let nextRuntimeSettings = DEFAULT_RUNTIME_SETTINGS;
        if (runtimeSettingsResult.status === "fulfilled") {
          nextRuntimeSettings = runtimeSettingsResult.value;
        } else {
          setRuntimeSettingsError("运行参数暂时无法加载，已回退到默认值。");
        }

        if (environmentResult.status === "fulfilled") {
          const response = environmentResult.value;
          const normalized = normalizeRuntimeSettingsForEnvironment(nextRuntimeSettings, response);
          nextRuntimeSettings = normalized.runtimeSettings;
          setRuntimeSettings(normalized.runtimeSettings);
          setEnvironmentSummary(response.summary);
          setRecommendedExecutionMode(response.recommended_execution_mode);
          setExecutionPresets(response.execution_presets);
          setEnvironmentTools(response.tools);
          setConnectedDevices(normalized.connectedDevices);
          setRecommendedDeviceSerial(normalized.recommendedDeviceSerial);
          setLiveCaptureRuntime(response.live_capture);
          const preferredMode =
            response.execution_presets.find((preset) => preset.key === nextRuntimeSettings.execution_mode)?.key ??
            response.recommended_execution_mode ??
            response.execution_presets.find((preset) => preset.available)?.key ??
            "fake_backend";
          setSelectedExecutionMode(preferredMode);
        } else {
          setEnvironmentSummary(null);
          setRecommendedExecutionMode(null);
          setExecutionPresets([]);
          setEnvironmentTools([]);
          setConnectedDevices([]);
          setRecommendedDeviceSerial(null);
          setLiveCaptureRuntime(null);
          setEnvironmentError("执行环境暂时不可用，请稍后重试。");
          setRuntimeSettings(nextRuntimeSettings);
          setSelectedExecutionMode(nextRuntimeSettings.execution_mode || "fake_backend");
        }
      })
      .finally(() => {
        if (active) {
          setIsLoadingEnvironment(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setEvents([]);
      return;
    }

    let active = true;
    void refreshExecutionHistory(caseId);
    void getWorkspaceEvents(caseId, { limit: 20 })
      .then((historyEvents) => {
        if (!active || activeCaseIdRef.current !== caseId) {
          return;
        }
        setEvents((current) => mergeWorkspaceEvents(historyEvents, current));
      })
      .catch(() => {
        if (!active || activeCaseIdRef.current !== caseId) {
          return;
        }
        setEvents((current) =>
          mergeWorkspaceEvents(current, [
            {
              type: "workspace.events.error",
              case_id: caseId,
              message: "加载执行历史失败。",
            },
          ]),
        );
      });

    const connection = connectWorkspaceEvents({
      caseId,
      onEvent: (event) => {
        if (event.case_id && event.case_id !== caseId) {
          return;
        }
        setEvents((current) => mergeWorkspaceEvents(current, [event]));
        if (event.type.startsWith("execution.")) {
          const normalizedStatus = normalizeExecutionStatus(event.status, event.type);
          setExecutionResponse((current) => ({
            case_id: caseId,
            status: normalizedStatus,
            stage: event.stage ?? current?.stage ?? null,
            execution_mode: event.execution_mode ?? current?.execution_mode ?? null,
            executed_backend_key: event.executed_backend_key ?? current?.executed_backend_key ?? null,
            run_id: event.run_id ?? current?.run_id ?? null,
            event_count: event.event_count ?? current?.event_count ?? null,
            db_path: event.db_path ?? current?.db_path ?? null,
            bundle_path: event.bundle_path ?? current?.bundle_path ?? null,
            executed_backend_label: event.executed_backend_label ?? current?.executed_backend_label ?? null,
            error_code: event.type === "execution.failed" ? event.error_code ?? current?.error_code ?? null : null,
            message: event.type === "execution.failed" ? event.message ?? current?.message : null,
          }));
          setHookPlanState((current) =>
            current
              ? {
                  ...current,
                  last_execution_mode: event.execution_mode ?? current.last_execution_mode,
                  last_executed_backend_key: event.executed_backend_key ?? current.last_executed_backend_key,
                  last_execution_status: normalizedStatus,
                  last_execution_stage: event.stage ?? current.last_execution_stage,
                  last_execution_error_code:
                    event.type === "execution.failed" ? event.error_code ?? current.last_execution_error_code : null,
                  last_execution_error_message:
                    event.type === "execution.failed"
                      ? event.message ?? current.last_execution_error_message
                      : null,
                  last_execution_event_count: event.event_count ?? current.last_execution_event_count,
                  last_execution_db_path: event.db_path ?? current.last_execution_db_path,
                  last_execution_result_path: event.bundle_path ?? current.last_execution_result_path,
                  last_execution_bundle_path: event.bundle_path ?? current.last_execution_bundle_path,
                }
              : current,
          );
          setIsCancellingExecution(event.type === "execution.cancelling");
          if (event.type !== "execution.progress" && event.type !== "execution.event") {
            void refreshExecutionHistory(caseId);
          }
        }
        if (event.type === "traffic.live.updated") {
          updateLiveTrafficCaptureSnapshot((current) => ({
            case_id: event.case_id ?? caseId,
            status: event.status ?? current?.status ?? "idle",
            session_id: event.session_id ?? current?.session_id ?? null,
            artifact_path: event.artifact_path ?? current?.artifact_path ?? null,
            output_path: event.output_path ?? current?.output_path ?? event.artifact_path ?? current?.artifact_path ?? null,
            preview_path: event.preview_path ?? current?.preview_path ?? null,
            message: event.message ?? current?.message ?? null,
          }));
          void getLiveTrafficPreview(caseId)
            .then((response) => {
              if (activeCaseIdRef.current !== caseId) {
                return;
              }
              setLiveTrafficPreview(response);
            })
            .catch(() => {
              if (activeCaseIdRef.current !== caseId) {
                return;
              }
              setLiveTrafficPreview(null);
            });
          if (event.status === "stopped") {
            void getWorkspaceTraffic(caseId)
              .then((response) => {
                if (activeCaseIdRef.current !== caseId) {
                  return;
                }
                setTrafficCapture(response);
              })
              .catch(() => {
                if (activeCaseIdRef.current !== caseId) {
                  return;
                }
                setTrafficError("实时抓包停止后刷新流量证据失败，请稍后重试。");
              });
          }
        }
        if (
          event.type === "execution.completed" ||
          event.type === "execution.failed" ||
          event.type === "execution.cancelled"
        ) {
          setIsCancellingExecution(false);
          void refreshRuntimeSnapshots(caseId);
        }
      },
      onError: () => {
        setEvents((current) =>
          mergeWorkspaceEvents(current, [
            {
              type: "workspace.events.error",
              case_id: caseId,
            },
          ]),
        );
      },
    });

    return () => {
      active = false;
      connection.close();
    };
  }, [caseId]);

  useEffect(() => {
    if (!caseId) {
      setExecutionPreflight(null);
      setIsLoadingExecutionPreflight(false);
      return;
    }

    let active = true;
    setIsLoadingExecutionPreflight(true);
    const nextDeviceSerial = resolvePreferredDeviceSerial(
      runtimeSettings,
      connectedDevices,
      recommendedDeviceSerial,
    );
    void getExecutionPreflight(caseId, {
      executionMode: selectedExecutionMode,
      deviceSerial: nextDeviceSerial,
      fridaServerBinaryPath: runtimeSettings.frida_server_binary_path,
      fridaServerRemotePath: runtimeSettings.frida_server_remote_path,
      fridaSessionSeconds: runtimeSettings.frida_session_seconds,
    })
      .then((response) => {
        if (!active || activeCaseIdRef.current !== caseId) {
          return;
        }
        setExecutionPreflight(response);
      })
      .catch(() => {
        if (!active || activeCaseIdRef.current !== caseId) {
          return;
        }
        setExecutionPreflight({
          case_id: caseId,
          ready: false,
          execution_mode: selectedExecutionMode,
          executed_backend_key: null,
          executed_backend_label: null,
          detail: "执行前检查失败，请稍后重试。",
        });
      })
      .finally(() => {
        if (active && activeCaseIdRef.current === caseId) {
          setIsLoadingExecutionPreflight(false);
        }
      });

    return () => {
      active = false;
    };
  }, [
    caseId,
    selectedExecutionMode,
    runtimeSettings.device_serial,
    runtimeSettings.frida_server_binary_path,
    runtimeSettings.frida_server_remote_path,
    runtimeSettings.frida_session_seconds,
    connectedDevices,
    recommendedDeviceSerial,
    hookPlanItems.length,
  ]);

  useEffect(() => {
    if (!caseId || !detail) {
      return;
    }

    let active = true;
    setIsLoadingRecommendations(true);
    setRecommendationsError(null);

    void getWorkspaceRecommendations(caseId, { limit: RECOMMENDATION_LIMIT })
      .then((response) => {
        if (!active) {
          return;
        }
        setRecommendations(response.items);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setRecommendations([]);
        setRecommendationsError("离线推荐暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingRecommendations(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId, detail]);

  useEffect(() => {
    if (!caseId || !detail) {
      setHookPlanItems([]);
      setIsLoadingHookPlan(false);
      setHookPlanError(null);
      return;
    }

    let active = true;
    setIsLoadingHookPlan(true);
    setHookPlanError(null);

    void getHookPlan(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        setHookPlanState(response);
        setHookPlanItems(response.items);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setHookPlanItems([]);
        setHookPlanError("Hook 计划暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingHookPlan(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId, detail]);

  useEffect(() => {
    if (!caseId || !detail) {
      setCustomScripts([]);
      setCustomScriptsError(null);
      return;
    }

    let active = true;
    setCustomScriptsError(null);

    void listWorkspaceCustomScripts(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        setCustomScripts(response.items);
        if (selectedCustomScriptId && !response.items.some((item) => item.script_id === selectedCustomScriptId)) {
          setSelectedCustomScriptId(null);
          setDraftScriptName("");
          setDraftScriptContent("");
        }
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setCustomScripts(detail.custom_scripts);
        setCustomScriptsError("自定义脚本列表暂时不可用，已显示静态快照。");
      });

    return () => {
      active = false;
    };
  }, [caseId, detail]);

  useEffect(() => {
    if (!caseId || !detail) {
      setTrafficCapture(null);
      setTrafficImportMessage(null);
      setTrafficError(null);
      return;
    }

    let active = true;
    setTrafficError(null);

    void getWorkspaceTraffic(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        setTrafficCapture(response);
        setTrafficPath(response?.source_path ?? "");
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setTrafficCapture(null);
        setTrafficError("流量证据暂时不可用，请稍后重试。");
      });

    return () => {
      active = false;
    };
  }, [caseId, detail]);

  useEffect(() => {
    if (!caseId || !detail) {
      replaceLiveTrafficCapture(null);
      setLiveTrafficPreview(null);
      setLiveTrafficError(null);
      setIsStartingLiveTraffic(false);
      setIsStoppingLiveTraffic(false);
      return;
    }

    let active = true;
    setLiveTrafficError(null);

    void getLiveTrafficCapture(caseId)
      .then((response) => {
        if (!active) {
          return;
        }
        const applied = applyLiveTrafficCaptureSnapshot(response);
        if (applied && response.status !== "running" && response.artifact_path === null) {
          setLiveTrafficPreview(null);
        }
      })
      .catch(() => {
        if (!active) {
          return;
        }
        replaceLiveTrafficCapture(null);
        setLiveTrafficError("实时抓包状态暂时不可用，请稍后重试。");
      });

    return () => {
      active = false;
    };
  }, [caseId, detail]);

  useEffect(() => {
    if (!caseId || !detail) {
      setLiveTrafficPreview(null);
      return;
    }
    const activePreviewCaseId = caseId;

    const shouldPollPreview =
      liveTrafficCapture?.status === "running" ||
      (liveTrafficCapture?.artifact_path ?? liveTrafficCapture?.output_path ?? liveTrafficCapture?.preview_path ?? null) !== null;
    if (!shouldPollPreview) {
      setLiveTrafficPreview(buildEmptyLiveTrafficPreview(activePreviewCaseId, liveTrafficCapture?.status ?? "idle"));
      return;
    }

    let active = true;

    async function loadPreview(): Promise<void> {
      try {
        const response = await getLiveTrafficPreview(activePreviewCaseId);
        if (!active || activeCaseIdRef.current !== activePreviewCaseId) {
          return;
        }
        setLiveTrafficPreview(response);
      } catch {
        if (!active || activeCaseIdRef.current !== activePreviewCaseId) {
          return;
        }
        setLiveTrafficPreview(null);
      }
    }

    void loadPreview();
    const timerId =
      liveTrafficCapture?.status === "running"
        ? window.setInterval(() => {
            void loadPreview();
          }, LIVE_TRAFFIC_PREVIEW_POLL_INTERVAL_MS)
        : null;

    return () => {
      active = false;
      if (timerId !== null) {
        window.clearInterval(timerId);
      }
    };
  }, [caseId, detail, liveTrafficCapture?.status, liveTrafficCapture?.artifact_path]);

  useEffect(() => {
    if (!caseId || !detail || !detail.has_method_index) {
      setMethods([]);
      setSelectedMethodKey(null);
      setMethodTotal(0);
      setMethodsError(null);
      setIsLoadingMethods(false);
      return;
    }

    let active = true;
    setIsLoadingMethods(true);
    setMethodsError(null);

    void getWorkspaceMethods(caseId, {
      query: methodQuery.trim(),
      limit: METHOD_LIMIT,
      scope: methodScope,
    })
      .then((response) => {
        if (!active) {
          return;
        }
        setMethods(response.items);
        setMethodScope(response.scope ?? methodScope);
        setAvailableMethodScopes(response.available_scopes ?? ["first_party", "all"]);
        setSelectedMethodKey((current) => {
          if (response.items.length === 0) {
            return null;
          }
          if (current && response.items.some((method) => workspaceMethodKey(method) === current)) {
            return current;
          }
          return workspaceMethodKey(response.items[0]);
        });
        setMethodTotal(response.total);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setMethods([]);
        setSelectedMethodKey(null);
        setMethodTotal(0);
        setMethodsError("方法索引暂时不可用，请稍后重试。");
      })
      .finally(() => {
        if (active) {
          setIsLoadingMethods(false);
        }
      });

    return () => {
      active = false;
    };
  }, [caseId, detail, methodQuery, methodScope]);

  useEffect(() => {
    if (pendingHookStudioFocusNonce === 0 || !hookStudioExternalContext || methods.length === 0) {
      return;
    }

    const focusedMethod = pickTrafficFocusedMethod({
      methods,
      externalContext: hookStudioExternalContext,
      recommendations,
    });

    if (focusedMethod) {
      setSelectedMethodKey(workspaceMethodKey(focusedMethod));
    }
    setPendingHookStudioFocusNonce(0);
  }, [pendingHookStudioFocusNonce, hookStudioExternalContext, methods, recommendations]);

  async function handleRefreshMethodIndex(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    const startedAt = Date.now();
    const progressTimerId = window.setInterval(() => {
      const elapsedMs = Date.now() - startedAt;
      let activeStep: (typeof METHOD_INDEX_PROGRESS_STEPS)[number] = METHOD_INDEX_PROGRESS_STEPS[0];
      for (const step of METHOD_INDEX_PROGRESS_STEPS) {
        if (elapsedMs >= step.afterMs) {
          activeStep = step;
        }
      }
      setMethodIndexProgress(activeStep.progress);
      setMethodIndexStageLabel(activeStep.label);
    }, 240);
    setIsRefreshingMethodIndex(true);
    setMethodIndexMessage("正在重新构建方法索引，过程中可以继续浏览其他区域。");
    setMethodsError(null);
    setMethodIndexProgress(METHOD_INDEX_PROGRESS_STEPS[0].progress);
    setMethodIndexStageLabel(METHOD_INDEX_PROGRESS_STEPS[0].label);
    try {
      const response = await getWorkspaceDetail(requestCaseId, {
        refresh: true,
        timeoutMs: METHOD_INDEX_REFRESH_TIMEOUT_MS,
      });
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setDetail(response);
      setCustomScripts(response.custom_scripts);
      setExecutionResponse(deriveExecutionSnapshot(response));
      applyLiveTrafficCaptureSnapshot(deriveLiveTrafficSnapshot(response));
      setMethodIndexProgress(100);
      setMethodIndexStageLabel("方法索引已完成。");
      setMethodIndexMessage(
        response.has_method_index
          ? `方法索引已刷新，共发现 ${response.method_count} 个函数入口。`
          : "已重新扫描静态产物，但当前案件仍未生成可用的方法索引。",
      );
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setMethodIndexProgress(0);
      setMethodIndexStageLabel(null);
      if (error instanceof DOMException && error.name === "AbortError") {
        setMethodIndexMessage(
          "重建方法索引超过 30 秒，已停止当前等待。你可以稍后再试，或直接在上方打开 JADX 查看源码。",
        );
        setMethodsError("方法索引重建超时，请改用更小范围的案件或稍后重试。");
      } else {
        setMethodIndexMessage(null);
        setMethodsError("重新构建方法索引失败，请稍后重试。");
      }
    } finally {
      window.clearInterval(progressTimerId);
      if (activeCaseIdRef.current === requestCaseId) {
        setIsRefreshingMethodIndex(false);
      }
    }
  }

  async function handleAddMethodToPlan(method: WorkspaceMethodSummary): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await addMethodToHookPlan(requestCaseId, method);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage(`已将 ${method.class_name}.${method.method_name} 加入 Hook 计划。`);
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("加入方法 Hook 计划失败，请稍后重试。");
    }
  }

  const selectedMethod =
    methods.find((method) => workspaceMethodKey(method) === selectedMethodKey) ?? methods[0] ?? null;
  const methodInsight = useMemo(
    () =>
      buildMethodInsightSummary({
        selectedMethod,
        events,
        executionResponse,
        hookPlanState,
        trafficCapture,
        liveTrafficPreview,
        liveCaptureRuntime,
      }),
    [selectedMethod, events, executionResponse, hookPlanState, trafficCapture, liveTrafficPreview, liveCaptureRuntime],
  );
  const localizedPreflightDetail = localizeExecutionDetail(executionPreflight?.detail ?? null);

  async function handleAddRecommendationToPlan(recommendationId: string): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await addRecommendationToHookPlan(requestCaseId, recommendationId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage("已将推荐项加入 Hook 计划。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("接受推荐失败，请稍后重试。");
    }
  }

  async function handleAddTemplateToPlan(template: {
    template_id: string;
    template_name: string;
    plugin_id: string;
  }): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await addTemplateToHookPlan(requestCaseId, template);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage(`已将 ${template.template_name} 加入 Hook 计划。`);
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("加入模板 Hook 计划失败，请稍后重试。");
    }
  }

  function handleInspectHookContext(payload: {
    hint: string;
    query: string;
    scope: WorkspaceMethodScope;
  }): void {
    const normalizedQuery = payload.query.trim();
    const contextKeywords = normalizedQuery.length > 0 ? normalizedQuery.split(/\s+/).filter(Boolean) : [];
    const focusRecommendation =
      [...recommendations]
        .filter(isTrafficLinkedRecommendation)
        .sort((left, right) => scoreTrafficRecommendationForPanel(right) - scoreTrafficRecommendationForPanel(left))[0] ??
      null;

    setHookStudioExternalContext({
      source: "traffic_evidence",
      title: "来自流量证据的线索",
      summary: payload.hint,
      keywords: contextKeywords,
      suggested_query: normalizedQuery,
      suggested_scope: payload.scope,
      recommendation_id: focusRecommendation?.recommendation_id ?? null,
      recommendation_title: focusRecommendation?.title ?? null,
      focused_method: null,
    });
    setTrafficEvidenceExternalContext(null);
    setExecutionConsoleExternalContext(null);
    setHookStudioError(null);
    setHookStudioMessage(null);
    setMethodScope(payload.scope);
    setSearchValue(normalizedQuery);
    setMethodQuery(normalizedQuery);
    setSelectedMethodKey(null);
    setPendingHookStudioFocusNonce((current) => current + 1);
    setActiveSectionId("hook-studio-section");
    window.requestAnimationFrame(() => {
      const hookStudioSection = document.getElementById("hook-studio-section");
      if (hookStudioSection instanceof HTMLElement && typeof hookStudioSection.scrollIntoView === "function") {
        hookStudioSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  }

  function handleInspectHookFromExecutionContext(event: WorkspaceEvent, source: "execution_console" | "evidence_center"): void {
    const methodRef = buildExecutionEventMethodRef(event);
    if (!methodRef) {
      return;
    }

    const query = `${methodRef.class_name} ${methodRef.method_name}`.trim();
    setHookStudioExternalContext({
      source,
      title: source === "execution_console" ? "来自执行控制台的定位" : "来自证据中心的定位",
      summary: `已根据 ${methodRef.class_name}.${methodRef.method_name} 切到 Hook 工作台，并尝试定位对应函数。`,
      keywords: [methodRef.class_name, methodRef.method_name],
      suggested_query: query,
      suggested_scope: "all",
      recommendation_id: null,
      recommendation_title: null,
      focused_method: methodRef,
    });
    setTrafficEvidenceExternalContext(null);
    setExecutionConsoleExternalContext(null);
    setHookStudioError(null);
    setHookStudioMessage(null);
    setMethodScope("all");
    setSearchValue(query);
    setMethodQuery(query);
    setSelectedMethodKey(null);
    setPendingHookStudioFocusNonce((current) => current + 1);
    setActiveSectionId("hook-studio-section");
    window.requestAnimationFrame(() => {
      const hookStudioSection = document.getElementById("hook-studio-section");
      if (hookStudioSection instanceof HTMLElement && typeof hookStudioSection.scrollIntoView === "function") {
        hookStudioSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  }

  function handleInspectExecutionContext(payload: { class_name: string; method_name: string }): void {
    setHookStudioExternalContext(null);
    setTrafficEvidenceExternalContext(null);
    setExecutionConsoleExternalContext({
      source: "hook_studio",
      title: "来自 Hook 工作台的回看",
      summary: `已根据 ${payload.class_name}.${payload.method_name} 回到执行控制台，可继续核对相关事件、返回值与堆栈。`,
      class_name: payload.class_name,
      method_name: payload.method_name,
    });
    setActiveSectionId("execution-console-section");
    window.requestAnimationFrame(() => {
      const executionSection = document.getElementById("execution-console-section");
      if (executionSection instanceof HTMLElement && typeof executionSection.scrollIntoView === "function") {
        executionSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  }

  function handleInspectTrafficContext(payload: {
    hint: string;
    recommendationId: string | null;
    recommendationTitle: string | null;
  }): void {
    setHookStudioExternalContext(null);
    setTrafficEvidenceExternalContext({
      source: "hook_studio",
      title: "来自 Hook 工作台的回看",
      summary: payload.hint,
      recommendation_id: payload.recommendationId,
      recommendation_title: payload.recommendationTitle,
    });
    setExecutionConsoleExternalContext(null);
    setActiveSectionId("traffic-evidence-section");
    window.requestAnimationFrame(() => {
      const trafficSection = document.getElementById("traffic-evidence-section");
      if (trafficSection instanceof HTMLElement && typeof trafficSection.scrollIntoView === "function") {
        trafficSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  }

  async function handleAddCustomScriptToPlan(scriptId: string): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await addCustomScriptToHookPlan(requestCaseId, scriptId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage("已将自定义脚本加入 Hook 计划。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("加入自定义脚本失败，请稍后重试。");
    }
  }

  async function handleClearHookPlan(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await clearHookPlan(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage("已清空当前 Hook 计划。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("清空 Hook 计划失败，请稍后重试。");
    }
  }

  async function handleRemoveHookPlanItem(itemId: string): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await removeHookPlanItem(requestCaseId, itemId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage("已移除 Hook 计划项。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("移除 Hook 计划项失败，请稍后重试。");
    }
  }

  async function handleSetHookPlanItemEnabled(itemId: string, enabled: boolean): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await setHookPlanItemEnabled(requestCaseId, itemId, enabled);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage(enabled ? "已启用 Hook 计划项。" : "已禁用 Hook 计划项。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("更新 Hook 计划项状态失败，请稍后重试。");
    }
  }

  async function handleMoveHookPlanItem(itemId: string, direction: HookPlanMoveDirection): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await moveHookPlanItem(requestCaseId, itemId, direction);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
      setHookStudioMessage(direction === "up" ? "已上移 Hook 计划项。" : "已下移 Hook 计划项。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError("调整 Hook 计划顺序失败，请稍后重试。");
    }
  }

  async function refreshHookPlanAfterScriptMutation(requestCaseId: string): Promise<void> {
    try {
      const response = await getHookPlan(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanState(response);
      setHookPlanItems(response.items);
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookPlanError("自定义脚本变更后刷新 Hook 计划失败，请稍后手动刷新。");
    }
  }

  function handleCreateCustomScriptDraft(): void {
    setSelectedCustomScriptId(null);
    setDraftScriptName("");
    setDraftScriptContent("");
    setHookStudioMessage(null);
    setHookStudioError(null);
  }

  async function handleLoadCustomScript(scriptId: string): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setIsLoadingCustomScript(true);
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = await getWorkspaceCustomScript(requestCaseId, scriptId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setSelectedCustomScriptId(response.script_id);
      setDraftScriptName(response.name);
      setDraftScriptContent(response.content);
      setHookStudioMessage(`已加载脚本 ${response.name}。`);
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError(error instanceof Error ? error.message : "加载自定义脚本失败，请稍后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsLoadingCustomScript(false);
      }
    }
  }

  async function handleSaveCustomScript(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    const normalizedName = draftScriptName.trim();
    const normalizedContent = draftScriptContent.trim();
    if (!normalizedName || !normalizedContent) {
      setHookStudioMessage(null);
      setHookStudioError("请先填写脚本名称和脚本内容。");
      return;
    }

    setIsSavingCustomScript(true);
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      const response = selectedCustomScriptId
        ? await updateWorkspaceCustomScript(requestCaseId, selectedCustomScriptId, {
            name: normalizedName,
            content: draftScriptContent,
          })
        : await saveWorkspaceCustomScript(requestCaseId, {
            name: normalizedName,
            content: draftScriptContent,
          });
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setCustomScripts((current) => {
        const next = current.filter((item) => item.script_id !== (selectedCustomScriptId ?? response.script_id));
        return [...next, response];
      });
      setSelectedCustomScriptId(response.script_id);
      setDraftScriptName(response.name);
      setHookStudioMessage(
        selectedCustomScriptId ? `已更新脚本 ${response.name}。` : `已保存脚本 ${response.name}。`,
      );
      await refreshHookPlanAfterScriptMutation(requestCaseId);
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError(error instanceof Error ? error.message : "保存自定义脚本失败，请稍后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsSavingCustomScript(false);
      }
    }
  }

  async function handleDeleteCustomScript(scriptId: string): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    const targetScript =
      customScripts.find((item) => item.script_id === scriptId) ??
      (selectedCustomScriptId === scriptId
        ? {
            script_id: scriptId,
            name: draftScriptName.trim(),
            script_path: "",
          }
        : null);
    setIsDeletingCustomScript(true);
    setHookStudioMessage(null);
    setHookStudioError(null);
    try {
      await deleteWorkspaceCustomScript(requestCaseId, scriptId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setCustomScripts((current) => current.filter((item) => item.script_id !== scriptId));
      if (selectedCustomScriptId === scriptId) {
        setSelectedCustomScriptId(null);
        setDraftScriptName("");
        setDraftScriptContent("");
      }
      const deletedName = targetScript?.name?.trim() || "所选脚本";
      setHookStudioMessage(`已删除脚本 ${deletedName}。`);
      await refreshHookPlanAfterScriptMutation(requestCaseId);
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setHookStudioError(error instanceof Error ? error.message : "删除自定义脚本失败，请稍后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsDeletingCustomScript(false);
      }
    }
  }

  async function handleOpenInJadx(): Promise<void> {
    if (!caseId || !detail?.can_open_in_jadx) {
      return;
    }

    const requestCaseId = caseId;
    setIsOpeningInJadx(true);
    setOpenJadxMessage(null);
    setOpenJadxError(null);

    try {
      await openWorkspaceInJadx(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setOpenJadxMessage("已尝试在本机打开 JADX。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setOpenJadxError("打开 JADX 失败，请检查本机配置。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsOpeningInJadx(false);
      }
    }
  }

  async function handleStartLiveTrafficCapture(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setIsStartingLiveTraffic(true);
    setLiveTrafficError(null);
    try {
      const response = await startLiveTrafficCapture(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      replaceLiveTrafficCapture(response);
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setLiveTrafficError(error instanceof Error ? error.message : "启动实时抓包失败，请稍后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsStartingLiveTraffic(false);
      }
    }
  }

  async function handleStopLiveTrafficCapture(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setIsStoppingLiveTraffic(true);
    setLiveTrafficError(null);
    try {
      const response = await stopLiveTrafficCapture(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      replaceLiveTrafficCapture(response);
      if (response.artifact_path) {
        const nextCapture = await getWorkspaceTraffic(requestCaseId);
        if (activeCaseIdRef.current !== requestCaseId) {
          return;
        }
        setTrafficCapture(nextCapture);
      }
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setLiveTrafficError(error instanceof Error ? error.message : "停止实时抓包失败，请稍后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsStoppingLiveTraffic(false);
      }
    }
  }

  async function handleImportTraffic(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    const normalizedPath = trafficPath.trim();
    if (!normalizedPath) {
      setTrafficImportMessage(null);
      setTrafficError("请先提供 HAR 文件路径。");
      return;
    }

    setIsImportingTraffic(true);
    setTrafficImportMessage(null);
    setTrafficError(null);
    try {
      const response = await importWorkspaceTraffic(requestCaseId, {
        harPath: normalizedPath,
      });
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setTrafficCapture(response);
      setTrafficPath(response.source_path);
      setTrafficImportMessage("已加载流量证据。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setTrafficError("导入 HAR 失败，请检查文件路径后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsImportingTraffic(false);
      }
    }
  }

  async function persistRuntimeSettings(
    nextSettings: RuntimeSettings,
    options: { silent?: boolean; feedbackTarget?: "execution" | "traffic" } = {},
  ): Promise<RuntimeSettings | null> {
    setIsSavingRuntimeSettings(true);
    setRuntimeSettingsFeedbackTarget(options.feedbackTarget ?? null);
    if (!options.silent) {
      setRuntimeSettingsMessage(null);
      setRuntimeSettingsError(null);
    }
    try {
      const saved = await saveRuntimeSettings(nextSettings);
      if (activeCaseIdRef.current !== caseId) {
        return null;
      }
      setRuntimeSettings(saved);
      try {
        const environment = await getEnvironmentStatus();
        if (activeCaseIdRef.current === caseId) {
          const normalized = normalizeRuntimeSettingsForEnvironment(saved, environment);
          setEnvironmentSummary(environment.summary);
          setRecommendedExecutionMode(environment.recommended_execution_mode);
          setExecutionPresets(environment.execution_presets);
          setEnvironmentTools(environment.tools);
          setConnectedDevices(normalized.connectedDevices);
          setRecommendedDeviceSerial(normalized.recommendedDeviceSerial);
          setLiveCaptureRuntime(environment.live_capture);
          setRuntimeSettings(normalized.runtimeSettings);
        }
      } catch {
        if (activeCaseIdRef.current === caseId) {
          setEnvironmentError("执行环境暂时不可用，请稍后重试。");
        }
      }
      if (!options.silent) {
        setRuntimeSettingsMessage("已保存运行参数。");
      }
      return saved;
    } catch {
      if (activeCaseIdRef.current !== caseId) {
        return null;
      }
      setRuntimeSettings(nextSettings);
      setRuntimeSettingsError(
        options.silent ? "运行参数未能保存，但本次执行仍会继续。" : "保存运行参数失败，请稍后重试。",
      );
      return null;
    } finally {
      if (activeCaseIdRef.current === caseId) {
        setIsSavingRuntimeSettings(false);
      }
    }
  }

  function handleRuntimeSettingChange(field: keyof RuntimeSettings, value: string): void {
    setRuntimeSettingsFeedbackTarget(null);
    setRuntimeSettingsMessage(null);
    setRuntimeSettingsError(null);
    setRuntimeSettings((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSaveRuntimeSettings(target: "execution" | "traffic" = "execution"): Promise<void> {
    if (!caseId) {
      return;
    }

    const nextDeviceSerial = resolvePreferredDeviceSerial(
      runtimeSettings,
      connectedDevices,
      recommendedDeviceSerial,
    );
    await persistRuntimeSettings({
      ...runtimeSettings,
      device_serial: nextDeviceSerial,
      execution_mode: selectedExecutionMode,
    }, { feedbackTarget: target });
  }

  async function handlePickFridaServerBinary(): Promise<void> {
    try {
      const selectedPath = await pickFridaServerBinary();
      if (!selectedPath) {
        return;
      }
      handleRuntimeSettingChange("frida_server_binary_path", selectedPath);
    } catch {
      setRuntimeSettingsMessage(null);
      setRuntimeSettingsError("选择 Frida Server 文件失败，请检查桌面权限或手动填写路径。");
    }
  }

  async function handleStartExecution(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setIsStartingExecution(true);
    const nextDeviceSerial = resolvePreferredDeviceSerial(
      runtimeSettings,
      connectedDevices,
      recommendedDeviceSerial,
    );
    const nextRuntimeSettings: RuntimeSettings = {
      ...runtimeSettings,
      device_serial: nextDeviceSerial,
      execution_mode: selectedExecutionMode,
    };
    try {
      void persistRuntimeSettings(nextRuntimeSettings, { silent: true });
      const response = await startExecution(requestCaseId, {
        executionMode: selectedExecutionMode,
        deviceSerial: nextRuntimeSettings.device_serial,
        fridaServerBinaryPath: nextRuntimeSettings.frida_server_binary_path,
        fridaServerRemotePath: nextRuntimeSettings.frida_server_remote_path,
        fridaSessionSeconds: nextRuntimeSettings.frida_session_seconds,
      });
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setRuntimeSettings(nextRuntimeSettings);
      setExecutionResponse(response);
      setHookPlanState((current) =>
        current
          ? {
              ...current,
              last_execution_run_id: response.run_id ?? current.last_execution_run_id,
              last_execution_mode: response.execution_mode ?? current.last_execution_mode,
              last_executed_backend_key:
                response.executed_backend_key ?? current.last_executed_backend_key,
              last_execution_status: response.status,
              last_execution_stage: response.stage ?? current.last_execution_stage,
              last_execution_error_code: null,
              last_execution_error_message: null,
              last_execution_event_count: response.event_count ?? current.last_execution_event_count,
              last_execution_result_path: response.bundle_path ?? current.last_execution_result_path,
              last_execution_db_path: response.db_path ?? current.last_execution_db_path,
              last_execution_bundle_path: response.bundle_path ?? current.last_execution_bundle_path,
            }
          : current,
      );
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      const message = error instanceof Error ? error.message : "启动执行失败，请稍后重试。";
      setExecutionResponse({
        case_id: requestCaseId,
        status: "error",
        stage: "failed",
        execution_mode: selectedExecutionMode,
        executed_backend_key: null,
        error_code: "unknown_execution_error",
        message,
      });
      setEvents((current) =>
        [
          ...current,
          {
            type: "execution.failed",
            case_id: requestCaseId,
            status: "error",
            stage: "failed",
            execution_mode: selectedExecutionMode,
            error_code: "unknown_execution_error",
            message,
          },
        ].slice(-20),
      );
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsStartingExecution(false);
      }
    }
  }

  async function handleCancelExecution(): Promise<void> {
    if (!caseId || !isExecutionBusy(executionStatusText)) {
      return;
    }

    const requestCaseId = caseId;
    setIsCancellingExecution(true);
    try {
      const response = await cancelExecution(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setExecutionResponse((current) => ({
        case_id: requestCaseId,
        status: response.status,
        stage: response.stage ?? current?.stage ?? null,
        execution_mode: response.execution_mode ?? current?.execution_mode ?? null,
        executed_backend_key: response.executed_backend_key ?? current?.executed_backend_key ?? null,
        run_id: current?.run_id ?? null,
        event_count: current?.event_count ?? null,
        db_path: current?.db_path ?? null,
        bundle_path: current?.bundle_path ?? null,
        executed_backend_label: current?.executed_backend_label ?? null,
        error_code: null,
        message: null,
      }));
      setHookPlanState((current) =>
        current
          ? {
              ...current,
              last_execution_mode: response.execution_mode ?? current.last_execution_mode,
              last_executed_backend_key:
                response.executed_backend_key ?? current.last_executed_backend_key,
              last_execution_status: response.status,
              last_execution_stage: response.stage ?? current.last_execution_stage,
              last_execution_error_code: null,
              last_execution_error_message: null,
            }
          : current,
      );
    } catch (error) {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      const message = error instanceof Error ? error.message : "取消执行失败，请稍后重试。";
      setEvents((current) =>
        [
          ...current,
          {
            type: "workspace.events.error",
            case_id: requestCaseId,
            message,
          },
        ].slice(-20),
      );
      setIsCancellingExecution(false);
    }
  }

  async function handleExportReport(): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setIsExportingReport(true);
    setReportExportError(null);
    try {
      const response = await exportReport(requestCaseId);
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setReportResponse(response);
      setHookPlanState((current) =>
        current
          ? {
              ...current,
              last_report_path: response.report_path,
              last_execution_db_path: response.last_execution_db_path ?? current.last_execution_db_path,
              last_execution_bundle_path:
                response.last_execution_bundle_path ?? current.last_execution_bundle_path,
            }
          : current,
      );
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setReportResponse(null);
      setReportExportError("报告导出失败，请稍后重试。");
    } finally {
      if (activeCaseIdRef.current === requestCaseId) {
        setIsExportingReport(false);
      }
    }
  }

  async function handleOpenWorkspacePath(targetPath: string): Promise<void> {
    const normalizedPath = targetPath.trim();
    if (!normalizedPath) {
      return;
    }

    setIsOpeningWorkspacePath(true);
    setWorkspacePathMessage(null);
    setWorkspacePathError(null);
    try {
      await openWorkspacePath(normalizedPath);
      setWorkspacePathMessage("已在本机打开所选路径。");
    } catch {
      setWorkspacePathError("打开本地路径失败，请检查路径是否存在。");
    } finally {
      setIsOpeningWorkspacePath(false);
    }
  }

  async function handleReplayExecutionHistory(historyId: string): Promise<void> {
    if (!caseId) {
      return;
    }

    const requestCaseId = caseId;
    setExecutionHistoryMessage(null);
    try {
      const replayedEvents = await getExecutionHistoryEvents(requestCaseId, historyId, { limit: 20 });
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setEvents(replayedEvents);
      setExecutionHistoryMessage("已回放所选执行的最近事件。");
    } catch {
      if (activeCaseIdRef.current !== requestCaseId) {
        return;
      }
      setExecutionHistoryMessage("回放执行历史失败，请稍后重试。");
    }
  }

  // C4: 输入即搜索（250ms 防抖）。手动按钮 / 回车仍可立即触发。
  useEffect(() => {
    if (!detail?.has_method_index) {
      return undefined;
    }
    const trimmed = searchValue.trim();
    if (trimmed === methodQuery) {
      return undefined;
    }
    const timerId = window.setTimeout(() => {
      setMethodQuery(trimmed);
    }, 250);
    return () => window.clearTimeout(timerId);
  }, [searchValue, methodQuery, detail?.has_method_index]);

  function handleMethodSearch(): void {
    if (!detail?.has_method_index) {
      return;
    }

    setMethodQuery(searchValue.trim());
  }

  const latestEvent = events.length > 0 ? events[events.length - 1] : null;
  const runtimeStatus = hookPlanState?.last_execution_status ?? detail?.runtime.last_execution_status ?? null;
  const runtimeStage = hookPlanState?.last_execution_stage ?? detail?.runtime.last_execution_stage ?? null;
  const runtimeRequestedMode = hookPlanState?.last_execution_mode ?? detail?.runtime.last_execution_mode ?? null;
  const runtimeExecutedBackendKey =
    hookPlanState?.last_executed_backend_key ?? detail?.runtime.last_executed_backend_key ?? null;
  const runtimeErrorCode = hookPlanState?.last_execution_error_code ?? detail?.runtime.last_execution_error_code ?? null;
  const runtimeErrorMessage =
    hookPlanState?.last_execution_error_message ?? detail?.runtime.last_execution_error_message ?? null;
  const executionStatusText = normalizeExecutionStatus(
    latestEvent?.status ?? executionResponse?.status ?? runtimeStatus,
    latestEvent?.type,
  );
  const executionStageText = latestEvent?.stage ?? executionResponse?.stage ?? runtimeStage;
  const requestedExecutionMode =
    latestEvent?.execution_mode ?? executionResponse?.execution_mode ?? runtimeRequestedMode;
  const executedBackendKey =
    latestEvent?.executed_backend_key ?? executionResponse?.executed_backend_key ?? runtimeExecutedBackendKey;
  const failureCode =
    (latestEvent?.type === "execution.failed" ? latestEvent.error_code ?? null : null) ??
    executionResponse?.error_code ??
    runtimeErrorCode;
  const failureMessage = localizeExecutionDetail(
    (latestEvent?.type === "execution.failed" ? latestEvent.message ?? null : null) ??
      executionResponse?.message ??
      runtimeErrorMessage,
  );
  const startBlockedReason =
    !caseId
      ? "当前案件尚未加载完成。"
      : isStartingExecution
        ? "执行正在启动，请稍候。"
        : isExecutionBusy(executionStatusText)
          ? "当前已有执行任务在运行或取消中，请等待当前任务结束。"
          : hookPlanItems.length === 0
          ? "当前 Hook 计划为空，请先在 Hook 工作台中选择函数、接受推荐，或加入自定义脚本。"
          : executionPreflight?.ready === false
              ? localizedPreflightDetail
              : null;
  const runtimeLiveTraffic = deriveLiveTrafficSnapshot(detail);
  const liveTrafficStatus = liveTrafficCapture?.status ?? runtimeLiveTraffic?.status ?? "idle";
  const liveTrafficArtifactPath =
    liveTrafficCapture?.artifact_path ?? runtimeLiveTraffic?.artifact_path ?? null;
  const liveTrafficMessage = liveTrafficCapture?.message ?? runtimeLiveTraffic?.message ?? null;
  const liveTrafficStatusText = normalizeLiveTrafficStatus(liveTrafficStatus);
  const liveTrafficBusy = isStartingLiveTraffic || isStoppingLiveTraffic;
  const trafficRecommendations = [...recommendations]
    .filter(isTrafficLinkedRecommendation)
    .sort((left, right) => scoreTrafficRecommendationForPanel(right) - scoreTrafficRecommendationForPanel(left))
    .slice(0, 3);
  const startLiveTrafficDisabled =
    !caseId ||
    liveTrafficBusy ||
    isLiveTrafficRunning(liveTrafficStatus) ||
    liveTrafficStatus === "starting" ||
    liveCaptureRuntime?.available === false;
  const stopLiveTrafficDisabled =
    !caseId || liveTrafficBusy || (!isLiveTrafficRunning(liveTrafficStatus) && liveTrafficStatus !== "starting");
  const workspaceSummary: WorkspaceSummary | null = detail
    ? {
        case_id: detail.case_id,
        title: detail.title,
        view: "workspace",
      }
    : null;
  const workspaceMetricDetails = [
    {
      id: "case-id",
      label: "案件编号",
      summary: caseId ?? "未选择",
      detail: caseId ? `当前工作台绑定案件 ${caseId}。后续执行、流量证据和报告都会围绕这个案件落盘。` : "当前还没有选中案件。",
    },
    {
      id: "package-name",
      label: "包名",
      summary: detail?.package_name ?? "等待静态简报加载",
      detail: detail?.package_name
        ? `当前样本的包名是 ${detail.package_name}。如果你准备按函数定位，一般先围绕这个包名前缀筛一方代码。`
        : "静态简报还没有完成加载，包名将在静态产物就绪后显示。",
    },
    {
      id: "method-index",
      label: "方法索引",
      summary: detail?.has_method_index ? "已建立" : "尚未建立",
      detail: detail?.has_method_index
        ? `当前已建立 ${detail.method_count} 个函数入口索引，可以在 Hook 工作台里按类浏览、搜索函数并直接加入 Hook 计划。`
        : "当前案件还没有可用的方法索引。你可以在 Hook 工作台里重新构建索引，或先直接在 JADX 中查看源码。",
    },
    {
      id: "execution-status",
      label: "当前执行状态",
      summary: localizeWorkspaceStatus(executionStatusText),
      detail: `最近一次执行状态为 ${localizeWorkspaceStatus(executionStatusText)}，当前阶段是 ${localizeWorkspaceStage(executionStageText)}。`,
    },
    {
      id: "execution-stage",
      label: "执行阶段",
      summary: localizeWorkspaceStage(executionStageText),
      detail:
        executionStageText && executionStageText !== ""
          ? `当前阶段标记为 ${localizeWorkspaceStage(executionStageText)}。这通常对应执行队列、会话注入、日志落盘等内部阶段。`
          : "当前还没有可用的执行阶段信息。",
    },
    {
      id: "requested-mode",
      label: "最近执行模式",
      summary: localizeWorkspaceExecutionMode(requestedExecutionMode),
      detail: requestedExecutionMode
        ? `最近一次请求执行时使用的是 ${localizeWorkspaceExecutionMode(requestedExecutionMode)} 模式。`
        : "当前还没有记录到最近执行模式。",
    },
    {
      id: "backend",
      label: "实际后端",
      summary: localizeWorkspaceExecutionMode(executedBackendKey),
      detail: executedBackendKey
        ? `后端最终实际路由到 ${localizeWorkspaceExecutionMode(executedBackendKey)}。这个值比“请求模式”更接近真实落地执行路径。`
        : "当前还没有记录到实际执行后端。",
    },
    {
      id: "failure",
      label: "最近失败",
      summary: failureCode ? localizeExecutionFailureCode(failureCode) : "暂无",
      detail: failureCode
        ? `最近一次失败分类是 ${localizeExecutionFailureCode(failureCode)}。${failureMessage ?? "具体原因请查看执行控制台和事件历史。"}`
        : "当前没有记录到最近失败信息。",
    },
  ] as const;
  const expandedWorkspaceMetric =
    workspaceMetricDetails.find((metric) => metric.id === expandedWorkspaceMetricId) ?? null;

  return (
    <section className="page-shell" aria-labelledby="case-workspace-title">
      <header className="workspace-hero">
        <div>
          <p className="eyebrow">Case Workspace</p>
          <h2 id="case-workspace-title">{detail?.title ?? "案件工作台"}</h2>
          <p className="workspace-hero__description">
            {caseId
              ? "围绕当前样本查看静态分析、Hook 计划、执行状态、流量证据和报告导出。"
              : "工作台已准备就绪。选择一个案件后，这里会集中展示静态简报、Hook 计划、执行状态和证据回放。"}
          </p>
          {!isLoadingDetail && detail ? <p className="message-inline">当前案件：{detail.title}</p> : null}
          <div className="button-row" style={{ marginTop: "18px" }}>
            <a className="button-ghost" href="#static-brief-section">
              查看静态简报
            </a>
            <a className="button-ghost" href="#hook-studio-section">
              前往 Hook 工作台
            </a>
            <a className="button-ghost" href="#execution-console-section">
              查看执行控制台
            </a>
            <button
              className="button-secondary"
              type="button"
              onClick={() => {
                void handleOpenInJadx();
              }}
              disabled={!detail?.can_open_in_jadx || isOpeningInJadx}
            >
              {isOpeningInJadx ? "正在打开 JADX..." : "在 JADX 中打开"}
            </button>
          </div>
          {openJadxMessage ? <p className="message-inline">{openJadxMessage}</p> : null}
          {openJadxError ? <p className="message-inline" role="alert">{openJadxError}</p> : null}
          {isLoadingDetail ? <p className="message-inline">正在加载工作区数据...</p> : null}
          {detailError ? <p className="message-inline">{detailError}</p> : null}
        </div>

        <div className="workspace-hero__metrics">
          {workspaceMetricDetails.map((metric) => (
            <button
              key={metric.id}
              type="button"
              className={`app-banner__metric app-banner__metric--interactive${
                expandedWorkspaceMetricId === metric.id ? " app-banner__metric--active" : ""
              }`}
              onClick={() => setExpandedWorkspaceMetricId((current) => (current === metric.id ? null : metric.id))}
              aria-expanded={expandedWorkspaceMetricId === metric.id}
            >
              <span>{metric.label}</span>
              <strong>{metric.summary}</strong>
            </button>
          ))}
        </div>
        <div className="workspace-hero__inspector" aria-live="polite">
          {expandedWorkspaceMetric ? (
            <>
              <strong>{expandedWorkspaceMetric.label}</strong>
              <p>{expandedWorkspaceMetric.detail}</p>
            </>
          ) : (
            <p>点击右侧摘要卡片查看更完整的说明，默认先保持工作台简洁。</p>
          )}
        </div>
      </header>

      {caseId ? (
        <>
          <nav className="workspace-nav" aria-label="工作台分区导航">
            {WORKSPACE_SECTIONS.map((section) => (
              <a
                key={section.id}
                className={`workspace-nav__link${activeSectionId === section.id ? " workspace-nav__link--active" : ""}`}
                href={`#${section.id}`}
                aria-current={activeSectionId === section.id ? "location" : undefined}
              >
                {section.label}
              </a>
            ))}
          </nav>

          <div className="workspace-grid workspace-grid--overview">
            <div className="surface workspace-pane" id="static-brief-section">
              <StaticBriefPanel detail={detail} errorMessage={detailError} isLoading={isLoadingDetail} />
            </div>
            <div className="surface workspace-pane" id="execution-console-section">
              <ExecutionConsolePanel
                cancelDisabled={!caseId || !isExecutionBusy(executionStatusText) || isCancellingExecution}
                environmentError={environmentError}
                environmentSummary={environmentSummary}
                externalContext={executionConsoleExternalContext}
                executionHistory={executionHistory}
                executionPresets={executionPresets}
                executionPreflightDetail={localizedPreflightDetail}
                executionPreflightReady={executionPreflight?.ready ?? null}
                events={events}
                executedBackendKey={executedBackendKey}
                executionStageText={executionStageText}
                failureCode={failureCode}
                failureMessage={failureMessage}
                historyReplayMessage={executionHistoryMessage}
                isLoadingEnvironment={isLoadingEnvironment}
                isLoadingExecutionHistory={isLoadingExecutionHistory}
                isLoadingExecutionPreflight={isLoadingExecutionPreflight}
                isCancelling={isCancellingExecution}
                isStarting={isStartingExecution}
                isSavingRuntimeSettings={isSavingRuntimeSettings}
                onCancel={() => {
                  void handleCancelExecution();
                }}
                onClearExternalContext={() => {
                  setExecutionConsoleExternalContext(null);
                }}
                onExecutionModeChange={setSelectedExecutionMode}
                onInspectHookContext={(event) => {
                  handleInspectHookFromExecutionContext(event, "execution_console");
                }}
                onPickFridaServerBinary={() => {
                  void handlePickFridaServerBinary();
                }}
                onReplayExecutionHistory={(historyId) => {
                  void handleReplayExecutionHistory(historyId);
                }}
                onRuntimeSettingChange={handleRuntimeSettingChange}
                onSaveRuntimeSettings={() => {
                  void handleSaveRuntimeSettings("execution");
                }}
                onStart={() => {
                  void handleStartExecution();
                }}
                requestedExecutionMode={requestedExecutionMode}
                recommendedExecutionMode={recommendedExecutionMode}
                runtimeSettings={runtimeSettings}
                runtimeSettingsError={runtimeSettingsFeedbackTarget === "execution" ? runtimeSettingsError : null}
                runtimeSettingsMessage={runtimeSettingsFeedbackTarget === "execution" ? runtimeSettingsMessage : null}
                selectedExecutionMode={selectedExecutionMode}
                startBlockedReason={startBlockedReason}
                startDisabled={
                  !caseId ||
                  isStartingExecution ||
                  hookPlanItems.length === 0 ||
                  isExecutionBusy(executionStatusText) ||
                  executionPreflight?.ready === false
                }
                statusText={executionStatusText}
                connectedDevices={connectedDevices}
                recommendedDeviceSerial={recommendedDeviceSerial}
                tools={environmentTools}
              />
            </div>
          </div>

          <div className="surface workspace-pane" id="hook-studio-section">
            <HookStudioPanel
              customScripts={customScripts}
              customScriptsError={customScriptsError}
              draftScriptContent={draftScriptContent}
              draftScriptName={draftScriptName}
              externalContext={hookStudioExternalContext}
              hasMethodIndex={Boolean(detail?.has_method_index)}
              hookPlanError={hookPlanError}
              hookPlanItems={hookPlanItems}
              hookStudioError={hookStudioError}
              hookStudioMessage={hookStudioMessage}
              isLoadingHookPlan={isLoadingHookPlan}
              isLoadingMethods={isLoadingMethods}
              isLoadingRecommendations={isLoadingRecommendations}
              isLoadingCustomScript={isLoadingCustomScript}
              isDeletingCustomScript={isDeletingCustomScript}
              isRefreshingMethodIndex={isRefreshingMethodIndex}
              isSavingCustomScript={isSavingCustomScript}
              methodIndexProgress={methodIndexProgress}
              methodIndexStageLabel={methodIndexStageLabel}
              methodScope={methodScope}
              availableMethodScopes={availableMethodScopes}
              methodTotal={methodTotal}
              methods={methods}
              methodIndexMessage={methodIndexMessage}
              methodInsight={methodInsight}
              selectedMethod={selectedMethod}
              onAddCustomScriptToPlan={(scriptId) => {
                void handleAddCustomScriptToPlan(scriptId);
              }}
              onAddMethodToPlan={(method) => {
                void handleAddMethodToPlan(method);
              }}
              onAddRecommendationToPlan={(recommendationId) => {
                void handleAddRecommendationToPlan(recommendationId);
              }}
              onInspectExecutionContext={handleInspectExecutionContext}
              onInspectTrafficContext={handleInspectTrafficContext}
              onClearHookPlan={() => {
                void handleClearHookPlan();
              }}
              onClearExternalContext={() => {
                setHookStudioExternalContext(null);
              }}
              onCreateCustomScriptDraft={handleCreateCustomScriptDraft}
              onDeleteCustomScript={(scriptId) => {
                void handleDeleteCustomScript(scriptId);
              }}
              onDraftScriptContentChange={setDraftScriptContent}
              onDraftScriptNameChange={setDraftScriptName}
              onLoadCustomScript={(scriptId) => {
                void handleLoadCustomScript(scriptId);
              }}
              onMethodQueryChange={setSearchValue}
              onMethodSearch={handleMethodSearch}
              onMethodScopeChange={setMethodScope}
              onRefreshMethodIndex={() => {
                void handleRefreshMethodIndex();
              }}
              onSelectMethod={(method) => {
                setSelectedMethodKey(workspaceMethodKey(method));
              }}
              onMoveHookPlanItem={(itemId, direction) => {
                void handleMoveHookPlanItem(itemId, direction);
              }}
              onRemoveHookPlanItem={(itemId) => {
                void handleRemoveHookPlanItem(itemId);
              }}
              onSaveCustomScript={() => {
                void handleSaveCustomScript();
              }}
              onSetHookPlanItemEnabled={(itemId, enabled) => {
                void handleSetHookPlanItemEnabled(itemId, enabled);
              }}
              recommendations={recommendations}
              recommendationsError={recommendationsError}
              searchError={methodsError}
              searchValue={searchValue}
              selectedCustomScriptId={selectedCustomScriptId}
            />
          </div>

          <div className="workspace-grid workspace-grid--split">
            <div className="surface workspace-pane" id="traffic-evidence-section">
              <TrafficEvidencePanel
                capture={trafficCapture}
                externalContext={trafficEvidenceExternalContext}
                harErrorMessage={trafficError}
                harPath={trafficPath}
                harImportMessage={trafficImportMessage}
                isImporting={isImportingTraffic}
                isSavingRuntimeSettings={isSavingRuntimeSettings}
                isStartingLiveCapture={isStartingLiveTraffic}
                isStoppingLiveCapture={isStoppingLiveTraffic}
                liveArtifactPath={liveTrafficArtifactPath}
                liveRuntimeAvailable={liveCaptureRuntime?.available ?? false}
                liveCertificateDirectoryPath={liveCaptureRuntime?.certificate_directory_path ?? null}
                liveCertificateExists={liveCaptureRuntime?.certificate_exists ?? false}
                liveCertificateHelpText={liveCaptureRuntime?.certificate_help_text ?? null}
                liveCertificatePath={liveCaptureRuntime?.certificate_path ?? null}
                liveCaptureListenHost={runtimeSettings.live_capture_listen_host}
                liveCaptureListenPort={runtimeSettings.live_capture_listen_port}
                liveErrorMessage={liveTrafficError}
                liveInstallUrl={liveCaptureRuntime?.install_url ?? null}
                liveMessage={liveTrafficMessage}
                liveProxyAddressHint={liveCaptureRuntime?.proxy_address_hint ?? null}
                livePreview={liveTrafficPreview}
                liveRuntimeDetail={liveCaptureRuntime?.detail ?? null}
                liveRuntimeHelpText={liveCaptureRuntime?.help_text ?? null}
                liveSetupSteps={liveCaptureRuntime?.setup_steps ?? []}
                liveProxySteps={liveCaptureRuntime?.proxy_steps ?? []}
                liveCertificateSteps={liveCaptureRuntime?.certificate_steps ?? []}
                liveRecommendedActions={liveCaptureRuntime?.recommended_actions ?? []}
                liveSetupStepDetails={liveCaptureRuntime?.setup_step_details ?? []}
                liveProxyStepDetails={liveCaptureRuntime?.proxy_step_details ?? []}
                liveCertificateStepDetails={liveCaptureRuntime?.certificate_step_details ?? []}
                liveNetworkSummary={liveCaptureRuntime?.network_summary ?? null}
                liveSslHookGuidance={liveCaptureRuntime?.ssl_hook_guidance ?? null}
                liveRuntimeListenHost={liveCaptureRuntime?.listen_host ?? runtimeSettings.live_capture_listen_host}
                liveRuntimeListenPort={
                  liveCaptureRuntime?.listen_port ?? Number(runtimeSettings.live_capture_listen_port || 8080)
                }
                liveStatusText={liveTrafficStatusText}
                onOpenPath={(path) => {
                  void handleOpenWorkspacePath(path);
                }}
                onHarPathChange={setTrafficPath}
                onImport={() => {
                  void handleImportTraffic();
                }}
                onAddRecommendationToPlan={(recommendationId) => {
                  void handleAddRecommendationToPlan(recommendationId);
                }}
                onAddTemplateToPlan={(template) => {
                  void handleAddTemplateToPlan(template);
                }}
                onClearExternalContext={() => {
                  setTrafficEvidenceExternalContext(null);
                }}
                onInspectHookContext={handleInspectHookContext}
                onLiveCaptureListenHostChange={(value) => {
                  handleRuntimeSettingChange("live_capture_listen_host", value);
                }}
                onLiveCaptureListenPortChange={(value) => {
                  handleRuntimeSettingChange("live_capture_listen_port", value);
                }}
                onSaveLiveCaptureSettings={() => {
                  void handleSaveRuntimeSettings("traffic");
                }}
                onStartLiveCapture={() => {
                  void handleStartLiveTrafficCapture();
                }}
                onStopLiveCapture={() => {
                  void handleStopLiveTrafficCapture();
                }}
                runtimeSettingsError={runtimeSettingsFeedbackTarget === "traffic" ? runtimeSettingsError : null}
                runtimeSettingsMessage={runtimeSettingsFeedbackTarget === "traffic" ? runtimeSettingsMessage : null}
                startLiveCaptureDisabled={startLiveTrafficDisabled}
                stopLiveCaptureDisabled={stopLiveTrafficDisabled}
                trafficRecommendations={trafficRecommendations}
              />
            </div>

            <div className="surface workspace-pane" id="evidence-center-section">
              <EvidencePanel
                caseId={caseId ?? null}
                events={events}
                executionResponse={executionResponse}
                hookPlan={hookPlanState}
                isOpeningPath={isOpeningWorkspacePath}
                onInspectHookContext={(event) => {
                  handleInspectHookFromExecutionContext(event, "evidence_center");
                }}
                onOpenPath={(path) => {
                  void handleOpenWorkspacePath(path);
                }}
                openPathError={workspacePathError}
                openPathMessage={workspacePathMessage}
                trafficCapture={trafficCapture}
                workspace={workspaceSummary}
              />
            </div>
          </div>

          <div className="surface workspace-pane" id="reports-section">
            <ReportsPanel
              exportError={reportExportError}
              hookPlan={hookPlanState}
              isExporting={isExportingReport}
              isOpeningPath={isOpeningWorkspacePath}
              onExport={() => {
                void handleExportReport();
              }}
              onOpenPath={(path) => {
                void handleOpenWorkspacePath(path);
              }}
              openPathError={workspacePathError}
              openPathMessage={workspacePathMessage}
              report={reportResponse}
              trafficCapture={trafficCapture}
            />
          </div>
        </>
      ) : (
        <div className="empty-workspace">
          <div className="surface">
            <h3>请先进入一个案件</h3>
            <p>当前工作台还没有选中案件。你可以先回到案件队列，导入样本或打开已有案件，再回来继续分析。</p>
          </div>
        </div>
      )}
    </section>
  );
}
