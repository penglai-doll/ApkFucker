import type { CaseListResponse, WorkspaceSummary } from "./types";

async function parseJsonResponse<T>(response: Response, errorMessage: string): Promise<T> {
  if (!response.ok) {
    throw new Error(errorMessage);
  }
  return (await response.json()) as T;
}

export async function listCases(): Promise<CaseListResponse> {
  const response = await fetch("/api/cases");
  return parseJsonResponse<CaseListResponse>(response, "加载案件列表失败");
}

export async function getWorkspace(caseId: string): Promise<WorkspaceSummary> {
  const response = await fetch(`/api/cases/${caseId}/workspace`);
  return parseJsonResponse<WorkspaceSummary>(response, "加载案件工作台失败");
}
