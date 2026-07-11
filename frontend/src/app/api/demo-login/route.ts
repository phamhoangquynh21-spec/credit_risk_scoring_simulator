import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

const ROLES = ["analyst", "manager", "compliance", "executive"] as const;

export async function POST(request: Request) {
  const { role } = await request.json();
  if (!ROLES.includes(role)) {
    return NextResponse.json({ error: "unknown role" }, { status: 400 });
  }
  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signInWithPassword({
    email: `demo-${role}@demo.local`,
    password: process.env.DEMO_PASSWORD!,
  });
  if (error) return NextResponse.json({ error: error.message }, { status: 401 });
  return NextResponse.json({ ok: true });
}
