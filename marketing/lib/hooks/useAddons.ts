import useSWR from "swr";
import { listAddons } from "@/lib/api/catalog";

export function useAddons() {
  return useSWR("/addons", () => listAddons());
}
