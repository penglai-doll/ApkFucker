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
  tags: string[];
  evidence: string[];
};

export type WorkspaceMethodsResponse = {
  items: WorkspaceMethodSummary[];
  total: number;
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

export type OpenJadxResponse = {
  case_id: string;
  status: string;
};

export type StartupSettings = {
  launch_view: "queue" | "workspace" | string;
  last_workspace_root: string | null;
  case_id: string | null;
  title: string | null;
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

export type EnvironmentPresetStatus = {
  key: string;
  label: string;
  available: boolean;
  detail: string;
};

export type EnvironmentStatus = {
  summary: string;
  recommended_execution_mode: string | null;
  tools: EnvironmentToolStatus[];
  execution_presets: EnvironmentPresetStatus[];
};

export type ExecutionStartResponse = {
  case_id: string;
  status: string;
};

export type ReportExportResponse = {
  case_id: string;
  report_path: string;
};

export type WorkspaceEvent = {
  type: string;
  case_id?: string;
  status?: string;
  run_id?: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
};
