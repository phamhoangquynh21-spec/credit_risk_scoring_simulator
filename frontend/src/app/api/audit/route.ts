import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { callMlGet } from "@/lib/ml";

// Forwards the caller's Supabase JWT to the ML service audit export
// (GET /api/v1/audit/events). The ML service enforces the governance/compliance
// role; a non-privileged caller receives its 403 verbatim.
export async function GET() {
  const supabase = await createServerSupabase();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  try {
    const out = await callMlGet("/api/v1/audit/events?limit=100", session.access_token);
    return NextResponse.json(out);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 502 });
  }
}
