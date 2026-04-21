type TauriWindow = Window & {
  __TAURI__?: unknown;
  __TAURI_INTERNALS__?: unknown;
};

function isTauriRuntime(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const runtimeWindow = window as TauriWindow;
  return Boolean(runtimeWindow.__TAURI__ || runtimeWindow.__TAURI_INTERNALS__);
}

function normalizeDialogSelection(selection: string | string[] | null): string | null {
  if (typeof selection === "string") {
    return selection;
  }

  if (Array.isArray(selection)) {
    return selection[0] ?? null;
  }

  return null;
}

async function openNativeDialog(options: {
  directory: boolean;
  filters?: Array<{ name: string; extensions: string[] }>;
}): Promise<string | null> {
  if (!isTauriRuntime()) {
    throw new Error("desktop unavailable");
  }

  const dialog = await import("@tauri-apps/plugin-dialog");
  const selected = await dialog.open({
    multiple: false,
    directory: options.directory,
    filters: options.filters,
  });

  return normalizeDialogSelection(selected);
}

export async function pickSampleFile(): Promise<string | null> {
  return openNativeDialog({
    directory: false,
    filters: [
      {
        name: "Android 样本",
        extensions: ["apk", "apks", "xapk", "zip"],
      },
    ],
  });
}

export async function pickWorkspaceDirectory(): Promise<string | null> {
  return openNativeDialog({
    directory: true,
  });
}

export async function pickHarFile(): Promise<string | null> {
  return openNativeDialog({
    directory: false,
    filters: [
      {
        name: "HAR 抓包文件",
        extensions: ["har"],
      },
    ],
  });
}

export async function pickFridaServerBinary(): Promise<string | null> {
  return openNativeDialog({
    directory: false,
  });
}
