
import os
from getpass import getpass

from database import initialize_database, get_connection
from auth import hash_password

email = input("Admin email: ").strip().lower()
password = getpass("Choose admin password (at least 10 characters): ")
name = input("Admin name: ").strip() or "Platform Administrator"

if "@" not in email:
    raise SystemExit("Enter a valid email address.")

if len(password) < 10:
    raise SystemExit("Password must be at least 10 characters.")

initialize_database()

with get_connection() as connection:
    existing = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if existing:
        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, role = 'admin', is_active = 1,
                full_name = ?
            WHERE id = ?
            """,
            (hash_password(password), name, existing["id"]),
        )
    else:
        connection.execute(
            """
            INSERT INTO users
                (full_name, email, password_hash, role, is_active)
            VALUES (?, ?, ?, 'admin', 1)
            """,
            (name, email, hash_password(password)),
        )

print("Administrator account created or updated successfully.")
