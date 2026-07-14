import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { callMl } from "@/lib/ml";

// Forwards a model-promotion request to the ML service
// (POST /api/v1/models/{semver}/promote). The ML service is governance-gated and
// independently refuses champion promotion without an approver, so this handler
// only relays the caller's JWT — it grants no privilege of its own.
export async function POST(request: Request) {
  const supabase = await createServerSupabase();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const { semver, to_stage } = await request.json();
  if (!semver || !to_stage) {
    return NextResponse.json({ error: "semver and to_stage are required" }, { status: 400 });
  }
  try {
    const out = await callMl(`/api/v1/models/${encodeURIComponent(semver)}/promote`, session.access_token, { to_stage });
    return NextResponse.json(out);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 502 });
  }
}
