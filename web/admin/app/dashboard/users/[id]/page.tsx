"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getUser, listRoles, assignRole, revokeRole, updateUser } from "@/lib/api";

interface Role {
  id: string;
  name: string;
  is_system: boolean;
  permissions: { id: string; name: string }[];
}

interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  onboarding_status: string;
  roles: string[];
  permissions: string[];
  created_at: string;
}

const ROLE_COLORS: Record<string, string> = {
  admin:    "bg-red-900/60 text-red-300 border-red-800",
  detailer: "bg-blue-900/60 text-blue-300 border-blue-800",
  client:   "bg-green-900/60 text-green-300 border-green-800",
};

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [allRoles, setAllRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function fetchUser() {
    try {
      const data = await getUser(id);
      setUser(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchUser();
    listRoles().then(setAllRoles);
  }, [id]);

  async function handleAssignRole() {
    if (!selectedRole) return;
    setSaving(true);
    try {
      await assignRole(id, selectedRole);
      await fetchUser();
      setSelectedRole("");
    } finally {
      setSaving(false);
    }
  }

  async function handleRevokeRole(roleId: string) {
    setSaving(true);
    try {
      await revokeRole(id, roleId);
      await fetchUser();
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive() {
    if (!user) return;
    setSaving(true);
    try {
      await updateUser(id, { is_active: !user.is_active });
      await fetchUser();
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-zinc-800 rounded w-48" />
        <div className="h-40 bg-zinc-800 rounded-xl" />
      </div>
    );
  }

  if (!user) return <p className="text-red-400">User not found.</p>;

  const assignableRoles = allRoles.filter((r) => !user.roles.includes(r.name));
  const userRoleObjects = allRoles.filter((r) => user.roles.includes(r.name));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="text-zinc-400 hover:text-white text-sm"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-white">{user.email}</h1>
      </div>

      {/* User info card */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 grid grid-cols-2 gap-4">
        <Info label="Full name" value={user.full_name ?? "—"} />
        <Info label="Status">
          <button
            onClick={toggleActive}
            disabled={saving}
            className={`px-3 py-0.5 rounded-full text-xs font-medium border ${
              user.is_active
                ? "bg-green-900/60 text-green-300 border-green-800"
                : "bg-zinc-700 text-zinc-400 border-zinc-600"
            } cursor-pointer hover:opacity-80 transition-opacity`}
          >
            {user.is_active ? "Active" : "Inactive"}
          </button>
        </Info>
        <Info label="Email verified" value={user.is_verified ? "Yes" : "No"} />
        <Info label="Onboarding" value={user.onboarding_status} />
        <Info label="Member since" value={new Date(user.created_at).toLocaleDateString()} />
      </div>

      {/* Roles */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-4">Roles</h2>

        <div className="flex flex-wrap gap-2 mb-4">
          {userRoleObjects.map((role) => (
            <span
              key={role.id}
              className={`flex items-center gap-2 pl-3 pr-2 py-1 rounded-full text-xs font-medium border ${
                ROLE_COLORS[role.name] ?? "bg-zinc-700 text-zinc-300 border-zinc-600"
              }`}
            >
              {role.name}
              <button
                onClick={() => handleRevokeRole(role.id)}
                disabled={saving}
                className="hover:text-white opacity-60 hover:opacity-100 transition-opacity"
                title="Revoke role"
              >
                ×
              </button>
            </span>
          ))}
        </div>

        {assignableRoles.length > 0 && (
          <div className="flex gap-2">
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none"
            >
              <option value="">Assign role…</option>
              {assignableRoles.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
            <button
              onClick={handleAssignRole}
              disabled={!selectedRole || saving}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
            >
              Assign
            </button>
          </div>
        )}
      </div>

      {/* Effective permissions */}
      {user.permissions.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4">
            Effective Permissions ({user.permissions.length})
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {user.permissions.sort().map((p) => (
              <span
                key={p}
                className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-xs text-zinc-300 font-mono"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Info({
  label,
  value,
  children,
}: {
  label: string;
  value?: string;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-zinc-500 text-xs uppercase tracking-wider mb-1">{label}</p>
      {children ?? <p className="text-white text-sm">{value}</p>}
    </div>
  );
}
