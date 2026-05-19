"use client";

import { useEffect, useState } from "react";
import { listPermissions, createPermission, deletePermission } from "@/lib/api";

interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  description: string | null;
}

export default function PermissionsPage() {
  const [perms, setPerms] = useState<Permission[]>([]);
  const [form, setForm] = useState({
    name: "", resource: "", action: "", description: "",
  });
  const [saving, setSaving] = useState(false);

  async function load() {
    const data = await listPermissions();
    setPerms(data);
  }

  useEffect(() => { load(); }, []);

  function handleFormChange(key: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
    // Auto-fill name from resource:action
    if (key === "resource" || key === "action") {
      const r = key === "resource" ? value : form.resource;
      const a = key === "action" ? value : form.action;
      if (r && a) setForm((prev) => ({ ...prev, [key]: value, name: `${a}:${r}` }));
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name || !form.resource || !form.action) return;
    setSaving(true);
    try {
      await createPermission({
        name: form.name.trim(),
        resource: form.resource.trim(),
        action: form.action.trim(),
        description: form.description.trim() || undefined,
      });
      setForm({ name: "", resource: "", action: "", description: "" });
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(perm: Permission) {
    if (!confirm(`Delete permission "${perm.name}"?`)) return;
    setSaving(true);
    try {
      await deletePermission(perm.id);
      await load();
    } finally {
      setSaving(false);
    }
  }

  const resources = [...new Set(perms.map((p) => p.resource))].sort();

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Permissions</h1>
      <p className="text-zinc-400 text-sm mb-6">
        {perms.length} permissions across {resources.length} resources
      </p>

      <div className="grid grid-cols-3 gap-6">
        {/* Permission catalog grouped by resource */}
        <div className="col-span-2 space-y-5">
          {resources.map((resource) => (
            <div key={resource}>
              <p className="text-zinc-400 text-xs uppercase tracking-wider font-medium mb-2">
                {resource}
              </p>
              <div className="rounded-xl border border-zinc-800 bg-zinc-900 divide-y divide-zinc-800">
                {perms
                  .filter((p) => p.resource === resource)
                  .map((perm) => (
                    <div key={perm.id} className="flex items-center justify-between px-4 py-3">
                      <div>
                        <p className="text-white font-mono text-sm">{perm.name}</p>
                        {perm.description && (
                          <p className="text-zinc-500 text-xs mt-0.5">{perm.description}</p>
                        )}
                      </div>
                      <button
                        onClick={() => handleDelete(perm)}
                        disabled={saving}
                        className="text-zinc-600 hover:text-red-400 text-xs transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>

        {/* Create permission form */}
        <div>
          <form
            onSubmit={handleCreate}
            className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-3"
          >
            <p className="text-white font-semibold text-sm">New permission</p>

            <div>
              <label className="text-zinc-400 text-xs mb-1 block">Resource</label>
              <input
                type="text"
                placeholder="e.g. users"
                value={form.resource}
                onChange={(e) => handleFormChange("resource", e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-white text-sm placeholder-zinc-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-zinc-400 text-xs mb-1 block">Action</label>
              <input
                type="text"
                placeholder="e.g. read"
                value={form.action}
                onChange={(e) => handleFormChange("action", e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-white text-sm placeholder-zinc-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-zinc-400 text-xs mb-1 block">Name (auto-filled)</label>
              <input
                type="text"
                placeholder="action:resource"
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-white text-sm font-mono placeholder-zinc-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-zinc-400 text-xs mb-1 block">Description</label>
              <input
                type="text"
                placeholder="Optional"
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-white text-sm placeholder-zinc-600 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={!form.name || !form.resource || !form.action || saving}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
            >
              Create permission
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
