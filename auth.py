"""Authentication helpers using the standard library's scrypt password hashing."""
import base64
import hashlib
import hmac
import os
from db import create_user, get_user


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt + digest).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        raw = base64.b64decode(stored_hash.encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def register(name: str, email: str, password: str) -> tuple[bool, str]:
    if not name.strip() or "@" not in email or len(password) < 8:
        return False, "Use a name, valid email, and password with at least 8 characters."
    if create_user(name, email, hash_password(password)):
        return True, "Account created. You can log in now."
    return False, "An account with that email already exists."


def login(email: str, password: str):
    user = get_user(email)
    if user and verify_password(password, user["password_hash"]):
        return dict(user)
    return None
