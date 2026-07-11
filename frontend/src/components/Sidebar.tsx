import Link from "next/link";
import { navForRole } from "@/lib/nav";
import { signOut } from "@/app/login/actions";

export function Sidebar({ role, name }: { role: string; name: string }) {
  const items = navForRole(role);
  return (
    <aside className="flex w-56 flex-col border-r bg-gray-50 p-4">
      <div className="mb-6">
        <div className="text-sm font-semibold">Credit Risk</div>
        <div className="text-xs capitalize text-gray-500">{name} · {role}</div>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {items.map((n) => (
          <Link key={n.href} href={n.href}
            className="rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-200">
            {n.label}
          </Link>
        ))}
      </nav>
      <form action={signOut}>
        <button className="w-full rounded px-3 py-2 text-left text-sm text-gray-600 hover:bg-gray-200">
          Sign out
        </button>
      </form>
    </aside>
  );
}
