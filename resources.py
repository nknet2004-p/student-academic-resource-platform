from pathlib import Path
from uuid import uuid4
from database import get_connection

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".csv", ".txt", ".md", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".zip"
}
MAX_FILE_SIZE = 20 * 1024 * 1024

def initialize_resource_table():
    UPLOAD_DIR.mkdir(exist_ok=True)
    # Database initialization creates/migrates the table.
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

def save_resource(owner_id, title, description, subject, semester, resource_type, uploaded_file):
    title = title.strip()
    if not title:
        raise ValueError("Resource title is required.")
    original_filename = Path(uploaded_file.name).name
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("This file type is not supported.")
    file_bytes = uploaded_file.getvalue()
    if not file_bytes:
        raise ValueError("The uploaded file is empty.")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("Maximum file size is 20 MB.")
    UPLOAD_DIR.mkdir(exist_ok=True)
    stored_filename = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR / stored_filename
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO resources
            (owner_id, title, description, subject, semester, resource_type,
             original_filename, stored_filename, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            owner_id, title, description.strip(), subject, str(semester),
            resource_type, original_filename, stored_filename, len(file_bytes)
        ))
        try:
            destination.write_bytes(file_bytes)
        except OSError:
            connection.rollback()
            raise
        return cursor.lastrowid

def search_resources(keyword="", subject="All", semester="All", resource_type="All"):
    query = """
        SELECT resources.*, users.full_name AS uploader,
               COALESCE(AVG(ratings.rating), 0) AS average_rating,
               COUNT(DISTINCT ratings.user_id) AS rating_count
        FROM resources
        JOIN users ON users.id = resources.owner_id
        LEFT JOIN ratings ON ratings.resource_id = resources.id
        WHERE users.is_active = 1
    """
    params = []
    if keyword.strip():
        query += " AND (resources.title LIKE ? OR resources.description LIKE ? OR resources.subject LIKE ?)"
        term = f"%{keyword.strip()}%"
        params.extend([term, term, term])
    if subject != "All":
        query += " AND resources.subject = ?"
        params.append(subject)
    if semester != "All":
        query += " AND resources.semester = ?"
        params.append(str(semester))
    if resource_type != "All":
        query += " AND resources.resource_type = ?"
        params.append(resource_type)
    query += " GROUP BY resources.id ORDER BY resources.created_at DESC"
    with get_connection() as connection:
        return connection.execute(query, params).fetchall()

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
        connection.execute(
            "UPDATE resources SET downloads = downloads + 1 WHERE id = ?",
            (resource_id,)
        )

def update_resource(resource_id, owner_id, title, description, subject, semester, resource_type):
    title = title.strip()
    description = description.strip()
    if not title:
        raise ValueError("Resource title is required.")
    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE resources
            SET title=?, description=?, subject=?, semester=?, resource_type=?
            WHERE id=? AND owner_id=?
        """, (title, description, subject, str(semester), resource_type, resource_id, owner_id))
        return cursor.rowcount > 0

def delete_resource(resource_id, owner_id):
    with get_connection() as connection:
        resource = connection.execute(
            "SELECT stored_filename FROM resources WHERE id=? AND owner_id=?",
            (resource_id, owner_id)
        ).fetchone()
        if resource is None:
            return False
        connection.execute(
            "DELETE FROM resources WHERE id=? AND owner_id=?",
            (resource_id, owner_id)
        )
        path = UPLOAD_DIR / Path(resource["stored_filename"]).name
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return True

def toggle_bookmark(user_id, resource_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM bookmarks WHERE user_id=? AND resource_id=?",
            (user_id, resource_id)
        ).fetchone()
        if row:
            connection.execute(
                "DELETE FROM bookmarks WHERE user_id=? AND resource_id=?",
                (user_id, resource_id)
            )
            return False
        connection.execute(
            "INSERT OR IGNORE INTO bookmarks (user_id, resource_id) VALUES (?, ?)",
            (user_id, resource_id)
        )
        return True

def is_bookmarked(user_id, resource_id):
    with get_connection() as connection:
        return connection.execute(
            "SELECT 1 FROM bookmarks WHERE user_id=? AND resource_id=?",
            (user_id, resource_id)
        ).fetchone() is not None

def get_bookmarks(user_id):
    with get_connection() as connection:
        return connection.execute("""
            SELECT resources.*, users.full_name AS uploader
            FROM bookmarks
            JOIN resources ON resources.id = bookmarks.resource_id
            JOIN users ON users.id = resources.owner_id
            WHERE bookmarks.user_id=? AND users.is_active=1
            ORDER BY bookmarks.created_at DESC
        """, (user_id,)).fetchall()

def rate_resource(user_id, resource_id, rating):
    if rating not in range(1, 6):
        raise ValueError("Rating must be from 1 to 5.")
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO ratings (user_id, resource_id, rating)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, resource_id)
            DO UPDATE SET rating=excluded.rating, created_at=CURRENT_TIMESTAMP
        """, (user_id, resource_id, rating))

def get_user_rating(user_id, resource_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT rating FROM ratings WHERE user_id=? AND resource_id=?",
            (user_id, resource_id)
        ).fetchone()
        return row["rating"] if row else 0

def report_resource(resource_id, reporter_id, reason):
    reason = reason.strip()
    if not reason:
        raise ValueError("Please provide a reason for reporting.")
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO reports (resource_id, reporter_id, reason) VALUES (?, ?, ?)",
            (resource_id, reporter_id, reason)
        )

def get_resource_stats():
    with get_connection() as connection:
        totals = connection.execute("""
            SELECT COUNT(*) AS resource_count,
                   COALESCE(SUM(downloads), 0) AS total_downloads,
                   COALESCE(AVG(file_size), 0) AS average_file_size
            FROM resources
        """).fetchone()
        popular = connection.execute("""
            SELECT resources.id, resources.title, resources.downloads,
                   COALESCE(AVG(ratings.rating), 0) AS average_rating
            FROM resources LEFT JOIN ratings ON ratings.resource_id=resources.id
            GROUP BY resources.id ORDER BY resources.downloads DESC LIMIT 10
        """).fetchall()
        subjects = connection.execute("""
            SELECT subject, COUNT(*) AS count FROM resources
            GROUP BY subject ORDER BY count DESC
        """).fetchall()
        return totals, popular, subjects

def get_admin_reports():
    with get_connection() as connection:
        return connection.execute("""
            SELECT reports.*, resources.title AS resource_title,
                   reporter.full_name AS reporter_name
            FROM reports
            JOIN resources ON resources.id=reports.resource_id
            JOIN users AS reporter ON reporter.id=reports.reporter_id
            ORDER BY CASE reports.status WHEN 'Pending' THEN 0 ELSE 1 END,
                     reports.created_at DESC
        """).fetchall()

def update_report_status(report_id, status):
    if status not in ("Pending", "Reviewed", "Dismissed"):
        raise ValueError("Invalid report status.")
    with get_connection() as connection:
        connection.execute(
            "UPDATE reports SET status=? WHERE id=?",
            (status, report_id)
        )

def moderate_resource(resource_id, admin_id, action, notes=""):
    if action not in ("approve", "remove"):
        raise ValueError("Invalid moderation action.")
    with get_connection() as connection:
        resource = connection.execute(
            "SELECT stored_filename FROM resources WHERE id=?",
            (resource_id,)
        ).fetchone()
        if not resource:
            return False
        if action == "remove":
            connection.execute("DELETE FROM resources WHERE id=?", (resource_id,))
        connection.execute("""
            INSERT INTO moderation_log (admin_id, resource_id, action, notes)
            VALUES (?, ?, ?, ?)
        """, (admin_id, resource_id, action, notes.strip()))
    if action == "remove":
        path = UPLOAD_DIR / Path(resource["stored_filename"]).name
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return True

def get_report_count():
    with get_connection() as connection:
        return connection.execute(
            "SELECT COUNT(*) AS count FROM reports WHERE status='Pending'"
        ).fetchone()["count"]
