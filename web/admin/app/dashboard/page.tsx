"use client";

import { useEffect, useState } from "react";
import { getStats } from "@/lib/api";

interface Stats {
  total_users: number;
  active_users: number;
  total_detailers: number;
  total_clients: number;
  pending_verification: number;
  total_appointments: number;
  total_roles: number;
  total_permissions: number;
}

const CARDS = [
  { key: "total_users",          label: "Total Users",            color: "blue" },
  { key: "active_users",         label: "Active Users",           color: "green" },
  { key: "total_detailers",      label: "Detailers",              color: "purple" },
  { key: "total_clients",        label: "Clients",                color: "cyan" },
  { key: "pending_verification", label: "Pending Verification",   color: "yellow" },
  { key: "total_appointments",   label: "Total Appointments",     color: "orange" },
  { key: "total_roles",          label: "Roles",                  color: "gray" },
  { key: "total_permissions",    label: "Permissions",            color: "gray" },
] as const;

const COLOR_MAP: Record<string, string> = {
  blue:   "border-blue-800 bg-blue-950/30",
  green:  "border-green-800 bg-green-950/30",
  purple: "border-purple-800 bg-purple-950/30",
  cyan:   "border-cyan-800 bg-cyan-950/30",
  yellow: "border-yellow-800 bg-yellow-950/30",
  orange: "border-orange-800 bg-orange-950/30",
  gray:   "border-zinc-700 bg-zinc-800/30",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setError("Failed to load stats."));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Overview</h1>
      <p className="text-zinc-400 text-sm mb-8">Platform statistics</p>

      {error && (
        <p className="text-red-400 text-sm mb-4">{error}</p>
      )}

      {!stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {CARDS.map((c) => (
            <div key={c.key} className="h-24 rounded-xl bg-zinc-800 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {CARDS.map(({ key, label, color }) => (
            <div
              key={key}
              className={`rounded-xl border p-5 ${COLOR_MAP[color]}`}
            >
              <p className="text-zinc-400 text-xs font-medium uppercase tracking-wider">
                {label}
              </p>
              <p className="text-3xl font-bold text-white mt-2">
                {(stats[key] as number).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
