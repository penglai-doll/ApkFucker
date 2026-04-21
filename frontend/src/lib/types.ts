export type AppMode = "queue" | "workspace";

export type CaseQueueItem = {
  case_id: string;
  title: string;
  workspace_root: string;
};

export type CaseListResponse = {
  items: CaseQueueItem[];
};

export type ImportCaseRequest = {
  sample_path: string;
  workspace_root: string;
  title?: string | null;
};

export type ImportedCaseResponse = {
  case_id: string;
  title: string;
  workspace_root: string;
  sample_path: string;
};

export type WorkspaceSummary = {
  case_id: string;
  title: string;
  view: string;
};

export type CustomScriptSummary = {
  script_id: string;
  name: string;
  script_path: string;
};

export type CustomScriptContentResponse = {
  script_id: string;
  name: string;
  script_path: string;
  content: string;
};

export type WorkspaceDetailResponse = {
  case_id: string;
  title: string;
  package_name: string;
  technical_tags: string[];
  dangerous_permissions: string[];
  callback_endpoints: string[];
  callback_clues: string[];
  crypto_signals: string[];
  packer_hints: string[];
  limitations: string[];
  custom_scripts: CustomScriptSummary[];
  can_open_in_jadx: boolean;
  has_method_index: boolean;
  method_count: number;
  runtime: WorkspaceRuntimeSummary;
};

export type WorkspaceMethodSummary = {
  class_name: string;
  method_name: string;
  parameter_types: string[];
  return_type: string;
  is_constructor: boolean;
  overload_count: number;
  source_path: string;
  line_hint: number | null;
  declaration?: string | null;
  source_preview?: string | null;
  tags: string[];
  evidence: string[];
};

export type WorkspaceMethodScope = "first_party" | "related_candidates" | "all";

export type WorkspaceMethodsResponse = {
  items: WorkspaceMethodSummary[];
  total: number;
  scope?: WorkspaceMethodScope;
  available_scopes?: WorkspaceMethodScope[];
};

export type HookRecommendationSummary = {
  recommendation_id: string;
  kind: string;
  title: string;
  reason: string;
  score: number;
  matched_terms: string[];
  method: WorkspaceMethodSummary | null;
  template_id: string | null;
  template_name: string | null;
  plugin_id: string | null;
};

export type WorkspaceRecommendationsResponse = {
  items: HookRecommendationSummary[];
};

export type HookPlanMoveDirection = "up" | "down";

export type HookPlanTemplateSource = {
  source_id: string;
  template_id: string;
  template_name: string;
  plugin_id: string;
  label: string;
};

export type HookStudioExternalContext = {
  source: "traffic_evidence" | "execution_console" | "evidence_center";
  title: string;
  summary: string;
  keywords: string[];
  suggested_query: string;
  suggested_scope: WorkspaceMethodScope;
  recommendation_id: string | null;
  recommendation_title: string | null;
  focused_method:
    | {
        class_name: string;
        method_name: string;
      }
    | null;
};

export type TrafficEvidenceExternalContext = {
  source: "hook_studio";
  title: string;
  summary: string;
  recommendation_id: string | null;
  recommendation_title: string | null;
};

export type ExecutionConsoleExternalContext = {
  source: "hook_studio";
  title: string;
  summary: string;
  class_name: string;
  method_name: string;
};

export type HookMethodExecutionInsight = {
  related_event_count: number;
  latest_event_type: string | null;
  latest_status: string | null;
  latest_message: string | null;
  latest_timestamp: string | null;
  latest_arguments: string[];
  latest_return_value: string | null;
  latest_stack_preview: string | null;
  failure_code: string | null;
  failure_message: string | null;
};

export type HookMethodTrafficInsight = {
  source_label: string | null;
  flow_count: number;
  suspicious_count: number;
  https_flow_count: number | null;
  matched_indicator_count: number | null;
  preview_count: number | null;
  top_host_summary: string | null;
  suspicious_host_summary: string | null;
  matched_flow_label: string | null;
  matched_flow_reason: string | null;
  guidance_summary: string | null;
};

export type HookMethodInsightSummary = {
  execution: HookMethodExecutionInsight | null;
  traffic: HookMethodTrafficInsight | null;
};

export type HookPlanItemSummary = {
  item_id: string;
  kind: string;
  inject_order: number;
  enabled: boolean;
  plugin_id: string | null;
  rendered_script: string;
  method: WorkspaceMethodSummary | null;
  template_name: string | null;
  script_name: string | null;
  script_path: string | null;
};

export type WorkspaceRuntimeSummary = {
  execution_count: number;
  last_execution_run_id: string | null;
  last_execution_mode: string | null;
  last_executed_backend_key: string | null;
  last_execution_status: string | null;
  last_execution_stage: string | null;
  last_execution_error_code: string | null;
  last_execution_error_message: string | null;
  last_execution_event_count: number | null;
  last_execution_result_path: string | null;
  last_execution_db_path: string | null;
  last_execution_bundle_path: string | null;
  last_report_path: string | null;
  traffic_capture_source_path: string | null;
  traffic_capture_summary_path: string | null;
  traffic_capture_flow_count: number | null;
  traffic_capture_suspicious_count: number | null;
  live_traffic_status: string | null;
  live_traffic_artifact_path: string | null;
  live_traffic_message: string | null;
};

export type HookPlanResponse = {
  case_id: string;
  updated_at: string | null;
  items: HookPlanItemSummary[];
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

export type TrafficFlowSummary = {
  flow_id: string;
  method: string;
  url: string;
  status_code: number | null;
  mime_type: string | null;
  request_preview: string;
  response_preview: string;
  matched_indicators: string[];
  suspicious: boolean;
};

export type TrafficCaptureProvenance = {
  kind: string;
  label: string;
};

export type TrafficHostSummary = {
  host: string;
  flow_count: number;
  suspicious_count: number;
  https_flow_count: number;
};

export type TrafficCaptureSummary = {
  https_flow_count: number;
  matched_indicator_count: number;
  top_hosts: TrafficHostSummary[];
  suspicious_hosts: TrafficHostSummary[];
};

export type TrafficCaptureResponse = {
  case_id: string;
  source_path: string;
  provenance: TrafficCaptureProvenance;
  flow_count: number;
  suspicious_count: number;
  https_flow_count?: number;
  matched_indicator_count?: number;
  top_hosts?: TrafficHostSummary[];
  suspicious_hosts?: TrafficHostSummary[];
  summary?: TrafficCaptureSummary;
  flows: TrafficFlowSummary[];
};

export type LiveTrafficCaptureResponse = {
  case_id: string;
  status: string;
  artifact_path: string | null;
  message: string | null;
};

export type LiveTrafficPreviewItem = {
  flow_id: string;
  timestamp: string | null;
  method: string;
  url: string;
  status_code: number | null;
  matched_indicators: string[];
  suspicious: boolean;
};

export type LiveTrafficPreviewResponse = {
  case_id: string;
  status: string;
  preview_path: string | null;
  truncated: boolean;
  items: LiveTrafficPreviewItem[];
};

export type SaveCustomScriptRequest = {
  name: string;
  content: string;
};

export type CustomScriptsResponse = {
  items: CustomScriptSummary[];
};

export type OpenJadxResponse = {
  case_id: string;
  status: string;
};

export type OpenPathResponse = {
  path: string;
  status: string;
};

export type StartupSettings = {
  launch_view: "queue" | "workspace" | string;
  last_workspace_root: string | null;
  case_id: string | null;
  title: string | null;
};

export type RuntimeSettings = {
  execution_mode: string;
  device_serial: string;
  frida_server_binary_path: string;
  frida_server_remote_path: string;
  frida_session_seconds: string;
  live_capture_listen_host: string;
  live_capture_listen_port: string;
};

export type ApiHealth = {
  status: string;
  service: string;
  default_workspace_root: string;
};

export type EnvironmentToolStatus = {
  name: string;
  label: string;
  available: boolean;
  path: string | null;
};

export type EnvironmentConnectedDevice = {
  serial?: string | null;
  device_serial?: string | null;
  label?: string | null;
  name?: string | null;
  status?: string | null;
  detail?: string | null;
  model?: string | null;
  transport?: string | null;
  recommended?: boolean | null;
  is_recommended?: boolean | null;
  selected?: boolean | null;
  is_selected?: boolean | null;
};

export type ConnectedDeviceSummary = {
  serial: string;
  label: string;
  status: string | null;
  detail: string | null;
  model: string | null;
  transport: string | null;
  recommended: boolean;
};

export type EnvironmentPresetStatus = {
  key: string;
  label: string;
  available: boolean;
  detail: string;
};

export type GuidanceStepStatus = {
  key: string;
  title: string;
  detail: string;
  emphasis: string;
};

export type LiveCaptureNetworkSummary = {
  supports_https_intercept: boolean;
  supports_packet_capture: boolean;
  supports_ssl_hooking: boolean;
  proxy_ready: boolean;
  certificate_ready: boolean;
  https_capture_ready: boolean;
};

export type SslHookGuidanceStatus = {
  recommended: boolean;
  summary: string;
  reason: string;
  suggested_templates: string[];
  suggested_template_entries?: HookPlanTemplateSource[];
  suggested_terms: string[];
};

export type LiveCaptureRuntimeStatus = {
  available: boolean;
  source: string;
  detail: string;
  listen_host: string;
  listen_port: number;
  help_text: string | null;
  proxy_address_hint: string | null;
  install_url: string | null;
  certificate_path: string | null;
  certificate_directory_path: string | null;
  certificate_exists: boolean;
  certificate_help_text: string | null;
  setup_steps: string[];
  proxy_steps: string[];
  certificate_steps: string[];
  recommended_actions: string[];
  setup_step_details?: GuidanceStepStatus[];
  proxy_step_details?: GuidanceStepStatus[];
  certificate_step_details?: GuidanceStepStatus[];
  network_summary?: LiveCaptureNetworkSummary | null;
  ssl_hook_guidance?: SslHookGuidanceStatus | null;
};

export type EnvironmentStatus = {
  summary: string;
  recommended_execution_mode: string | null;
  tools: EnvironmentToolStatus[];
  live_capture: LiveCaptureRuntimeStatus;
  execution_presets: EnvironmentPresetStatus[];
  connected_devices?: Array<EnvironmentConnectedDevice | string>;
  recommended_device_serial?: string | null;
};

export type ExecutionStartResponse = {
  case_id: string;
  status: string;
  execution_mode: string | null;
  executed_backend_key?: string | null;
  stage?: string | null;
  run_id?: string | null;
  event_count?: number | null;
  db_path?: string | null;
  bundle_path?: string | null;
  executed_backend_label?: string | null;
  error_code?: string | null;
  message?: string | null;
};

export type StartExecutionOptions = {
  executionMode?: string | null;
  deviceSerial?: string;
  fridaServerBinaryPath?: string;
  fridaServerRemotePath?: string;
  fridaSessionSeconds?: string;
};

export type ExecutionCancelResponse = {
  case_id: string;
  status: string;
  execution_mode: string | null;
  executed_backend_key?: string | null;
  stage?: string | null;
};

export type ExecutionPreflightResponse = {
  case_id: string;
  ready: boolean;
  execution_mode: string;
  executed_backend_key?: string | null;
  executed_backend_label?: string | null;
  detail: string;
};

export type ExecutionHistoryEntry = {
  history_id: string;
  run_id: string | null;
  execution_mode: string | null;
  executed_backend_key: string | null;
  status: string | null;
  stage: string | null;
  error_code: string | null;
  error_message: string | null;
  event_count: number | null;
  db_path: string | null;
  bundle_path: string | null;
  started_at: string;
  updated_at: string;
};

export type ExecutionHistoryResponse = {
  case_id: string;
  items: ExecutionHistoryEntry[];
};

export type ReportExportResponse = {
  case_id: string;
  report_path: string;
  static_report_path?: string | null;
  last_execution_db_path?: string | null;
  last_execution_bundle_path?: string | null;
};

export type WorkspaceEvent = {
  type: string;
  case_id?: string;
  status?: string;
  artifact_path?: string | null;
  stage?: string;
  run_id?: string;
  execution_mode?: string;
  executed_backend_key?: string;
  event_count?: number;
  db_path?: string;
  bundle_path?: string;
  executed_backend_label?: string;
  error_code?: string | null;
  message?: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
};

export type WorkspaceEventsResponse = {
  case_id: string;
  items: WorkspaceEvent[];
};
