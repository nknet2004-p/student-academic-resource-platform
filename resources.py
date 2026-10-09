
from pathlib import Path
from uuid import uuid4
import sqlite3

from database import get_connection

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx",
    ".ppt", ".pptx",
    ".xls", ".xlsx", ".csv",
    ".txt", ".md",
    ".jpg", ".jpeg", ".png",
    ".gif", ".webp",
    ".zip"
}

MAX_FILE_SIZE = 20 * 1024 * 1024


def initialize_resource_table():
    UPLOAD_DIR.mkdir(exist_ok=True)

    with get_connection() as connection:
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


def save_resource(
    owner_id,
    title,
    description,
    subject,
    semester,
    resource_type,
    uploaded_file
):
    original_filename = Path(uploaded_file.name).name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("This file type is not supported.")

    file_bytes = uploaded_file.getvalue()

    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("Maximum file size is 20 MB.")

    stored_filename = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR / stored_filename

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO resources (
                owner_id, title, description, subject, semester,
                resource_type, original_filename, stored_filename,
                file_size
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            owner_id,
            title.strip(),
            description.strip(),
            subject,
            semester,
            resource_type,
            original_filename,
            stored_filename,
            len(file_bytes)
        ))

        try:
            destination.write_bytes(file_bytes)
        except OSError:
            connection.rollback()
            raise

        return cursor.lastrowid


def search_resources(
    keyword="",
    subject="All",
    semester="All",
    resource_type="All"
):
    query = """
        SELECT resources.*, users.full_name AS uploader
        FROM resources
        JOIN users ON users.id = resources.owner_id
        WHERE 1 = 1
    """
    parameters = []

    if keyword.strip():
        query += """
            AND (
                resources.title LIKE ?
                OR resources.description LIKE ?
                OR resources.subject LIKE ?
            )
        """
        term = f"%{keyword.strip()}%"
        parameters.extend([term, term, term])

    if subject != "All":
        query += " AND resources.subject = ?"
        parameters.append(subject)

    if semester != "All":
        query += " AND resources.semester = ?"
        parameters.append(semester)

    if resource_type != "All":
        query += " AND resources.resource_type = ?"
        parameters.append(resource_type)

    query += " ORDER BY resources.created_at DESC"

    with get_connection() as connection:
        return connection.execute(query, parameters).fetchall()


def get_resource_file(stored_filename):
    filename = Path(stored_filename).name

    if filename != stored_filename:
        return None

    path = UPLOAD_DIR / filename

    if not path.is_file():
        return None

    return path.read_bytes()


def increment_downloads(resource_id):
    with get_connection() as connection:
        connection.execute("""
            UPDATE resources
            SET downloads = downloads + 1
            WHERE id = ?
        """, (resource_id,))


def delete_resource(resource_id, owner_id):
    with get_connection() as connection:
        resource = connection.execute("""
            SELECT stored_filename
            FROM resources
            WHERE id = ? AND owner_id = ?
        """, (resource_id, owner_id)).fetchone()

        if resource is None:
            return False

        connection.execute(
            "DELETE FROM resources WHERE id = ? AND owner_id = ?",
            (resource_id, owner_id)
        )

        path = UPLOAD_DIR / resource["stored_filename"]

        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

        return True
