"""
auth/user_manager.py — Multi-company version.
Wraps API calls with client-side password-policy validation.
All authorization + company isolation is enforced server-side.
"""
import re
from database import api_client
from database.api_client import ApiError


class UserManagerError(Exception):
    pass


def check_password_policy(password: str):
    if len(password) < 8:
        raise UserManagerError("Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        raise UserManagerError("Password needs at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise UserManagerError("Password needs at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise UserManagerError("Password needs at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
        raise UserManagerError("Password needs at least one special character.")


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ApiError as e:
        raise UserManagerError(str(e))


# ── Company Admin operations ────────────────────────────────────────────────

def create_user(au, ap, new_username, new_password):
    new_username = new_username.strip()
    if not new_username:
        raise UserManagerError("Username cannot be empty.")
    check_password_policy(new_password)
    _wrap(api_client.admin_create_user, au, ap, new_username, new_password)


def list_users(au, ap) -> list:
    return _wrap(api_client.admin_list_users, au, ap)


def manage_user(au, ap, target, action, new_password=None):
    if action == "reset_password":
        check_password_policy(new_password or "")
    _wrap(api_client.admin_manage_user, au, ap, target, action, new_password)


# ── Main Admin operations ────────────────────────────────────────────────────

def create_company(mu, mp, company_name, admin_user, admin_pw) -> dict:
    company_name = company_name.strip()
    admin_user = admin_user.strip()
    if not company_name:
        raise UserManagerError("Company name cannot be empty.")
    if not admin_user:
        raise UserManagerError("Admin username cannot be empty.")
    check_password_policy(admin_pw)
    return _wrap(api_client.main_create_company, mu, mp, company_name, admin_user, admin_pw)


def list_companies(mu, mp) -> list:
    return _wrap(api_client.main_list_companies, mu, mp)


def set_company_active(mu, mp, company_id, active):
    _wrap(api_client.main_set_company_active, mu, mp, company_id, active)


def create_company_admin(mu, mp, company_id, new_user, new_pw):
    check_password_policy(new_pw)
    _wrap(api_client.main_create_company_admin, mu, mp, company_id, new_user.strip(), new_pw)


def list_admins(mu, mp) -> list:
    return _wrap(api_client.main_list_admins, mu, mp)


def manage_admin(mu, mp, target, action, new_password=None):
    if action == "reset_password":
        check_password_policy(new_password or "")
    _wrap(api_client.main_manage_admin, mu, mp, target, action, new_password)


# ── Shared ───────────────────────────────────────────────────────────────────

def change_own_password(username, old_p, new_p):
    check_password_policy(new_p)
    _wrap(api_client.change_own_password, username, old_p, new_p)
