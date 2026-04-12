import type { WorkspaceEvent } from "./types";

type WsEnv = {
  VITE_API_BASE_URL?: string;
};

type WorkspaceEventsOptions = {
  caseId: string;
  onEvent: (event: WorkspaceEvent) => void;
  onError?: () => void;
};

export type WorkspaceEventsConnection = {
  close: () => void;
};

function resolveWebSocketUrl(): string {
  const configuredBaseUrl = ((import.meta as ImportMeta & { env?: WsEnv }).env?.VITE_API_BASE_URL ?? "").replace(
    /\/$/,
    "",
  );

  if (configuredBaseUrl) {
    const wsBaseUrl = configuredBaseUrl.replace(/^http/i, "ws");
    return `${wsBaseUrl}/ws`;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

export function connectWorkspaceEvents({
  caseId,
  onEvent,
  onError,
}: WorkspaceEventsOptions): WorkspaceEventsConnection {
  if (typeof WebSocket === "undefined") {
    return {
      close: () => undefined,
    };
  }

  const socket = new WebSocket(resolveWebSocketUrl());
  socket.addEventListener("message", (message) => {
    try {
      const parsed = JSON.parse(String(message.data)) as WorkspaceEvent;
      if (parsed.case_id && parsed.case_id !== caseId) {
        return;
      }
      onEvent(parsed);
    } catch {
      onError?.();
    }
  });
  socket.addEventListener("error", () => {
    onError?.();
  });

  return {
    close: () => {
      socket.close();
    },
  };
}
