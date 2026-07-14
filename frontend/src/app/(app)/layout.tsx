import { redirect } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase/server";
import { Sidebar } from "@/components/Sidebar";
import { DisclaimerBar } from "@/components/DisclaimerBar";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  const { data: profile } = await supabase.from("profiles")
    .select("role, display_name").eq("user_id", user.id).single();
  const role = profile?.role ?? "analyst";
  const name = profile?.display_name ?? "User";
  return (
    <div className="app">
      <Sidebar role={role} name={name} />
      <div className="main">
        <div className="mobile-bar">
          <span className="brand-name">Credit Risk</span>
          <span className="eyebrow" style={{ color: "#8FA3C0" }}>Synthetic demo</span>
        </div>
        <DisclaimerBar />
        {children}
      </div>
    </div>
  );
}
