import { resolveAuthState } from "./auth-controller";

/**
 * @deprecated Use `resolveAuthState()` from auth-controller directly.
 * Kept as a thin wrapper so existing callers (DetailerOnboardingScreen,
 * LoginScreen) keep working until they migrate.
 */
export async function navigateAfterAuth(navigation: any): Promise<void> {
  try {
    await resolveAuthState(navigation);
  } catch {
    navigation.reset({ index: 0, routes: [{ name: "Main" }] });
  }
}
