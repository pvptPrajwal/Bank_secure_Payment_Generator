"""
auth/auth_manager.py
---------------------
Login / logout. All verification, lockout, and audit logging happens
server-side inside the login_user Postgres function.
"""
from database import api_client
from database.api_client import ApiError


class AuthError(Exception):
    pass


def login(username: str, password: str) -> dict:
    """Returns user dict on success. Raises AuthError on failure."""
    try:
        return api_client.login(username.strip(), password)
    except ApiError as e:
        raise AuthError(str(e))


def logout(username: str):
    api_client.log_event(username, "LOGOUT", "User logged out.")
