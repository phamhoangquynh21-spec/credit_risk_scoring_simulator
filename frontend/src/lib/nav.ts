export type NavIcon =
  | "grid" | "search" | "rows" | "scale" | "bulb" | "gauge"
  | "shield" | "list" | "pulse" | "cog";

export type NavItem = { href: string; label: string; group: string; icon: NavIcon };

const BASE: NavItem[] = [
  { href: "/", label: "Executive overview", group: "Overview", icon: "grid" },
  { href: "/assess", label: "Assess applicant", group: "Assessment", icon: "search" },
  { href: "/portfolio", label: "Portfolio monitor", group: "Assessment", icon: "rows" },
  { href: "/fairness", label: "Fairness & responsible AI", group: "Governance", icon: "scale" },
  { href: "/explainability", label: "Explainability center", group: "Governance", icon: "bulb" },
  { href: "/performance", label: "Model performance", group: "Governance", icon: "gauge" },
];

const ADMIN: NavItem[] = [
  { href: "/governance", label: "Model governance", group: "Admin", icon: "shield" },
  { href: "/audit", label: "Audit trail", group: "Admin", icon: "list" },
  { href: "/system", label: "System health", group: "Admin", icon: "pulse" },
  { href: "/settings", label: "Settings", group: "Admin", icon: "cog" },
];

// Executives get the read-only analytical surfaces (overview + governance),
// not the applicant/portfolio data-entry views.
const EXECUTIVE_HREFS = new Set(["/", "/fairness", "/explainability", "/performance"]);

// Roles that see the admin section (model registry, audit trail, health, settings).
const ADMIN_ROLES = new Set(["admin", "compliance", "governance"]);

export function navForRole(role: string): NavItem[] {
  if (role === "executive") return BASE.filter((n) => EXECUTIVE_HREFS.has(n.href));
  return ADMIN_ROLES.has(role) ? [...BASE, ...ADMIN] : [...BASE];
}

export function navGroups(role: string): { group: string; items: NavItem[] }[] {
  const items = navForRole(role);
  const order: string[] = [];
  const byGroup = new Map<string, NavItem[]>();
  for (const item of items) {
    if (!byGroup.has(item.group)) { byGroup.set(item.group, []); order.push(item.group); }
    byGroup.get(item.group)!.push(item);
  }
  return order.map((group) => ({ group, items: byGroup.get(group)! }));
}
