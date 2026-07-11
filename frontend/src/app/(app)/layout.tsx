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
  return (
    <div className="flex h-screen">
      <Sidebar role={role} name={profile?.display_name ?? "User"} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <DisclaimerBar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
