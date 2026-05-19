"use client";

import { useEffect, useState } from "react";
import { listVerifications, approveVerification, rejectVerification } from "@/lib/api";

type TabStatus = "pending" | "approved" | "rejected";

const TABS: { label: string; value: TabStatus }[] = [
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
];

const STATUS_COLORS: Record<string, string> = {
  pending:  "bg-yellow-900/40 text-yellow-300 border-yellow-800",
  approved: "bg-green-900/40 text-green-300 border-green-800",
  rejected: "bg-red-900/40 text-red-300 border-red-800",
};

interface Verification {
  provider_id: string;
  user_email: string | null;
  legal_full_name: string | null;
  verification_status: string;
  background_check_consent: boolean;
  submitted_at: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
}

export default function VerificationsPage() {
  const [tab, setTab] = useState<TabStatus>("pending");
  const [items, setItems] = useState<Verification[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Reject modal
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  function load(s: TabStatus) {
    setLoading(true);
    setError("");
    setActionMsg("");
    listVerifications(s)
      .then((data: Verification[]) => setItems(data))
      .catch(() => setError("Failed to load verifications."))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(tab); }, [tab]);

  async function handleApprove(providerId: string) {
    if (!confirm("Approve this detailer?")) return;
    try {
      await approveVerification(providerId);
      setActionMsg("Detailer approved.");
      load(tab);
    } catch {
      setActionMsg("Failed to approve.");
    }
  }

  async function handleReject() {
    if (!rejectTarget || rejectReason.trim().length < 5) return;
    try {
      await rejectVerification(rejectTarget, rejectReason.trim());
      setActionMsg("Detailer rejected.");
      setRejectTarget(null);
      setRejectReason("");
      load(tab);
    } catch {
      setActionMsg("Failed to reject.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Verifications</h1>
      <p className="text-zinc-400 text-sm mb-6">Detailer identity verification queue</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-zinc-800/50 p-1 rounded-lg w-fit">
        {TABS.map(({ label, value }) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === value
                ? "bg-zinc-700 text-white"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {actionMsg && <p className="text-zinc-400 text-sm mb-4">{actionMsg}</p>}
      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {/* Table */}
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800/60">
            <tr>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Name</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Email</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">BG Check</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Submitted</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Status</th>
              {tab === "pending" && (
                <th className="text-right text-zinc-400 font-medium px-4 py-3">Actions</th>
              )}
              {tab === "rejected" && (
                <th className="text-left text-zinc-400 font-medium px-4 py-3">Reason</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {loading && (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: tab === "pending" ? 6 : 5 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            )}
            {!loading && items.map((v) => (
              <tr key={v.provider_id} className="hover:bg-zinc-800/30 transition-colors">
                <td className="px-4 py-3 text-zinc-200">{v.legal_full_name ?? "—"}</td>
                <td className="px-4 py-3 text-zinc-400">{v.user_email ?? "—"}</td>
                <td className="px-4 py-3">
                  {v.background_check_consent
                    ? <span className="text-green-400 text-xs">Consented</span>
                    : <span className="text-zinc-500 text-xs">No</span>}
                </td>
                <td className="px-4 py-3 text-zinc-500 text-xs">
                  {v.submitted_at ? new Date(v.submitted_at).toLocaleDateString() : "—"}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_COLORS[v.verification_status] ?? ""}`}>
                    {v.verification_status}
                  </span>
                </td>
                {tab === "pending" && (
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => handleApprove(v.provider_id)}
                        className="px-3 py-1 text-xs rounded-lg bg-green-900/50 text-green-300 border border-green-800 hover:bg-green-800/60 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => { setRejectTarget(v.provider_id); setRejectReason(""); }}
                        className="px-3 py-1 text-xs rounded-lg bg-red-900/50 text-red-300 border border-red-800 hover:bg-red-800/60 transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                )}
                {tab === "rejected" && (
                  <td className="px-4 py-3 text-zinc-400 text-xs max-w-xs truncate">
                    {v.rejection_reason ?? "—"}
                  </td>
                )}
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-zinc-500">
                  No {tab} verifications.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Reject Modal */}
      {rejectTarget && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-white font-semibold mb-1">Reject Detailer</h3>
            <p className="text-zinc-400 text-sm mb-4">Provide a reason for rejection (required).</p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Enter rejection reason..."
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 h-24 resize-none focus:outline-none focus:border-zinc-500"
            />
            <div className="flex gap-3 mt-4 justify-end">
              <button
                onClick={() => { setRejectTarget(null); setRejectReason(""); }}
                className="px-4 py-2 text-sm rounded-lg text-zinc-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={rejectReason.trim().length < 5}
                className="px-4 py-2 text-sm rounded-lg bg-red-700 hover:bg-red-600 text-white disabled:opacity-40 transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
