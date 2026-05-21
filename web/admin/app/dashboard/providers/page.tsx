"use client";

import { useEffect, useState } from "react";
import { listVerifications, listUsers } from "@/lib/api";

type TabStatus = "all" | "pending" | "approved" | "rejected";

const TABS: { label: string; value: TabStatus }[] = [
  { label: "All Detailers", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
];

const STATUS_COLORS: Record<string, string> = {
  pending:     "bg-yellow-900/40 text-yellow-300 border-yellow-800",
  approved:    "bg-green-900/40 text-green-300 border-green-800",
  rejected:    "bg-red-900/40 text-red-300 border-red-800",
  not_started: "bg-zinc-800 text-zinc-400 border-zinc-700",
};

interface Provider {
  provider_id: string;
  user_email: string | null;
  legal_full_name: string | null;
  verification_status: string;
  background_check_consent: boolean;
  submitted_at: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
}

interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  roles: string[];
}

export default function ProvidersPage() {
  const [tab, setTab] = useState<TabStatus>("all");
  const [verifications, setVerifications] = useState<Provider[]>([]);
  const [allDetailers, setAllDetailers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  function load(t: TabStatus) {
    setLoading(true);
    setError("");
    if (t === "all") {
      listUsers({ role: "detailer", per_page: 100 })
        .then((res: { users: User[] }) => setAllDetailers(res.users ?? []))
        .catch(() => setError("Failed to load detailers."))
        .finally(() => setLoading(false));
    } else {
      listVerifications(t)
        .then((data: Provider[]) => setVerifications(data))
        .catch(() => setError("Failed to load verifications."))
        .finally(() => setLoading(false));
    }
  }

  useEffect(() => { load(tab); }, [tab]);

  const filteredDetailers = allDetailers.filter(
    (u) =>
      !search ||
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      (u.full_name ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const filteredVerifications = verifications.filter(
    (v) =>
      !search ||
      (v.user_email ?? "").toLowerCase().includes(search.toLowerCase()) ||
      (v.legal_full_name ?? "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Providers</h1>
      <p className="text-zinc-400 text-sm mb-6">Detailer accounts and verification status</p>

      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex gap-1 bg-zinc-800/50 p-1 rounded-lg w-fit">
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

        <input
          type="text"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-1.5 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
        />
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800/60">
            <tr>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Name / Email</th>
              {tab === "all" ? (
                <>
                  <th className="text-left text-zinc-400 font-medium px-4 py-3">Status</th>
                  <th className="text-left text-zinc-400 font-medium px-4 py-3">Joined</th>
                </>
              ) : (
                <>
                  <th className="text-left text-zinc-400 font-medium px-4 py-3">BG Check</th>
                  <th className="text-left text-zinc-400 font-medium px-4 py-3">Submitted</th>
                  <th className="text-left text-zinc-400 font-medium px-4 py-3">Reviewed</th>
                  <th className="text-left text-zinc-400 font-medium px-4 py-3">Verification</th>
                </>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {loading &&
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 4 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))}

            {!loading && tab === "all" &&
              filteredDetailers.map((u) => (
                <tr key={u.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-zinc-200">{u.full_name ?? "—"}</p>
                    <p className="text-zinc-500 text-xs">{u.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                        u.is_active
                          ? "bg-green-900/40 text-green-300 border-green-800"
                          : "bg-red-900/40 text-red-300 border-red-800"
                      }`}
                    >
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}

            {!loading && tab !== "all" &&
              filteredVerifications.map((v) => (
                <tr key={v.provider_id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-zinc-200">{v.legal_full_name ?? "—"}</p>
                    <p className="text-zinc-500 text-xs">{v.user_email ?? "—"}</p>
                  </td>
                  <td className="px-4 py-3">
                    {v.background_check_consent ? (
                      <span className="text-green-400 text-xs">Consented</span>
                    ) : (
                      <span className="text-zinc-500 text-xs">No</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">
                    {v.submitted_at ? new Date(v.submitted_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">
                    {v.reviewed_at ? new Date(v.reviewed_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                        STATUS_COLORS[v.verification_status] ?? ""
                      }`}
                    >
                      {v.verification_status}
                    </span>
                  </td>
                </tr>
              ))}

            {!loading &&
              ((tab === "all" && filteredDetailers.length === 0) ||
                (tab !== "all" && filteredVerifications.length === 0)) && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                    No {tab === "all" ? "detailers" : `${tab} verifications`} found.
                  </td>
                </tr>
              )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
