"""
scripts/create_initial_admin.py
---------------------------------
Run ONCE after deploying supabase_setup.sql to create the first admin.
Only works when the Users table is completely empty.

Usage:
    python scripts\\create_initial_admin.py
"""
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import api_client
from database.api_client import ApiError


def check_policy(pw: str) -> tuple:
    if len(pw) < 8:
        return False, "Minimum 8 characters."
    if not re.search(r"[A-Z]", pw): return False, "Need at least one uppercase letter."
    if not re.search(r"[a-z]", pw): return False, "Need at least one lowercase letter."
    if not re.search(r"\d",    pw): return False, "Need at least one digit."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", pw):
        return False, "Need at least one special character (!@#$% etc.)."
    return True, "OK"


def main():
    print("=== Bank Payment File Generator — Initial Admin Setup ===\n")
    username = input("Choose an admin username [admin]: ").strip() or "admin"

    while True:
        password = input("Choose a strong admin password: ").strip()
        ok, msg = check_policy(password)
        if ok:
            break
        print(f"  ✗ {msg}  Try again.\n")

    try:
        api_client.bootstrap_first_admin(username, password)
    except ApiError as e:
        print(f"\n✗ Error: {e}")
        if "already exists" in str(e):
            print("\nThe initial admin was already created.")
            print("Log in with that account, then use Admin Dashboard → Create User for more accounts.")
        return

    print(f"\n✓ Administrator account '{username}' created successfully.")
    print("Run  python main.py  and log in with these credentials.")


if __name__ == "__main__":
    main()
