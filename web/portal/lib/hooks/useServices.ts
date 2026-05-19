import useSWR from "swr";
import { listServices } from "@/lib/api/catalog";

export function useServices() {
  return useSWR("/services", () => listServices());
}
