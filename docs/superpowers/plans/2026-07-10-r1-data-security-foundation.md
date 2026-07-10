# R1 Plan 1/3 — Data & Security Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace synthetic data with the real UCI dataset and stand up the Supabase schema, RLS security model, and demo users that every later plan builds on.

**Architecture:** A one-time ingest turns the official UCI file into `data/raw/credit_card_default.csv` so the existing pipeline retrains unchanged on real data. Three SQL migrations (committed to `supabase/migrations/`, applied via the connected Supabase MCP) create the 18-table schema with default-deny RLS. A seed script creates 4 demo users, the public demo portfolio (real UCI rows), and the model-registry row. Integration tests prove cross-user isolation.

**Tech Stack:** Python 3.14 (project venv), pandas, xlrd (xls read), supabase-py (seed + tests), Supabase Postgres 17 (project `uiormpweobimumzlxjml`, ap-southeast-2), pytest.

## Global Constraints

- Existing ML code (`src/`) and its 16 tests must not be modified; the synthetic generator remains for tests.
- All secrets live in `.env` (gitignored). Never commit keys. `.env.example` documents required names.
- Spec source of truth: `docs/superpowers/specs/2026-07-10-production-platform-design.md` (§4 schema, §5 security).
- RLS: default-deny on every table; owner-only for portfolio data; `is_demo` rows are public-read; audit tables append-only.
- Demo users: `demo-analyst@demo.local`, `demo-manager@demo.local`, `demo-compliance@demo.local`, `demo-executive@demo.local` — password from env `DEMO_PASSWORD`, email pre-confirmed, `profiles.is_demo = true`.
- Run Python via `.venv/Scripts/python.exe` (bare `python` is a Windows Store stub on this machine).
- Commits: conventional style `type(scope): message`, one commit per task minimum.

**Prerequisite (user, one-time):** copy the **service_role key** and **anon key** from Supabase dashboard → Project Settings → API into `.env` (`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`). `SUPABASE_URL=https://uiormpweobimumzlxjml.supabase.co`.

---

### Task 1: Platform scaffolding + env contract

**Files:**
- Create: `scripts/requirements.txt`, `.env.example`
- Modify: `.gitignore` (append)

**Interfaces:**
- Produces: env var names every later task reads: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DEMO_PASSWORD`.

- [ ] **Step 1: Create `scripts/requirements.txt`**

```
# Platform tooling only — NOT installed by Streamlit Cloud (that uses root requirements.txt)
supabase>=2.4
xlrd>=2.0
python-dotenv>=1.0
requests>=2.31
```

- [ ] **Step 2: Create `.env.example`**

```
# Supabase (dashboard -> Project Settings -> API)
SUPABASE_URL=https://uiormpweobimumzlxjml.supabase.co
SUPABASE_ANON_KEY=replace-me
SUPABASE_SERVICE_ROLE_KEY=replace-me   # server-side only, never expose
# Password used for the four seeded demo accounts
DEMO_PASSWORD=replace-me
```

- [ ] **Step 3: Append to `.gitignore`**

```
# Secrets
.env
```

- [ ] **Step 4: Install tooling deps into the venv**

Run: `.venv/Scripts/python.exe -m pip install -r scripts/requirements.txt`
Expected: `Successfully installed supabase-... xlrd-... python-dotenv-...`

- [ ] **Step 5: Commit**

```bash
git add scripts/requirements.txt .env.example .gitignore
git commit -m "chore(platform): scaffolding, env contract, tooling deps"
```

---

### Task 2: Real UCI ingest — transform function (TDD)

**Files:**
- Create: `scripts/ingest_uci.py`
- Test: `tests/platform/test_ingest_uci.py`, `tests/platform/__init__.py` (empty)

**Interfaces:**
- Produces: `transform_uci(df: pd.DataFrame) -> pd.DataFrame` (raw xls frame → exact `data/raw` CSV format with target column `default.payment.next.month`), and CLI `python scripts/ingest_uci.py` that downloads + writes `data/raw/credit_card_default.csv`.
- Consumes: nothing from other tasks.

- [ ] **Step 1: Write the failing test**

```python
# tests/platform/test_ingest_uci.py
import pandas as pd
import pytest

from scripts.ingest_uci import transform_uci


def _fake_xls_frame():
    # Mimics pd.read_excel(xls, header=1): ID column + 23 features + verbose target
    cols = (["ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
             "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
            + [f"BILL_AMT{i}" for i in range(1, 7)]
            + [f"PAY_AMT{i}" for i in range(1, 7)]
            + ["default payment next month"])
    row = [1, 20000, 2, 2, 1, 24, 2, 2, -1, -1, -2, -2,
           3913, 3102, 689, 0, 0, 0, 0, 689, 0, 0, 0, 0, 1]
    return pd.DataFrame([row], columns=cols)


def test_transform_renames_target_to_dotted_name():
    out = transform_uci(_fake_xls_frame())
    assert "default.payment.next.month" in out.columns
    assert "default payment next month" not in out.columns


def test_transform_keeps_id_and_all_feature_columns():
    out = transform_uci(_fake_xls_frame())
    assert out.shape == (1, 25)  # ID + 23 features + target
    for col in ["ID", "LIMIT_BAL", "PAY_0", "BILL_AMT6", "PAY_AMT1"]:
        assert col in out.columns


def test_transform_rejects_frame_missing_columns():
    bad = _fake_xls_frame().drop(columns=["AGE"])
    with pytest.raises(ValueError, match="AGE"):
        transform_uci(bad)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/test_ingest_uci.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'scripts.ingest_uci'`

- [ ] **Step 3: Implement `scripts/ingest_uci.py`**

```python
"""One-time ingest of the real UCI 'Default of Credit Card Clients' dataset.

Downloads the official zip, extracts the .xls, and writes it in the exact
format the existing pipeline expects (data/raw/credit_card_default.csv),
so `python -m src.train_model` retrains on REAL data with zero code changes.

License: UCI dataset, public for academic/portfolio use. Cited in README.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config  # noqa: E402

UCI_ZIP_URL = ("https://archive.ics.uci.edu/static/public/350/"
               "default+of+credit+card+clients.zip")
TARGET_VERBOSE = "default payment next month"

EXPECTED = (["ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
             "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
            + [f"BILL_AMT{i}" for i in range(1, 7)]
            + [f"PAY_AMT{i}" for i in range(1, 7)]
            + [TARGET_VERBOSE])


def transform_uci(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the raw xls frame and rename the target to the dotted form."""
    missing = [c for c in EXPECTED if c not in df.columns]
    if missing:
        raise ValueError(f"UCI frame missing expected columns: {missing}")
    out = df[EXPECTED].copy()
    return out.rename(columns={TARGET_VERBOSE: "default.payment.next.month"})


def download_raw() -> pd.DataFrame:
    import requests

    resp = requests.get(UCI_ZIP_URL, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xls_name = next(n for n in zf.namelist() if n.endswith(".xls"))
        with zf.open(xls_name) as fh:
            return pd.read_excel(fh, header=1, engine="xlrd")


def main() -> None:
    df = transform_uci(download_raw())
    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.RAW_CSV, index=False)
    rate = df["default.payment.next.month"].mean()
    print(f"Wrote {len(df):,} REAL rows to {config.RAW_CSV}")
    print(f"Default rate: {rate:.4f} (expected ~0.2212)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/test_ingest_uci.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_uci.py tests/platform/
git commit -m "feat(data): real UCI ingest with validated transform"
```

---

### Task 3: Download real data + retrain + verify AUC ≥ 0.75

**Files:**
- Modify (generated artifacts): `data/raw/credit_card_default.csv`, `models/metrics.json` (committed), `models/model.pkl` + `data/processed/*` (gitignored, regenerated)

**Interfaces:**
- Consumes: `scripts/ingest_uci.py` CLI (Task 2).
- Produces: model + `models/metrics.json` trained on real data; the numbers Plan 2's API and the seed script (Task 7) read.

- [ ] **Step 1: Run the ingest**

Run: `.venv/Scripts/python.exe scripts/ingest_uci.py`
Expected: `Wrote 30,000 REAL rows ...` and `Default rate: 0.2212`

- [ ] **Step 2: Retrain the existing pipeline on real data**

Run: `.venv/Scripts/python.exe -m src.train_model`
Expected: completes; prints `Advanced  AUC-ROC: 0.7x` (real-UCI XGBoost typically lands ≈ 0.78).

- [ ] **Step 3: Assert the PRD gate**

Run: `.venv/Scripts/python.exe -c "import json; m=json.load(open('models/metrics.json')); auc=m['advanced']['auc_roc']; print('AUC', auc); assert auc >= 0.75, 'AUC below PRD target'"`
Expected: `AUC 0.7...` and no assertion error.

- [ ] **Step 4: Confirm the 16 existing tests still pass** (they use the synthetic generator, not the CSV)

Run: `.venv/Scripts/python.exe -m pytest`
Expected: 16 passed (+ the 3 new platform tests = 19 total).

- [ ] **Step 5: Commit**

```bash
git add data/raw/credit_card_default.csv models/metrics.json
git commit -m "feat(data): retrain on real UCI dataset (30k rows, AUC >= 0.75)"
```

---

### Task 4: Migration 0001 — identity (profiles, roles, signup trigger)

**Files:**
- Create: `supabase/migrations/0001_identity.sql`

**Interfaces:**
- Produces: `public.app_role` enum, `public.profiles`, helper `public.user_role()` (SECURITY DEFINER, avoids RLS recursion), signup trigger. Every later policy calls `public.user_role()`.

- [ ] **Step 1: Write the migration file**

```sql
-- 0001_identity.sql
create type public.app_role as enum
  ('analyst','manager','compliance','executive','admin');

create table public.profiles (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  org          text,
  role         public.app_role not null default 'analyst',
  is_demo      boolean not null default false,
  created_at   timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- SECURITY DEFINER helper: read caller's role without recursive RLS.
create or replace function public.user_role() returns public.app_role
language sql stable security definer set search_path = public as
$$ select role from public.profiles where user_id = auth.uid() $$;

create policy "profiles_select_own_or_admin" on public.profiles
  for select using (user_id = auth.uid() or public.user_role() = 'admin');
create policy "profiles_update_own" on public.profiles
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "profiles_admin_update" on public.profiles
  for update using (public.user_role() = 'admin');

-- Users may never change their own role: column-level privilege revoke.
revoke update on public.profiles from authenticated;
grant update (display_name, org) on public.profiles to authenticated;

-- Auto-create a profile on signup.
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (user_id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', ''));
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
```

- [ ] **Step 2: Apply via Supabase MCP**

Call MCP `apply_migration` (project `uiormpweobimumzlxjml`) with name `0001_identity` and the SQL above.
Expected: success, no error.

- [ ] **Step 3: Verify**

Call MCP `execute_sql`: `select count(*) from information_schema.tables where table_schema='public' and table_name='profiles';`
Expected: `1`.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/0001_identity.sql
git commit -m "feat(db): identity schema — profiles, app_role, signup trigger, RLS"
```

---

### Task 5: Migration 0002 — portfolios with owner-only RLS

**Files:**
- Create: `supabase/migrations/0002_portfolios.sql`

**Interfaces:**
- Consumes: `public.user_role()` (Task 4).
- Produces: `portfolios`, `portfolio_rows`, `upload_files` with the RLS Task 8 penetration-tests and Task 7 seeds.

- [ ] **Step 1: Write the migration file**

```sql
-- 0002_portfolios.sql
create table public.portfolios (
  id         uuid primary key default gen_random_uuid(),
  owner_id   uuid not null references auth.users(id) on delete cascade,
  name       text not null,
  is_demo    boolean not null default false,
  row_count  integer not null default 0,
  created_at timestamptz not null default now()
);

create table public.portfolio_rows (
  id           bigint generated always as identity primary key,
  portfolio_id uuid not null references public.portfolios(id) on delete cascade,
  row_index    integer not null,
  features     jsonb not null
);
create index portfolio_rows_pid_idx on public.portfolio_rows (portfolio_id);

create table public.upload_files (
  id            uuid primary key default gen_random_uuid(),
  portfolio_id  uuid not null references public.portfolios(id) on delete cascade,
  storage_path  text not null,
  original_name text not null,
  size_bytes    bigint not null,
  created_at    timestamptz not null default now()
);

alter table public.portfolios     enable row level security;
alter table public.portfolio_rows enable row level security;
alter table public.upload_files   enable row level security;

-- Owner full access; demo portfolios world-readable (auth.uid() is null for anon).
create policy "pf_select_own_or_demo" on public.portfolios
  for select using (owner_id = auth.uid() or is_demo);
create policy "pf_insert_own" on public.portfolios
  for insert with check (owner_id = auth.uid());
create policy "pf_update_own" on public.portfolios
  for update using (owner_id = auth.uid());
create policy "pf_delete_own" on public.portfolios
  for delete using (owner_id = auth.uid());

create policy "pr_select_via_portfolio" on public.portfolio_rows
  for select using (exists (select 1 from public.portfolios p
    where p.id = portfolio_id and (p.owner_id = auth.uid() or p.is_demo)));
create policy "pr_insert_own" on public.portfolio_rows
  for insert with check (exists (select 1 from public.portfolios p
    where p.id = portfolio_id and p.owner_id = auth.uid()));
create policy "pr_delete_own" on public.portfolio_rows
  for delete using (exists (select 1 from public.portfolios p
    where p.id = portfolio_id and p.owner_id = auth.uid()));

create policy "uf_select_own" on public.upload_files
  for select using (exists (select 1 from public.portfolios p
    where p.id = portfolio_id and p.owner_id = auth.uid()));
create policy "uf_insert_own" on public.upload_files
  for insert with check (exists (select 1 from public.portfolios p
    where p.id = portfolio_id and p.owner_id = auth.uid()));
create policy "uf_delete_own" on public.upload_files
  for delete using (exists (select 1 from public.portfolios p
    where p.id = portfolio_id and p.owner_id = auth.uid()));
```

- [ ] **Step 2: Apply via Supabase MCP** — `apply_migration`, name `0002_portfolios`. Expected: success.

- [ ] **Step 3: Verify**

MCP `execute_sql`: `select relrowsecurity from pg_class where relname in ('portfolios','portfolio_rows','upload_files');`
Expected: three rows, all `true`.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/0002_portfolios.sql
git commit -m "feat(db): portfolio tables with owner-only RLS, demo public-read"
```

---

### Task 6: Migration 0003 — scoring, governance, ops (13 tables)

**Files:**
- Create: `supabase/migrations/0003_scoring_governance.sql`

**Interfaces:**
- Consumes: `public.user_role()`, `portfolios`.
- Produces: `model_versions`, `predictions`, `prediction_explanations`, `decision_recommendations`, `human_decisions`, `override_logs`, `llm_reports`, `fairness_runs`, `fairness_results`, `audit_logs`, `macro_indicators`, `monitoring_metrics`, `feature_flags`, `api_keys` — exact names Plan 2's ML service writes to.

- [ ] **Step 1: Write the migration file**

```sql
-- 0003_scoring_governance.sql
create table public.model_versions (
  id          uuid primary key default gen_random_uuid(),
  semver      text not null unique,
  algo        text not null,
  stage       text not null default 'dev'
              check (stage in ('dev','staging','champion','retired')),
  metrics     jsonb not null default '{}'::jsonb,
  trained_on  text not null,
  threshold   double precision not null default 0.5,
  approved_by uuid references auth.users(id),
  created_at  timestamptz not null default now()
);

create table public.predictions (
  id               uuid primary key default gen_random_uuid(),
  portfolio_id     uuid references public.portfolios(id) on delete cascade,
  applicant        jsonb,
  probability      double precision not null check (probability between 0 and 1),
  risk_score       double precision not null,
  risk_band        text not null check (risk_band in ('Low','Medium','High')),
  threshold_used   double precision not null,
  model_version_id uuid not null references public.model_versions(id),
  input_hash       text not null,
  latency_ms       integer,
  created_by       uuid references auth.users(id),
  created_at       timestamptz not null default now()
);
create index predictions_pid_idx  on public.predictions (portfolio_id, created_at);
create index predictions_hash_idx on public.predictions (input_hash);

create table public.prediction_explanations (
  prediction_id uuid primary key references public.predictions(id) on delete cascade,
  method        text not null default 'shap_tree',
  top_factors   jsonb not null,
  base_value    double precision
);

create table public.decision_recommendations (
  prediction_id      uuid primary key references public.predictions(id) on delete cascade,
  recommended_action text not null check (recommended_action in ('approve','refer','decline')),
  rationale          text not null,
  policy_version     text not null default 'v1'
);

create table public.human_decisions (
  id            uuid primary key default gen_random_uuid(),
  prediction_id uuid not null references public.predictions(id),
  final_action  text not null check (final_action in ('approve','refer','decline')),
  notes         text,
  decided_by    uuid not null references auth.users(id),
  decided_at    timestamptz not null default now()
);

create table public.override_logs (
  id          uuid primary key default gen_random_uuid(),
  decision_id uuid not null references public.human_decisions(id),
  overrode    boolean not null,
  reason_code text,
  created_at  timestamptz not null default now()
);

create table public.llm_reports (
  id                uuid primary key default gen_random_uuid(),
  prediction_id     uuid references public.predictions(id) on delete cascade,
  provider          text not null,
  model_name        text not null,
  prompt            jsonb not null,
  structured_inputs jsonb not null,
  output_text       text not null,
  source_fields     jsonb not null,
  redacted          boolean not null default true,
  review_status     text not null default 'draft'
                    check (review_status in ('draft','reviewed','rejected')),
  created_by        uuid references auth.users(id),
  created_at        timestamptz not null default now()
);

create table public.fairness_runs (
  id               uuid primary key default gen_random_uuid(),
  model_version_id uuid not null references public.model_versions(id),
  run_at           timestamptz not null default now()
);

create table public.fairness_results (
  run_id          uuid not null references public.fairness_runs(id) on delete cascade,
  attribute       text not null,
  grp             text not null,
  n               integer not null,
  selection_rate  double precision,
  recall          double precision,
  precision       double precision,
  disparity_ratio double precision,
  primary key (run_id, attribute, grp)
);

create table public.audit_logs (
  id          bigint generated always as identity primary key,
  actor_id    uuid,
  action      text not null,
  entity_type text not null,
  entity_id   text,
  detail      jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

create table public.macro_indicators (
  source    text not null,
  indicator text not null,
  period    date not null,
  value     double precision not null,
  primary key (source, indicator, period)
);

create table public.monitoring_metrics (
  period timestamptz not null,
  metric text not null,
  value  double precision not null,
  primary key (period, metric)
);

create table public.feature_flags (
  key     text primary key,
  enabled boolean not null default true,
  note    text
);

create table public.api_keys (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  key_hash   text not null unique,
  scopes     jsonb not null default '[]'::jsonb,
  expires_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

-- RLS everywhere, default deny.
alter table public.model_versions           enable row level security;
alter table public.predictions              enable row level security;
alter table public.prediction_explanations  enable row level security;
alter table public.decision_recommendations enable row level security;
alter table public.human_decisions          enable row level security;
alter table public.override_logs            enable row level security;
alter table public.llm_reports              enable row level security;
alter table public.fairness_runs            enable row level security;
alter table public.fairness_results         enable row level security;
alter table public.audit_logs               enable row level security;
alter table public.macro_indicators         enable row level security;
alter table public.monitoring_metrics       enable row level security;
alter table public.feature_flags            enable row level security;
alter table public.api_keys                 enable row level security;

-- Public/reference reads.
create policy "mv_read_all"    on public.model_versions    for select using (true);
create policy "macro_read_all" on public.macro_indicators  for select using (true);
create policy "flags_read_all" on public.feature_flags     for select using (true);

-- Predictions readable via owning portfolio (or demo), or by their creator.
create policy "pred_select" on public.predictions for select using (
  created_by = auth.uid()
  or exists (select 1 from public.portfolios p
             where p.id = portfolio_id and (p.owner_id = auth.uid() or p.is_demo)));
create policy "pred_insert_own" on public.predictions
  for insert with check (created_by = auth.uid());

create policy "pexp_select" on public.prediction_explanations for select using (
  exists (select 1 from public.predictions pr where pr.id = prediction_id
          and (pr.created_by = auth.uid()
               or exists (select 1 from public.portfolios p
                          where p.id = pr.portfolio_id
                            and (p.owner_id = auth.uid() or p.is_demo)))));

create policy "drec_select" on public.decision_recommendations for select using (
  exists (select 1 from public.predictions pr
          where pr.id = prediction_id and pr.created_by = auth.uid()));

create policy "hd_select_own" on public.human_decisions
  for select using (decided_by = auth.uid()
                    or public.user_role() in ('compliance','admin'));
create policy "hd_insert_own" on public.human_decisions
  for insert with check (decided_by = auth.uid());

create policy "ovr_select_gov" on public.override_logs
  for select using (public.user_role() in ('compliance','admin'));

create policy "llm_select_own" on public.llm_reports
  for select using (created_by = auth.uid() or public.user_role() = 'admin');
create policy "llm_insert_own" on public.llm_reports
  for insert with check (created_by = auth.uid());

create policy "fr_read_all"  on public.fairness_runs    for select using (true);
create policy "fres_read_all" on public.fairness_results for select using (true);

create policy "audit_select_gov" on public.audit_logs
  for select using (public.user_role() in ('compliance','admin'));

create policy "mon_select_roles" on public.monitoring_metrics
  for select using (public.user_role() in ('manager','admin'));

create policy "keys_own" on public.api_keys
  for select using (user_id = auth.uid());
create policy "keys_insert_own" on public.api_keys
  for insert with check (user_id = auth.uid());
create policy "keys_update_own" on public.api_keys
  for update using (user_id = auth.uid());

-- Append-only guarantees: no UPDATE/DELETE for client roles.
revoke update, delete on public.audit_logs    from authenticated, anon;
revoke update, delete on public.predictions   from authenticated, anon;
revoke update, delete on public.override_logs from authenticated, anon;

-- Governance writes (model_versions, fairness, flags, macro, monitoring)
-- happen via service-role only in R1: no client insert policies on purpose.
```

- [ ] **Step 2: Apply via Supabase MCP** — `apply_migration`, name `0003_scoring_governance`. Expected: success.

- [ ] **Step 3: Verify table count**

MCP `execute_sql`: `select count(*) from information_schema.tables where table_schema='public';`
Expected: `18`.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/0003_scoring_governance.sql
git commit -m "feat(db): scoring/governance/ops schema, append-only audit, RLS"
```

---

### Task 7: Seed script — demo users, demo portfolio (real rows), model registry, flags

**Files:**
- Create: `scripts/seed_platform.py`

**Interfaces:**
- Consumes: `.env` vars (Task 1), real CSV (Task 3), tables (Tasks 4–6), `models/metrics.json`.
- Produces: 4 demo users; demo portfolio named `UCI Taiwan 30k (demo)` with `is_demo=true`; `model_versions` row semver `1.0.0-real-uci` stage `champion`; feature flags `llm_features`, `uploads`, `signup` (all enabled). Plan 2/3 read all of these.

- [ ] **Step 1: Write `scripts/seed_platform.py`**

```python
"""Seed the Supabase project: demo users, demo portfolio, model registry, flags.

Idempotent: safe to re-run (skips users/portfolio that already exist).
Requires .env with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEMO_PASSWORD.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config  # noqa: E402

load_dotenv()
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # server-side only
DEMO_PASSWORD = os.environ["DEMO_PASSWORD"]

DEMO_USERS = [
    ("demo-analyst@demo.local", "Demo Analyst", "analyst"),
    ("demo-manager@demo.local", "Demo Manager", "manager"),
    ("demo-compliance@demo.local", "Demo Compliance", "compliance"),
    ("demo-executive@demo.local", "Demo Executive", "executive"),
]
DEMO_PORTFOLIO = "UCI Taiwan 30k (demo)"
CHUNK = 1000

sb = create_client(URL, KEY)


def ensure_demo_users() -> dict[str, str]:
    existing = {u.email: u.id for u in sb.auth.admin.list_users()}
    ids = {}
    for email, name, role in DEMO_USERS:
        if email in existing:
            ids[email] = existing[email]
        else:
            res = sb.auth.admin.create_user({
                "email": email, "password": DEMO_PASSWORD,
                "email_confirm": True,
                "user_metadata": {"display_name": name},
            })
            ids[email] = res.user.id
        sb.table("profiles").update(
            {"role": role, "is_demo": True, "display_name": name}
        ).eq("user_id", ids[email]).execute()
        print(f"demo user ready: {email} ({role})")
    return ids


def ensure_demo_portfolio(owner_id: str) -> None:
    found = (sb.table("portfolios").select("id")
             .eq("name", DEMO_PORTFOLIO).execute().data)
    if found:
        print("demo portfolio already seeded")
        return
    df = pd.read_csv(config.RAW_CSV)
    pf = (sb.table("portfolios").insert({
        "owner_id": owner_id, "name": DEMO_PORTFOLIO,
        "is_demo": True, "row_count": len(df),
    }).execute().data[0])
    rows = [{"portfolio_id": pf["id"], "row_index": i,
             "features": r._asdict() if hasattr(r, "_asdict") else r}
            for i, r in enumerate(df.to_dict(orient="records"))]
    for i in range(0, len(rows), CHUNK):
        sb.table("portfolio_rows").insert(rows[i:i + CHUNK]).execute()
        print(f"  rows {i + len(rows[i:i + CHUNK]):,}/{len(rows):,}")
    print(f"demo portfolio seeded: {len(rows):,} real rows")


def ensure_model_version() -> None:
    if sb.table("model_versions").select("id").eq(
            "semver", "1.0.0-real-uci").execute().data:
        print("model version already registered")
        return
    metrics = json.loads(Path(config.METRICS_PATH).read_text())
    sb.table("model_versions").insert({
        "semver": "1.0.0-real-uci",
        "algo": metrics["model_type"],
        "stage": "champion",
        "metrics": metrics["advanced"],
        "trained_on": "UCI Default of Credit Card Clients (real, 30k)",
        "threshold": 0.5,
    }).execute()
    print("model version 1.0.0-real-uci registered as champion")


def ensure_flags() -> None:
    for key in ("llm_features", "uploads", "signup"):
        sb.table("feature_flags").upsert(
            {"key": key, "enabled": True}).execute()
    print("feature flags ensured")


if __name__ == "__main__":
    ids = ensure_demo_users()
    ensure_demo_portfolio(ids["demo-analyst@demo.local"])
    ensure_model_version()
    ensure_flags()
    print("SEED COMPLETE")
```

- [ ] **Step 2: Run it**

Run: `.venv/Scripts/python.exe scripts/seed_platform.py`
Expected: 4 `demo user ready` lines, row-chunk progress to `30,000/30,000`, `model version ... registered`, `SEED COMPLETE`.

- [ ] **Step 3: Verify via MCP `execute_sql`**

`select (select count(*) from public.profiles where is_demo) as demo_users, (select count(*) from public.portfolio_rows) as rows, (select count(*) from public.model_versions where stage='champion') as champions;`
Expected: `demo_users=4, rows=30000, champions=1`.

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_platform.py
git commit -m "feat(platform): idempotent seed — demo users, real demo portfolio, registry, flags"
```

---

### Task 8: RLS penetration tests (the security proof)

**Files:**
- Test: `tests/platform/test_rls.py`

**Interfaces:**
- Consumes: anon + service clients (`.env`), tables and demo portfolio from Tasks 4–7.
- Produces: the repeatable proof required by spec §12: user A cannot read user B's data.

- [ ] **Step 1: Write the integration tests**

```python
"""RLS penetration tests — run against the live Supabase project.

Skipped automatically when .env credentials are absent (e.g. CI without
secrets). These tests are the security acceptance gate of spec section 12.
"""
from __future__ import annotations

import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("SUPABASE_URL")
ANON = os.getenv("SUPABASE_ANON_KEY")
SERVICE = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

pytestmark = pytest.mark.skipif(
    not (URL and ANON and SERVICE),
    reason="Supabase credentials not configured",
)


@pytest.fixture(scope="module")
def clients():
    from supabase import create_client

    admin = create_client(URL, SERVICE)
    users, sessions = [], []
    for _ in range(2):
        email = f"rls-test-{uuid.uuid4().hex[:10]}@demo.local"
        pw = f"Pw!{uuid.uuid4().hex[:12]}"
        u = admin.auth.admin.create_user(
            {"email": email, "password": pw, "email_confirm": True})
        users.append(u.user.id)
        c = create_client(URL, ANON)
        c.auth.sign_in_with_password({"email": email, "password": pw})
        sessions.append(c)
    yield admin, sessions[0], sessions[1]
    for uid in users:
        admin.auth.admin.delete_user(uid)


def test_user_cannot_read_another_users_portfolio(clients):
    _, user_a, user_b = clients
    pf = user_a.table("portfolios").insert(
        {"owner_id": user_a.auth.get_user().user.id,
         "name": "private-A"}).execute().data[0]
    user_a.table("portfolio_rows").insert(
        {"portfolio_id": pf["id"], "row_index": 0,
         "features": {"limit_bal": 50000}}).execute()

    stolen = user_b.table("portfolio_rows").select("*").eq(
        "portfolio_id", pf["id"]).execute().data
    assert stolen == []  # RLS: B sees nothing of A's data

    stolen_pf = user_b.table("portfolios").select("*").eq(
        "id", pf["id"]).execute().data
    assert stolen_pf == []


def test_user_cannot_insert_into_another_users_portfolio(clients):
    _, user_a, user_b = clients
    pf = user_a.table("portfolios").insert(
        {"owner_id": user_a.auth.get_user().user.id,
         "name": "private-A2"}).execute().data[0]
    with pytest.raises(Exception):
        user_b.table("portfolio_rows").insert(
            {"portfolio_id": pf["id"], "row_index": 0,
             "features": {}}).execute()


def test_demo_portfolio_is_world_readable(clients):
    _, user_a, _ = clients
    demo = user_a.table("portfolios").select("id").eq(
        "is_demo", True).execute().data
    assert len(demo) >= 1


def test_client_cannot_update_predictions(clients):
    # predictions are append-only for client roles (UPDATE revoked)
    _, user_a, _ = clients
    with pytest.raises(Exception):
        user_a.table("predictions").update(
            {"risk_score": 0}).eq("input_hash", "nonexistent").execute()


def test_user_cannot_escalate_own_role(clients):
    _, user_a, _ = clients
    uid = user_a.auth.get_user().user.id
    with pytest.raises(Exception):
        user_a.table("profiles").update(
            {"role": "admin"}).eq("user_id", uid).execute()
```

- [ ] **Step 2: Run the suite**

Run: `.venv/Scripts/python.exe -m pytest tests/platform/test_rls.py -v`
Expected: 5 passed (or 5 skipped if `.env` absent — passing requires the env).

- [ ] **Step 3: Run everything**

Run: `.venv/Scripts/python.exe -m pytest`
Expected: 24 passed (16 ML + 3 ingest + 5 RLS).

- [ ] **Step 4: Commit + tag**

```bash
git add tests/platform/test_rls.py
git commit -m "test(security): RLS penetration tests — cross-user isolation proven"
git tag r1-plan1-complete
git push origin main --tags
```

---

## Self-Review

- **Spec coverage:** §4 schema (Tasks 4–6, all 18 tables) ✓ · §5 security: RLS default-deny (4–6), append-only (6), role-escalation block (4, tested in 8), demo public-read (5) ✓ · real UCI data (2–3) ✓ · demo users/roles (7) ✓ · §12's RLS proof (8) ✓. Storage-bucket policy and macro connectors are Plans 2/3 scope (spec §3, §13) — intentionally absent here.
- **Placeholders:** none; every step has full code/SQL/commands.
- **Type consistency:** `public.user_role()` used in 0003 matches its definition in 0001; seed table/column names match migrations; `transform_uci` name consistent between test and implementation.

---

**Execution prerequisite reminder:** before Task 7, you must put the real `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, and a chosen `DEMO_PASSWORD` into `.env` (5 minutes, Supabase dashboard → Project Settings → API).
