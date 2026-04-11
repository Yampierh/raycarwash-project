import React from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import AppNavigator from "./src/navigation/AppNavigator";

// Lazy-load StripeProvider — crashes in Expo Go (needs custom dev client)
let StripeProvider: React.ComponentType<any> | null = null;
try {
  StripeProvider = require("@stripe/stripe-react-native").StripeProvider;
} catch {
  // Expo Go — Stripe native module unavailable
}

const STRIPE_PK = process.env.EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "";

export default function App() {
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
