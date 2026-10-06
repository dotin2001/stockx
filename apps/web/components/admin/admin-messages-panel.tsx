"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { CustomerMessageRead } from "@/lib/types";
import { ErrorState, LoadingState } from "@/components/ui/states";

export function AdminMessagesPanel() {
  const { status, user, accessToken } = useAuth();
  const [messages, setMessages] = useState<CustomerMessageRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutating, setMutating] = useState<string | null>(null);

  useEffect(() => {
    if (status === "checking") {
      return;
    }
    if (status !== "authenticated" || !user?.is_admin || !accessToken) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    api
      .listAdminCustomerMessages(accessToken)
      .then((page) => {
        if (active) {
          setMessages(page.items);
          setError(null);
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof ApiError ? caught.message : "Could not load customer messages.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [accessToken, status, user?.is_admin]);

  async function markRead(message: CustomerMessageRead) {
    if (!accessToken) {
      return;
    }
    setMutating(message.id);
    try {
      const updated = await api.markAdminCustomerMessageRead(accessToken, message.id);
      setMessages((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not update message.");
    } finally {
      setMutating(null);
    }
  }

  if (status === "checking" || loading) {
    return <LoadingState label="Loading customer messages..." />;
  }

  if (status !== "authenticated") {
    return (
      <section className="surface mx-auto max-w-2xl p-6">
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Login required</p>
        <h1 className="mt-2 text-3xl font-black">Admin messages require login</h1>
        <Link href="/login" className="mt-6 inline-flex bg-market-green px-5 py-3 text-sm font-bold text-white hover:bg-ink-900">
          Login
        </Link>
      </section>
    );
  }

  if (!user?.is_admin) {
    return <ErrorState title="Admin required" message="Customer messages are only visible to store admins." href="/account" action="Return to account" />;
  }

  if (error) {
    return <ErrorState title="Could not load messages" message={error} href="/admin/messages" action="Try again" />;
  }

  return (
    <section className="surface mx-auto grid max-w-4xl gap-5 p-6">
      <div>
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Admin Messages</p>
        <h1 className="mt-2 text-3xl font-black">Customer messages</h1>
      </div>
      {messages.length === 0 ? (
        <p className="border border-ink-200 bg-ink-50 px-3 py-2 text-sm font-semibold text-ink-600">No customer messages yet.</p>
      ) : (
        <div className="grid gap-3">
          {messages.map((message) => (
            <article key={message.id} className="border border-ink-200 p-4 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-black">{message.subject}</h2>
                  <p className="mt-1 text-ink-500">
                    {message.sender_name} - {message.sender_email}
                  </p>
                </div>
                <span className="border border-ink-200 px-2 py-1 text-xs font-bold uppercase text-ink-600">{message.is_read ? "Read" : "Unread"}</span>
              </div>
              <p className="mt-3 leading-6 text-ink-700">{message.body}</p>
              {!message.is_read ? (
                <button
                  type="button"
                  onClick={() => void markRead(message)}
                  disabled={mutating === message.id}
                  className="mt-4 bg-ink-900 px-4 py-2 text-xs font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {mutating === message.id ? "Updating..." : "Mark Read"}
                </button>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
