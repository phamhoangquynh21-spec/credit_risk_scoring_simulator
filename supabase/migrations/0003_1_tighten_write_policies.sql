-- 0003_1_tighten_write_policies.sql
-- Security fixes for write-side RLS holes found in review of 0003.

-- FIX 1 (Critical): api_keys — clients could self-escalate `scopes` via INSERT/UPDATE.
-- In R1, key issuance is a governed server-role flow. Remove client write policies;
-- clients keep read-only visibility (keys_own SELECT remains).
drop policy if exists "keys_insert_own" on public.api_keys;
drop policy if exists "keys_update_own" on public.api_keys;

-- FIX 2 (Critical): predictions — a client could forge a prediction against another
-- user's portfolio. Require the target portfolio to be the caller's own, or a
-- portfolio-less ad-hoc applicant scoring (portfolio_id is null).
alter policy "pred_insert_own" on public.predictions
  with check (
    created_by = auth.uid()
    and (
      portfolio_id is null
      or exists (select 1 from public.portfolios p
                 where p.id = portfolio_id and p.owner_id = auth.uid())
    )
  );

-- FIX 3 (Critical): human_decisions — require the referenced prediction to be one
-- the caller is authorized over (their own, or in their own portfolio).
alter policy "hd_insert_own" on public.human_decisions
  with check (
    decided_by = auth.uid()
    and exists (
      select 1 from public.predictions pr where pr.id = prediction_id
      and (pr.created_by = auth.uid()
           or exists (select 1 from public.portfolios p
                      where p.id = pr.portfolio_id and p.owner_id = auth.uid()))
    )
  );

-- FIX 4 (Critical): llm_reports — same authorization gate on the referenced prediction.
alter policy "llm_insert_own" on public.llm_reports
  with check (
    created_by = auth.uid()
    and exists (
      select 1 from public.predictions pr where pr.id = prediction_id
      and (pr.created_by = auth.uid()
           or exists (select 1 from public.portfolios p
                      where p.id = pr.portfolio_id and p.owner_id = auth.uid()))
    )
  );

-- FIX 5 (Important): fairness tables were world-readable including anon. Restrict to
-- authenticated users (role-level visibility is refined in the UI layer).
alter policy "fr_read_all"   on public.fairness_runs    using (auth.uid() is not null);
alter policy "fres_read_all" on public.fairness_results using (auth.uid() is not null);
