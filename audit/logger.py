"""
audit/logger.py
-----------------
Logs events to the online Audit_Logs table AND to a local daily text
file. If the server is unreachable, the local log still records the
event (tagged [OFFLINE]).
"""
import os
from datetime import datetime
from database import api_client

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def _write_local(username, action, description, note=""):
    ts = datetime.now().isoformat(timespec="seconds")
    log_file = os.path.join(LOG_DIR, f"audit_{datetime.now().strftime('%Y-%m-%d')}.log")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [{api_client.machine_name()}] [{username}] {action}: {description}{' ' + note if note else ''}\n")
    except OSError:
        pass


def log_action(username: str, action: str, description: str = ""):
    try:
        api_client.log_event(username, action, description)
        _write_local(username, action, description)
    except Exception:
        _write_local(username, action, description, note="[OFFLINE]")


def get_logs(adm_u: str, adm_p: str, limit: int = 500) -> list:
    return api_client.admin_list_audit_logs(adm_u, adm_p, limit=limit)
