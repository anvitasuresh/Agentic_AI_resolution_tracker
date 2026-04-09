import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta

# default db location is data/ in the project root, but can be overridden via env var
# (the eval script does this so it doesn't touch the real database)
DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent.parent / "data" / "resolutions.db"))


# opens a connection and sets row_factory so we can access columns by name
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# creates all three tables if they don't exist yet
# safe to call multiple times — IF NOT EXISTS handles it
def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            target    REAL,
            unit      TEXT,
            frequency TEXT    DEFAULT 'daily',
            deadline  TEXT,
            created_at TEXT   DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id    INTEGER NOT NULL,
            value      REAL,
            note       TEXT,
            logged_at  TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (goal_id) REFERENCES goals(id)
        )
    """)
    # journal entries are separate from progress logs — they store
    # free-text reflections, not just numeric check-ins
    conn.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id    INTEGER NOT NULL,
            text       TEXT    NOT NULL,
            written_at TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (goal_id) REFERENCES goals(id)
        )
    """)
    conn.commit()
    conn.close()


# counts how many consecutive days the user has logged something,
# starting from today or yesterday (so you don't lose your streak overnight)
def calculate_streak(logs) -> int:
    if not logs:
        return 0

    # pull out just the dates, ignoring any bad timestamps
    logged_dates = set()
    for log in logs:
        try:
            d = datetime.fromisoformat(str(log["logged_at"])).date()
            logged_dates.add(d)
        except Exception:
            pass

    if not logged_dates:
        return 0

    # start counting from today if there's a log today, otherwise yesterday
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    start = today if today in logged_dates else yesterday

    streak = 0
    current = start
    while current in logged_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak
