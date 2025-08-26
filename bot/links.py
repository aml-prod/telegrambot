from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "storage"
DB_PATH = DATA_DIR / "links.db"
FILES_DIR = DATA_DIR / "files"


@dataclass
class Link:
    token: str
    path: Path
    remaining: int


def _ensure_dirs() -> None:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS links (
                    token TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    remaining INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


def _conn() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def save_file(content: bytes) -> Path:
    _ensure_dirs()
    filename = secrets.token_urlsafe(12) + ".jpg"
    path = FILES_DIR / filename
    path.write_bytes(content)
    return path


def create_link(content: bytes, max_views: int) -> Link:
    if max_views <= 0:
        max_views = 1
    path = save_file(content)
    token = secrets.token_urlsafe(16)
    with _conn() as c:
        c.execute(
            "INSERT INTO links(token, path, remaining) VALUES (?, ?, ?)",
            (token, str(path), max_views),
        )
    return Link(token=token, path=path, remaining=max_views)


def fetch_link(token: str) -> Optional[Link]:
    with _conn() as c:
        row = c.execute(
            "SELECT token, path, remaining FROM links WHERE token = ?",
            (token,),
        ).fetchone()
    if not row:
        return None
    return Link(token=row[0], path=Path(row[1]), remaining=int(row[2]))


def consume_view(token: str) -> Optional[Link]:
    """Атомарно уменьшает счётчик и отдаёт ссылку; если 0 — удаляет запись."""
    with _conn() as c:
        cur = c.execute(
            "SELECT path, remaining FROM links WHERE token = ?",
            (token,),
        )
        row = cur.fetchone()
        if not row:
            return None
        path, remaining = Path(row[0]), int(row[1])
        if remaining <= 0:
            c.execute("DELETE FROM links WHERE token = ?", (token,))
            return None
        remaining -= 1
        if remaining == 0:
            c.execute("DELETE FROM links WHERE token = ?", (token,))
        else:
            c.execute(
                "UPDATE links SET remaining = ? WHERE token = ?",
                (remaining, token),
            )
    return Link(token=token, path=path, remaining=remaining)
