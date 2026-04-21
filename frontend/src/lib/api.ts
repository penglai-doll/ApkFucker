import type {
  CustomScriptContentResponse,
  CustomScriptsResponse,
  ApiHealth,
  CaseListResponse,
  ConnectedDeviceSummary,
  EnvironmentStatus,
  ExecutionCancelResponse,
  ExecutionHistoryResponse,
  ExecutionPreflightResponse,
  HookPlanMoveDirection,
  ImportCaseRequest,
  ImportedCaseResponse,
  ExecutionStartResponse,
  HookPlanResponse,
  HookPlanTemplateSource,
  LiveTrafficCaptureResponse,
  LiveTrafficPreviewResponse,
  LiveCaptureRuntimeStatus,
  OpenJadxResponse,
  OpenPathResponse,
  ReportExportResponse,
  RuntimeSettings,
  SaveCustomScriptRequest,
  SslHookGuidanceStatus,
  StartExecutionOptions,
  StartupSettings,
  TrafficCaptureResponse,
  WorkspaceDetailResponse,
  WorkspaceEventsResponse,
  WorkspaceEvent,
  WorkspaceMethodsResponse,
  WorkspaceRecommendationsResponse,
  WorkspaceSummary,
} from "./types";

type HookPlanSourceApiResponse = {
  source_id: string;
  kind: string;
  method?: WorkspaceMethodsResponse["items"][number] | null;
  script_name?: string | null;
  script_path?: string | null;
  template_id?: string | null;
  template_name?: string | null;
  plugin_id?: string | null;
};

type HookPlanTargetApiResponse = {
  target_id: string;
  class_name: string;
  method_name: string;
  parameter_types: string[];
  return_type: string;
  source_origin: string;
  notes: string;
};

type HookPlanItemApiResponse = {
  item_id: string;
  kind: string;
  inject_order: number;
  enabled: boolean;
  source?: HookPlanSourceApiResponse | null;
  target?: HookPlanTargetApiResponse | null;
  render_context?: Record<string, unknown>;
  plugin_id?: string | null;
};

type HookPlanApiResponse = {
  case_id: string;
  updated_at: string | null;
  selected_hook_sources?: HookPlanSourceApiResponse[];
  items: HookPlanItemApiResponse[];
  execution_count?: number;
  last_execution_run_id?: string | null;
  last_execution_mode?: string | null;
  last_executed_backend_key?: string | null;
  last_execution_status?: string | null;
  last_execution_stage?: string | null;
  last_execution_error_code?: string | null;
  last_execution_error_message?: string | null;
  last_execution_event_count?: number | null;
  last_execution_result_path?: string | null;
  last_execution_db_path?: string | null;
  last_execution_bundle_path?: string | null;
  last_report_path?: string | null;
};

type ReportExportApiResponse = {
  case_id: string;
  report_path: string;
  static_report_path?: string | null;
  last_execution_db_path?: string | null;
  last_execution_bundle_path?: string | null;
};

type WorkspaceTrafficApiResponse = {
  case_id: string;
  capture?: TrafficCaptureResponse | null;
};

type ApiEnv = {
  VITE_API_BASE_URL?: string;
};

type RuntimeLocation = Pick<Location, "protocol" | "host">;

declare global {
  interface Window {
    __APKHACKER_API_BASE__?: string;
    __TAURI__?: unknown;
    __TAURI_INTERNALS__?: unknown;
  }
}

const DEFAULT_PACKAGED_API_BASE_URL = "http://127.0.0.1:8765";

function normalizeBaseUrl(value: string): string {
  return value.trim().replace(/\/$/, "");
}

export function isTauriRuntime(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  const location = window.location;
  const host = location.host.toLowerCase();
  return Boolean(window.__TAURI__ || window.__TAURI_INTERNALS__) || host === "tauri.localhost" || location.protocol === "tauri:";
}

export function resolveApiBaseUrl(options: {
  configuredBaseUrl?: string;
  runtimeBaseUrl?: string;
  location?: RuntimeLocation | null;
  tauriRuntime?: boolean;
} = {}): string {
  const configuredBaseUrl =
    options.configuredBaseUrl ??
    (import.meta as ImportMeta & { env?: ApiEnv }).env?.VITE_API_BASE_URL ??
    "";
  const runtimeBaseUrl =
    options.runtimeBaseUrl ?? (typeof window !== "undefined" ? window.__APKHACKER_API_BASE__ ?? "" : "");
  const normalizedConfiguredBaseUrl = normalizeBaseUrl(configuredBaseUrl);
  if (normalizedConfiguredBaseUrl) {
    return normalizedConfiguredBaseUrl;
  }

  const normalizedRuntimeBaseUrl = normalizeBaseUrl(runtimeBaseUrl);
  if (normalizedRuntimeBaseUrl) {
    return normalizedRuntimeBaseUrl;
  }

  const location = options.location ?? (typeof window !== "undefined" ? window.location : null);
  const tauriRuntime = options.tauriRuntime ?? isTauriRuntime();
  if (tauriRuntime || (location && !/^https?:$/.test(location.protocol))) {
    return DEFAULT_PACKAGED_API_BASE_URL;
  }

  return "";
}

const apiBaseUrl = resolveApiBaseUrl();

function apiUrl(path: string): string {
  return apiBaseUrl ? `${apiBaseUrl}${path}` : path;
}

async function parseJsonResponse<T>(response: Response, errorMessage: string): Promise<T> {
  if (!response.ok) {
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail.trim().length > 0) {
        throw new Error(`${errorMessage}：${payload.detail}`);
      }
    } catch (error) {
      if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
        throw error;
      }
    }
    throw new Error(errorMessage);
  }
  return (await response.json()) as T;
}

function asNullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asTruthyBoolean(value: unknown): boolean {
  return value === true;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0);
}

function asRenderedScript(renderContext: Record<string, unknown> | undefined): string {
  const renderedScript = renderContext?.rendered_script;
  return typeof renderedScript === "string" ? renderedScript : "";
}

const CONNECTED_DEVICE_KEYS = [
  "connected_devices",
  "connectedDevices",
  "device_options",
  "deviceOptions",
  "devices",
  "device_list",
  "deviceList",
  "available_devices",
  "availableDevices",
] as const;

function toConnectedDeviceSummary(value: unknown): ConnectedDeviceSummary | null {
  if (typeof value === "string") {
    const serial = value.trim();
    if (!serial) {
      return null;
    }
    return {
      serial,
      label: serial,
      status: null,
      detail: null,
      model: null,
      transport: null,
      recommended: false,
    };
  }

  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const serial =
    asNullableString(record.serial) ??
    asNullableString(record.device_serial) ??
    asNullableString(record.id) ??
    asNullableString(record.value);
  if (!serial) {
    return null;
  }

  const label =
    asNullableString(record.label) ??
    asNullableString(record.name) ??
    asNullableString(record.title) ??
    asNullableString(record.device_name) ??
    serial;

  return {
    serial,
    label,
    status: asNullableString(record.status) ?? asNullableString(record.state) ?? asNullableString(record.device_status),
    detail: asNullableString(record.detail) ?? asNullableString(record.message),
    model: asNullableString(record.model) ?? asNullableString(record.device_model),
    transport:
      asNullableString(record.transport) ??
      asNullableString(record.connection_type) ??
      asNullableString(record.connection),
    recommended:
      asTruthyBoolean(record.recommended) ||
      asTruthyBoolean(record.is_recommended) ||
      asTruthyBoolean(record.selected) ||
      asTruthyBoolean(record.is_selected),
  };
}

function normalizeConnectedDeviceEntries(value: unknown): ConnectedDeviceSummary[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const normalized: ConnectedDeviceSummary[] = [];
  const seen = new Set<string>();
  for (const entry of value) {
    const device = toConnectedDeviceSummary(entry);
    if (!device || seen.has(device.serial)) {
      continue;
    }
    seen.add(device.serial);
    normalized.push(device);
  }
  return normalized;
}

export function normalizeConnectedDevices(environment: EnvironmentStatus): ConnectedDeviceSummary[] {
  const payload = environment as EnvironmentStatus & Record<string, unknown>;
  for (const key of CONNECTED_DEVICE_KEYS) {
    const devices = normalizeConnectedDeviceEntries(payload[key]);
    if (devices.length > 0) {
      return devices;
    }
  }
  return [];
}

export function resolveRecommendedDeviceSerial(
  environment: EnvironmentStatus,
  connectedDevices: ConnectedDeviceSummary[] = normalizeConnectedDevices(environment),
): string | null {
  const payload = environment as EnvironmentStatus & Record<string, unknown>;
  const explicitRecommended =
    asNullableString(payload.recommended_device_serial) ?? asNullableString(payload.recommendedDeviceSerial);
  if (explicitRecommended) {
    return explicitRecommended;
  }

  const recommendedDevice = connectedDevices.find((device) => device.recommended);
  if (recommendedDevice) {
    return recommendedDevice.serial;
  }

  return connectedDevices[0]?.serial ?? null;
}

export function resolvePreferredDeviceSerial(
  runtimeSettings: Pick<RuntimeSettings, "device_serial">,
  connectedDevices: ConnectedDeviceSummary[],
  recommendedDeviceSerial: string | null,
): string {
  const manualSerial = runtimeSettings.device_serial.trim();
  if (manualSerial) {
    return manualSerial;
  }
  if (recommendedDeviceSerial) {
    return recommendedDeviceSerial;
  }
  return connectedDevices[0]?.serial ?? "";
}

function mapHookPlanResponse(payload: HookPlanApiResponse): HookPlanResponse {
  const sources = payload.selected_hook_sources ?? [];
  return {
    case_id: payload.case_id,
    updated_at: payload.updated_at,
    items: payload.items.map((item, index) => {
      const source = item.source ?? sources[index];
      const method =
        source?.method ??
        (item.target
          ? {
              class_name: item.target.class_name,
              method_name: item.target.method_name,
              parameter_types: item.target.parameter_types,
              return_type: item.target.return_type,
              is_constructor: false,
              overload_count: 1,
              source_path: "",
              line_hint: null,
              tags: [],
              evidence: item.target.notes ? [item.target.notes] : [],
            }
          : null);
      return {
        item_id: item.item_id,
        kind: item.kind,
        inject_order: item.inject_order,
        enabled: item.enabled,
        plugin_id: asNullableString(item.plugin_id),
        rendered_script: asRenderedScript(item.render_context),
        method,
        template_name:
          asNullableString(source?.template_name) ?? asNullableString(item.render_context?.template_name),
        script_name:
          asNullableString(source?.script_name) ?? asNullableString(item.render_context?.script_name),
        script_path:
          asNullableString(source?.script_path) ?? asNullableString(item.render_context?.script_path),
      };
    }),
    execution_count: payload.execution_count,
    last_execution_run_id: payload.last_execution_run_id,
    last_execution_mode: payload.last_execution_mode,
    last_executed_backend_key: payload.last_executed_backend_key,
    last_execution_status: payload.last_execution_status,
    last_execution_stage: payload.last_execution_stage,
    last_execution_error_code: payload.last_execution_error_code,
    last_execution_error_message: payload.last_execution_error_message,
    last_execution_event_count: payload.last_execution_event_count,
    last_execution_result_path: payload.last_execution_result_path,
    last_execution_db_path: payload.last_execution_db_path,
    last_execution_bundle_path: payload.last_execution_bundle_path,
    last_report_path: payload.last_report_path,
  };
}

function normalizeHookPlanTemplateSource(value: unknown): HookPlanTemplateSource | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const templateId = asNullableString(record.template_id);
  const templateName = asNullableString(record.template_name);
  const pluginId = asNullableString(record.plugin_id);
  if (!templateId || !templateName || !pluginId) {
    return null;
  }

  return {
    source_id:
      asNullableString(record.source_id) ?? `template:${pluginId}:${templateId}`,
    template_id: templateId,
    template_name: templateName,
    plugin_id: pluginId,
    label: asNullableString(record.label) ?? templateName,
  };
}

function normalizeSslHookGuidance(value: unknown): SslHookGuidanceStatus | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const suggestedTemplateEntries = Array.isArray(record.suggested_template_entries)
    ? record.suggested_template_entries
        .map((entry) => normalizeHookPlanTemplateSource(entry))
        .filter((entry): entry is HookPlanTemplateSource => entry !== null)
    : [];

  return {
    recommended: asTruthyBoolean(record.recommended),
    summary: asNullableString(record.summary) ?? "",
    reason: asNullableString(record.reason) ?? "",
    suggested_templates: asStringArray(record.suggested_templates),
    suggested_template_entries: suggestedTemplateEntries,
    suggested_terms: asStringArray(record.suggested_terms),
  };
}

function mapEnvironmentStatus(payload: EnvironmentStatus): EnvironmentStatus {
  const liveCaptureRecord = asRecord((payload as EnvironmentStatus & Record<string, unknown>).live_capture);
  if (!liveCaptureRecord) {
    return payload;
  }

  return {
    ...payload,
    live_capture: {
      ...(payload.live_capture as LiveCaptureRuntimeStatus),
      ssl_hook_guidance: normalizeSslHookGuidance(liveCaptureRecord.ssl_hook_guidance),
    },
  };
}

export async function listCases(): Promise<CaseListResponse> {
  const response = await fetch(apiUrl("/api/cases"));
  return parseJsonResponse<CaseListResponse>(response, "加载案件列表失败");
}

export async function importCase(payload: ImportCaseRequest): Promise<ImportedCaseResponse> {
  const response = await fetch(apiUrl("/api/cases/import"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse<ImportedCaseResponse>(response, "导入案件失败");
}

export async function getStartupSettings(): Promise<StartupSettings> {
  const response = await fetch(apiUrl("/api/settings/startup"));
  return parseJsonResponse<StartupSettings>(response, "加载启动配置失败");
}

export async function getRuntimeSettings(): Promise<RuntimeSettings> {
  const response = await fetch(apiUrl("/api/settings/runtime"));
  return parseJsonResponse<RuntimeSettings>(response, "加载运行参数失败");
}

export async function saveRuntimeSettings(payload: RuntimeSettings): Promise<RuntimeSettings> {
  const response = await fetch(apiUrl("/api/settings/runtime"), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse<RuntimeSettings>(response, "保存运行参数失败");
}

export async function getApiHealth(): Promise<ApiHealth> {
  const response = await fetch(apiUrl("/api/settings/health"));
  return parseJsonResponse<ApiHealth>(response, "本地后端健康检查失败");
}

export async function getEnvironmentStatus(): Promise<EnvironmentStatus> {
  const response = await fetch(apiUrl("/api/settings/environment"));
  return mapEnvironmentStatus(await parseJsonResponse<EnvironmentStatus>(response, "执行环境检查失败"));
}

export async function getWorkspace(caseId: string): Promise<WorkspaceSummary> {
  const response = await fetch(apiUrl(`/api/cases/${caseId}/workspace`));
  return parseJsonResponse<WorkspaceSummary>(response, "加载案件工作台失败");
}

export async function getWorkspaceDetail(
  caseId: string,
  options: { refresh?: boolean; timeoutMs?: number } = {},
): Promise<WorkspaceDetailResponse> {
  const searchParams = new URLSearchParams();
  if (options.refresh) {
    searchParams.set("refresh", "true");
  }
  const suffix = searchParams.size > 0 ? `?${searchParams.toString()}` : "";
  const controller = options.timeoutMs ? new AbortController() : null;
  const timeoutId =
    controller && options.timeoutMs
      ? window.setTimeout(() => {
          controller.abort();
        }, options.timeoutMs)
      : null;
  try {
    const url = apiUrl(`/api/cases/${encodeURIComponent(caseId)}/workspace/detail${suffix}`);
    const response = controller ? await fetch(url, { signal: controller.signal }) : await fetch(url);
    return parseJsonResponse<WorkspaceDetailResponse>(response, "加载工作区简报失败");
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  }
}

export async function getWorkspaceMethods(
  caseId: string,
  options: { query?: string; limit?: number; scope?: "first_party" | "related_candidates" | "all" } = {},
): Promise<WorkspaceMethodsResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("query", options.query ?? "");
  searchParams.set("limit", String(options.limit ?? 12));
  searchParams.set("scope", options.scope ?? "first_party");

  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/workspace/methods?${searchParams.toString()}`),
  );
  return parseJsonResponse<WorkspaceMethodsResponse>(response, "加载方法索引失败");
}

export async function getWorkspaceEvents(
  caseId: string,
  options: { limit?: number } = {},
): Promise<WorkspaceEvent[]> {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(options.limit ?? 20));
  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/workspace/events?${searchParams.toString()}`),
  );
  const payload = await parseJsonResponse<WorkspaceEventsResponse>(response, "加载执行事件失败");
  return payload.items;
}

export async function getWorkspaceRecommendations(
  caseId: string,
  options: { limit?: number } = {},
): Promise<WorkspaceRecommendationsResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(options.limit ?? 6));

  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/workspace/recommendations?${searchParams.toString()}`),
  );
  return parseJsonResponse<WorkspaceRecommendationsResponse>(response, "加载离线推荐失败");
}

export async function getHookPlan(caseId: string): Promise<HookPlanResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan`));
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "加载 Hook 计划失败"));
}

export async function addMethodToHookPlan(
  caseId: string,
  method: WorkspaceMethodsResponse["items"][number],
): Promise<HookPlanResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan/methods`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(method),
  });
  return mapHookPlanResponse(
    await parseJsonResponse<HookPlanApiResponse>(response, "加入方法 Hook 计划失败"),
  );
}

export async function addRecommendationToHookPlan(
  caseId: string,
  recommendationId: string,
): Promise<HookPlanResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan/recommendations`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ recommendation_id: recommendationId }),
  });
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "接受推荐失败"));
}

export async function addTemplateToHookPlan(
  caseId: string,
  template: {
    template_id: string;
    template_name: string;
    plugin_id: string;
  },
): Promise<HookPlanResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan/templates`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(template),
  });
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "加入模板 Hook 计划失败"));
}

export async function addCustomScriptToHookPlan(caseId: string, scriptId: string): Promise<HookPlanResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan/custom-scripts`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ script_id: scriptId }),
  });
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "加入自定义脚本失败"));
}

export async function clearHookPlan(caseId: string): Promise<HookPlanResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan`), {
    method: "DELETE",
  });
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "清空 Hook 计划失败"));
}

export async function removeHookPlanItem(caseId: string, itemId: string): Promise<HookPlanResponse> {
  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan/items/${encodeURIComponent(itemId)}`),
    {
      method: "DELETE",
    },
  );
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "移除 Hook 计划项失败"));
}

export async function setHookPlanItemEnabled(
  caseId: string,
  itemId: string,
  enabled: boolean,
): Promise<HookPlanResponse> {
  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan/items/${encodeURIComponent(itemId)}`),
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ enabled }),
    },
  );
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "更新 Hook 计划项状态失败"));
}

export async function moveHookPlanItem(
  caseId: string,
  itemId: string,
  direction: HookPlanMoveDirection,
): Promise<HookPlanResponse> {
  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/hook-plan/items/${encodeURIComponent(itemId)}/move`),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ direction }),
    },
  );
  return mapHookPlanResponse(await parseJsonResponse<HookPlanApiResponse>(response, "调整 Hook 计划顺序失败"));
}

export async function listWorkspaceCustomScripts(caseId: string): Promise<CustomScriptsResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/custom-scripts`));
  return parseJsonResponse<CustomScriptsResponse>(response, "加载自定义脚本失败");
}

export async function getWorkspaceCustomScript(
  caseId: string,
  scriptId: string,
): Promise<CustomScriptContentResponse> {
  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/custom-scripts/${encodeURIComponent(scriptId)}`),
  );
  return parseJsonResponse<CustomScriptContentResponse>(response, "加载自定义脚本内容失败");
}

export async function saveWorkspaceCustomScript(
  caseId: string,
  payload: SaveCustomScriptRequest,
): Promise<CustomScriptsResponse["items"][number]> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/custom-scripts`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse<CustomScriptsResponse["items"][number]>(response, "保存自定义脚本失败");
}

export async function updateWorkspaceCustomScript(
  caseId: string,
  scriptId: string,
  payload: SaveCustomScriptRequest,
): Promise<CustomScriptsResponse["items"][number]> {
  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/custom-scripts/${encodeURIComponent(scriptId)}`),
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
  return parseJsonResponse<CustomScriptsResponse["items"][number]>(response, "更新自定义脚本失败");
}

export async function deleteWorkspaceCustomScript(caseId: string, scriptId: string): Promise<void> {
  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/custom-scripts/${encodeURIComponent(scriptId)}`),
    {
      method: "DELETE",
    },
  );
  if (!response.ok) {
    await parseJsonResponse(response, "删除自定义脚本失败");
  }
}

export async function openWorkspaceInJadx(caseId: string): Promise<OpenJadxResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/actions/open-jadx`), {
    method: "POST",
  });
  return parseJsonResponse<OpenJadxResponse>(response, "打开 JADX 失败");
}

export async function openWorkspacePath(path: string): Promise<OpenPathResponse> {
  const response = await fetch(apiUrl("/api/settings/open-path"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ path }),
  });
  return parseJsonResponse<OpenPathResponse>(response, "打开本地路径失败");
}

export async function getWorkspaceTraffic(caseId: string): Promise<TrafficCaptureResponse | null> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/traffic`));
  const payload = await parseJsonResponse<WorkspaceTrafficApiResponse>(response, "加载流量证据失败");
  return payload.capture ?? null;
}

export async function importWorkspaceTraffic(
  caseId: string,
  payload: { harPath: string },
): Promise<TrafficCaptureResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/traffic/import`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      har_path: payload.harPath,
    }),
  });
  return parseJsonResponse<TrafficCaptureResponse>(response, "导入 HAR 失败");
}

export async function getLiveTrafficCapture(caseId: string): Promise<LiveTrafficCaptureResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/traffic/live`));
  return parseJsonResponse<LiveTrafficCaptureResponse>(response, "加载实时抓包状态失败");
}

export async function getLiveTrafficPreview(caseId: string): Promise<LiveTrafficPreviewResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/traffic/live/preview`));
  return parseJsonResponse<LiveTrafficPreviewResponse>(response, "加载实时抓包预览失败");
}

export async function startLiveTrafficCapture(caseId: string): Promise<LiveTrafficCaptureResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/traffic/live/start`), {
    method: "POST",
  });
  return parseJsonResponse<LiveTrafficCaptureResponse>(response, "启动实时抓包失败");
}

export async function stopLiveTrafficCapture(caseId: string): Promise<LiveTrafficCaptureResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/traffic/live/stop`), {
    method: "POST",
  });
  return parseJsonResponse<LiveTrafficCaptureResponse>(response, "停止实时抓包失败");
}

export async function startExecution(
  caseId: string,
  options: StartExecutionOptions = {},
): Promise<ExecutionStartResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/executions`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      execution_mode: options.executionMode ?? null,
      device_serial: options.deviceSerial ?? "",
      frida_server_binary_path: options.fridaServerBinaryPath ?? "",
      frida_server_remote_path: options.fridaServerRemotePath ?? "",
      frida_session_seconds: options.fridaSessionSeconds ?? "",
    }),
  });
  return parseJsonResponse<ExecutionStartResponse>(response, "启动执行失败");
}

export async function cancelExecution(caseId: string): Promise<ExecutionCancelResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/executions/cancel`), {
    method: "POST",
  });
  return parseJsonResponse<ExecutionCancelResponse>(response, "取消执行失败");
}

export async function getExecutionPreflight(
  caseId: string,
  options: StartExecutionOptions = {},
): Promise<ExecutionPreflightResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/executions/preflight`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      execution_mode: options.executionMode ?? null,
      device_serial: options.deviceSerial ?? "",
      frida_server_binary_path: options.fridaServerBinaryPath ?? "",
      frida_server_remote_path: options.fridaServerRemotePath ?? "",
      frida_session_seconds: options.fridaSessionSeconds ?? "",
    }),
  });
  return parseJsonResponse<ExecutionPreflightResponse>(response, "执行前检查失败");
}

export async function getExecutionHistory(caseId: string): Promise<ExecutionHistoryResponse["items"]> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/executions/history`));
  const payload = await parseJsonResponse<ExecutionHistoryResponse>(response, "加载执行历史失败");
  return payload.items;
}

export async function getExecutionHistoryEvents(
  caseId: string,
  historyId: string,
  options: { limit?: number } = {},
): Promise<WorkspaceEvent[]> {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(options.limit ?? 20));
  const response = await fetch(
    apiUrl(
      `/api/cases/${encodeURIComponent(caseId)}/executions/history/${encodeURIComponent(historyId)}/events?${searchParams.toString()}`,
    ),
  );
  const payload = await parseJsonResponse<WorkspaceEventsResponse>(response, "回放执行历史失败");
  return payload.items;
}

export async function exportReport(caseId: string): Promise<ReportExportResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/reports/export`), {
    method: "POST",
  });
  const payload = await parseJsonResponse<ReportExportApiResponse>(response, "导出报告失败");
  return {
    case_id: payload.case_id,
    report_path: payload.report_path,
    static_report_path: payload.static_report_path ?? null,
    last_execution_db_path: payload.last_execution_db_path ?? null,
    last_execution_bundle_path: payload.last_execution_bundle_path ?? null,
  };
}
