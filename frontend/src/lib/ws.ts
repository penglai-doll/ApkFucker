import type { WorkspaceEvent } from "./types";
import { resolveApiBaseUrl } from "./api";

type WsEnv = {
  VITE_API_BASE_URL?: string;
};

type RuntimeLocation = Pick<Location, "protocol" | "host">;

type WorkspaceEventsOptions = {
  caseId: string;
  onEvent: (event: WorkspaceEvent) => void;
  onError?: () => void;
};

export type WorkspaceEventsConnection = {
  close: () => void;
};

export function resolveWebSocketBaseUrl(options: {
  configuredBaseUrl?: string;
  runtimeBaseUrl?: string;
  location?: RuntimeLocation | null;
  tauriRuntime?: boolean;
} = {}): string {
  const apiBaseUrl = resolveApiBaseUrl({
    configuredBaseUrl: options.configuredBaseUrl ?? (import.meta as ImportMeta & { env?: WsEnv }).env?.VITE_API_BASE_URL,
    runtimeBaseUrl: options.runtimeBaseUrl,
    location: options.location,
    tauriRuntime: options.tauriRuntime,
  });

  if (apiBaseUrl) {
    return apiBaseUrl.replace(/^http/i, "ws");
  }

  const location = options.location ?? (typeof window !== "undefined" ? window.location : null);
  if (!location) {
    return "ws://127.0.0.1:8765";
  }

  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}`;
}

export function resolveWebSocketUrl(): string {
  return `${resolveWebSocketBaseUrl()}/ws`;
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
