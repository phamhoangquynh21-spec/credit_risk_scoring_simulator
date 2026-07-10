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
