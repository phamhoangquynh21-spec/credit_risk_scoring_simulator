import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

async function probe(path: string) {
  const started = Date.now();
  try {
    const res = await fetch(`${process.env.ML_SERVICE_URL}${path}`, { cache: "no-store" });
    const latency = Date.now() - started;
    const body = res.headers.get("content-type")?.includes("application/json")
      ? await res.json()
      : { raw: (await res.text()).slice(0, 200) };
    return { ok: res.ok, status: res.status, latency, body };
  } catch (e) {
    return { ok: false, status: 0, latency: Date.now() - started, error: (e as Error).message };
  }
}

// Probes the ML service liveness/readiness endpoints. Keeps the ML base URL
// server-only; requires an authenticated session but no special role.
export async function GET() {
  const supabase = await createServerSupabase();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const [health, ready] = await Promise.all([probe("/health"), probe("/ready")]);
  return NextResponse.json({ health, ready });
}
