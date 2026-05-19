import useSWR from "swr";
import { listVehicles } from "@/lib/api/vehicles";

export function useVehicles() {
  return useSWR("/vehicles", () => listVehicles());
}
