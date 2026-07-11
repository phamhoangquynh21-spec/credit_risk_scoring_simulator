export type NavItem = { href: string; label: string };

const ALL: NavItem[] = [
  { href: "/assess", label: "Single Applicant" },
  { href: "/portfolio", label: "Portfolio Monitor" },
  { href: "/performance", label: "Model Performance" },
];

export function navForRole(role: string): NavItem[] {
  if (role === "executive") return ALL.filter((n) => n.href === "/performance");
  return ALL;
}
