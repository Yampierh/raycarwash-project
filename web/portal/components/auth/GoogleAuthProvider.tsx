"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";

export default function GoogleAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  if (!clientId) {
    // Without a configured Google client, just render children — Google button
    // will be hidden by checking the env var in the consumer.
    return <>{children}</>;
  }

  return <GoogleOAuthProvider clientId={clientId}>{children}</GoogleOAuthProvider>;
}
