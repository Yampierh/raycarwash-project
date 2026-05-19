"use client";

import { useState } from "react";
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { loadStripe, type Stripe } from "@stripe/stripe-js";
import { useTranslations } from "next-intl";
import { Button } from "@/components/forms/Button";
import { FormError } from "@/components/forms/FormError";
import { ShieldCheck } from "lucide-react";

let stripePromise: Promise<Stripe | null> | null = null;
function getStripe(): Promise<Stripe | null> | null {
  const pk = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
  if (!pk) return null;
  if (!stripePromise) stripePromise = loadStripe(pk);
  return stripePromise;
}

type Props = {
  clientSecret: string;
  amountCents: number;
  returnUrl: string;
  onSuccess: () => void;
};

export function CheckoutForm({
  clientSecret,
  amountCents,
  returnUrl,
  onSuccess,
}: Props) {
  const t = useTranslations("checkout");
  const stripe = getStripe();

  if (!stripe) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
        {t("missingKey")}
      </div>
    );
  }

  return (
    <Elements
      stripe={stripe}
      options={{
        clientSecret,
        appearance: { theme: "stripe" },
      }}
    >
      <InnerForm
        amountCents={amountCents}
        returnUrl={returnUrl}
        onSuccess={onSuccess}
      />
    </Elements>
  );
}

function InnerForm({
  amountCents,
  returnUrl,
  onSuccess,
}: {
  amountCents: number;
  returnUrl: string;
  onSuccess: () => void;
}) {
  const t = useTranslations("checkout");
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!stripe || !elements) return;
    setError(null);
    setLoading(true);
    const result = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: returnUrl },
      redirect: "if_required",
    });
    if (result.error) {
      setError(result.error.message ?? t("error"));
      setLoading(false);
      return;
    }
    onSuccess();
    setLoading(false);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <PaymentElement />
      <FormError message={error} />
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <ShieldCheck className="size-3.5 text-emerald-600" />
        {t("securedByStripe")}
      </div>
      <Button
        type="submit"
        loading={loading}
        disabled={!stripe || !elements}
        className="w-full"
        size="lg"
      >
        {t("pay", { amount: `$${(amountCents / 100).toFixed(2)}` })}
      </Button>
    </form>
  );
}
