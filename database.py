
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "students.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


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


def create_user(full_name, email, password_hash):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (full_name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (full_name, email, password_hash)
        )


def get_user_by_email(email):
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
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
