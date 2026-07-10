-- 0002_1_demo_flag_guard.sql
-- Security fix: clients may never set is_demo; demo portfolios are seeded
-- exclusively via the service role (which bypasses RLS).
alter policy "pf_insert_own" on public.portfolios
  with check (owner_id = auth.uid() and is_demo = false);
alter policy "pf_update_own" on public.portfolios
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid() and is_demo = false);
