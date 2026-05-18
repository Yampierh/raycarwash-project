import React, { useCallback, useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClientProvider } from "@tanstack/react-query";
import * as Notifications from "expo-notifications";
import AppNavigator from "./src/navigation/AppNavigator";
import { useAuthStore } from "./src/store/authStore";
import { getToken } from "./src/utils/storage";
import { usePushNotifications } from "./src/hooks/usePushNotifications";
import { navigationRef } from "./src/navigation/navigationRef";
import { queryClient } from "./src/lib/react-query";

// Lazy-load StripeProvider — crashes in Expo Go (needs custom dev client)
let StripeProvider: React.ComponentType<any> | null = null;
try {
  StripeProvider = require("@stripe/stripe-react-native").StripeProvider;
} catch {
  // Expo Go — Stripe native module unavailable
}

const STRIPE_PK = process.env.EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "";

/** Decode the `role` claim from a JWT payload without verifying signature. */
function extractRoleFromJwt(token: string): string[] {
  try {
    const payloadB64 = token.split(".")[1];
    // base64url → base64
    const padded = payloadB64.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(padded);
    const payload = JSON.parse(json) as Record<string, unknown>;
    const role = payload["role"];
    if (typeof role === "string") return [role];
    if (Array.isArray(role)) return role.map(String);
  } catch {
    // Malformed token — store stays empty
  }
  return [];
}

export default function App() {
  const setTokens  = useAuthStore((s) => s.setTokens);
  const isDetailer = useAuthStore((s) => s.isDetailer);
  const token      = useAuthStore((s) => s.token);

  // Hydrate Zustand store from SecureStore on first mount.
  useEffect(() => {
    getToken().then((t) => {
      if (t) setTokens(t, extractRoleFromJwt(t));
    });
  }, [setTokens]);

  const handleNotificationTap = useCallback(
    (notification: Notifications.Notification) => {
      if (!navigationRef.isReady()) return;
      // Navigate to the user's main dashboard so they can find the appointment
      if (isDetailer()) {
        navigationRef.navigate("DetailerMain");
      } else {
        navigationRef.navigate("Main");
      }
    },
    [isDetailer]
  );

  // Register device push token when authenticated; unregister is handled by clearAuthTokens
  usePushNotifications(token ? handleNotificationTap : undefined);

  const inner = (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <AppNavigator />
      </SafeAreaProvider>
    </QueryClientProvider>
  );

  if (StripeProvider && STRIPE_PK && !STRIPE_PK.includes("placeholder")) {
    return (
      <StripeProvider
        publishableKey={STRIPE_PK}
        merchantIdentifier="merchant.com.raycarwash"
      >
        {inner}
      </StripeProvider>
    );
  }

  return inner;
}
