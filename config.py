"""
config.py — Loads Supabase credentials from the .env file.
Uses the low-privilege PUBLISHABLE key (not the secret key).
"""
import os
import sys
from dotenv import load_dotenv

# Works correctly both as a plain Python script AND as a PyInstaller .exe
if getattr(sys, "frozen", False):
    _base = os.path.dirname(sys.executable)
else:
    _base = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(_base, ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
IS_CONFIGURED = bool(SUPABASE_URL and SUPABASE_KEY)


class ConfigError(Exception):
    pass


def require_configured():
    if not IS_CONFIGURED:
        raise ConfigError(
            "Supabase is not configured.\n"
            "Create a .env file next to the application with:\n"
            "  SUPABASE_URL=https://your-project.supabase.co\n"
            "  SUPABASE_KEY=sb_publishable_..."
        )
