-- Run this in Supabase SQL Editor to add the permanent delete function
create or replace function admin_delete_user(
    p_admin_username text, p_admin_password text,
    p_target_username text,
    p_machine text default 'unknown'
) returns json
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
    v_admin "Users"%rowtype;
begin
    select * into v_admin from "Users" where username = p_admin_username;
    if v_admin.id is null or not v_admin.is_active or v_admin.role != 'Administrator'
       or v_admin.password_hash != crypt(p_admin_password, v_admin.password_hash) then
        return json_build_object('success', false, 'error', 'Not authorized.');
    end if;

    if p_target_username = p_admin_username then
        return json_build_object('success', false, 'error', 'You cannot delete your own account.');
    end if;

    if not exists (select 1 from "Users" where username = p_target_username) then
        return json_build_object('success', false, 'error', 'User not found.');
    end if;

    delete from "Users" where username = p_target_username;

    insert into "Audit_Logs" (username, action, description, machine_name)
    values (p_admin_username, 'USER_DELETED',
            format('Permanently deleted user: %s', p_target_username), p_machine);

    return json_build_object('success', true);
end;
$$;

grant execute on function admin_delete_user(text, text, text, text) to anon, authenticated;
