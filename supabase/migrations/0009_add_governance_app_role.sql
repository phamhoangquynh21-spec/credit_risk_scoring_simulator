-- 0009: add the missing 'governance' role to app_role.
--
-- The API (services/ml/routers/models.py -> require_role("governance") on
-- POST /api/v1/models/{semver}/promote, and audit.py ->
-- require_role("governance","compliance")) and the frontend (governance page:
-- `role === "governance"`) both gate on a governance role that migration 0001
-- never added to the enum (analyst/manager/compliance/executive/admin).
--
-- Effect of the gap: no user could ever hold 'governance', so the champion
-- promotion gate silently degraded to admin-only via require_role's admin
-- bypass, and the Governance page's promote control was unusable. Adding the
-- value makes the approval workflow work as designed.
--
-- Applied live via Supabase MCP on 2026-07-15.

alter type public.app_role add value if not exists 'governance';
