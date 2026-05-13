import { getAuthState, type AuthState } from "../services/auth.service";

type AnyNavigation = {
  navigate: (name: string, params?: any) => void;
  reset: (state: any) => void;
};

/**
 * Route to the correct screen based on a structured AuthState from the backend.
 * Single source of truth for all post-auth navigation decisions.
 */
export function handleAuthState(
  state: AuthState,
  navigation: AnyNavigation,
): void {
  switch (state.type) {
    case "onboarding":
      navigation.reset({
        index: 0,
        routes: [{ name: state.step === "provider_type" ? "ProviderType" : "CompleteProfile" }],
      });
      break;

    case "active":
      if (state.step === "detailer_setup") {
        navigation.reset({ index: 0, routes: [{ name: "DetailerOnboarding" }] });
      } else if (state.context.role === "detailer") {
        navigation.reset({ index: 0, routes: [{ name: "DetailerMain" }] });
      } else {
        navigation.reset({ index: 0, routes: [{ name: "Main" }] });
      }
      break;

    default:
      navigation.reset({ index: 0, routes: [{ name: "Login" }] });
  }
}

/**
 * Route from any auth response. Uses auth_state when available (v3),
 * falls back to GET /auth/state (which always returns auth_state).
 */
export async function routeFromAuthResponse(
  result: { auth_state?: AuthState },
  navigation: AnyNavigation,
): Promise<void> {
  if (result.auth_state) {
    handleAuthState(result.auth_state, navigation);
    return;
  }
  await resolveAuthState(navigation);
}

/**
 * Fetch the current auth state from the backend and route accordingly.
 * Use on app launch (LoadingScreen) or after token refresh.
 */
export async function resolveAuthState(navigation: AnyNavigation): Promise<void> {
  const state = await getAuthState();
  handleAuthState(state, navigation);
}
