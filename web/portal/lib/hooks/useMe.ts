import useSWR from "swr";
import { getMe } from "@/lib/api/user";

export function useMe() {
  return useSWR("/auth/me", () => getMe());
}
