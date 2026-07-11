import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { callMl } from "@/lib/ml";

export async function POST(request: Request) {
  const supabase = await createServerSupabase();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const applicant = await request.json();
  try {
    const out = await callMl("/api/v1/explain", session.access_token, applicant);
    return NextResponse.json(out);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 502 });
  }
}
