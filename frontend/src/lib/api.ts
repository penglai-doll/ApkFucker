import type {
  CaseListResponse,
  ImportCaseRequest,
  ImportedCaseResponse,
  ExecutionStartResponse,
  OpenJadxResponse,
  ReportExportResponse,
  StartupSettings,
  WorkspaceDetailResponse,
  WorkspaceMethodsResponse,
  WorkspaceRecommendationsResponse,
  WorkspaceSummary,
} from "./types";

type ApiEnv = {
  VITE_API_BASE_URL?: string;
};

const apiBaseUrl =
  ((import.meta as ImportMeta & { env?: ApiEnv }).env?.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

function apiUrl(path: string): string {
  return apiBaseUrl ? `${apiBaseUrl}${path}` : path;
}

async function parseJsonResponse<T>(response: Response, errorMessage: string): Promise<T> {
  if (!response.ok) {
    throw new Error(errorMessage);
  }
  return (await response.json()) as T;
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

export async function getWorkspace(caseId: string): Promise<WorkspaceSummary> {
  const response = await fetch(apiUrl(`/api/cases/${caseId}/workspace`));
  return parseJsonResponse<WorkspaceSummary>(response, "加载案件工作台失败");
}

export async function getWorkspaceDetail(caseId: string): Promise<WorkspaceDetailResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/workspace/detail`));
  return parseJsonResponse<WorkspaceDetailResponse>(response, "加载工作区简报失败");
}

export async function getWorkspaceMethods(
  caseId: string,
  options: { query?: string; limit?: number } = {},
): Promise<WorkspaceMethodsResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("query", options.query ?? "");
  searchParams.set("limit", String(options.limit ?? 12));

  const response = await fetch(
    apiUrl(`/api/cases/${encodeURIComponent(caseId)}/workspace/methods?${searchParams.toString()}`),
  );
  return parseJsonResponse<WorkspaceMethodsResponse>(response, "加载方法索引失败");
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

export async function openWorkspaceInJadx(caseId: string): Promise<OpenJadxResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/actions/open-jadx`), {
    method: "POST",
  });
  return parseJsonResponse<OpenJadxResponse>(response, "打开 JADX 失败");
}

export async function startExecution(caseId: string): Promise<ExecutionStartResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/executions`), {
    method: "POST",
  });
  return parseJsonResponse<ExecutionStartResponse>(response, "启动执行失败");
}

export async function exportReport(caseId: string): Promise<ReportExportResponse> {
  const response = await fetch(apiUrl(`/api/cases/${encodeURIComponent(caseId)}/reports/export`), {
    method: "POST",
  });
  return parseJsonResponse<ReportExportResponse>(response, "导出报告失败");
}
