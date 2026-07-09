-- ============================================================================
-- audit_upgrade.sql  (Patch — apply after supabase_setup.sql)
-- Adds:
--   1. Company Admin sees ONLY their own company's User activity
--      (Admin's own actions filtered out).
--   2. Main Admin sees ALL logs with company name prefix in description,
--      supports date filtering (from/to) + company filter, and can
--      purge old logs to keep the free tier from filling up.
--   3. Every audit log INSERT going forward gets a "[Company X]" prefix
--      in its description via the log wrappers below.
-- ============================================================================

-- Helper: prepend company name to a description
create or replace function _prefix(p_company_id int, p_desc text)
returns text
language sql
security definer
set search_path = public, extensions
as $$
    select coalesce('[' || (select name from "Companies" where id = p_company_id) || '] ', '[SYSTEM] ')
           || coalesce(p_desc, '');
$$;

-- Backfill existing rows so old entries also show company name
update "Audit_Logs" a
set description = _prefix(a.company_id, a.description)
where a.description is not null
  and a.description not like '[%]%';

-- ============================================================================
-- OVERRIDE: log_event (auto-prefix company name)
-- ============================================================================
create or replace function log_event(
    p_username text, p_action text, p_description text,
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_cid int;
begin
    select company_id into v_cid from "Users" where username = p_username;
    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_cid, p_username, p_action, _prefix(v_cid, p_description), p_machine);
    return json_build_object('success', true);
end;
$$;

-- ============================================================================
-- OVERRIDE: admin_list_audit_logs
-- Now returns ONLY logs for the admin's own company USERS
-- (excludes the admin's own actions).
-- ============================================================================
create or replace function admin_list_audit_logs(
    p_admin_username text, p_admin_password text, p_limit int default 500
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
begin
    v_caller := _auth(p_admin_username, p_admin_password);
    if v_caller.id is null or v_caller.role != 'Admin' then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;

    return json_build_object('success', true, 'logs', (select coalesce(json_agg(t), '[]'::json) from (
        select a.id, a.username, a.action, a.description, a.timestamp, a.machine_name
        from "Audit_Logs" a
        join "Users" u on u.username = a.username
        where a.company_id = v_caller.company_id
          and u.role = 'User'                       -- only company-user actions
        order by a.id desc limit p_limit
    ) t));
end;
$$;

-- ============================================================================
-- OVERRIDE: main_list_audit_logs
-- Supports date range + optional company filter.
-- Pass p_from_date / p_to_date as ISO strings ('2026-07-01'), or NULL.
-- Pass p_company_id as null for all companies.
-- ============================================================================
drop function if exists main_list_audit_logs(text, text, int);

create or replace function main_list_audit_logs(
    p_main_username text, p_main_password text,
    p_from_date date default null,
    p_to_date   date default null,
    p_company_id int default null,
    p_limit int default 500
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
begin
    v_caller := _auth(p_main_username, p_main_password);
    if v_caller.id is null or v_caller.role != 'MainAdmin' then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;

    return json_build_object('success', true, 'logs', (select coalesce(json_agg(t), '[]'::json) from (
        select a.id, c.name as company_name, a.username, a.action,
               a.description, a.timestamp, a.machine_name
        from "Audit_Logs" a left join "Companies" c on c.id = a.company_id
        where (p_from_date is null or a.timestamp >= p_from_date::timestamptz)
          and (p_to_date   is null or a.timestamp <  (p_to_date + 1)::timestamptz)
          and (p_company_id is null or a.company_id = p_company_id)
        order by a.id desc limit p_limit
    ) t));
end;
$$;

-- ============================================================================
-- NEW: main_purge_old_logs
-- Deletes audit logs older than the given number of days.
-- Keeps the free tier under control.
-- ============================================================================
create or replace function main_purge_old_logs(
    p_main_username text, p_main_password text,
    p_older_than_days int,
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
    v_deleted int;
begin
    v_caller := _auth(p_main_username, p_main_password);
    if v_caller.id is null or v_caller.role != 'MainAdmin' then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;
    if p_older_than_days is null or p_older_than_days < 1 then
        return json_build_object('success', false, 'error', 'Days must be a positive integer.');
    end if;

    with deleted as (
        delete from "Audit_Logs"
        where timestamp < now() - (p_older_than_days || ' days')::interval
        returning 1
    )
    select count(*) into v_deleted from deleted;

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (null, p_main_username, 'LOGS_PURGED',
            format('[SYSTEM] Purged %s log(s) older than %s days.', v_deleted, p_older_than_days),
            p_machine);

    return json_build_object('success', true, 'deleted_count', v_deleted);
end;
$$;

-- Grants
grant execute on function _prefix(int, text) to anon, authenticated;
grant execute on function main_list_audit_logs(text, text, date, date, int, int) to anon, authenticated;
grant execute on function main_purge_old_logs(text, text, int, text) to anon, authenticated;
