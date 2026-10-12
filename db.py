"""Small SQLite persistence layer for local development and demos."""
from collections.abc import Generator
from contextlib import contextmanager
import sqlite3
from typing import Optional
from config import DATABASE_PATH


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()


def create_user(name: str, email: str, password_hash: str) -> bool:
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name.strip(), email.strip().lower(), password_hash),
            )
            connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_user(email: str) -> Optional[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
