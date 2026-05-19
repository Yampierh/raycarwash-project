"use client";

import { useEffect, useState } from "react";
import { getPaymentSummary, getPaymentLedger } from "@/lib/api";

const ENTRY_TYPES = ["AUTHORIZATION", "CAPTURE", "REFUND", "PAYOUT", "CHARGE_COMMISSION"];

const ENTRY_COLORS: Record<string, string> = {
  AUTHORIZATION:    "bg-zinc-800 text-zinc-300 border-zinc-700",
  CAPTURE:          "bg-green-900/40 text-green-300 border-green-800",
  REFUND:           "bg-red-900/40 text-red-300 border-red-800",
  PAYOUT:           "bg-blue-900/40 text-blue-300 border-blue-800",
  CHARGE_COMMISSION:"bg-purple-900/40 text-purple-300 border-purple-800",
};

interface Summary {
  total_captured: number;
  total_refunded: number;
  total_commissions: number;
  total_payouts: number;
  net_revenue: number;
  period_start: string | null;
  period_end: string | null;
}

interface LedgerEntry {
  id: string;
  appointment_id: string;
  entry_type: string;
  amount_cents: number;
  currency: string;
  stripe_payment_intent_id: string | null;
  created_at: string;
}

interface LedgerResponse {
  entries: LedgerEntry[];
  total: number;
  page: number;
  per_page: number;
}

function fmt(cents: number) {
  const sign = cents < 0 ? "-" : "";
  return `${sign}$${(Math.abs(cents) / 100).toFixed(2)}`;
}

const SUMMARY_CARDS = [
  { key: "total_captured",    label: "Captured",    color: "border-green-800 bg-green-950/30"  },
  { key: "total_refunded",    label: "Refunded",    color: "border-red-800 bg-red-950/30"      },
  { key: "total_commissions", label: "Commissions", color: "border-purple-800 bg-purple-950/30"},
  { key: "total_payouts",     label: "Payouts",     color: "border-blue-800 bg-blue-950/30"    },
] as const;

export default function PaymentsPage() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [appliedStart, setAppliedStart] = useState("");
  const [appliedEnd, setAppliedEnd] = useState("");

  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const [ledger, setLedger] = useState<LedgerResponse | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("");
  const [error, setError] = useState("");

  function applyFilters() {
    setAppliedStart(startDate);
    setAppliedEnd(endDate);
    setPage(1);
  }

  useEffect(() => {
    setSummaryLoading(true);
    getPaymentSummary({
      start_date: appliedStart || undefined,
      end_date: appliedEnd || undefined,
    } as Record<string, string | undefined>)
      .then(setSummary)
      .catch(() => setError("Failed to load summary."))
      .finally(() => setSummaryLoading(false));
  }, [appliedStart, appliedEnd]);

  useEffect(() => {
    setLedgerLoading(true);
    getPaymentLedger({
      page,
      per_page: 20,
      entry_type: typeFilter || undefined,
      start_date: appliedStart || undefined,
      end_date: appliedEnd || undefined,
    } as Record<string, string | number | undefined>)
      .then(setLedger)
      .catch(() => setError("Failed to load ledger."))
      .finally(() => setLedgerLoading(false));
  }, [page, typeFilter, appliedStart, appliedEnd]);

  const totalPages = ledger ? Math.ceil(ledger.total / ledger.per_page) : 1;

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Payments</h1>
      <p className="text-zinc-400 text-sm mb-6">Financial ledger and revenue summary</p>

      {/* Date range */}
      <div className="flex flex-wrap gap-3 mb-6 items-center">
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500"
        />
        <span className="text-zinc-600 text-sm">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500"
        />
        <button
          onClick={applyFilters}
          className="px-4 py-2 text-sm rounded-lg bg-zinc-700 hover:bg-zinc-600 text-white transition-colors"
        >
          Apply
        </button>
        {(appliedStart || appliedEnd) && (
          <button
            onClick={() => { setStartDate(""); setEndDate(""); setAppliedStart(""); setAppliedEnd(""); }}
            className="text-zinc-400 hover:text-white text-sm px-3 py-2 rounded-lg transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {SUMMARY_CARDS.map(({ key, label, color }) => (
          <div key={key} className={`rounded-xl border p-5 ${color}`}>
            <p className="text-zinc-400 text-xs font-medium uppercase tracking-wider">{label}</p>
            <p className="text-2xl font-bold text-white mt-2 font-mono">
              {summaryLoading || !summary
                ? <span className="inline-block w-24 h-6 bg-zinc-700 animate-pulse rounded" />
                : fmt(summary[key])}
            </p>
          </div>
        ))}
      </div>

      {/* Net revenue */}
      {summary && (
        <div className="rounded-xl border border-zinc-700 p-4 mb-6 flex items-center justify-between">
          <div>
            <p className="text-zinc-400 text-xs uppercase tracking-wider">Net Revenue</p>
            <p className={`text-3xl font-bold mt-1 font-mono ${summary.net_revenue >= 0 ? "text-green-400" : "text-red-400"}`}>
              {fmt(summary.net_revenue)}
            </p>
          </div>
          <p className="text-zinc-600 text-xs text-right">
            Captured − Refunded − Payouts
          </p>
        </div>
      )}

      {/* Ledger filter */}
      <div className="flex gap-3 mb-4">
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500"
        >
          <option value="">All types</option>
          {ENTRY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <p className="text-zinc-500 text-sm self-center">
          {ledger ? `${ledger.total.toLocaleString()} entries` : ""}
        </p>
      </div>

      {/* Ledger table */}
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800/60">
            <tr>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Type</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Appointment</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Stripe PI</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Date</th>
              <th className="text-right text-zinc-400 font-medium px-4 py-3">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {ledgerLoading && (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            )}
            {!ledgerLoading && ledger?.entries.map((e) => (
              <tr key={e.id} className="hover:bg-zinc-800/30 transition-colors">
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${ENTRY_COLORS[e.entry_type] ?? "bg-zinc-800 text-zinc-300 border-zinc-700"}`}>
                    {e.entry_type}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-zinc-400 text-xs">
                  {e.appointment_id.slice(0, 8)}…
                </td>
                <td className="px-4 py-3 font-mono text-zinc-500 text-xs">
                  {e.stripe_payment_intent_id ? e.stripe_payment_intent_id.slice(0, 20) + "…" : "—"}
                </td>
                <td className="px-4 py-3 text-zinc-400 text-xs">
                  {new Date(e.created_at).toLocaleString()}
                </td>
                <td className={`px-4 py-3 text-right font-mono text-sm ${e.entry_type === "REFUND" ? "text-red-400" : "text-zinc-200"}`}>
                  {fmt(e.amount_cents)}
                </td>
              </tr>
            ))}
            {!ledgerLoading && ledger?.entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                  No ledger entries found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-zinc-500 text-sm">Page {page} of {totalPages}</p>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1.5 text-sm rounded-lg bg-zinc-800 text-zinc-300 disabled:opacity-40 hover:bg-zinc-700 transition-colors"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 text-sm rounded-lg bg-zinc-800 text-zinc-300 disabled:opacity-40 hover:bg-zinc-700 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
