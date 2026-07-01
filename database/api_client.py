"""
database/api_client.py
-----------------------
The ONLY module that makes network calls.
Uses the publishable key + SECURITY DEFINER Postgres functions.
Every privileged call re-verifies username + password server-side.
Master/payment file contents NEVER pass through here.
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
            raise ApiError(f"Could not connect to Supabase: {e}")
    return _client


def machine_name() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "UNKNOWN"


def check_connection():
    """Startup connectivity check. Expects 'Invalid credentials' response — that means the server is up."""
    try:
        _call("get_latest_master_hash", {"p_username": "__ping__", "p_password": "__ping__"})
    except ApiError as e:
        if "Invalid credentials" in str(e):
            return   # Server is reachable and responding correctly
        raise


def _call(fn: str, params: dict) -> dict:
    """Call a Postgres RPC function. Raises ApiError on failure."""
    try:
        res = get_client().rpc(fn, params).execute()
    except Exception as e:
        raise ApiError(f"Could not reach the online server. Check your internet connection.\nDetails: {e}")

    data = res.data
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        raise ApiError(f"Unexpected response from server ({fn}).")
    if not data.get("success", False):
        raise ApiError(data.get("error", "Request rejected by server."))
    return data


# ── Authentication ──────────────────────────────────────────────────────────

def login(username: str, password: str) -> dict:
    return _call("login_user", {
        "p_username": username,
        "p_password": password,
        "p_machine": machine_name(),
    })["user"]


def change_own_password(username: str, old_pw: str, new_pw: str):
    _call("change_own_password", {
        "p_username": username,
        "p_old_password": old_pw,
        "p_new_password": new_pw,
        "p_machine": machine_name(),
    })


# ── Admin: user management ───────────────────────────────────────────────────

def admin_create_user(adm_u: str, adm_p: str, new_u: str, new_p: str, role: str) -> dict:
    return _call("admin_create_user", {
        "p_admin_username": adm_u, "p_admin_password": adm_p,
        "p_new_username": new_u, "p_new_password": new_p,
        "p_role": role, "p_machine": machine_name(),
    })["user"]


def admin_set_active(adm_u: str, adm_p: str, target: str, active: bool) -> dict:
    return _call("admin_set_active", {
        "p_admin_username": adm_u, "p_admin_password": adm_p,
        "p_target_username": target, "p_active": active,
        "p_machine": machine_name(),
    })["user"]


def admin_delete_user(adm_u: str, adm_p: str, target: str):
    _call("admin_delete_user", {
        "p_admin_username": adm_u, "p_admin_password": adm_p,
        "p_target_username": target, "p_machine": machine_name(),
    })


def admin_reset_password(adm_u: str, adm_p: str, target: str, new_pw: str):
    _call("admin_reset_password", {
        "p_admin_username": adm_u, "p_admin_password": adm_p,
        "p_target_username": target, "p_new_password": new_pw,
        "p_machine": machine_name(),
    })


def admin_list_users(adm_u: str, adm_p: str) -> list:
    return _call("admin_list_users", {
        "p_admin_username": adm_u,
        "p_admin_password": adm_p,
    })["users"]


# ── Master hash ──────────────────────────────────────────────────────────────

def admin_upload_master_hash(adm_u: str, adm_p: str, hash_value: str) -> dict:
    return _call("admin_upload_master_hash", {
        "p_admin_username": adm_u, "p_admin_password": adm_p,
        "p_hash_value": hash_value, "p_machine": machine_name(),
    })["hash"]


def get_latest_master_hash(username: str, password: str):
    return _call("get_latest_master_hash", {
        "p_username": username,
        "p_password": password,
    }).get("hash")


def admin_list_master_hash_versions(adm_u: str, adm_p: str) -> list:
    return _call("admin_list_master_hash_versions", {
        "p_admin_username": adm_u,
        "p_admin_password": adm_p,
    })["versions"]


# ── Audit log ────────────────────────────────────────────────────────────────

def log_event(username: str, action: str, description: str):
    try:
        _call("log_event", {
            "p_username": username,
            "p_action": action,
            "p_description": description,
            "p_machine": machine_name(),
        })
    except ApiError:
        pass   # logging failure must never crash the app


def admin_list_audit_logs(adm_u: str, adm_p: str, limit: int = 500) -> list:
    return _call("admin_list_audit_logs", {
        "p_admin_username": adm_u,
        "p_admin_password": adm_p,
        "p_limit": limit,
    })["logs"]


# ── First-time setup ─────────────────────────────────────────────────────────

def bootstrap_first_admin(username: str, password: str):
    """Only succeeds once — when the Users table is completely empty."""
    _call("bootstrap_first_admin", {
        "p_username": username,
        "p_password": password,
    })
