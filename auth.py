
import hashlib
import hmac
import secrets
import re

from database import create_user, get_user_by_email

ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS
    )
    return f"{salt.hex()}${password_hash.hex()}"


def verify_password(password, stored_hash):
    try:
        salt_hex, expected_hash = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            ITERATIONS
        )

        return hmac.compare_digest(
            actual_hash.hex(),
            expected_hash
        )
    except (ValueError, TypeError):
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

    password_hash = hash_password(password)

    try:
        create_user(full_name, email, password_hash)
        return True, "Registration successful! You can now log in."
    except Exception:
        if get_user_by_email(email):
            return False, "An account with this email already exists."
        return False, "Registration failed. Please try again."
