export type NavIcon =
  | "grid" | "search" | "rows" | "scale" | "bulb" | "gauge";

export type NavItem = { href: string; label: string; group: string; icon: NavIcon };

const ALL: NavItem[] = [
  { href: "/", label: "Executive overview", group: "Overview", icon: "grid" },
  { href: "/assess", label: "Assess applicant", group: "Assessment", icon: "search" },
  { href: "/portfolio", label: "Portfolio monitor", group: "Assessment", icon: "rows" },
  { href: "/fairness", label: "Fairness & responsible AI", group: "Governance", icon: "scale" },
  { href: "/explainability", label: "Explainability center", group: "Governance", icon: "bulb" },
  { href: "/performance", label: "Model performance", group: "Governance", icon: "gauge" },
];

// Executives get the read-only analytical surfaces (overview + governance),
// not the applicant/portfolio data-entry views.
const EXECUTIVE_HREFS = new Set(["/", "/fairness", "/explainability", "/performance"]);

export function navForRole(role: string): NavItem[] {
  if (role === "executive") return ALL.filter((n) => EXECUTIVE_HREFS.has(n.href));
  return ALL;
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
