"""
config.py — Loads Supabase credentials.
Works both as Python script AND as PyInstaller .exe with bundled .env.
"""
import os
import sys
from dotenv import load_dotenv


def _find_env():
    # Running as PyInstaller .exe
    if getattr(sys, "frozen", False):
        # First try next to the .exe (allows override)
        exe_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(exe_dir, ".env")):
            return os.path.join(exe_dir, ".env")
        # Fall back to bundled .env inside the .exe
        return os.path.join(sys._MEIPASS, ".env")
    # Running as normal Python script
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


load_dotenv(_find_env())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
IS_CONFIGURED = bool(SUPABASE_URL and SUPABASE_KEY)


class ConfigError(Exception):
    pass


def require_configured():
    if not IS_CONFIGURED:
        raise ConfigError(
            "Supabase is not configured. Contact your administrator."
        )