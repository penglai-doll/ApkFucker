import { create } from "zustand";

import type { AppMode } from "../lib/types";

type AppStore = {
  currentMode: AppMode;
  setCurrentMode: (mode: AppMode) => void;
};

export const useAppStore = create<AppStore>((set) => ({
  currentMode: "queue",
  setCurrentMode: (mode) => set({ currentMode: mode }),
}));
