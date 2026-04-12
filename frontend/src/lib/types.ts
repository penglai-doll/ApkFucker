export type AppMode = "queue" | "workspace";

export type CaseQueueItem = {
  case_id: string;
  title: string;
  workspace_root: string;
};

export type CaseListResponse = {
  items: CaseQueueItem[];
};

export type WorkspaceSummary = {
  case_id: string;
  title: string;
  view: string;
};

export type StartupSettings = {
  launch_view: "queue" | "workspace" | string;
  last_workspace_root: string | null;
  case_id: string | null;
  title: string | null;
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
