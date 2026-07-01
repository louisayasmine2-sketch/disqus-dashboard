import json
import sqlite3
from pathlib import Path

from flask import g


DATABASE_PATH = Path("disqus_dashboard.sqlite3")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            data TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            email TEXT PRIMARY KEY,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            company TEXT,
            workflow TEXT,
            source TEXT,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = [row[1] for row in db.execute("PRAGMA table_info(contact_requests)").fetchall()]
    if "source" not in columns:
        db.execute("ALTER TABLE contact_requests ADD COLUMN source TEXT")
    db.commit()


def save_threads(threads):
    db = get_db()
    for thread in threads:
        db.execute(
            """
            INSERT INTO threads (id, data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (str(thread["id"]), json.dumps(thread)),
        )
    db.commit()


def get_cached_threads():
    rows = get_db().execute("SELECT data FROM threads ORDER BY updated_at DESC").fetchall()
    return [json.loads(row["data"]) for row in rows]


def save_posts(thread_id, posts):
    db = get_db()
    for post in posts:
        db.execute(
            """
            INSERT INTO posts (id, thread_id, data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                data = excluded.data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (str(post["id"]), str(thread_id), json.dumps(post)),
        )
    db.commit()


def get_cached_posts(thread_id):
    rows = (
        get_db()
        .execute(
            "SELECT data FROM posts WHERE thread_id = ? ORDER BY updated_at DESC",
            (str(thread_id),),
        )
        .fetchall()
    )
    return [json.loads(row["data"]) for row in rows]


def save_subscriber(email, source):
    db = get_db()
    db.execute(
        """
        INSERT INTO newsletter_subscribers (email, source, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(email) DO UPDATE SET
            source = excluded.source
        """,
        (email.strip().lower(), source.strip()),
    )
    db.commit()


def get_subscribers(limit=100):
    rows = (
        get_db()
        .execute(
            """
            SELECT email, source, created_at
            FROM newsletter_subscribers
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        .fetchall()
    )
    return [dict(row) for row in rows]


def save_contact_request(name, email, company, workflow, source, message):
    db = get_db()
    db.execute(
        """
        INSERT INTO contact_requests (name, email, company, workflow, source, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            name.strip(),
            email.strip().lower(),
            company.strip(),
            workflow.strip(),
            (source or "").strip(),
            message.strip(),
        ),
    )
    db.commit()


def get_contact_requests(limit=100, workflow=None, source=None):
    base_sql = "SELECT id, name, email, company, workflow, source, message, created_at FROM contact_requests"
    filters = []
    params = []

    if workflow:
        filters.append("workflow = ?")
        params.append(workflow.strip())

    if source:
        filters.append("source = ?")
        params.append(source.strip())

    if filters:
        base_sql += " WHERE " + " AND ".join(filters)

    base_sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = get_db().execute(base_sql, params).fetchall()
    return [dict(row) for row in rows]
