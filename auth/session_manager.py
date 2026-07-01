"""
auth/session_manager.py
------------------------
Tracks the currently logged-in user and enforces a 15-minute idle timeout.
The plaintext password is stored in RAM only (never written to disk) so
that privileged API calls can re-authenticate with the server each time.
"""
from datetime import datetime, timedelta

SESSION_TIMEOUT_MINUTES = 15


class SessionManager:
    def __init__(self, timeout_minutes: int = SESSION_TIMEOUT_MINUTES):
        self.timeout = timedelta(minutes=timeout_minutes)
        self.current_user = None
        self._password = None        # RAM only, never written to disk
        self.last_activity = None

    def start_session(self, user: dict, password: str):
        self.current_user = user
        self._password = password
        self.last_activity = datetime.now()

    def touch(self):
        """Call on any user interaction to reset the idle timer."""
        if self.current_user:
            self.last_activity = datetime.now()

    def end_session(self):
        self.current_user = None
        self._password = None
        self.last_activity = None

    def update_password(self, new_password: str):
        """Call after a successful self-password-change."""
        self._password = new_password

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def is_expired(self) -> bool:
        if not self.current_user or not self.last_activity:
            return False
        return datetime.now() - self.last_activity > self.timeout

    def is_admin(self) -> bool:
        return self.is_logged_in() and self.current_user.get("role") == "Administrator"

    def username(self) -> str:
        return self.current_user["username"] if self.current_user else ""

    def password(self) -> str:
        return self._password or ""

    def time_remaining_seconds(self) -> int:
        if not self.current_user or not self.last_activity:
            return 0
        remaining = self.timeout - (datetime.now() - self.last_activity)
        return max(0, int(remaining.total_seconds()))


# Single shared instance used across the whole application
session = SessionManager()
