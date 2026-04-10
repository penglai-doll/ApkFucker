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
