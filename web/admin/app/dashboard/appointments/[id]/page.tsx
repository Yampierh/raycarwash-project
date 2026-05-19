"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getAppointment, forceAppointmentStatus } from "@/lib/api";

const STATUSES = [
  "pending", "confirmed", "arrived", "in_progress", "completed",
  "cancelled_by_client", "cancelled_by_detailer", "no_show",
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
};

interface AppointmentDetail {
  id: string;
  status: string;
  scheduled_time: string;
  client_email: string | null;
  detailer_email: string | null;
  service_name: string | null;
  estimated_price: number;
  actual_price: number | null;
  client_notes: string | null;
  detailer_notes: string | null;
  service_address: string | null;
  stripe_payment_intent_id: string | null;
  arrived_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

function fmt(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function fmtDate(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString();
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start py-2.5 border-b border-zinc-800 last:border-0">
      <span className="text-zinc-500 text-sm">{label}</span>
      <span className="text-zinc-200 text-sm text-right max-w-xs font-mono">{value ?? "—"}</span>
    </div>
  );
}

export default function AppointmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [appt, setAppt] = useState<AppointmentDetail | null>(null);
  const [error, setError] = useState("");
  const [newStatus, setNewStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    getAppointment(id)
      .then((data: AppointmentDetail) => { setAppt(data); setNewStatus(data.status); })
      .catch(() => setError("Failed to load appointment."));
  }, [id]);

  async function handleForceStatus() {
    if (!appt || newStatus === appt.status) return;
    if (!confirm(`Force status to "${newStatus.replace(/_/g, " ")}"?`)) return;
    setSaving(true);
    setSaveMsg("");
    try {
      const updated = await forceAppointmentStatus(id, newStatus);
      setAppt(updated);
      setSaveMsg("Status updated.");
    } catch {
      setSaveMsg("Failed to update status.");
    } finally {
      setSaving(false);
    }
  }

  if (error) return <p className="text-red-400">{error}</p>;
  if (!appt) return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-32 rounded-xl bg-zinc-800 animate-pulse" />
      ))}
    </div>
  );

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => router.back()}
          className="text-zinc-400 hover:text-white text-sm transition-colors"
        >
          ← Back
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Appointment</h1>
          <p className="text-zinc-500 text-xs font-mono">{appt.id}</p>
        </div>
        <span className={`ml-auto inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${STATUS_COLORS[appt.status] ?? "bg-zinc-800 text-zinc-300 border-zinc-700"}`}>
          {appt.status.replace(/_/g, " ")}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Participants */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <h2 className="text-zinc-300 text-xs font-semibold uppercase tracking-wider mb-3">Participants</h2>
          <InfoRow label="Client" value={appt.client_email} />
          <InfoRow label="Detailer" value={appt.detailer_email} />
        </div>

        {/* Service & Pricing */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <h2 className="text-zinc-300 text-xs font-semibold uppercase tracking-wider mb-3">Service & Pricing</h2>
          <InfoRow label="Service" value={appt.service_name} />
          <InfoRow label="Estimated" value={fmt(appt.estimated_price)} />
          <InfoRow label="Actual" value={appt.actual_price != null ? fmt(appt.actual_price) : "—"} />
          <InfoRow label="Address" value={appt.service_address} />
        </div>
      </div>

      {/* Timeline */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 mb-4">
        <h2 className="text-zinc-300 text-xs font-semibold uppercase tracking-wider mb-3">Timeline</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Scheduled", value: fmtDate(appt.scheduled_time) },
            { label: "Arrived", value: fmtDate(appt.arrived_at) },
            { label: "Started", value: fmtDate(appt.started_at) },
            { label: "Completed", value: fmtDate(appt.completed_at) },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-zinc-500 text-xs mb-1">{label}</p>
              <p className="text-zinc-300 text-xs font-mono">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Notes */}
      {(appt.client_notes || appt.detailer_notes) && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 mb-4">
          <h2 className="text-zinc-300 text-xs font-semibold uppercase tracking-wider mb-3">Notes</h2>
          {appt.client_notes && (
            <div className="mb-2">
              <p className="text-zinc-500 text-xs mb-1">Client notes</p>
              <p className="text-zinc-300 text-sm">{appt.client_notes}</p>
            </div>
          )}
          {appt.detailer_notes && (
            <div>
              <p className="text-zinc-500 text-xs mb-1">Detailer notes</p>
              <p className="text-zinc-300 text-sm">{appt.detailer_notes}</p>
            </div>
          )}
        </div>
      )}

      {/* Stripe */}
      {appt.stripe_payment_intent_id && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 mb-4">
          <h2 className="text-zinc-300 text-xs font-semibold uppercase tracking-wider mb-3">Payment</h2>
          <InfoRow label="Stripe PI" value={appt.stripe_payment_intent_id} />
        </div>
      )}

      {/* Force Status */}
      <div className="rounded-xl border border-zinc-700 bg-zinc-900/40 p-4">
        <h2 className="text-zinc-300 text-xs font-semibold uppercase tracking-wider mb-3">Admin Override</h2>
        <div className="flex gap-3 items-center">
          <select
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-zinc-500"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
            ))}
          </select>
          <button
            onClick={handleForceStatus}
            disabled={saving || newStatus === appt.status}
            className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 transition-colors"
          >
            {saving ? "Saving…" : "Force status"}
          </button>
          {saveMsg && <p className="text-sm text-zinc-400">{saveMsg}</p>}
        </div>
      </div>
    </div>
  );
}
