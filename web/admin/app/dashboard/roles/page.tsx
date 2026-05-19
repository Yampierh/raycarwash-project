"use client";

import { useEffect, useState } from "react";
import {
  listRoles,
  listPermissions,
  createRole,
  deleteRole,
  assignPermissionToRole,
  revokePermissionFromRole,
} from "@/lib/api";

interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
}

interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Permission[];
}

export default function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [allPerms, setAllPerms] = useState<Permission[]>([]);
  const [selected, setSelected] = useState<Role | null>(null);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    const [r, p] = await Promise.all([listRoles(), listPermissions()]);
    setRoles(r);
    setAllPerms(p);
    if (selected) {
      setSelected(r.find((x: Role) => x.id === selected.id) ?? null);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSaving(true);
    try {
      await createRole({ name: newName.trim(), description: newDesc.trim() || undefined });
      setNewName("");
      setNewDesc("");
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(role: Role) {
    if (!confirm(`Delete role "${role.name}"?`)) return;
    setSaving(true);
    try {
      await deleteRole(role.id);
      if (selected?.id === role.id) setSelected(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function togglePerm(perm: Permission) {
    if (!selected) return;
    const has = selected.permissions.some((p) => p.id === perm.id);
    setSaving(true);
    try {
      if (has) {
        await revokePermissionFromRole(selected.id, perm.id);
      } else {
        await assignPermissionToRole(selected.id, perm.id);
      }
      await load();
    } finally {
      setSaving(false);
    }
  }

  const resources = [...new Set(allPerms.map((p) => p.resource))].sort();

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Roles</h1>
      <p className="text-zinc-400 text-sm mb-6">Manage roles and their permissions</p>

      <div className="grid grid-cols-3 gap-6">
        {/* Role list */}
        <div className="space-y-3">
          {roles.map((role) => (
            <div
              key={role.id}
              onClick={() => setSelected(role)}
              className={`rounded-xl border p-4 cursor-pointer transition-colors ${
                selected?.id === role.id
                  ? "border-blue-600 bg-blue-950/20"
                  : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-white font-medium text-sm">{role.name}</p>
                    {role.is_system && (
                      <span className="text-xs text-zinc-500 border border-zinc-700 rounded px-1.5 py-0.5">
                        system
                      </span>
                    )}
                  </div>
                  {role.description && (
                    <p className="text-zinc-500 text-xs mt-0.5 line-clamp-2">{role.description}</p>
                  )}
                  <p className="text-zinc-600 text-xs mt-1">
                    {role.permissions.length} permission{role.permissions.length !== 1 ? "s" : ""}
                  </p>
                </div>
                {!role.is_system && (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(role); }}
                    className="text-zinc-600 hover:text-red-400 text-xs transition-colors"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}

          {/* Create role form */}
          <form
            onSubmit={handleCreate}
            className="rounded-xl border border-dashed border-zinc-700 p-4 space-y-2"
          >
            <p className="text-zinc-400 text-xs font-medium uppercase tracking-wider">New role</p>
            <input
              type="text"
              placeholder="Role name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-white text-sm placeholder-zinc-600 focus:outline-none"
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-white text-sm placeholder-zinc-600 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!newName.trim() || saving}
              className="w-full py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded transition-colors"
            >
              Create
            </button>
          </form>
        </div>

        {/* Permission matrix */}
        <div className="col-span-2">
          {!selected ? (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center text-zinc-500 text-sm">
              Select a role to manage its permissions
            </div>
          ) : (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 space-y-5">
              <div className="flex items-center gap-2">
                <h2 className="text-white font-semibold">{selected.name}</h2>
                {selected.is_system && (
                  <span className="text-xs text-zinc-500 border border-zinc-700 rounded px-1.5 py-0.5">
                    system
                  </span>
                )}
              </div>

              {resources.map((resource) => {
                const perms = allPerms.filter((p) => p.resource === resource);
                return (
                  <div key={resource}>
                    <p className="text-zinc-400 text-xs uppercase tracking-wider font-medium mb-2">
                      {resource}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {perms.map((perm) => {
                        const assigned = selected.permissions.some((p) => p.id === perm.id);
                        return (
                          <button
                            key={perm.id}
                            onClick={() => togglePerm(perm)}
                            disabled={saving}
                            className={`px-3 py-1 rounded-lg text-xs font-mono transition-colors border ${
                              assigned
                                ? "bg-blue-900/60 text-blue-300 border-blue-700"
                                : "bg-zinc-800 text-zinc-500 border-zinc-700 hover:border-zinc-600"
                            }`}
                          >
                            {perm.action}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
