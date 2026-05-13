import useSWR from "swr";
import { getMyServices } from "@/lib/api/detailer";

export function useDetailerServices() {
  return useSWR("/detailers/me/services", () => getMyServices());
}
