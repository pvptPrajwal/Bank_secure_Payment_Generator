"""
auth/user_manager.py
---------------------
Administrator user management. Every function requires the calling
admin's own credentials — re-verified server-side on every call.
"""
from database import api_client
from database.api_client import ApiError


class UserManagerError(Exception):
    pass


def _check_password_policy(password: str):
    import re
    if len(password) < 8:
        raise UserManagerError("Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        raise UserManagerError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise UserManagerError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise UserManagerError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
        raise UserManagerError("Password must contain at least one special character.")


def create_user(adm_u: str, adm_p: str, new_u: str, new_p: str, role: str) -> dict:
    new_u = new_u.strip()
    if not new_u:
        raise UserManagerError("Username cannot be empty.")
    if role not in ("Administrator", "User"):
        raise UserManagerError("Role must be 'Administrator' or 'User'.")
    _check_password_policy(new_p)
    try:
        return api_client.admin_create_user(adm_u, adm_p, new_u, new_p, role)
    except ApiError as e:
        raise UserManagerError(str(e))


def disable_user(adm_u: str, adm_p: str, target: str):
    try:
        api_client.admin_set_active(adm_u, adm_p, target, False)
    except ApiError as e:
        raise UserManagerError(str(e))


def delete_user(adm_u: str, adm_p: str, target: str):
    """Permanently delete a user from the database. Cannot be undone."""
    try:
        api_client.admin_delete_user(adm_u, adm_p, target)
    except ApiError as e:
        raise UserManagerError(str(e))


def enable_user(adm_u: str, adm_p: str, target: str):
    try:
        api_client.admin_set_active(adm_u, adm_p, target, True)
    except ApiError as e:
        raise UserManagerError(str(e))


def reset_password(adm_u: str, adm_p: str, target: str, new_p: str):
    _check_password_policy(new_p)
    try:
        api_client.admin_reset_password(adm_u, adm_p, target, new_p)
    except ApiError as e:
        raise UserManagerError(str(e))


def change_own_password(username: str, old_p: str, new_p: str):
    _check_password_policy(new_p)
    try:
        api_client.change_own_password(username, old_p, new_p)
    except ApiError as e:
        raise UserManagerError(str(e))


def list_users(adm_u: str, adm_p: str) -> list:
    try:
        return api_client.admin_list_users(adm_u, adm_p)
    except ApiError as e:
        raise UserManagerError(str(e))
