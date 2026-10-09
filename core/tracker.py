"""
core/tracker.py
Lightweight local SQLite tracker for job applications. Everything stays on
your machine -- nothing is sent anywhere.
"""

import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "applications.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            role TEXT,
            url TEXT,
            status TEXT,
            date_applied TEXT,
            notes TEXT,
            auto_applied INTEGER DEFAULT 0,
            platform TEXT DEFAULT '',
            fit_score INTEGER DEFAULT 0
        )
    """)
    # Run migrations for existing DBs that don't have new columns
    try:
        conn.execute("ALTER TABLE applications ADD COLUMN auto_applied INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE applications ADD COLUMN platform TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE applications ADD COLUMN fit_score INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    return conn


def add_application(company: str, role: str, url: str = "", status: str = "Saved",
                     notes: str = "", auto_applied: bool = False, platform: str = "",
                     fit_score: int = 0) -> int:
    """Add a new application. Returns the new row's id."""
    conn = _conn()
    cursor = conn.execute(
        "INSERT INTO applications (company, role, url, status, date_applied, notes, auto_applied, platform, fit_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (company, role, url, status, str(date.today()), notes,
         1 if auto_applied else 0, platform, fit_score),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def list_applications() -> list[dict]:
    conn = _conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM applications ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_application(app_id: int) -> dict | None:
    conn = _conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_status(app_id: int, status: str) -> None:
    conn = _conn()
    conn.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
    conn.commit()
    conn.close()


def update_notes(app_id: int, notes: str) -> None:
    conn = _conn()
    conn.execute("UPDATE applications SET notes = ? WHERE id = ?", (notes, app_id))
    conn.commit()
    conn.close()


def update_fit_score(app_id: int, fit_score: int) -> None:
    conn = _conn()
    conn.execute("UPDATE applications SET fit_score = ? WHERE id = ?", (fit_score, app_id))
    conn.commit()
    conn.close()


def delete_application(app_id: int) -> None:
    conn = _conn()
    conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Return summary statistics for the dashboard."""
    conn = _conn()
    rows = conn.execute("SELECT status, COUNT(*) as cnt FROM applications GROUP BY status").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    auto = conn.execute("SELECT COUNT(*) FROM applications WHERE auto_applied = 1").fetchone()[0]
    conn.close()

    status_counts = {r[0]: r[1] for r in rows}
    return {
        "total": total,
        "auto_applied": auto,
        "saved": status_counts.get("Saved", 0),
        "applied": status_counts.get("Applied", 0),
        "interviewing": status_counts.get("Interviewing", 0),
        "offer": status_counts.get("Offer", 0),
        "rejected": status_counts.get("Rejected", 0),
    }
