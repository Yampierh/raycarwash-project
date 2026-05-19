"use client";

import { useGoogleLogin } from "@react-oauth/google";

type Props = {
  label: string;
  onSuccess: (args: {
    code: string;
    code_verifier: string;
    redirect_uri: string;
  }) => Promise<void> | void;
  onError?: (err: unknown) => void;
  disabled?: boolean;
};

export default function GoogleButton(props: Props) {
  // Hooks-rules-safe gate: if no Google client is configured, we never render the
  // inner button (and therefore never call useGoogleLogin which requires the
  // GoogleOAuthProvider to be present in the tree).
  if (!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) return null;
  return <GoogleButtonInner {...props} />;
}

function GoogleButtonInner({ label, onSuccess, onError, disabled }: Props) {
  const redirectUri =
    typeof window !== "undefined" ? window.location.origin : "";

  const triggerLogin = useGoogleLogin({
    flow: "auth-code",
    ux_mode: "popup",
    onSuccess: async (resp) => {
      try {
        await onSuccess({
          code: resp.code,
          code_verifier: "",
          redirect_uri: redirectUri,
        });
      } catch (e) {
        onError?.(e);
      }
    },
    onError: (err) => onError?.(err),
  });

  return (
    <button
      type="button"
      onClick={() => triggerLogin()}
      disabled={disabled}
      className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-900 transition hover:bg-zinc-50 disabled:opacity-50"
    >
      <GoogleIcon />
      {label}
    </button>
  );
}

function GoogleIcon() {
  return (
    <svg className="size-4" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M12 5.04c1.69 0 3.21.58 4.4 1.72l3.3-3.3C17.7 1.62 15.06.5 12 .5 7.31.5 3.26 3.19 1.3 7.13l3.84 2.98C6.07 7.27 8.81 5.04 12 5.04z"
      />
      <path
        fill="#4285F4"
        d="M23.5 12.27c0-.81-.07-1.59-.21-2.34H12v4.43h6.46c-.28 1.5-1.13 2.77-2.4 3.62l3.7 2.87c2.16-2 3.74-4.95 3.74-8.58z"
      />
      <path
        fill="#FBBC05"
        d="M5.14 14.27a7.18 7.18 0 010-4.54L1.3 6.74A11.5 11.5 0 00.5 12c0 1.86.44 3.62 1.3 5.26l3.84-2.99z"
      />
      <path
        fill="#34A853"
        d="M12 23.5c3.06 0 5.63-1.01 7.5-2.74l-3.7-2.87c-1.02.69-2.34 1.09-3.8 1.09-3.19 0-5.93-2.23-6.86-5.07l-3.84 2.99C3.26 20.81 7.31 23.5 12 23.5z"
      />
    </svg>
  );
}
