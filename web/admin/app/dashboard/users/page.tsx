"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listUsers, listRoles, updateUser } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  onboarding_status: string;
  roles: string[];
  created_at: string;
}

const ROLE_COLORS: Record<string, string> = {
  admin:    "bg-red-900/60 text-red-300 border-red-800",
  detailer: "bg-blue-900/60 text-blue-300 border-blue-800",
  client:   "bg-green-900/60 text-green-300 border-green-800",
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [roles, setRoles] = useState<{ name: string }[]>([]);
  const [loading, setLoading] = useState(true);

  const perPage = 20;

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listUsers({
        page,
        per_page: perPage,
        search: search || undefined,
        role: roleFilter || undefined,
      });
      setUsers(data.users);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [page, search, roleFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  useEffect(() => {
    listRoles().then(setRoles);
  }, []);

  async function toggleActive(user: User) {
    await updateUser(user.id, { is_active: !user.is_active });
    fetchUsers();
  }

  const pages = Math.ceil(total / perPage);

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-1">Users</h1>
      <p className="text-zinc-400 text-sm mb-6">
        {total.toLocaleString()} total users
      </p>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <input
          type="search"
          placeholder="Search by email…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm w-64 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none"
        >
          <option value="">All roles</option>
          {roles.map((r) => (
            <option key={r.name} value={r.name}>{r.name}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800/50">
            <tr>
              {["Email", "Name", "Roles", "Status", "Verified", "Created", ""].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-zinc-400 font-medium text-xs uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-zinc-800 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 text-white font-mono text-xs">{user.email}</td>
                  <td className="px-4 py-3 text-zinc-300">{user.full_name ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {user.roles.map((r) => (
                        <span
                          key={r}
                          className={`px-2 py-0.5 rounded-full text-xs font-medium border ${ROLE_COLORS[r] ?? "bg-zinc-700 text-zinc-300 border-zinc-600"}`}
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleActive(user)}
                      className={`px-2 py-0.5 rounded-full text-xs font-medium border cursor-pointer transition-opacity hover:opacity-80 ${
                        user.is_active
                          ? "bg-green-900/60 text-green-300 border-green-800"
                          : "bg-zinc-700 text-zinc-400 border-zinc-600"
                      }`}
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs ${user.is_verified ? "text-green-400" : "text-zinc-500"}`}>
                      {user.is_verified ? "✓" : "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/dashboard/users/${user.id}`}
                      className="text-blue-400 hover:text-blue-300 text-xs"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-zinc-500 text-sm">
            Page {page} of {pages}
          </p>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 bg-zinc-800 border border-zinc-700 rounded text-sm text-white disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 bg-zinc-800 border border-zinc-700 rounded text-sm text-white disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
