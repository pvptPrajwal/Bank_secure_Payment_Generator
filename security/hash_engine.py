"""
security/hash_engine.py
------------------------
SHA-256 hashing of files. Always runs locally — file contents
never leave the machine. Only the resulting hash string is ever
sent to the server.
"""
import hashlib

CHUNK = 65536  # 64 KB


def generate_file_hash(file_path: str) -> str:
    """Stream-hash a file and return its lowercase hex SHA-256 digest."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()
