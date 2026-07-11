# R1 Plan 3/3 — Next.js Frontend Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A deployable Next.js dashboard (auth + 3 sections) that lets a signed-in user score a single applicant, monitor the real-UCI demo portfolio, and view model performance — reading Supabase directly for data and proxying to the FastAPI ML service for scoring.

**Architecture:** Next.js 15 App Router (TypeScript) in `frontend/`. Supabase Auth via `@supabase/ssr` (server + browser clients; RLS enforces per-user isolation). Sections 3 & 6 are server components reading Supabase with the user's session. Section 2 posts to Next.js **route handlers** (`/api/predict`, `/api/explain`) that forward the user's JWT to the Python ML service at `ML_SERVICE_URL` — the browser never calls the ML service or Supabase service role directly. Tests use Vitest + Testing Library (jsdom).

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, Recharts, `@supabase/ssr`, `@supabase/supabase-js`, Vitest, `@testing-library/react`, jsdom.

## Global Constraints

- **Node is portable and NOT on PATH.** Every shell command that runs node/npm/npx MUST first: `export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"`. Node v24.18.0, npm 11.16.0.
- All frontend code lives under `frontend/`. Do NOT modify `src/`, `services/`, or `supabase/`.
- **Never expose secrets to the browser.** Only `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` may be public. `ML_SERVICE_URL` and any service key are server-only (no `NEXT_PUBLIC_` prefix).
- Supabase project: url `https://uiormpweobimumzlxjml.supabase.co`, anon key is in the repo root `.env` (copy the two public values into `frontend/.env.local`). RLS is already live (Plan 1) — the frontend relies on it; never use the service-role key in the frontend.
- The ML service contract (Plan 2): `POST /api/v1/predict` and `POST /api/v1/explain` accept the 23-field raw UCI **Applicant** JSON (snake_case: `limit_bal, sex, education, marriage, age, pay_0, pay_2..pay_6, bill_amt1..6, pay_amt1..6`) with a `Authorization: Bearer <supabase_jwt>` header. `/predict` returns `{prediction_id, probability, risk_score, risk_band, model_version, top_factors?}`; `/explain` returns `{factors:[{feature,friendly,contribution,direction}], ...}`. Confirm exact response shape against `services/ml/schemas.py` (PredictResponse, ExplainResponse) while implementing.
- **Every scoring surface shows: model version, "decision-support only — not a lending decision" disclaimer, and separates the model output from any human action.** (Spec §7, §10.)
- Risk band colors: Low=green, Medium=amber, High=red; always paired with the text label (never color-only). WCAG AA.
- Demo accounts (Plan 1 seed): `demo-analyst@demo.local` / `demo-manager@demo.local` / `demo-compliance@demo.local` / `demo-executive@demo.local`, password = the repo `.env` `DEMO_PASSWORD`. Put it in `frontend/.env.local` as `DEMO_PASSWORD` (server-only) for the one-click demo login route.
- Commits: conventional `type(scope): message`, one per task minimum. Branch `feat/r1-plan3-frontend` is already checked out.
- Run the app for manual checks with `npm run dev` (port 3000). Run tests with `npm run test` (Vitest, non-watch).

**Prerequisite files the implementer must create early:** `frontend/.env.local` (gitignored by the Next scaffold) holding `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (copy from repo `.env`), `ML_SERVICE_URL=http://localhost:8000`, `DEMO_PASSWORD` (copy from repo `.env`).

---

### Task 1: Scaffold Next.js app + Vitest

**Files:**
- Create: `frontend/` (via create-next-app), `frontend/vitest.config.ts`, `frontend/vitest.setup.ts`, `frontend/src/lib/format.ts`, `frontend/src/lib/format.test.ts`
- Modify: `frontend/package.json` (add test script)

**Interfaces:**
- Produces: `riskBand(score:number): "Low"|"Medium"|"High"` and `bandColor(band:string): string` in `src/lib/format.ts`, used by every section.

- [ ] **Step 1: Scaffold the app** (non-interactive)

```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator"
npx --yes create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-turbopack --use-npm
```
Expected: `Success! Created frontend at ...`.

- [ ] **Step 2: Install test + data deps**

```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator/frontend"
npm install @supabase/ssr @supabase/supabase-js recharts
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
```
Expected: installs succeed.

- [ ] **Step 3: Add Vitest config**

Create `frontend/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"], globals: true },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
```
Create `frontend/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```
Add to `frontend/package.json` "scripts": `"test": "vitest run"`.

- [ ] **Step 4: Write the failing test** — `frontend/src/lib/format.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { riskBand, bandColor } from "./format";

describe("riskBand", () => {
  it("maps scores to bands", () => {
    expect(riskBand(10)).toBe("Low");
    expect(riskBand(50)).toBe("Medium");
    expect(riskBand(80)).toBe("High");
  });
  it("gives each band a distinct color", () => {
    expect(bandColor("Low")).not.toBe(bandColor("High"));
  });
});
```

- [ ] **Step 5: Run it, expect FAIL**

```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator/frontend" && npm run test
```
Expected: FAIL (Cannot find module './format').

- [ ] **Step 6: Implement** — `frontend/src/lib/format.ts`:
```ts
export type Band = "Low" | "Medium" | "High";

export function riskBand(score: number): Band {
  if (score < 33) return "Low";
  if (score < 66) return "Medium";
  return "High";
}

export function bandColor(band: string): string {
  return band === "Low" ? "#16a34a" : band === "Medium" ? "#d97706" : "#dc2626";
}
```

- [ ] **Step 7: Run tests, expect PASS.** Then verify the app builds:
```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator/frontend" && npm run test && npm run build
```
Expected: 2 tests pass; `npm run build` succeeds (Compiled successfully).

- [ ] **Step 8: Ensure `.env.local` is gitignored** (create-next-app adds `.env*` to `frontend/.gitignore` — verify `git check-ignore frontend/.env.local` prints the path). Create `frontend/.env.local` per the Global Constraints prerequisite. Create `frontend/.env.example` (committed) listing the 4 var names with placeholder values.

- [ ] **Step 9: Commit**
```bash
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator"
git add frontend/ && git reset frontend/.env.local
git commit -m "feat(frontend): scaffold Next.js app + Vitest + risk-band helpers"
```

---

### Task 2: Supabase browser + server clients

**Files:**
- Create: `frontend/src/lib/supabase/client.ts`, `frontend/src/lib/supabase/server.ts`, `frontend/src/lib/supabase/client.test.ts`

**Interfaces:**
- Consumes: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Produces: `createBrowserSupabase()` (client components) and `createServerSupabase()` (async, server components/route handlers — reads cookies). Used by auth + all sections.

- [ ] **Step 1: Write the failing test** — `frontend/src/lib/supabase/client.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://x.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon-key");
});

describe("createBrowserSupabase", () => {
  it("returns a client with auth + from()", async () => {
    const { createBrowserSupabase } = await import("./client");
    const sb = createBrowserSupabase();
    expect(sb.auth).toBeDefined();
    expect(typeof sb.from).toBe("function");
  });
});
```

- [ ] **Step 2: Run it, expect FAIL** (`npm run test -- client.test`).

- [ ] **Step 3: Implement** — `frontend/src/lib/supabase/client.ts`:
```ts
import { createBrowserClient } from "@supabase/ssr";

export function createBrowserSupabase() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
```
`frontend/src/lib/supabase/server.ts`:
```ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createServerSupabase() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (list) => {
          try {
            list.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options));
          } catch {
            // called from a Server Component — safe to ignore; middleware refreshes
          }
        },
      },
    },
  );
}
```

- [ ] **Step 4: Run tests, expect PASS.**

- [ ] **Step 5: Commit**
```bash
git add frontend/src/lib/supabase
git commit -m "feat(frontend): Supabase browser + server clients (@supabase/ssr)"
```

---

### Task 3: Auth — middleware, login (demo + email), sign-out

**Files:**
- Create: `frontend/src/middleware.ts`, `frontend/src/app/login/page.tsx`, `frontend/src/app/login/actions.ts`, `frontend/src/app/api/demo-login/route.ts`, `frontend/src/app/login/actions.test.ts`

**Interfaces:**
- Consumes: `createServerSupabase()`, `DEMO_PASSWORD` (server env).
- Produces: session cookies; a signed-in user is redirected from `/login` to `/`. `POST /api/demo-login` with `{role}` signs in the matching `demo-<role>@demo.local`.

- [ ] **Step 1: Middleware** — `frontend/src/middleware.ts` (refreshes the session and gates the app):
```ts
import { type NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (list) => {
          list.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          list.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options));
        },
      },
    },
  );
  const { data: { user } } = await supabase.auth.getUser();
  const isLogin = request.nextUrl.pathname.startsWith("/login");
  const isPublic = isLogin || request.nextUrl.pathname.startsWith("/api/demo-login");
  if (!user && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (user && isLogin) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.png$).*)"],
};
```

- [ ] **Step 2: Email login server action** — `frontend/src/app/login/actions.ts`:
```ts
"use server";
import { createServerSupabase } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export async function loginWithEmail(formData: FormData) {
  const email = String(formData.get("email"));
  const password = String(formData.get("password"));
  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: error.message };
  redirect("/");
}

export async function signOut() {
  const supabase = await createServerSupabase();
  await supabase.auth.signOut();
  redirect("/login");
}
```

- [ ] **Step 3: Demo-login route** — `frontend/src/app/api/demo-login/route.ts`:
```ts
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
```

- [ ] **Step 4: Login page** — `frontend/src/app/login/page.tsx`:
```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { loginWithEmail } from "./actions";

const ROLES = ["analyst", "manager", "compliance", "executive"] as const;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function demo(role: string) {
    setError(null);
    const res = await fetch("/api/demo-login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    if (res.ok) router.push("/"); else setError("Demo login failed");
  }

  return (
    <main className="mx-auto max-w-md p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Credit Risk Platform</h1>
        <p className="text-sm text-gray-500">Decision-support demo — not a lending system.</p>
      </div>
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-gray-700">Explore as a demo user</h2>
        <div className="grid grid-cols-2 gap-2">
          {ROLES.map((r) => (
            <button key={r} onClick={() => demo(r)}
              className="rounded border px-3 py-2 text-sm capitalize hover:bg-gray-50">
              {r}
            </button>
          ))}
        </div>
      </section>
      <form action={async (fd) => { const r = await loginWithEmail(fd); if (r?.error) setError(r.error); }}
        className="space-y-3">
        <h2 className="text-sm font-medium text-gray-700">Or sign in</h2>
        <input name="email" type="email" placeholder="Email" required
          className="w-full rounded border px-3 py-2 text-sm" />
        <input name="password" type="password" placeholder="Password" required
          className="w-full rounded border px-3 py-2 text-sm" />
        <button type="submit" className="w-full rounded bg-blue-600 px-3 py-2 text-sm text-white">
          Sign in
        </button>
      </form>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    </main>
  );
}
```

- [ ] **Step 5: Test the role guard** — `frontend/src/app/login/actions.test.ts`:
```ts
import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: async () => ({
    auth: { signInWithPassword: vi.fn(async () => ({ error: null })) },
  }),
}));

describe("demo-login route", () => {
  it("rejects an unknown role with 400", async () => {
    const { POST } = await import("./../api/demo-login/route");
    const res = await POST(new Request("http://x/api/demo-login", {
      method: "POST", body: JSON.stringify({ role: "hacker" }),
    }));
    expect(res.status).toBe(400);
  });
});
```

- [ ] **Step 6: Run tests (expect PASS), then build.**
```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator/frontend" && npm run test && npm run build
```

- [ ] **Step 7: Commit**
```bash
git add frontend/src
git commit -m "feat(frontend): Supabase auth — middleware, demo-role + email login, sign-out"
```

---

### Task 4: App shell — layout, role-aware sidebar, disclaimer header

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`, `frontend/src/components/DisclaimerBar.tsx`, `frontend/src/lib/nav.ts`, `frontend/src/lib/nav.test.ts`
- Modify: `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`

**Interfaces:**
- Consumes: `createServerSupabase()` (to read the user + role for nav).
- Produces: `navForRole(role:string): {href,label}[]` in `src/lib/nav.ts` (Section 2/3/6 links; role gates visibility per spec §6 — for this plan all three are visible to analyst/manager/admin; executive sees only Model Performance).

- [ ] **Step 1: Write the failing test** — `frontend/src/lib/nav.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { navForRole } from "./nav";

describe("navForRole", () => {
  it("gives analyst the applicant + portfolio + performance links", () => {
    const hrefs = navForRole("analyst").map((n) => n.href);
    expect(hrefs).toContain("/assess");
    expect(hrefs).toContain("/portfolio");
    expect(hrefs).toContain("/performance");
  });
  it("limits executive to performance only", () => {
    const hrefs = navForRole("executive").map((n) => n.href);
    expect(hrefs).toEqual(["/performance"]);
  });
});
```

- [ ] **Step 2: Run it, expect FAIL.**

- [ ] **Step 3: Implement** — `frontend/src/lib/nav.ts`:
```ts
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
```

- [ ] **Step 4: DisclaimerBar** — `frontend/src/components/DisclaimerBar.tsx`:
```tsx
export function DisclaimerBar({ modelVersion }: { modelVersion?: string }) {
  return (
    <div className="border-b bg-amber-50 px-4 py-1.5 text-xs text-amber-900">
      Decision-support only — not a lending decision.
      {modelVersion && <span className="ml-2 text-amber-700">Model {modelVersion}</span>}
    </div>
  );
}
```

- [ ] **Step 5: Sidebar** — `frontend/src/components/Sidebar.tsx`:
```tsx
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
```

- [ ] **Step 6: Layout + home** — replace `frontend/src/app/layout.tsx` body to render the shell for signed-in users. Because `layout.tsx` wraps `/login` too, keep the shell in a route group instead: create `frontend/src/app/(app)/layout.tsx`:
```tsx
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
```
Move the home page into the group: create `frontend/src/app/(app)/page.tsx` that redirects to the first nav item:
```tsx
import { redirect } from "next/navigation";
export default function Home() { redirect("/performance"); }
```
Delete the scaffold's default `frontend/src/app/page.tsx` (it conflicts with the group's page). Keep `frontend/src/app/layout.tsx` as the minimal root (html/body + globals import only — leave the scaffold's version).

- [ ] **Step 7: Run tests (PASS) + build (succeeds).** Commit:
```bash
git add frontend/src && git rm --cached frontend/src/app/page.tsx 2>/dev/null; true
git commit -m "feat(frontend): app shell — role-aware sidebar, disclaimer bar, (app) route group"
```

---

### Task 5: Section 6 — Model Performance

**Files:**
- Create: `frontend/src/app/(app)/performance/page.tsx`, `frontend/src/components/MetricTile.tsx`, `frontend/src/components/MetricTile.test.tsx`

**Interfaces:**
- Consumes: `createServerSupabase()` → reads `model_versions` (champion). Metrics live in `model_versions.metrics` JSONB (`auc_roc, precision, recall, f1, accuracy, confusion_matrix`), seeded in Plan 1.
- Produces: the `/performance` page and a reusable `<MetricTile label value help/>`.

- [ ] **Step 1: Write the failing test** — `frontend/src/components/MetricTile.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricTile } from "./MetricTile";

describe("MetricTile", () => {
  it("renders label and value", () => {
    render(<MetricTile label="AUC-ROC" value="0.780" />);
    expect(screen.getByText("AUC-ROC")).toBeInTheDocument();
    expect(screen.getByText("0.780")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run it, expect FAIL.**

- [ ] **Step 3: Implement** — `frontend/src/components/MetricTile.tsx`:
```tsx
export function MetricTile({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {help && <div className="mt-1 text-xs text-gray-400">{help}</div>}
    </div>
  );
}
```

- [ ] **Step 4: Performance page** — `frontend/src/app/(app)/performance/page.tsx`:
```tsx
import { createServerSupabase } from "@/lib/supabase/server";
import { MetricTile } from "@/components/MetricTile";

export default async function PerformancePage() {
  const supabase = await createServerSupabase();
  const { data: champ } = await supabase.from("model_versions")
    .select("semver, algo, metrics").eq("stage", "champion").limit(1).single();
  const m = (champ?.metrics ?? {}) as Record<string, number>;
  const cm = (m.confusion_matrix as unknown as number[][]) ?? [[0, 0], [0, 0]];
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Model Performance</h1>
        <p className="text-sm text-gray-500">
          Champion: {champ?.semver} ({champ?.algo}) · target AUC ≥ 0.75
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricTile label="AUC-ROC" value={fmt(m.auc_roc)} help="Ranking quality (≥0.75 target)" />
        <MetricTile label="Recall" value={fmt(m.recall)} help="Defaulters caught" />
        <MetricTile label="Precision" value={fmt(m.precision)} />
        <MetricTile label="F1" value={fmt(m.f1)} />
      </div>
      <div>
        <h2 className="mb-2 text-sm font-medium">Confusion matrix (test set)</h2>
        <table className="text-sm">
          <tbody>
            <tr><td className="p-2 text-gray-500">TN {cm[0]?.[0]}</td><td className="p-2">FP {cm[0]?.[1]}</td></tr>
            <tr><td className="p-2 font-medium text-red-600">FN {cm[1]?.[0]}</td><td className="p-2">TP {cm[1]?.[1]}</td></tr>
          </tbody>
        </table>
        <p className="mt-1 text-xs text-gray-400">False negatives (missed defaulters) are the costliest error.</p>
      </div>
    </div>
  );
}

function fmt(v?: number) { return v == null ? "—" : v.toFixed(3); }
```

- [ ] **Step 5: Run tests (PASS) + build. Manual check:** run `npm run dev`, sign in as demo-executive, confirm `/performance` shows real champion metrics (AUC 0.780). Commit:
```bash
git add frontend/src
git commit -m "feat(frontend): Section 6 Model Performance (champion metrics from Supabase)"
```

---

### Task 6: Section 3 — Portfolio Risk Monitor

**Files:**
- Create: `frontend/src/app/(app)/portfolio/page.tsx`, `frontend/src/components/BandBar.tsx`, `frontend/src/lib/bands.ts`, `frontend/src/lib/bands.test.ts`

**Interfaces:**
- Consumes: `createServerSupabase()` → reads the demo portfolio's rows. The demo portfolio (`portfolios.is_demo = true`, name "UCI Taiwan 30k (demo)") is world-readable to authenticated users (RLS). Its 30k rows are in `portfolio_rows.features` (JSONB, snake_case raw fields).
- Produces: `bandCounts(scores:number[]): {Low:number,Medium:number,High:number}` in `src/lib/bands.ts`.

- [ ] **Step 1: Write the failing test** — `frontend/src/lib/bands.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { bandCounts } from "./bands";

describe("bandCounts", () => {
  it("buckets scores into the three bands", () => {
    expect(bandCounts([10, 40, 40, 90])).toEqual({ Low: 1, Medium: 2, High: 1 });
  });
});
```

- [ ] **Step 2: Run it, expect FAIL.**

- [ ] **Step 3: Implement** — `frontend/src/lib/bands.ts`:
```ts
import { riskBand } from "./format";

export function bandCounts(scores: number[]) {
  const c = { Low: 0, Medium: 0, High: 0 };
  for (const s of scores) c[riskBand(s)]++;
  return c;
}
```

- [ ] **Step 4: BandBar (client, Recharts)** — `frontend/src/components/BandBar.tsx`:
```tsx
"use client";
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { bandColor } from "@/lib/format";

export function BandBar({ counts }: { counts: { Low: number; Medium: number; High: number } }) {
  const data = (["Low", "Medium", "High"] as const).map((b) => ({ band: b, count: counts[b] }));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data}>
          <XAxis dataKey="band" /><YAxis allowDecimals={false} /><Tooltip />
          <Bar dataKey="count">
            {data.map((d) => <Cell key={d.band} fill={bandColor(d.band)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 5: Portfolio page** — reads a sample of demo rows and scores them by reusing the ML service is out of scope for a 30k live scoring; instead this section shows the **actual default label distribution** and demographic segments from the real data. `frontend/src/app/(app)/portfolio/page.tsx`:
```tsx
import { createServerSupabase } from "@/lib/supabase/server";

export default async function PortfolioPage() {
  const supabase = await createServerSupabase();
  const { data: pf } = await supabase.from("portfolios")
    .select("id, name, row_count").eq("is_demo", true).limit(1).single();
  // Sample rows for a lightweight distribution (avoid pulling all 30k).
  const { data: rows } = await supabase.from("portfolio_rows")
    .select("features").eq("portfolio_id", pf?.id ?? "").limit(2000);
  const feats = (rows ?? []).map((r) => r.features as Record<string, number>);
  const total = feats.length;
  const defaults = feats.filter((f) => f["default.payment.next.month"] === 1).length;
  const byEdu = groupRate(feats, "education");
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Portfolio Risk Monitor</h1>
        <p className="text-sm text-gray-500">
          {pf?.name} · {pf?.row_count?.toLocaleString()} customers (showing a {total.toLocaleString()}-row sample)
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <div className="rounded-lg border p-4">
          <div className="text-xs uppercase text-gray-500">Sample default rate</div>
          <div className="mt-1 text-2xl font-semibold">{total ? ((defaults / total) * 100).toFixed(1) : "—"}%</div>
        </div>
      </div>
      <div>
        <h2 className="mb-2 text-sm font-medium">Default rate by education</h2>
        <table className="text-sm">
          <thead><tr><th className="p-2 text-left">Education</th><th className="p-2 text-right">Default rate</th></tr></thead>
          <tbody>
            {Object.entries(byEdu).map(([k, v]) => (
              <tr key={k}><td className="p-2">{eduLabel(Number(k))}</td>
                <td className="p-2 text-right tabular-nums">{(v * 100).toFixed(1)}%</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function groupRate(rows: Record<string, number>[], key: string) {
  const agg: Record<string, { n: number; d: number }> = {};
  for (const r of rows) {
    const g = String(r[key]);
    agg[g] ??= { n: 0, d: 0 };
    agg[g].n++; if (r["default.payment.next.month"] === 1) agg[g].d++;
  }
  const out: Record<string, number> = {};
  for (const [k, { n, d }] of Object.entries(agg)) out[k] = n ? d / n : 0;
  return out;
}
function eduLabel(v: number) {
  return { 1: "Graduate school", 2: "University", 3: "High school" }[v] ?? "Other";
}
```
(Note: the `BandBar` component and `bandCounts` helper are used in Task 7's result view and are unit-tested here; the portfolio page intentionally shows real-label segments rather than live-scoring 30k rows.)

- [ ] **Step 6: Run tests (PASS) + build. Manual check:** sign in as demo-analyst → `/portfolio` shows the real sample default rate (~22%) and by-education breakdown. Commit:
```bash
git add frontend/src
git commit -m "feat(frontend): Section 3 Portfolio Monitor (real demo-portfolio segments)"
```

---

### Task 7: Section 2 — Single Applicant Assessment (+ ML proxy routes)

**Files:**
- Create: `frontend/src/app/api/predict/route.ts`, `frontend/src/app/api/explain/route.ts`, `frontend/src/lib/ml.ts`, `frontend/src/lib/ml.test.ts`, `frontend/src/app/(app)/assess/page.tsx`, `frontend/src/components/ScoreResult.tsx`, `frontend/src/components/ApplicantForm.tsx`, `frontend/src/lib/applicant.ts`

**Interfaces:**
- Consumes: `createServerSupabase()` (to read the user's access token), `ML_SERVICE_URL` (server env), `riskBand`/`bandColor`.
- Produces: `defaultApplicant()` (23-field object with sane defaults) in `src/lib/applicant.ts`; `callMl(path, token, body)` in `src/lib/ml.ts`.

- [ ] **Step 1: Write the failing test** — `frontend/src/lib/ml.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from "vitest";

beforeEach(() => vi.stubEnv("ML_SERVICE_URL", "http://ml.test"));

describe("callMl", () => {
  it("posts JSON with a bearer token and returns the parsed body", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ risk_score: 82 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { callMl } = await import("./ml");
    const out = await callMl("/api/v1/predict", "tok", { age: 24 });
    expect(out.risk_score).toBe(82);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://ml.test/api/v1/predict");
    expect((init as RequestInit).headers).toMatchObject({ Authorization: "Bearer tok" });
  });
});
```

- [ ] **Step 2: Run it, expect FAIL.**

- [ ] **Step 3: Implement `callMl`** — `frontend/src/lib/ml.ts`:
```ts
export async function callMl(path: string, token: string, body: unknown) {
  const res = await fetch(`${process.env.ML_SERVICE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`ML service ${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json();
}
```

- [ ] **Step 4: Proxy routes** — `frontend/src/app/api/predict/route.ts`:
```ts
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { callMl } from "@/lib/ml";

export async function POST(request: Request) {
  const supabase = await createServerSupabase();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const applicant = await request.json();
  try {
    const out = await callMl("/api/v1/predict", session.access_token, applicant);
    return NextResponse.json(out);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 502 });
  }
}
```
`frontend/src/app/api/explain/route.ts` — identical but calls `/api/v1/explain`.

- [ ] **Step 5: Applicant defaults** — `frontend/src/lib/applicant.ts`:
```ts
export type Applicant = Record<string, number>;

export function defaultApplicant(): Applicant {
  const a: Applicant = {
    limit_bal: 150000, sex: 2, education: 2, marriage: 1, age: 35,
    pay_0: 0, pay_2: 0, pay_3: 0, pay_4: 0, pay_5: 0, pay_6: 0,
  };
  for (let i = 1; i <= 6; i++) { a[`bill_amt${i}`] = 50000; a[`pay_amt${i}`] = 5000; }
  return a;
}
```

- [ ] **Step 6: ScoreResult** — `frontend/src/components/ScoreResult.tsx`:
```tsx
"use client";
import { bandColor, riskBand } from "@/lib/format";

type Factor = { friendly: string; contribution: number; direction: string };
export function ScoreResult({ score, modelVersion, factors }:
  { score: number; modelVersion: string; factors: Factor[] }) {
  const band = riskBand(score);
  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-4">
        <div className="text-xs uppercase text-gray-500">Model output (prediction)</div>
        <div className="mt-1 flex items-baseline gap-3">
          <span className="text-3xl font-bold tabular-nums">{score.toFixed(1)}</span>
          <span className="rounded px-2 py-0.5 text-sm font-medium text-white"
            style={{ background: bandColor(band) }}>{band} risk</span>
        </div>
        <div className="mt-1 text-xs text-gray-400">Model {modelVersion} · SHAP contributions, not causal proof</div>
      </div>
      <div className="rounded-lg border p-4">
        <div className="mb-2 text-sm font-medium">Top contributing factors</div>
        <ul className="space-y-1 text-sm">
          {factors.map((f, i) => (
            <li key={i} className="flex justify-between">
              <span>{f.friendly}</span>
              <span className={f.contribution > 0 ? "text-red-600" : "text-green-600"}>
                {f.direction} risk
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded border border-dashed p-3 text-xs text-gray-500">
        Decision panel (human decision) — recording approve/refer/decline is a future release.
        This score is decision-support only.
      </div>
    </div>
  );
}
```

- [ ] **Step 7: ApplicantForm + assess page** — `frontend/src/components/ApplicantForm.tsx` (client): renders inputs for the key fields (limit_bal, age, sex, education, marriage, and pay_0..pay_6), starting from `defaultApplicant()`, and on submit POSTs to `/api/predict` and `/api/explain`, then renders `<ScoreResult/>`. Full code:
```tsx
"use client";
import { useState } from "react";
import { defaultApplicant, type Applicant } from "@/lib/applicant";
import { ScoreResult } from "./ScoreResult";

const PAYS = ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"];

export function ApplicantForm() {
  const [a, setA] = useState<Applicant>(defaultApplicant());
  const [result, setResult] = useState<{ score: number; version: string; factors: any[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function set(k: string, v: number) { setA((p) => ({ ...p, [k]: v })); }

  async function submit() {
    setLoading(true); setError(null);
    try {
      const [p, e] = await Promise.all([
        fetch("/api/predict", { method: "POST", body: JSON.stringify(a) }).then(r => r.json()),
        fetch("/api/explain", { method: "POST", body: JSON.stringify(a) }).then(r => r.json()),
      ]);
      if (p.error) throw new Error(p.error);
      setResult({ score: p.risk_score, version: p.model_version ?? "—", factors: (e.factors ?? []).slice(0, 5) });
    } catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-3">
        <Num label="Credit limit" k="limit_bal" a={a} set={set} />
        <Num label="Age" k="age" a={a} set={set} />
        <Num label="Sex (1=M,2=F)" k="sex" a={a} set={set} />
        <Num label="Education (1-4)" k="education" a={a} set={set} />
        <Num label="Marriage (1-3)" k="marriage" a={a} set={set} />
        <div className="text-sm font-medium">Repayment status (−1 duly … 8 late)</div>
        <div className="grid grid-cols-3 gap-2">
          {PAYS.map((p) => <Num key={p} label={p} k={p} a={a} set={set} />)}
        </div>
        <button onClick={submit} disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50">
          {loading ? "Scoring…" : "Score applicant"}
        </button>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      </div>
      <div>{result
        ? <ScoreResult score={result.score} modelVersion={result.version} factors={result.factors} />
        : <p className="text-sm text-gray-400">Enter a profile and score to see the result.</p>}</div>
    </div>
  );
}

function Num({ label, k, a, set }:
  { label: string; k: string; a: Record<string, number>; set: (k: string, v: number) => void }) {
  return (
    <label className="block text-sm">
      <span className="text-gray-600">{label}</span>
      <input type="number" value={a[k]} onChange={(e) => set(k, Number(e.target.value))}
        className="mt-1 w-full rounded border px-2 py-1" />
    </label>
  );
}
```
`frontend/src/app/(app)/assess/page.tsx`:
```tsx
import { ApplicantForm } from "@/components/ApplicantForm";

export default function AssessPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Single Applicant Assessment</h1>
        <p className="text-sm text-gray-500">Score one applicant and see the factors behind it.</p>
      </div>
      <ApplicantForm />
    </div>
  );
}
```

- [ ] **Step 8: Run unit tests (PASS) + build.** Then the **end-to-end manual check** (requires the ML service running): in one shell start the ML service — `export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"` is NOT needed here; run `.venv/Scripts/python.exe -m uvicorn services.ml.main:app --port 8000` from the repo root — then `npm run dev` in `frontend/`, sign in as demo-analyst, go to `/assess`, enter a risky profile (pay_0=3, high limit usage) and confirm a High band + SHAP factors render. If the ML service is not running, the page shows a 502 error message (acceptable — documented dependency).

- [ ] **Step 9: Commit**
```bash
git add frontend/src
git commit -m "feat(frontend): Section 2 Single Applicant — ML proxy routes + form + SHAP result"
```

---

### Task 8: Deploy config + docs

**Files:**
- Create: `frontend/README.md`, `frontend/.env.example` (if not already), `docs/runbooks/frontend-deploy.md`
- Modify: `frontend/next.config.ts` (ensure no `output: export`; default server output for Vercel)

**Interfaces:** none (docs + config).

- [ ] **Step 1: Frontend README** — document: prerequisites (Node 20+/portable path), `npm install`, `.env.local` vars, `npm run dev`, `npm run test`, `npm run build`, and that Section 2 needs the ML service reachable at `ML_SERVICE_URL`.

- [ ] **Step 2: Deploy runbook** — `docs/runbooks/frontend-deploy.md`: Vercel import of the `frontend/` subdirectory (root directory setting = `frontend`), the 4 env vars to set in Vercel (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `ML_SERVICE_URL`, `DEMO_PASSWORD`), and the explicit **follow-up**: the ML service (Plan 2 Dockerfile) must be deployed (e.g. Render) and `ML_SERVICE_URL` pointed at it before Section 2 works in production; until then Sections 3 & 6 work (Supabase-only) and Section 2 shows a 502.

- [ ] **Step 3: Verify production build** (the real gate for deployability):
```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator/frontend" && npm run build
```
Expected: `Compiled successfully`, all routes listed (`/login`, `/assess`, `/portfolio`, `/performance`, `/api/*`), no type errors.

- [ ] **Step 4: Full test run**
```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator/frontend" && npm run test
```
Expected: all suites pass.

- [ ] **Step 5: Commit + tag**
```bash
cd "C:/Users/Gamer/Documents/credit_risk_scoring_simulator"
git add frontend/README.md frontend/.env.example docs/runbooks/frontend-deploy.md frontend/next.config.ts
git commit -m "docs(frontend): README + Vercel deploy runbook; verify production build"
git tag r1-plan3-complete
```

---

## Self-Review

- **Spec coverage:** §4 Approach A frontend (Next.js/Vercel/Supabase) — Tasks 1–8 ✓. Auth: demo-role + email signup (signup deferred to R2 per spec rollout; login covers demo + email sign-in) — Task 3 ✓. Section 2 (single applicant, ML service, SHAP, prediction≠decision, disclaimer, model version) — Task 7 ✓. Section 3 (portfolio, real demo data) — Task 6 ✓. Section 6 (performance metrics) — Task 5 ✓. Role-aware nav (§6 matrix, subset) — Task 4 ✓. Security: secrets server-only, RLS-reliant reads, ML proxy forwards JWT — Tasks 2,3,7 ✓. UX: risk colors + labels, empty/error states, disclaimer — Tasks 4–7 ✓. Deploy — Task 8 ✓. **Deferred (documented, not in this plan):** email *signup* (R2), Sections 1/4/5/7–14, live 30k scoring, ML-service cloud hosting.
- **Placeholder scan:** none — every step has full code or exact commands.
- **Type consistency:** `riskBand`/`bandColor` (Task 1) reused in Tasks 6/7; `createServerSupabase`/`createBrowserSupabase` (Task 2) reused in Tasks 3–7; `callMl` (Task 7) signature matches its test; `defaultApplicant` shape matches the ML Applicant contract (23 snake_case fields).

---

**Environment reminder for the executor:** prepend the portable-Node path in EVERY node/npm/npx shell command (Global Constraints). The ML service (Plan 2) for Task 7's manual check runs via `.venv/Scripts/python.exe -m uvicorn services.ml.main:app --port 8000` from the repo root, needing the repo `.env`.
