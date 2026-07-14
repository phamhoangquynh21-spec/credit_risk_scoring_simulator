"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavItem } from "@/lib/nav";
import { NavGlyph } from "./icons";

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SidebarNav({ groups }: { groups: { group: string; items: NavItem[] }[] }) {
  const pathname = usePathname() ?? "/";
  return (
    <nav className="nav" aria-label="Primary">
      {groups.map((g) => (
        <div key={g.group}>
          <div className="nav-group">{g.group}</div>
          {g.items.map((n) => {
            const active = isActive(pathname, n.href);
            return (
              <Link
                key={n.href}
                href={n.href}
                className={active ? "active" : undefined}
                aria-current={active ? "page" : undefined}
              >
                <NavGlyph name={n.icon} />
                {n.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
