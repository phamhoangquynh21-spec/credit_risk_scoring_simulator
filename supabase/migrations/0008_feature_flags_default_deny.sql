-- 0008: defense-in-depth for gated data connectors (Stage 6 QA finding #3).
-- A bare INSERT of a flag key previously defaulted enabled=true, silently
-- arming a gate. Flip the default to false and seed the three gated flags
-- explicitly OFF (no-op if rows already exist).
-- Applied live via Supabase MCP on 2026-07-13.

alter table public.feature_flags alter column enabled set default false;

insert into public.feature_flags (key, enabled, note) values
  ('freddie_enabled',     false, 'Gated: enable only after Freddie Mac registration + license verification'),
  ('bureau_enabled',      false, 'Gated: enable only after commercial bureau contract + legal approval'),
  ('openbanking_enabled', false, 'Gated: enable only after CDR accreditation or accredited partner')
on conflict (key) do nothing;
