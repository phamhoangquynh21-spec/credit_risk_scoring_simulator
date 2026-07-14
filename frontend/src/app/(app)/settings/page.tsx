import { createServerSupabase } from "@/lib/supabase/server";
import { PageHeader } from "@/components/PageHeader";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  const { data: profile } = user
    ? await supabase.from("profiles").select("display_name, role").eq("user_id", user.id).maybeSingle()
    : { data: null };

  return (
    <>
      <PageHeader eyebrow="Admin" title="Settings" subtitle="Your profile and workspace preferences." />
      <div className="content">
        <div className="card" style={{ maxWidth: 560 }}>
          <div className="card-head"><h2>Profile</h2><span className="hint">Read-only</span></div>
          <div className="card-body">
            <dl style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", margin: 0 }}>
              <Field k="Name" v={profile?.display_name ?? "—"} />
              <Field k="Role" v={profile?.role ?? "—"} />
              <Field k="Email" v={user?.email ?? "—"} mono />
            </dl>
            <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-4)" }}>
              Theme follows your system preference and can be toggled from the header on any screen. Editable
              account settings are a future release.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

function Field({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <dt className="eyebrow">{k}</dt>
      <dd className={mono ? "mono" : undefined} style={{ margin: "2px 0 0", fontSize: "var(--text-sm)", color: "var(--color-text)", textTransform: mono ? "none" : "capitalize" }}>{v}</dd>
    </div>
  );
}
