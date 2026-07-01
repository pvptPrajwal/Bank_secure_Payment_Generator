"""
security/master_hash_manager.py
---------------------------------
Upload and verify master file hashes.
The file is read locally to compute a SHA-256 hash.
Only the hash string is sent to / compared with the server.
"""
from database import api_client
from database.api_client import ApiError
from security.hash_engine import generate_file_hash


class MasterHashError(Exception):
    pass


def upload_master_file(file_path: str, adm_u: str, adm_p: str) -> dict:
    hash_value = generate_file_hash(file_path)   # local only
    try:
        return api_client.admin_upload_master_hash(adm_u, adm_p, hash_value)
    except ApiError as e:
        raise MasterHashError(str(e))


def get_all_versions(adm_u: str, adm_p: str) -> list:
    try:
        return api_client.admin_list_master_hash_versions(adm_u, adm_p)
    except ApiError as e:
        raise MasterHashError(str(e))


def verify_against_latest(file_path: str, username: str, password: str) -> tuple:
    """
    Returns (is_match: bool, computed_hash: str).
    The file is never sent anywhere — only the two hash strings are compared.
    """
    try:
        latest = api_client.get_latest_master_hash(username, password)
    except ApiError as e:
        raise MasterHashError(str(e))

    if latest is None:
        raise MasterHashError(
            "No master file hash registered yet. Ask the Administrator to upload the master file first."
        )

    computed = generate_file_hash(file_path)   # local only
    return computed.lower() == latest["hash_value"].lower(), computed
