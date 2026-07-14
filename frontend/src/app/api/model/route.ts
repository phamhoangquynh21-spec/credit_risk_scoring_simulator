import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { callMlGet } from "@/lib/ml";

// Forwards the caller's Supabase JWT to the ML service's champion model card
// (GET /api/v1/models/current). Keeps the ML base URL server-only.
export async function GET() {
  const supabase = await createServerSupabase();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  try {
    const out = await callMlGet("/api/v1/models/current", session.access_token);
    return NextResponse.json(out);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 502 });
  }
}
