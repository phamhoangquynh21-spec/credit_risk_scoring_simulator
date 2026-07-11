"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { loginWithEmail } from "./actions";

const ROLES = ["analyst", "manager", "compliance", "executive"] as const;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function demo(role: string) {
    setError(null);
    const res = await fetch("/api/demo-login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    if (res.ok) router.push("/"); else setError("Demo login failed");
  }

  return (
    <main className="mx-auto max-w-md p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Credit Risk Platform</h1>
        <p className="text-sm text-gray-500">Decision-support demo — not a lending system.</p>
      </div>
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-gray-700">Explore as a demo user</h2>
        <div className="grid grid-cols-2 gap-2">
          {ROLES.map((r) => (
            <button key={r} onClick={() => demo(r)}
              className="rounded border px-3 py-2 text-sm capitalize hover:bg-gray-50">
              {r}
            </button>
          ))}
        </div>
      </section>
      <form action={async (fd) => { const r = await loginWithEmail(fd); if (r?.error) setError(r.error); }}
        className="space-y-3">
        <h2 className="text-sm font-medium text-gray-700">Or sign in</h2>
        <input name="email" type="email" placeholder="Email" required
          className="w-full rounded border px-3 py-2 text-sm" />
        <input name="password" type="password" placeholder="Password" required
          className="w-full rounded border px-3 py-2 text-sm" />
        <button type="submit" className="w-full rounded bg-blue-600 px-3 py-2 text-sm text-white">
          Sign in
        </button>
      </form>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    </main>
  );
}
