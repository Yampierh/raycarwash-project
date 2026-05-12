"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listAppointments } from "@/lib/api";

const STATUSES = [
  "pending", "confirmed", "arrived", "in_progress", "completed",
  "cancelled_by_client", "cancelled_by_detailer", "no_show",
  "searching", "no_detailer_found",
];

const STATUS_COLORS: Record<string, string> = {
  pending:               "bg-yellow-900/40 text-yellow-300 border-yellow-800",
  confirmed:             "bg-blue-900/40 text-blue-300 border-blue-800",
  arrived:               "bg-cyan-900/40 text-cyan-300 border-cyan-800",
  in_progress:           "bg-purple-900/40 text-purple-300 border-purple-800",
  completed:             "bg-green-900/40 text-green-300 border-green-800",
  cancelled_by_client:   "bg-red-900/40 text-red-300 border-red-800",
  cancelled_by_detailer: "bg-red-900/40 text-red-300 border-red-800",
  no_show:               "bg-orange-900/40 text-orange-300 border-orange-800",
  searching:             "bg-indigo-900/40 text-indigo-300 border-indigo-800",
  no_detailer_found:     "bg-zinc-800/60 text-zinc-400 border-zinc-700",
};

interface Appointment {
  id: string;
  status: string;
  scheduled_time: string;
  client_email: string | null;
  detailer_email: string | null;
  service_name: string | null;
  estimated_price: number;
  actual_price: number | null;
}

interface ListResponse {
  appointments: Appointment[];
  total: number;
  page: number;
  per_page: number;
}

function fmt(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

export default function AppointmentsPage() {
  const router = useRouter();
  const [data, setData] = useState<ListResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    listAppointments({
      page,
      per_page: 20,
      status: statusFilter || undefined,
      search: search || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    })
      .then(setData)
      .catch(() => setError("Failed to load appointments."))
      .finally(() => setLoading(false));
  }, [page, statusFilter, search, startDate, endDate]);

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 1;

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Appointments</h1>
      <p className="text-zinc-400 text-sm mb-6">
        {data ? `${data.total.toLocaleString()} total` : "Loading..."}
      </p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>

        <input
          type="date"
          value={startDate}
          onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500"
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500"
        />

        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search by email..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { setSearch(searchInput); setPage(1); } }}
            className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500 w-56"
          />
          <button
            onClick={() => { setSearch(searchInput); setPage(1); }}
            className="bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-3 py-2 rounded-lg transition-colors"
          >
            Search
          </button>
          {(statusFilter || search || startDate || endDate) && (
            <button
              onClick={() => { setStatusFilter(""); setSearch(""); setSearchInput(""); setStartDate(""); setEndDate(""); setPage(1); }}
              className="text-zinc-400 hover:text-white text-sm px-3 py-2 rounded-lg transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {/* Table */}
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800/60">
            <tr>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">ID</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Client</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Detailer</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Service</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Status</th>
              <th className="text-left text-zinc-400 font-medium px-4 py-3">Date</th>
              <th className="text-right text-zinc-400 font-medium px-4 py-3">Price</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {loading && !data && (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            )}
            {data?.appointments.map((appt) => (
              <tr
                key={appt.id}
                onClick={() => router.push(`/dashboard/appointments/${appt.id}`)}
                className="hover:bg-zinc-800/40 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3 font-mono text-zinc-400 text-xs">
                  {appt.id.slice(0, 8)}…
                </td>
                <td className="px-4 py-3 text-zinc-200">{appt.client_email ?? "—"}</td>
                <td className="px-4 py-3 text-zinc-400">{appt.detailer_email ?? "—"}</td>
                <td className="px-4 py-3 text-zinc-300">{appt.service_name ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_COLORS[appt.status] ?? "bg-zinc-800 text-zinc-300 border-zinc-700"}`}>
                    {appt.status.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-zinc-400 text-xs">
                  {new Date(appt.scheduled_time).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right text-zinc-300 font-mono text-xs">
                  {appt.actual_price != null ? fmt(appt.actual_price) : fmt(appt.estimated_price)}
                </td>
              </tr>
            ))}
            {data?.appointments.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                  No appointments found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-zinc-500 text-sm">
            Page {page} of {totalPages}
          </p>
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
