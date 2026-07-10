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
