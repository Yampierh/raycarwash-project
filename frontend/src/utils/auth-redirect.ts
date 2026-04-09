import { getMyDetailerProfile } from "../services/detailer-private.service";
import { getUserProfile } from "../services/user.service";

/**
 * Called after any successful login or registration.
 * Fetches the user role and redirects to the appropriate root navigator:
 *   - client only   → Main (client tabs)
 *   - detailer, no profile yet → DetailerOnboarding
 *   - detailer, profile exists → DetailerMain (detailer tabs)
 * 
 * RBAC Note: roles is now an array, e.g., ["client"] or ["detailer"]
 */
export async function navigateAfterAuth(navigation: any): Promise<void> {
  try {
    const profile = await getUserProfile();

    if (!profile.roles.includes("detailer")) {
      navigation.reset({ index: 0, routes: [{ name: "Main" }] });
      return;
    }

    const detailerProfile = await getMyDetailerProfile().catch((err) => {
      console.log("Error fetching detailer profile:", err?.response?.status);
      return null;
    });
    const route = detailerProfile ? "DetailerMain" : "DetailerOnboarding";
    navigation.reset({ index: 0, routes: [{ name: route }] });
  } catch (err) {
    console.log("Error in navigateAfterAuth:", err);
    // Fallback to client main — user can re-login if needed
    navigation.reset({ index: 0, routes: [{ name: "Main" }] });
  }
}
