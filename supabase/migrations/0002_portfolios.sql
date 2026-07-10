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
