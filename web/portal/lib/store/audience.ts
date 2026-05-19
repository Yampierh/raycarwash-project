"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type Audience = "client" | "detailer";

interface AudienceStore {
  audience: Audience;
  setAudience: (a: Audience) => void;
}

export const useAudienceStore = create<AudienceStore>()(
  persist(
    (set) => ({
      audience: "client",
      setAudience: (audience) => set({ audience }),
    }),
    {
      name: "rcw_audience",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
