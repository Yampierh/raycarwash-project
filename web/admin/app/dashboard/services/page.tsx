"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Service {
  id: string;
  name: string;
  description: string | null;
  category: string;
  base_price_cents: number;
  base_duration_minutes: number;
  price_small: number;
  price_medium: number;
  price_large: number;
  price_xl: number;
  is_active: boolean;
  created_at: string;
}

interface Addon {
  id: string;
  name: string;
  description: string | null;
  price_cents: number;
  duration_minutes: number;
  is_active: boolean;
  created_at: string;
}

type Tab = "services" | "addons";

const CATEGORY_COLORS: Record<string, string> = {
  basic_wash:       "bg-blue-900/40 text-blue-300 border-blue-800",
  interior_detail:  "bg-teal-900/40 text-teal-300 border-teal-800",
  full_detail:      "bg-green-900/40 text-green-300 border-green-800",
  ceramic_coating:  "bg-purple-900/40 text-purple-300 border-purple-800",
  paint_correction: "bg-orange-900/40 text-orange-300 border-orange-800",
};

function fmt(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function categoryLabel(cat: string) {
  return cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ServicesPage() {
  const [tab, setTab] = useState<Tab>("services");
  const [services, setServices] = useState<Service[]>([]);
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  function loadServices() {
    setLoading(true);
    setError("");
    api
      .get("/api/v1/services")
      .then((res) => setServices(res.data))
      .catch(() => setError("Failed to load services."))
      .finally(() => setLoading(false));
  }

  function loadAddons() {
    setLoading(true);
    setError("");
    api
      .get("/api/v1/addons")
      .then((res) => setAddons(res.data))
      .catch(() => setError("Failed to load addons."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (tab === "services") loadServices();
    else loadAddons();
  }, [tab]);

  async function toggleService(id: string, current: boolean) {
    setActionMsg("");
    try {
      await api.patch(`/api/v1/admin/services/${id}`, { is_active: !current });
      setActionMsg("Service updated.");
      loadServices();
    } catch {
      setActionMsg("Toggle requires admin service endpoint (not yet implemented on backend).");
    }
  }

  async function toggleAddon(id: string, current: boolean) {
    setActionMsg("");
    try {
      await api.patch(`/api/v1/admin/addons/${id}`, { is_active: !current });
      setActionMsg("Addon updated.");
      loadAddons();
    } catch {
      setActionMsg("Toggle requires admin addon endpoint (not yet implemented on backend).");
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Services & Addons</h1>
          <p className="text-zinc-400 text-sm">Platform service catalog management</p>
        </div>
      </div>

      <div className="flex gap-1 mb-6 bg-zinc-800/50 p-1 rounded-lg w-fit">
        {(["services", "addons"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
              tab === t ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {actionMsg && (
        <p className="text-zinc-400 text-sm mb-4 rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2">
          {actionMsg}
        </p>
      )}
      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {/* Services tab */}
      {tab === "services" && (
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-800/60">
              <tr>
                <th className="text-left text-zinc-400 font-medium px-4 py-3">Name</th>
                <th className="text-left text-zinc-400 font-medium px-4 py-3">Category</th>
                <th className="text-right text-zinc-400 font-medium px-4 py-3">Base Price</th>
                <th className="text-right text-zinc-400 font-medium px-4 py-3">S / M / L / XL</th>
                <th className="text-left text-zinc-400 font-medium px-4 py-3">Status</th>
                <th className="text-right text-zinc-400 font-medium px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {loading &&
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))}
              {!loading &&
                services.map((s) => (
                  <tr key={s.id} className="hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-zinc-200 font-medium">{s.name}</p>
                      {s.description && (
                        <p className="text-zinc-500 text-xs mt-0.5 max-w-xs truncate">
                          {s.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                          CATEGORY_COLORS[s.category] ?? "bg-zinc-800 text-zinc-300 border-zinc-700"
                        }`}
                      >
                        {categoryLabel(s.category)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-300 font-mono text-xs">
                      {fmt(s.base_price_cents)}
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-400 font-mono text-xs">
                      {fmt(s.price_small)} / {fmt(s.price_medium)} / {fmt(s.price_large)} / {fmt(s.price_xl)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                          s.is_active
                            ? "bg-green-900/40 text-green-300 border-green-800"
                            : "bg-zinc-800 text-zinc-500 border-zinc-700"
                        }`}
                      >
                        {s.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => toggleService(s.id, s.is_active)}
                        className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
                          s.is_active
                            ? "bg-zinc-800 text-zinc-300 border-zinc-700 hover:bg-red-900/40 hover:text-red-300 hover:border-red-800"
                            : "bg-zinc-800 text-zinc-300 border-zinc-700 hover:bg-green-900/40 hover:text-green-300 hover:border-green-800"
                        }`}
                      >
                        {s.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              {!loading && services.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-zinc-500">
                    No services found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Addons tab */}
      {tab === "addons" && (
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-zinc-800/60">
              <tr>
                <th className="text-left text-zinc-400 font-medium px-4 py-3">Name</th>
                <th className="text-right text-zinc-400 font-medium px-4 py-3">Price</th>
                <th className="text-right text-zinc-400 font-medium px-4 py-3">Duration (min)</th>
                <th className="text-left text-zinc-400 font-medium px-4 py-3">Status</th>
                <th className="text-right text-zinc-400 font-medium px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {loading &&
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 5 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))}
              {!loading &&
                addons.map((a) => (
                  <tr key={a.id} className="hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-zinc-200 font-medium">{a.name}</p>
                      {a.description && (
                        <p className="text-zinc-500 text-xs mt-0.5 max-w-xs truncate">
                          {a.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-300 font-mono text-xs">
                      {fmt(a.price_cents)}
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-400 text-xs">
                      {a.duration_minutes} min
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                          a.is_active
                            ? "bg-green-900/40 text-green-300 border-green-800"
                            : "bg-zinc-800 text-zinc-500 border-zinc-700"
                        }`}
                      >
                        {a.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => toggleAddon(a.id, a.is_active)}
                        className={`px-3 py-1 text-xs rounded-lg border transition-colors ${
                          a.is_active
                            ? "bg-zinc-800 text-zinc-300 border-zinc-700 hover:bg-red-900/40 hover:text-red-300 hover:border-red-800"
                            : "bg-zinc-800 text-zinc-300 border-zinc-700 hover:bg-green-900/40 hover:text-green-300 hover:border-green-800"
                        }`}
                      >
                        {a.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              {!loading && addons.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                    No addons found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
