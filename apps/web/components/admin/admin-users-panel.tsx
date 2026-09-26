"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { AdminUserRead } from "@/lib/types";
import { ErrorState, LoadingState } from "@/components/ui/states";

function roleLabel(user: AdminUserRead) {
  if (user.is_supreme_admin) {
    return "Supreme admin";
  }
  if (user.is_admin) {
    return "Admin";
  }
  return "Customer";
}

export function AdminUsersPanel() {
  const { status, user, accessToken } = useAuth();
  const [users, setUsers] = useState<AdminUserRead[]>([]);
  const [search, setSearch] = useState("");
  const [promoteEmail, setPromoteEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [mutating, setMutating] = useState<string | null>(null);

  const loadUsers = useCallback(
    async (query: string) => {
      if (!accessToken || !user?.is_supreme_admin) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const page = await api.listAdminUsers(accessToken, query, 50, 0);
        setUsers(page.items);
        setError(null);
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : "Could not load users.");
      } finally {
        setLoading(false);
      }
    },
    [accessToken, user?.is_supreme_admin]
  );

  useEffect(() => {
    if (status === "checking") {
      return;
    }
    void loadUsers("");
  }, [loadUsers, status]);

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    await loadUsers(search);
  }

  async function promote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) {
      return;
    }
    const email = promoteEmail.trim();
    if (!email) {
      setError("Enter an email address to promote.");
      return;
    }
    setMutating("promote");
    setError(null);
    setNotice(null);
    try {
      const updated = await api.promoteAdminUser(accessToken, { email });
      setUsers((current) => {
        const exists = current.some((item) => item.id === updated.id);
        return exists ? current.map((item) => (item.id === updated.id ? updated : item)) : [updated, ...current];
      });
      setPromoteEmail("");
      setNotice(`${updated.email} is now a normal admin.`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not promote user.");
    } finally {
      setMutating(null);
    }
  }

  async function demote(target: AdminUserRead) {
    if (!accessToken) {
      return;
    }
    setMutating(target.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.demoteAdminUser(accessToken, target.id);
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setNotice(`${updated.email} is now a customer.`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not demote user.");
    } finally {
      setMutating(null);
    }
  }

  if (status === "checking" || loading) {
    return <LoadingState label="Checking supreme admin access..." />;
  }

  if (status !== "authenticated") {
    return (
      <section className="surface mx-auto max-w-2xl p-6">
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Login required</p>
        <h1 className="mt-2 text-3xl font-black">User management requires login</h1>
        <Link href="/login" className="mt-6 inline-flex bg-market-green px-5 py-3 text-sm font-bold text-white hover:bg-ink-900">
          Login
        </Link>
      </section>
    );
  }

  if (!user?.is_supreme_admin) {
    return <ErrorState title="Supreme admin required" message="Normal admins can manage store operations, but user access changes require a supreme admin." href="/account" action="Return to account" />;
  }

  return (
    <section className="surface mx-auto grid max-w-5xl gap-5 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-wide text-market-green">Supreme admin</p>
          <h1 className="mt-2 text-3xl font-black">User management</h1>
          <p className="mt-2 text-sm leading-6 text-ink-500">Promote customers to normal admin or demote normal admins back to customer access.</p>
        </div>
        <Link href="/admin/products/new" className="border border-ink-300 px-4 py-2 text-sm font-bold text-ink-900 hover:border-market-green hover:text-market-green">
          Admin Products
        </Link>
      </div>

      <form onSubmit={promote} className="grid gap-3 border border-ink-200 bg-ink-50 p-4 sm:grid-cols-[1fr_auto]">
        <label className="grid gap-2 text-sm font-semibold">
          Promote by email
          <input
            type="email"
            required
            value={promoteEmail}
            onChange={(event) => setPromoteEmail(event.target.value)}
            className="border border-ink-200 bg-white px-3 py-3 font-normal"
            placeholder="customer@example.com"
            disabled={mutating === "promote"}
          />
        </label>
        <button
          type="submit"
          disabled={mutating === "promote"}
          className="self-end bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60"
        >
          {mutating === "promote" ? "Promoting..." : "Promote"}
        </button>
      </form>

      <form onSubmit={submitSearch} className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <label className="grid gap-2 text-sm font-semibold">
          Search users
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="border border-ink-200 px-3 py-3 font-normal"
            placeholder="Name or email"
          />
        </label>
        <button type="submit" className="self-end border border-ink-900 px-5 py-3 text-sm font-bold text-ink-900 hover:bg-ink-900 hover:text-white">
          Search
        </button>
      </form>

      {error ? <p className="border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{error}</p> : null}
      {notice ? <p className="border border-market-green/30 bg-market-mint px-3 py-2 text-sm font-semibold text-ink-800">{notice}</p> : null}

      {users.length === 0 ? (
        <p className="border border-ink-200 bg-ink-50 px-3 py-2 text-sm font-semibold text-ink-600">No users found.</p>
      ) : (
        <div className="grid gap-3">
          {users.map((managedUser) => (
            <article key={managedUser.id} className="grid gap-4 border border-ink-200 p-4 sm:grid-cols-[1fr_auto] sm:items-center">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-base font-black">{managedUser.name}</h2>
                  <span className="border border-ink-200 px-2 py-1 text-xs font-bold uppercase text-ink-600">{roleLabel(managedUser)}</span>
                </div>
                <p className="mt-1 text-sm text-ink-500">{managedUser.email}</p>
              </div>
              <button
                type="button"
                onClick={() => void demote(managedUser)}
                disabled={!managedUser.is_admin || managedUser.is_supreme_admin || managedUser.id === user.id || mutating === managedUser.id}
                className="border border-market-red/40 px-4 py-2 text-sm font-bold text-market-red hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {mutating === managedUser.id ? "Updating..." : "Demote"}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
