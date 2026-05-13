import useSWR from "swr";
import { getMyDetailer } from "@/lib/api/detailer";

export function useDetailerMe() {
  return useSWR("/detailers/me", () => getMyDetailer());
}
