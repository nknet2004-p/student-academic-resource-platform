import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "students.db"

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def _columns(connection, table):
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}

def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = _columns(connection, "users")
        if "role" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
        if "is_active" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

        connection.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                subject TEXT NOT NULL,
                semester TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                downloads INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                user_id INTEGER NOT NULL,
                resource_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, resource_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER NOT NULL,
                resource_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, resource_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                reporter_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
                FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS moderation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                resource_id INTEGER,
                action TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def create_user(full_name, email, password_hash):
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name.strip(), email.strip().lower(), password_hash)
        )

def get_user_by_email(email):
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.strip().lower(),)
        ).fetchone()

def update_user_profile(user_id, full_name):
    full_name = full_name.strip()
    if not full_name:
        raise ValueError("Full name cannot be empty.")
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE users SET full_name = ? WHERE id = ?",
            (full_name, user_id)
        )
        return cursor.rowcount > 0

def list_users():
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, full_name, email, role, is_active, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()

def set_user_active(user_id, is_active):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE users SET is_active = ? WHERE id = ? AND role != 'admin'",
            (1 if is_active else 0, user_id)
        )
        return cursor.rowcount > 0

def set_user_role(user_id, role):
    if role not in ("student", "admin"):
        raise ValueError("Invalid role.")
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id)
        )
        return cursor.rowcount > 0

def create_admin_if_configured():
    """Creates/promotes an admin only when ADMIN_EMAIL and ADMIN_PASSWORD are configured."""
    import os
    from auth import hash_password
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    name = os.getenv("ADMIN_NAME", "Platform Administrator").strip()
    if not email or not password:
        return
    if len(password) < 10:
        raise ValueError("ADMIN_PASSWORD must be at least 10 characters.")
    with get_connection() as connection:
        row = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            connection.execute(
                "UPDATE users SET role='admin', is_active=1 WHERE id=?",
                (row["id"],)
            )
        else:
            connection.execute(
                "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                (name, email, hash_password(password))
            )
