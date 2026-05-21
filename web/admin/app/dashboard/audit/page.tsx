"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface AuditEntry {
  id: string;
  actor_id: string | null;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  ip_address: string | null;
  created_at: string;
}

interface AuditResponse {
  entries: AuditEntry[];
  total: number;
  page: number;
  per_page: number;
}

const ACTION_GROUPS: Record<string, string> = {
  appointment: "bg-blue-900/40 text-blue-300 border-blue-800",
  payment: "bg-green-900/40 text-green-300 border-green-800",
  user_registered: "bg-purple-900/40 text-purple-300 border-purple-800",
  user_login: "bg-zinc-800 text-zinc-300 border-zinc-700",
  password: "bg-yellow-900/40 text-yellow-300 border-yellow-800",
  two_fa: "bg-orange-900/40 text-orange-300 border-orange-800",
  session: "bg-red-900/40 text-red-300 border-red-800",
  review: "bg-pink-900/40 text-pink-300 border-pink-800",
};

function actionColor(action: string): string {
  for (const [key, cls] of Object.entries(ACTION_GROUPS)) {
    if (action.startsWith(key)) return cls;
  }
  return "bg-zinc-800 text-zinc-400 border-zinc-700";
}

const PER_PAGE = 50;

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [filterAction, setFilterAction] = useState("");
  const [filterEntity, setFilterEntity] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [applied, setApplied] = useState(false);

  function load(p: number) {
    setLoading(true);
    setError("");
    const params: Record<string, string | number> = { page: p, per_page: PER_PAGE };
    if (filterAction) params.action = filterAction;
    if (filterEntity) params.entity_type = filterEntity;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    api
      .get("/api/v1/admin/audit-logs", { params })
      .then((res) => {
        const data: AuditResponse = res.data;
        setEntries(data.entries);
        setTotal(data.total);
        setPage(p);
      })
      .catch(() => setError("Failed to load audit log."))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(1); }, []);

  function handleApply() {
    setApplied(true);
    load(1);
  }

  function handleClear() {
    setFilterAction("");
    setFilterEntity("");
    setStartDate("");
    setEndDate("");
    setApplied(false);
    setPage(1);
    setLoading(true);
    api
      .get("/api/v1/admin/audit-logs", { params: { page: 1, per_page: PER_PAGE } })
      .then((res) => {
        const data: AuditResponse = res.data;
        setEntries(data.entries);
        setTotal(data.total);
      })
      .catch(() => setError("Failed to load audit log."))
      .finally(() => setLoading(false));
  }

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Audit Log</h1>
      <p className="text-zinc-400 text-sm mb-6">Security and activity event trail</p>

      {/* Filters */}
      <div className="mb-6 rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Action</label>
            <input
              type="text"
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              placeholder="e.g. user_login"
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-1.5 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">Entity Type</label>
            <input
              type="text"
              value={filterEntity}
              onChange={(e) => setFilterEntity(e.target.value)}
              placeholder="e.g. appointment"
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-1.5 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">From</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-zinc-500"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">To</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-zinc-500"
            />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleApply}
            className="px-4 py-1.5 text-sm rounded-lg bg-zinc-700 hover:bg-zinc-600 text-white transition-colors"
          >
            Apply
          </button>
          {applied && (
            <button
              onClick={handleClear}
              className="px-4 py-1.5 text-sm rounded-lg text-zinc-400 hover:text-white transition-colors"
            >
              Clear
            </button>
          )}
          <span className="ml-auto text-zinc-500 text-xs self-center">
            {total.toLocaleString()} entries
          </span>
        </div>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      <div className="rounded-xl border border-zinc-800 overflow-hidden mb-4">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800/60">
            <tr>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Timestamp</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Actor</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Action</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Entity</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {loading &&
              Array.from({ length: 10 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))}

            {!loading &&
              entries.map((e) => (
                <tr key={e.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 text-zinc-400 text-xs whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    {e.actor_email ? (
                      <span className="text-zinc-300 text-xs">{e.actor_email}</span>
                    ) : (
                      <span className="text-zinc-600 text-xs">system</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${actionColor(e.action)}`}
                    >
                      {e.action}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-zinc-400 text-xs">{e.entity_type}</span>
                    <span className="text-zinc-600 text-xs ml-1 font-mono">
                      {e.entity_id.length > 12 ? `${e.entity_id.slice(0, 8)}…` : e.entity_id}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-600 text-xs font-mono">
                    {e.ip_address ?? "—"}
                  </td>
                </tr>
              ))}

            {!loading && entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                  No audit log entries found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-zinc-500 text-xs">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => load(page - 1)}
              disabled={page <= 1 || loading}
              className="px-3 py-1.5 text-sm rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40 transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => load(page + 1)}
              disabled={page >= totalPages || loading}
              className="px-3 py-1.5 text-sm rounded-lg bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
