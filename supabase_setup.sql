-- ============================================================================
-- supabase_setup_v3.sql  (MULTI-COMPANY / PRODUCTION VERSION)
-- ----------------------------------------------------------------------------
-- Hierarchy:
--   MainAdmin (software owner)  ->  Admin (one per client company)  ->  User
--
-- Data isolation: every company has its OWN users, master hashes, and audit
-- logs. A company admin can only see/manage rows with their own company_id.
-- The MainAdmin manages companies and company admins, and can see all
-- audit logs.
--
-- WARNING: This script DROPS and recreates the old tables. Any existing
-- users/hashes/logs from the previous version will be deleted. Run once.
-- ============================================================================

create extension if not exists pgcrypto;

drop table if exists "Audit_Logs" cascade;
drop table if exists "Master_Hashes" cascade;
drop table if exists "Users" cascade;
drop table if exists "Companies" cascade;

create table "Companies" (
    id serial primary key,
    name text unique not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create table "Users" (
    id serial primary key,
    username text unique not null,
    password_hash text not null,
    role text not null check (role in ('MainAdmin', 'Admin', 'User')),
    company_id integer references "Companies"(id) on delete cascade,
    is_active boolean not null default true,
    failed_attempts integer not null default 0,
    created_at timestamptz not null default now(),
    last_login timestamptz,
    -- MainAdmin has no company; Admin/User must belong to one
    constraint company_required check (
        (role = 'MainAdmin' and company_id is null)
        or (role in ('Admin', 'User') and company_id is not null)
    )
);

create table "Master_Hashes" (
    id serial primary key,
    company_id integer not null references "Companies"(id) on delete cascade,
    hash_value text not null,
    uploaded_by text not null,
    uploaded_at timestamptz not null default now(),
    version integer not null
);

create table "Audit_Logs" (
    id serial primary key,
    company_id integer,          -- null = system/MainAdmin-level events
    username text,
    action text not null,
    description text,
    timestamp timestamptz not null default now(),
    machine_name text
);

create index idx_users_username on "Users" (username);
create index idx_users_company on "Users" (company_id);
create index idx_hashes_company_version on "Master_Hashes" (company_id, version desc);
create index idx_audit_company on "Audit_Logs" (company_id, id desc);

-- ============================================================================
-- Helper: authenticate any caller. Returns the Users row or NULL.
-- ============================================================================
create or replace function _auth(p_username text, p_password text)
returns "Users"
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_user "Users"%rowtype;
begin
    select * into v_user from "Users" where username = p_username;
    if v_user.id is null or not v_user.is_active
       or v_user.password_hash != crypt(p_password, v_user.password_hash) then
        v_user.id := null;
    end if;
    return v_user;
end;
$$;

-- ============================================================================
-- login_user  (any role; handles lockout; returns company info too)
-- ============================================================================
create or replace function login_user(p_username text, p_password text, p_machine text default 'unknown')
returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_user "Users"%rowtype;
    v_attempts int;
    v_company_name text;
    v_company_active boolean;
begin
    select * into v_user from "Users" where username = p_username;

    if v_user.id is null then
        insert into "Audit_Logs" (company_id, username, action, description, machine_name)
        values (null, p_username, 'LOGIN_FAILED', 'No such username.', p_machine);
        return json_build_object('success', false, 'error', 'Invalid username or password.');
    end if;

    if not v_user.is_active then
        insert into "Audit_Logs" (company_id, username, action, description, machine_name)
        values (v_user.company_id, p_username, 'LOGIN_BLOCKED', 'Account disabled or locked.', p_machine);
        return json_build_object('success', false, 'error', 'This account is disabled. Contact your administrator.');
    end if;

    -- Company must also be active (for Admin/User roles)
    if v_user.company_id is not null then
        select name, is_active into v_company_name, v_company_active
        from "Companies" where id = v_user.company_id;
        if not v_company_active then
            insert into "Audit_Logs" (company_id, username, action, description, machine_name)
            values (v_user.company_id, p_username, 'LOGIN_BLOCKED', 'Company is deactivated.', p_machine);
            return json_build_object('success', false, 'error',
                'Your company account is deactivated. Contact the software provider.');
        end if;
    end if;

    if v_user.password_hash != crypt(p_password, v_user.password_hash) then
        v_attempts := v_user.failed_attempts + 1;
        if v_attempts >= 5 then
            update "Users" set failed_attempts = v_attempts, is_active = false where username = p_username;
            insert into "Audit_Logs" (company_id, username, action, description, machine_name)
            values (v_user.company_id, p_username, 'LOGIN_FAILED', 'Incorrect password. Account locked.', p_machine);
            return json_build_object('success', false, 'error',
                'Account locked after too many failed attempts. Contact your administrator.');
        else
            update "Users" set failed_attempts = v_attempts where username = p_username;
            insert into "Audit_Logs" (company_id, username, action, description, machine_name)
            values (v_user.company_id, p_username, 'LOGIN_FAILED', 'Incorrect password.', p_machine);
            return json_build_object('success', false, 'error',
                format('Invalid username or password. %s attempt(s) remaining before lockout.', 5 - v_attempts));
        end if;
    end if;

    update "Users" set failed_attempts = 0, last_login = now() where username = p_username;
    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_user.company_id, p_username, 'LOGIN_SUCCESS', 'User logged in.', p_machine);

    return json_build_object('success', true, 'user', (select row_to_json(t) from (
        select u.id, u.username, u.role, u.company_id, c.name as company_name,
               u.is_active, 0 as failed_attempts, u.created_at, u.last_login
        from "Users" u left join "Companies" c on c.id = u.company_id
        where u.username = p_username
    ) t));
end;
$$;

-- ============================================================================
-- change_own_password  (any role)
-- ============================================================================
create or replace function change_own_password(
    p_username text, p_old_password text, p_new_password text,
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_user "Users"%rowtype;
begin
    select * into v_user from "Users" where username = p_username;
    if v_user.id is null then
        return json_build_object('success', false, 'error', 'User not found.');
    end if;
    if v_user.password_hash != crypt(p_old_password, v_user.password_hash) then
        return json_build_object('success', false, 'error', 'Current password is incorrect.');
    end if;

    update "Users" set password_hash = crypt(p_new_password, gen_salt('bf', 12)) where username = p_username;
    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_user.company_id, p_username, 'PASSWORD_CHANGED', 'User changed their own password.', p_machine);
    return json_build_object('success', true);
end;
$$;

-- ============================================================================
-- MAIN ADMIN FUNCTIONS
-- ============================================================================

-- Create a company together with its first Admin account (one step)
create or replace function main_create_company(
    p_main_username text, p_main_password text,
    p_company_name text,
    p_admin_username text, p_admin_password text,
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
    v_company_id int;
begin
    v_caller := _auth(p_main_username, p_main_password);
    if v_caller.id is null or v_caller.role != 'MainAdmin' then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;

    if exists (select 1 from "Companies" where lower(name) = lower(p_company_name)) then
        return json_build_object('success', false, 'error', 'Company name already exists.');
    end if;
    if exists (select 1 from "Users" where username = p_admin_username) then
        return json_build_object('success', false, 'error', 'Admin username already exists.');
    end if;

    insert into "Companies" (name) values (p_company_name) returning id into v_company_id;

    insert into "Users" (username, password_hash, role, company_id)
    values (p_admin_username, crypt(p_admin_password, gen_salt('bf', 12)), 'Admin', v_company_id);

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_company_id, p_main_username, 'COMPANY_CREATED',
            format('Created company "%s" with admin "%s".', p_company_name, p_admin_username), p_machine);

    return json_build_object('success', true, 'company', (select row_to_json(t) from (
        select id, name, is_active, created_at from "Companies" where id = v_company_id
    ) t));
end;
$$;

-- List all companies with their admin usernames and user counts
create or replace function main_list_companies(p_main_username text, p_main_password text)
returns json
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

    return json_build_object('success', true, 'companies', (select coalesce(json_agg(t), '[]'::json) from (
        select c.id, c.name, c.is_active, c.created_at,
               (select string_agg(u.username, ', ') from "Users" u
                 where u.company_id = c.id and u.role = 'Admin') as admins,
               (select count(*) from "Users" u
                 where u.company_id = c.id and u.role = 'User') as user_count
        from "Companies" c order by c.id
    ) t));
end;
$$;

-- Activate/deactivate a whole company (blocks all its logins)
create or replace function main_set_company_active(
    p_main_username text, p_main_password text,
    p_company_id int, p_active boolean,
    p_machine text default 'unknown'
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
    if not exists (select 1 from "Companies" where id = p_company_id) then
        return json_build_object('success', false, 'error', 'Company not found.');
    end if;

    update "Companies" set is_active = p_active where id = p_company_id;
    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (p_company_id, p_main_username,
            case when p_active then 'COMPANY_ENABLED' else 'COMPANY_DISABLED' end,
            format('Company id %s set active=%s.', p_company_id, p_active), p_machine);
    return json_build_object('success', true);
end;
$$;

-- Create an additional Admin for an existing company
create or replace function main_create_company_admin(
    p_main_username text, p_main_password text,
    p_company_id int, p_new_username text, p_new_password text,
    p_machine text default 'unknown'
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
    if not exists (select 1 from "Companies" where id = p_company_id) then
        return json_build_object('success', false, 'error', 'Company not found.');
    end if;
    if exists (select 1 from "Users" where username = p_new_username) then
        return json_build_object('success', false, 'error', 'Username already exists.');
    end if;

    insert into "Users" (username, password_hash, role, company_id)
    values (p_new_username, crypt(p_new_password, gen_salt('bf', 12)), 'Admin', p_company_id);

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (p_company_id, p_main_username, 'ADMIN_CREATED',
            format('Created company admin "%s".', p_new_username), p_machine);
    return json_build_object('success', true);
end;
$$;

-- List all company admins (optionally MainAdmin can see everything)
create or replace function main_list_admins(p_main_username text, p_main_password text)
returns json
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

    return json_build_object('success', true, 'admins', (select coalesce(json_agg(t), '[]'::json) from (
        select u.id, u.username, c.name as company_name, u.company_id,
               u.is_active, u.failed_attempts, u.created_at, u.last_login
        from "Users" u join "Companies" c on c.id = u.company_id
        where u.role = 'Admin' order by c.name, u.username
    ) t));
end;
$$;

-- Enable/disable/reset/delete a company admin
create or replace function main_manage_admin(
    p_main_username text, p_main_password text,
    p_target_username text, p_action text,   -- 'enable' | 'disable' | 'delete'
    p_new_password text default null,        -- for 'reset_password'
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
    v_target "Users"%rowtype;
begin
    v_caller := _auth(p_main_username, p_main_password);
    if v_caller.id is null or v_caller.role != 'MainAdmin' then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;

    select * into v_target from "Users" where username = p_target_username and role = 'Admin';
    if v_target.id is null then
        return json_build_object('success', false, 'error', 'Company admin not found.');
    end if;

    if p_action = 'enable' then
        update "Users" set is_active = true, failed_attempts = 0 where id = v_target.id;
    elsif p_action = 'disable' then
        update "Users" set is_active = false where id = v_target.id;
    elsif p_action = 'delete' then
        delete from "Users" where id = v_target.id;
    elsif p_action = 'reset_password' then
        if p_new_password is null or length(p_new_password) = 0 then
            return json_build_object('success', false, 'error', 'New password required.');
        end if;
        update "Users" set password_hash = crypt(p_new_password, gen_salt('bf', 12)),
                             failed_attempts = 0, is_active = true
        where id = v_target.id;
    else
        return json_build_object('success', false, 'error', 'Unknown action.');
    end if;

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_target.company_id, p_main_username, 'ADMIN_' || upper(p_action),
            format('Action %s on company admin "%s".', p_action, p_target_username), p_machine);
    return json_build_object('success', true);
end;
$$;

-- MainAdmin can view ALL audit logs (optionally filtered by company)
create or replace function main_list_audit_logs(
    p_main_username text, p_main_password text,
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
        order by a.id desc limit p_limit
    ) t));
end;
$$;

-- ============================================================================
-- COMPANY ADMIN FUNCTIONS  (scoped strictly to caller's own company)
-- ============================================================================

create or replace function admin_create_user(
    p_admin_username text, p_admin_password text,
    p_new_username text, p_new_password text,
    p_machine text default 'unknown'
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
    if exists (select 1 from "Users" where username = p_new_username) then
        return json_build_object('success', false, 'error', 'Username already exists.');
    end if;

    -- New user is ALWAYS created inside the caller's own company, role User.
    insert into "Users" (username, password_hash, role, company_id)
    values (p_new_username, crypt(p_new_password, gen_salt('bf', 12)), 'User', v_caller.company_id);

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_caller.company_id, p_admin_username, 'USER_CREATED',
            format('Created user "%s".', p_new_username), p_machine);

    return json_build_object('success', true);
end;
$$;

create or replace function admin_list_users(p_admin_username text, p_admin_password text)
returns json
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

    -- ONLY users of the caller's own company. Company isolation enforced here.
    return json_build_object('success', true, 'users', (select coalesce(json_agg(t), '[]'::json) from (
        select id, username, role, is_active, failed_attempts, created_at, last_login
        from "Users"
        where company_id = v_caller.company_id and role = 'User'
        order by id
    ) t));
end;
$$;

create or replace function admin_manage_user(
    p_admin_username text, p_admin_password text,
    p_target_username text, p_action text,   -- 'enable' | 'disable' | 'delete' | 'reset_password'
    p_new_password text default null,
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
    v_target "Users"%rowtype;
begin
    v_caller := _auth(p_admin_username, p_admin_password);
    if v_caller.id is null or v_caller.role != 'Admin' then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;

    -- Target must be a User in the SAME company. This is the isolation wall:
    -- an admin can never touch users of another company.
    select * into v_target from "Users"
    where username = p_target_username and role = 'User'
      and company_id = v_caller.company_id;
    if v_target.id is null then
        return json_build_object('success', false, 'error', 'User not found in your company.');
    end if;

    if p_action = 'enable' then
        update "Users" set is_active = true, failed_attempts = 0 where id = v_target.id;
    elsif p_action = 'disable' then
        update "Users" set is_active = false where id = v_target.id;
    elsif p_action = 'delete' then
        delete from "Users" where id = v_target.id;
    elsif p_action = 'reset_password' then
        if p_new_password is null or length(p_new_password) = 0 then
            return json_build_object('success', false, 'error', 'New password required.');
        end if;
        update "Users" set password_hash = crypt(p_new_password, gen_salt('bf', 12)),
                             failed_attempts = 0, is_active = true
        where id = v_target.id;
    else
        return json_build_object('success', false, 'error', 'Unknown action.');
    end if;

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_caller.company_id, p_admin_username, 'USER_' || upper(p_action),
            format('Action %s on user "%s".', p_action, p_target_username), p_machine);
    return json_build_object('success', true);
end;
$$;

-- Company admin uploads THEIR company's master hash
create or replace function admin_upload_master_hash(
    p_admin_username text, p_admin_password text, p_hash_value text,
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
    v_next int;
begin
    v_caller := _auth(p_admin_username, p_admin_password);
    if v_caller.id is null or v_caller.role != 'Admin' then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;

    select coalesce(max(version), 0) + 1 into v_next
    from "Master_Hashes" where company_id = v_caller.company_id;

    insert into "Master_Hashes" (company_id, hash_value, uploaded_by, version)
    values (v_caller.company_id, p_hash_value, p_admin_username, v_next);

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (v_caller.company_id, p_admin_username, 'HASH_GENERATED',
            format('Registered master file v%s (hash %s...).', v_next, left(p_hash_value, 16)), p_machine);

    return json_build_object('success', true, 'hash', (select row_to_json(t) from (
        select id, hash_value, uploaded_by, uploaded_at, version
        from "Master_Hashes" where company_id = v_caller.company_id and version = v_next
    ) t));
end;
$$;

create or replace function admin_list_master_hash_versions(p_admin_username text, p_admin_password text)
returns json
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

    return json_build_object('success', true, 'versions', (select coalesce(json_agg(t), '[]'::json) from (
        select id, hash_value, uploaded_by, uploaded_at, version
        from "Master_Hashes" where company_id = v_caller.company_id
        order by version desc
    ) t));
end;
$$;

-- Any Admin or User of a company fetches THEIR company's latest hash
create or replace function get_latest_master_hash(p_username text, p_password text)
returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_caller "Users";
begin
    v_caller := _auth(p_username, p_password);
    if v_caller.id is null or v_caller.company_id is null then
        return json_build_object('success', false, 'error', 'Invalid credentials.');
    end if;

    return json_build_object('success', true, 'hash', (select row_to_json(t) from (
        select id, hash_value, uploaded_by, uploaded_at, version
        from "Master_Hashes" where company_id = v_caller.company_id
        order by version desc limit 1
    ) t));
end;
$$;

-- Company admin views THEIR company's audit logs only
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
        select id, username, action, description, timestamp, machine_name
        from "Audit_Logs" where company_id = v_caller.company_id
        order by id desc limit p_limit
    ) t));
end;
$$;

-- ============================================================================
-- Generic client-side event logger (low-risk, text only)
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
    values (v_cid, p_username, p_action, p_description, p_machine);
    return json_build_object('success', true);
end;
$$;

-- ============================================================================
-- Bootstrap: creates the very first MainAdmin. Works only when Users is empty.
-- ============================================================================
create or replace function bootstrap_main_admin(p_username text, p_password text)
returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
begin
    if exists (select 1 from "Users" limit 1) then
        return json_build_object('success', false, 'error', 'Setup already completed - a user already exists.');
    end if;

    insert into "Users" (username, password_hash, role, company_id)
    values (p_username, crypt(p_password, gen_salt('bf', 12)), 'MainAdmin', null);

    insert into "Audit_Logs" (company_id, username, action, description, machine_name)
    values (null, p_username, 'MAIN_ADMIN_CREATED', 'Initial main admin created via bootstrap.', 'setup-script');
    return json_build_object('success', true);
end;
$$;

-- ============================================================================
-- Grants + RLS
-- ============================================================================
grant execute on function login_user(text, text, text) to anon, authenticated;
grant execute on function change_own_password(text, text, text, text) to anon, authenticated;
grant execute on function main_create_company(text, text, text, text, text, text) to anon, authenticated;
grant execute on function main_list_companies(text, text) to anon, authenticated;
grant execute on function main_set_company_active(text, text, int, boolean, text) to anon, authenticated;
grant execute on function main_create_company_admin(text, text, int, text, text, text) to anon, authenticated;
grant execute on function main_list_admins(text, text) to anon, authenticated;
grant execute on function main_manage_admin(text, text, text, text, text, text) to anon, authenticated;
grant execute on function main_list_audit_logs(text, text, int) to anon, authenticated;
grant execute on function admin_create_user(text, text, text, text, text) to anon, authenticated;
grant execute on function admin_list_users(text, text) to anon, authenticated;
grant execute on function admin_manage_user(text, text, text, text, text, text) to anon, authenticated;
grant execute on function admin_upload_master_hash(text, text, text, text) to anon, authenticated;
grant execute on function admin_list_master_hash_versions(text, text) to anon, authenticated;
grant execute on function get_latest_master_hash(text, text) to anon, authenticated;
grant execute on function admin_list_audit_logs(text, text, int) to anon, authenticated;
grant execute on function log_event(text, text, text, text) to anon, authenticated;
grant execute on function bootstrap_main_admin(text, text) to anon, authenticated;

-- _auth is internal only - explicitly revoke public execution
revoke execute on function _auth(text, text) from anon, authenticated, public;

alter table "Companies" enable row level security;
alter table "Users" enable row level security;
alter table "Master_Hashes" enable row level security;
alter table "Audit_Logs" enable row level security;
-- No policies: direct table access is fully denied for the publishable key.
