"""
main.py — Application entry point.
"""
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QObject, QEvent   # QObject + QEvent required for event filter

import config
from database import api_client
from auth.session_manager import session
from ui.styles import STYLESHEET, APP_TITLE
from ui.login_window import LoginWindow
from ui.admin_dashboard import AdminDashboard
from ui.user_dashboard import UserDashboard


# ── Activity filter ─────────────────────────────────────────────────────────
# MUST subclass QObject — installEventFilter() rejects plain Python objects.

class _ActivityFilter(QObject):
    def __init__(self, session_manager, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.KeyPress):
            self.session_manager.touch()
        return False   # never consume the event


# ── App controller ───────────────────────────────────────────────────────────

class AppController:
    def __init__(self, app: QApplication):
        self.app = app
        self.current_window = None
        self._activity_filter = None   # keep a reference so it isn't garbage-collected

        self.idle_timer = QTimer()
        self.idle_timer.setInterval(15_000)   # check every 15 s
        self.idle_timer.timeout.connect(self._check_timeout)

        self.show_login()

    def show_login(self):
        self.idle_timer.stop()
        self.current_window = LoginWindow(on_login_success=self._on_login)
        self.current_window.show()

    def _on_login(self, user: dict):
        self.current_window.close()
        if user["role"] == "Administrator":
            self.current_window = AdminDashboard(on_logout=self._on_logout)
        else:
            self.current_window = UserDashboard(on_logout=self._on_logout)
        self.current_window.show()
        self.idle_timer.start()
        self._activity_filter = _ActivityFilter(session)
        self.app.installEventFilter(self._activity_filter)

    def _on_logout(self):
        self.idle_timer.stop()
        if self._activity_filter:
            self.app.removeEventFilter(self._activity_filter)
            self._activity_filter = None
        self.current_window.close()
        self.show_login()

    def _check_timeout(self):
        if session.is_logged_in() and session.is_expired():
            username = session.username()
            from audit.logger import log_action
            log_action(username, "SESSION_TIMEOUT", "Session expired after 15 minutes of inactivity.")
            session.end_session()
            if self._activity_filter:
                self.app.removeEventFilter(self._activity_filter)
                self._activity_filter = None
            if self.current_window:
                self.current_window.close()
            QMessageBox.information(None, "Session Expired",
                "Your session has expired due to 15 minutes of inactivity.\nPlease log in again.")
            self.show_login()


# ── Icon helper ──────────────────────────────────────────────────────────────

def _set_app_icon(app: QApplication):
    """Load the app icon from resources/, works both in dev and as a .exe."""
    import os
    from PySide6.QtGui import QIcon

    # Locate resources/ folder correctly in both dev and PyInstaller modes
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    for name in ("app_icon.ico", "icon_small.png", "logo.png"):
        path = os.path.join(base, "resources", name)
        if os.path.exists(path):
            app.setWindowIcon(QIcon(path))
            break


# ── Global exception handler ─────────────────────────────────────────────────

def _excepthook(exc_type, exc_value, exc_tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(msg, file=sys.stderr)
    try:
        QMessageBox.critical(None, "Unexpected Error",
            f"An unexpected error occurred:\n\n{exc_value}\n\nDetails written to console.")
    except Exception:
        pass


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setStyleSheet(STYLESHEET)

    # Set application icon (works for taskbar, title bar, and .exe file icon)
    _set_app_icon(app)

    # Check .env is configured
    if not config.IS_CONFIGURED:
        QMessageBox.critical(None, "Configuration Missing",
            "Supabase is not configured.\n\n"
            "Create a .env file next to the application with:\n"
            "  SUPABASE_URL=https://your-project.supabase.co\n"
            "  SUPABASE_KEY=sb_publishable_...\n\n"
            "Then restart the application.")
        sys.exit(1)

    # Check server reachability
    try:
        api_client.check_connection()
    except api_client.ApiError as e:
        answer = QMessageBox.warning(None, "Server Unreachable",
            f"Cannot reach the online server:\n{e}\n\n"
            "You will not be able to log in until the connection is restored.\n\n"
            "Continue anyway?",
            QMessageBox.Ok | QMessageBox.Cancel)
        if answer == QMessageBox.Cancel:
            sys.exit(1)

    controller = AppController(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
