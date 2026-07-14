import { navGroups } from "@/lib/nav";
import { signOut } from "@/app/login/actions";
import { BrandMark, SignOutIcon } from "./icons";
import { SidebarNav } from "./SidebarNav";

export function Sidebar({ role, name }: { role: string; name: string }) {
  const groups = navGroups(role);
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark" aria-hidden>
          <BrandMark />
        </div>
        <div>
          <div className="brand-name">Credit Risk</div>
          <div className="brand-sub">Scoring Simulator</div>
        </div>
      </div>
      <SidebarNav groups={groups} />
      <div className="sidebar-foot">
        <div className="role-card">
          <div className="eyebrow">Signed in as</div>
          <div className="role-name">{name}</div>
          <div className="role-meta">{role}</div>
        </div>
        <form action={signOut}>
          <button type="submit" className="sidebar-signout">
            <SignOutIcon />
            Sign out
          </button>
        </form>
      </div>
    </aside>
  );
}
