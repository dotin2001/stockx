"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { ApiError } from "@/lib/api";

type Mode = "login" | "signup";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const { login, signup } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setError(null);

    try {
      if (mode === "signup") {
        await signup({
          name: String(form.get("name") ?? ""),
          email: String(form.get("email") ?? ""),
          password: String(form.get("password") ?? "")
        });
      } else {
        await login({
          email: String(form.get("email") ?? ""),
          password: String(form.get("password") ?? "")
        });
      }
      router.push("/account");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const isSignup = mode === "signup";

  return (
    <form onSubmit={submit} className="surface mx-auto grid w-full max-w-md gap-5 p-6">
      <div>
        <h1 className="text-3xl font-black">{isSignup ? "Create your account" : "Log in"}</h1>
        <p className="mt-2 text-sm text-ink-500">
          {isSignup ? "Start watching products and creating listings." : "Restore your marketplace session."}
        </p>
      </div>
      {isSignup ? (
        <label className="grid gap-2 text-sm font-semibold">
          Name
          <input name="name" required minLength={1} className="border border-ink-200 px-3 py-3 font-normal" autoComplete="name" />
        </label>
      ) : null}
      <label className="grid gap-2 text-sm font-semibold">
        Email
        <input name="email" required type="email" className="border border-ink-200 px-3 py-3 font-normal" autoComplete="email" />
      </label>
      <label className="grid gap-2 text-sm font-semibold">
        Password
        <input name="password" required type="password" minLength={8} className="border border-ink-200 px-3 py-3 font-normal" autoComplete={isSignup ? "new-password" : "current-password"} />
      </label>
      {error ? <p className="border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{error}</p> : null}
      <button type="submit" disabled={submitting} className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">
        {submitting ? "Working..." : isSignup ? "Sign Up" : "Login"}
      </button>
      <p className="text-sm text-ink-500">
        {isSignup ? "Already have an account? " : "Need an account? "}
        <Link href={isSignup ? "/login" : "/signup"} className="font-bold text-ink-900 hover:text-market-green">
          {isSignup ? "Log in" : "Sign up"}
        </Link>
      </p>
    </form>
  );
}
