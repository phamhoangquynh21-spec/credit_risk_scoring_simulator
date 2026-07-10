-- 0007_user_fk_ondelete.sql
-- Deleting a user must not fail with FK-restrict errors. Preserve the record but
-- null the actor reference (audit_logs separately retains actor_id for the trail).
-- Ownership tables (portfolios, profiles, api_keys) already cascade — unchanged.

alter table public.predictions
  drop constraint predictions_created_by_fkey,
  add constraint predictions_created_by_fkey
    foreign key (created_by) references auth.users(id) on delete set null;

alter table public.llm_reports
  drop constraint llm_reports_created_by_fkey,
  add constraint llm_reports_created_by_fkey
    foreign key (created_by) references auth.users(id) on delete set null;

alter table public.model_versions
  drop constraint model_versions_approved_by_fkey,
  add constraint model_versions_approved_by_fkey
    foreign key (approved_by) references auth.users(id) on delete set null;

-- human_decisions.decided_by is NOT NULL by design; relax it so the decision
-- record survives actor deletion (who-decided is still captured in audit_logs).
alter table public.human_decisions
  alter column decided_by drop not null;
alter table public.human_decisions
  drop constraint human_decisions_decided_by_fkey,
  add constraint human_decisions_decided_by_fkey
    foreign key (decided_by) references auth.users(id) on delete set null;
