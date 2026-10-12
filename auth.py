import hashlib
import hmac
import re
import secrets
from database import create_user, get_user_by_email

ITERATIONS = 600_000

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS
    )
    return f"{salt.hex()}${digest.hex()}"

def verify_password(password, stored_hash):
    try:
        salt_hex, expected = stored_hash.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError, AttributeError):
        return False

def register_user(full_name, email, password, confirm_password):
    full_name = full_name.strip()
    email = email.strip().lower()
    if not full_name:
        return False, "Please enter your full name."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Please enter a valid email address."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    if password != confirm_password:
        return False, "Passwords do not match."
    if get_user_by_email(email):
        return False, "An account with this email already exists."
    try:
        create_user(full_name, email, hash_password(password))
        return True, "Registration successful! You can now log in."
    except Exception:
        if get_user_by_email(email):
            return False, "An account with this email already exists."
        return False, "Registration failed. Please try again."
