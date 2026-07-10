-- 0003_2_demo_delete_guard.sql
-- Defense-in-depth: demo portfolios must be undeletable via any client session
-- (only the service role, which bypasses RLS, may remove them).
alter policy "pf_delete_own" on public.portfolios
  using (owner_id = auth.uid() and is_demo = false);
