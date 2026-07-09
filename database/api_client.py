"""
database/api_client.py — Multi-company version.
The ONLY module that makes network calls. Uses publishable key +
SECURITY DEFINER RPC functions. Every privileged call re-verifies
credentials server-side. Company isolation is enforced server-side.
"""
import socket
from supabase import create_client, Client
import config

_client: Client = None


class ApiError(Exception):
    pass


def get_client() -> Client:
    global _client
    config.require_configured()
    if _client is None:
        try:
            _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        except Exception as e:
            raise ApiError(f"Could not connect: {e}")
    return _client


def machine_name() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "UNKNOWN"


def check_connection():
    try:
        _call("get_latest_master_hash", {"p_username": "__ping__", "p_password": "__ping__"})
    except ApiError as e:
        if "Invalid credentials" in str(e):
            return
        raise


def _call(fn: str, params: dict) -> dict:
    try:
        res = get_client().rpc(fn, params).execute()
    except Exception as e:
        raise ApiError(f"Could not reach the online server. Check your internet connection.\nDetails: {e}")
    data = res.data
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        raise ApiError(f"Unexpected response ({fn}).")
    if not data.get("success", False):
        raise ApiError(data.get("error", "Request rejected by server."))
    return data


# ── Common (all roles) ───────────────────────────────────────────────────────

def login(username: str, password: str) -> dict:
    return _call("login_user", {
        "p_username": username, "p_password": password,
        "p_machine": machine_name(),
    })["user"]


def change_own_password(username: str, old_pw: str, new_pw: str):
    _call("change_own_password", {
        "p_username": username, "p_old_password": old_pw,
        "p_new_password": new_pw, "p_machine": machine_name(),
    })


def log_event(username: str, action: str, description: str):
    try:
        _call("log_event", {
            "p_username": username, "p_action": action,
            "p_description": description, "p_machine": machine_name(),
        })
    except ApiError:
        pass


# ── Main Admin ───────────────────────────────────────────────────────────────

def main_create_company(mu, mp, company_name, admin_user, admin_pw) -> dict:
    return _call("main_create_company", {
        "p_main_username": mu, "p_main_password": mp,
        "p_company_name": company_name,
        "p_admin_username": admin_user, "p_admin_password": admin_pw,
        "p_machine": machine_name(),
    })["company"]


def main_list_companies(mu, mp) -> list:
    return _call("main_list_companies", {
        "p_main_username": mu, "p_main_password": mp,
    })["companies"]


def main_set_company_active(mu, mp, company_id: int, active: bool):
    _call("main_set_company_active", {
        "p_main_username": mu, "p_main_password": mp,
        "p_company_id": company_id, "p_active": active,
        "p_machine": machine_name(),
    })


def main_create_company_admin(mu, mp, company_id: int, new_user, new_pw):
    _call("main_create_company_admin", {
        "p_main_username": mu, "p_main_password": mp,
        "p_company_id": company_id,
        "p_new_username": new_user, "p_new_password": new_pw,
        "p_machine": machine_name(),
    })


def main_list_admins(mu, mp) -> list:
    return _call("main_list_admins", {
        "p_main_username": mu, "p_main_password": mp,
    })["admins"]


def main_manage_admin(mu, mp, target: str, action: str, new_password: str = None):
    _call("main_manage_admin", {
        "p_main_username": mu, "p_main_password": mp,
        "p_target_username": target, "p_action": action,
        "p_new_password": new_password, "p_machine": machine_name(),
    })


def main_list_audit_logs(mu, mp, from_date=None, to_date=None, company_id=None, limit: int = 500) -> list:
    return _call("main_list_audit_logs", {
        "p_main_username": mu, "p_main_password": mp,
        "p_from_date": from_date, "p_to_date": to_date,
        "p_company_id": company_id, "p_limit": limit,
    })["logs"]


def main_purge_old_logs(mu, mp, older_than_days: int) -> int:
    d = _call("main_purge_old_logs", {
        "p_main_username": mu, "p_main_password": mp,
        "p_older_than_days": older_than_days,
        "p_machine": machine_name(),
    })
    return d.get("deleted_count", 0)


# ── Company Admin ────────────────────────────────────────────────────────────

def admin_create_user(au, ap, new_user, new_pw):
    _call("admin_create_user", {
        "p_admin_username": au, "p_admin_password": ap,
        "p_new_username": new_user, "p_new_password": new_pw,
        "p_machine": machine_name(),
    })


def admin_list_users(au, ap) -> list:
    return _call("admin_list_users", {
        "p_admin_username": au, "p_admin_password": ap,
    })["users"]


def admin_manage_user(au, ap, target: str, action: str, new_password: str = None):
    _call("admin_manage_user", {
        "p_admin_username": au, "p_admin_password": ap,
        "p_target_username": target, "p_action": action,
        "p_new_password": new_password, "p_machine": machine_name(),
    })


def admin_upload_master_hash(au, ap, hash_value: str) -> dict:
    return _call("admin_upload_master_hash", {
        "p_admin_username": au, "p_admin_password": ap,
        "p_hash_value": hash_value, "p_machine": machine_name(),
    })["hash"]


def admin_list_master_hash_versions(au, ap) -> list:
    return _call("admin_list_master_hash_versions", {
        "p_admin_username": au, "p_admin_password": ap,
    })["versions"]


def admin_list_audit_logs(au, ap, limit: int = 500) -> list:
    return _call("admin_list_audit_logs", {
        "p_admin_username": au, "p_admin_password": ap, "p_limit": limit,
    })["logs"]


# ── User / Admin ─────────────────────────────────────────────────────────────

def get_latest_master_hash(username: str, password: str):
    return _call("get_latest_master_hash", {
        "p_username": username, "p_password": password,
    }).get("hash")


# ── Setup ────────────────────────────────────────────────────────────────────

def bootstrap_main_admin(username: str, password: str):
    _call("bootstrap_main_admin", {
        "p_username": username, "p_password": password,
    })
