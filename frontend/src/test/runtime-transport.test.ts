import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "../lib/api";
import { resolveWebSocketBaseUrl } from "../lib/ws";

describe("runtime transport resolution", () => {
  it("prefers an explicitly configured API base URL", () => {
    expect(resolveApiBaseUrl({ configuredBaseUrl: "http://127.0.0.1:9000/" })).toBe("http://127.0.0.1:9000");
  });

  it("falls back to the packaged loopback API URL for Tauri runtimes", () => {
    expect(
      resolveApiBaseUrl({
        location: { protocol: "tauri:", host: "tauri.localhost" },
        tauriRuntime: true,
      }),
    ).toBe("http://127.0.0.1:8765");
  });

  it("keeps browser development traffic relative when no base URL is configured", () => {
    expect(
      resolveApiBaseUrl({
        location: { protocol: "http:", host: "127.0.0.1:5173" },
        tauriRuntime: false,
      }),
    ).toBe("");
  });

  it("derives the WebSocket base URL from the packaged loopback API", () => {
    expect(
      resolveWebSocketBaseUrl({
        location: { protocol: "tauri:", host: "tauri.localhost" },
        tauriRuntime: true,
      }),
    ).toBe("ws://127.0.0.1:8765");
  });

  it("converts configured HTTP API endpoints into WebSocket endpoints", () => {
    expect(resolveWebSocketBaseUrl({ configuredBaseUrl: "https://demo.example/api/" })).toBe("wss://demo.example/api");
  });
});
