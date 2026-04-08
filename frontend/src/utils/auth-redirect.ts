import { getMyDetailerProfile } from "../services/detailer-private.service";
import { getUserProfile } from "../services/user.service";

/**
 * Called after any successful login or registration.
 * Fetches the user role and redirects to the appropriate root navigator:
 *   - client   → Main (client tabs)
 *   - detailer, no profile yet → DetailerOnboarding
 *   - detailer, profile exists → DetailerMain (detailer tabs)
 */
export async function navigateAfterAuth(navigation: any): Promise<void> {
  try {
    const profile = await getUserProfile();

    if (profile.role !== "detailer") {
      navigation.reset({ index: 0, routes: [{ name: "Main" }] });
      return;
    }

    const detailerProfile = await getMyDetailerProfile().catch(() => null);
    const route = detailerProfile ? "DetailerMain" : "DetailerOnboarding";
    navigation.reset({ index: 0, routes: [{ name: route }] });
  } catch {
    // Fallback to client main — user can re-login if needed
    navigation.reset({ index: 0, routes: [{ name: "Main" }] });
  }
}
