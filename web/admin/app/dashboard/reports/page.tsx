"use client";

import { useEffect, useState } from "react";
import { getStats, getPaymentSummary, api } from "@/lib/api";

type Window = "today" | "7d" | "30d" | "90d";

const WINDOWS: { label: string; value: Window }[] = [
  { label: "Today", value: "today" },
  { label: "7 days", value: "7d" },
  { label: "30 days", value: "30d" },
  { label: "90 days", value: "90d" },
];

interface Stats {
  total_users: number;
  total_providers: number;
  total_appointments: number;
  total_revenue_cents: number;
  pending_verifications: number;
  active_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
}

interface PaymentSummary {
  total_captured: number;
  total_refunded: number;
  total_commissions: number;
  total_payouts: number;
  net_revenue: number;
}

interface OpsKpis {
  gmv_cents: { value: number };
  bookings: { value: number };
  active_jobs: { value: number };
  take_rate: { value: number };
  csat: { value: number };
  cancel_rate: { value: number };
}

interface OpsResponse {
  kpis: OpsKpis;
  window: string;
  period_start: string;
  period_end: string;
}

function fmt(cents: number) {
  return `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function ReportsPage() {
  const [window, setWindow] = useState<Window>("7d");
  const [stats, setStats] = useState<Stats | null>(null);
  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [ops, setOps] = useState<OpsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      getStats(),
      getPaymentSummary({}),
      api.get("/api/v1/admin/ops/dashboard", { params: { window } }).then((r) => r.data),
    ])
      .then(([s, pay, o]) => {
        setStats(s);
        setSummary(pay);
        setOps(o);
      })
      .catch(() => setError("Failed to load report data."))
      .finally(() => setLoading(false));
  }, [window]);

  const kpiCards = ops
    ? [
        { label: "GMV", value: fmt(ops.kpis.gmv_cents.value), sub: "Gross merchandise value" },
        { label: "Bookings", value: String(Math.round(ops.kpis.bookings.value)), sub: "Appointments placed" },
        { label: "Active Jobs", value: String(Math.round(ops.kpis.active_jobs.value)), sub: "Currently in-flight" },
        { label: "Take Rate", value: pct(ops.kpis.take_rate.value), sub: "Platform commission" },
        { label: "CSAT", value: ops.kpis.csat.value.toFixed(2), sub: "Avg rating (1–5)" },
        { label: "Cancel Rate", value: pct(ops.kpis.cancel_rate.value), sub: "Cancelled bookings" },
      ]
    : [];

  const revenueCards = summary
    ? [
        { label: "Captured", value: fmt(summary.total_captured), color: "border-green-800 bg-green-950/20" },
        { label: "Refunded", value: fmt(summary.total_refunded), color: "border-red-800 bg-red-950/20" },
        { label: "Commissions", value: fmt(summary.total_commissions), color: "border-purple-800 bg-purple-950/20" },
        { label: "Payouts", value: fmt(summary.total_payouts), color: "border-blue-800 bg-blue-950/20" },
        { label: "Net Revenue", value: fmt(summary.net_revenue), color: "border-zinc-700 bg-zinc-800/30" },
      ]
    : [];

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Reports</h1>
          <p className="text-zinc-400 text-sm">Platform performance and revenue metrics</p>
        </div>
        <div className="flex gap-1 bg-zinc-800/50 p-1 rounded-lg w-fit">
          {WINDOWS.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => setWindow(value)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                window === value ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-red-400 text-sm mb-6">{error}</p>}

      {/* Platform overview from /stats */}
      {stats && (
        <section className="mb-8">
          <h2 className="text-zinc-400 text-xs font-semibold uppercase tracking-wide mb-3">
            Platform Overview
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Total Users", value: stats.total_users.toLocaleString() },
              { label: "Total Providers", value: stats.total_providers.toLocaleString() },
              { label: "Total Appointments", value: stats.total_appointments.toLocaleString() },
              { label: "Lifetime Revenue", value: fmt(stats.total_revenue_cents) },
              { label: "Completed", value: stats.completed_appointments.toLocaleString() },
              { label: "Cancelled", value: stats.cancelled_appointments.toLocaleString() },
              { label: "Active Now", value: stats.active_appointments.toLocaleString() },
              { label: "Pending Verification", value: stats.pending_verifications.toLocaleString() },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                <p className="text-zinc-500 text-xs mb-1">{label}</p>
                <p className="text-xl font-bold text-white">{value}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Ops KPIs for selected window */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 animate-pulse">
              <div className="h-3 bg-zinc-800 rounded w-1/2 mb-2" />
              <div className="h-7 bg-zinc-800 rounded w-3/4" />
            </div>
          ))}
        </div>
      )}

      {!loading && kpiCards.length > 0 && (
        <section className="mb-8">
          <h2 className="text-zinc-400 text-xs font-semibold uppercase tracking-wide mb-3">
            Operations — {WINDOWS.find((w) => w.value === window)?.label}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {kpiCards.map(({ label, value, sub }) => (
              <div key={label} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                <p className="text-zinc-500 text-xs mb-1">{label}</p>
                <p className="text-2xl font-bold text-white">{value}</p>
                <p className="text-zinc-600 text-xs mt-1">{sub}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Revenue breakdown */}
      {!loading && revenueCards.length > 0 && (
        <section>
          <h2 className="text-zinc-400 text-xs font-semibold uppercase tracking-wide mb-3">
            Revenue Breakdown (all time)
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {revenueCards.map(({ label, value, color }) => (
              <div key={label} className={`rounded-xl border p-4 ${color}`}>
                <p className="text-zinc-400 text-xs mb-1">{label}</p>
                <p className="text-lg font-bold text-white">{value}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
