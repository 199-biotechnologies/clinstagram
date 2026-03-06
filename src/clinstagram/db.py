from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL,
                backend TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp DATETIME DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup
                ON rate_limits(account, backend, action, timestamp);

            CREATE TABLE IF NOT EXISTS capabilities (
                account TEXT NOT NULL,
                backend TEXT NOT NULL,
                feature TEXT NOT NULL,
                available BOOLEAN NOT NULL DEFAULT 1,
                last_probed DATETIME DEFAULT (datetime('now')),
                PRIMARY KEY (account, backend, feature)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now')),
                account TEXT,
                backend TEXT,
                command TEXT,
                args TEXT,
                exit_code INTEGER,
                response_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS user_cache (
                username TEXT PRIMARY KEY,
                user_id TEXT,
                graph_scoped_id TEXT,
                private_pk TEXT,
                last_updated DATETIME DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS thread_map (
                username TEXT PRIMARY KEY,
                graph_thread_id TEXT,
                private_thread_id TEXT,
                last_updated DATETIME DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    def list_tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [r["name"] for r in rows]

    def record_action(self, account: str, backend: str, action: str) -> None:
        self.conn.execute(
            "INSERT INTO rate_limits (account, backend, action) VALUES (?, ?, ?)",
            (account, backend, action),
        )
        self.conn.commit()

    def get_action_count(
        self, account: str, backend: str, action: str, window_minutes: int = 60
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM rate_limits WHERE account=? AND backend=? AND action=? AND timestamp>=?",
            (account, backend, action, cutoff.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchone()
        return row["cnt"]

    def check_rate_limit(
        self, account: str, backend: str, action: str, limit: int, window_minutes: int = 60
    ) -> bool:
        return self.get_action_count(account, backend, action, window_minutes) < limit

    def cache_user(
        self,
        username: str,
        user_id: Optional[str] = None,
        graph_scoped_id: Optional[str] = None,
        private_pk: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """INSERT INTO user_cache (username, user_id, graph_scoped_id, private_pk)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(username) DO UPDATE SET
                 user_id=COALESCE(excluded.user_id, user_cache.user_id),
                 graph_scoped_id=COALESCE(excluded.graph_scoped_id, user_cache.graph_scoped_id),
                 private_pk=COALESCE(excluded.private_pk, user_cache.private_pk),
                 last_updated=datetime('now')""",
            (username, user_id, graph_scoped_id, private_pk),
        )
        self.conn.commit()

    def get_cached_user(self, username: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM user_cache WHERE username=?", (username,)
        ).fetchone()
        return dict(row) if row else None

    def log_audit(
        self,
        account: str,
        backend: str,
        command: str,
        args: str,
        exit_code: int,
        response_summary: str,
    ) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (account, backend, command, args, exit_code, response_summary) VALUES (?, ?, ?, ?, ?, ?)",
            (account, backend, command, args, exit_code, response_summary),
        )
        self.conn.commit()

    def get_recent_audit(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
