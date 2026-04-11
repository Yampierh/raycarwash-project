import React, { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import AppNavigator from "./src/navigation/AppNavigator";
import { useAuthStore } from "./src/store/authStore";
import { getToken } from "./src/utils/storage";

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
  const setTokens = useAuthStore((s) => s.setTokens);

  // Hydrate Zustand store from SecureStore on first mount.
  // This enables synchronous token access in the WS hook without an
  // async SecureStore call each time a connection is (re-)established.
  useEffect(() => {
    getToken().then((token) => {
      if (token) {
        setTokens(token, extractRoleFromJwt(token));
      }
    });
  }, [setTokens]);

  const inner = (
    <SafeAreaProvider>
      <AppNavigator />
    </SafeAreaProvider>
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
