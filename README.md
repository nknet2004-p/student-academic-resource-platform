# Student Academic Resource Sharing Platform

A Streamlit + SQLite project covering the 25 planned user stories:
registration/login/logout, profile management, upload/categorization/details/download/edit/delete,
search/filter/sort, bookmarks, ratings, statistics, reports, admin login, user management,
moderation, and dashboards.

## Run locally

1. Use the existing project folder and keep `students.db` and `uploads/`.
2. Activate your virtual environment.
3. Install dependencies:

   `pip install -r requirements.txt`

4. Configure an admin account before starting Streamlit.

PowerShell (current terminal only):

```powershell
$env:ADMIN_EMAIL="admin@example.com"
$env:ADMIN_PASSWORD="Choose-A-Strong-Password-123"
$env:ADMIN_NAME="Platform Administrator"
python -m streamlit run app.py
```

Use the same configured email/password in the Admin Login tab. The admin account is created or promoted on startup. Use a unique strong password and do not commit credentials to GitHub.

## Existing data

The database initialization is additive: it adds missing columns/tables and does not intentionally delete existing users, resources, or uploaded files. Back up `students.db` and `uploads/` before replacing project files.

## Notes

- Uploaded files are limited to 20 MB and supported document/image/archive extensions.
- `students.db`, `.venv/`, and `uploads/` should not be committed to a public repository.
- This is a student project prototype; production deployment needs additional security review, rate limiting, backups, and stronger file scanning.
