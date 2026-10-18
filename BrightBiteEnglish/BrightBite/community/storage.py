"""BrightBite data storage. Only this app's tables are created."""

from __future__ import annotations

import base64

import binascii

import json

import re

import sqlite3

import uuid

from contextlib import contextmanager

from datetime import datetime, timezone

from pathlib import Path

from typing import Callable

from .errors import ValidationError


class RecordError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, content TEXT NOT NULL,
    feedback TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS favorites (recipe_id TEXT PRIMARY KEY);
"""

class Storage:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(SCHEMA)


    @contextmanager
    def connection(self, write: bool = False):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


    @staticmethod
    def _plan(row) -> dict:
        if row is None:
            raise RecordError("Meal plan not found.", 404)
        result = json.loads(row["content"])
        result.update(id=row["id"], created_at=row["created_at"], feedback=row["feedback"])
        return result


    def save_plan(self, plan: dict) -> dict:
        identifier, timestamp = uuid.uuid4().hex, now()
        with self.connection(write=True) as connection:
            connection.execute("INSERT INTO plans(id, created_at, content) VALUES (?, ?, ?)",
                               (identifier, timestamp, json.dumps(plan, ensure_ascii=False)))
        return self.get_plan(identifier)


    def get_plan(self, identifier: str) -> dict:
        with self.connection() as connection:
            return self._plan(connection.execute("SELECT * FROM plans WHERE id = ?", (identifier,)).fetchone())


    def latest_plan(self) -> dict | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM plans ORDER BY rowid DESC LIMIT 1").fetchone()
            return self._plan(row) if row else None


    def change_plan(self, identifier: str, change: Callable[[dict], None]) -> dict:
        with self.connection(write=True) as connection:
            row = connection.execute("SELECT * FROM plans WHERE id = ?", (identifier,)).fetchone()
            plan = self._plan(row)
            change(plan)
            for key in ("id", "created_at", "feedback"):
                plan.pop(key, None)
            connection.execute("UPDATE plans SET content = ? WHERE id = ?",
                               (json.dumps(plan, ensure_ascii=False), identifier))
        return self.get_plan(identifier)


    def set_feedback(self, identifier: str, feedback: str) -> dict:
        if feedback not in ("想尝试", "已经做过", "不合口味"):
            raise ValidationError("Choose a supported feedback option.")
        with self.connection(write=True) as connection:
            cursor = connection.execute("UPDATE plans SET feedback = ? WHERE id = ?", (feedback, identifier))
            if not cursor.rowcount:
                raise RecordError("Meal plan not found.", 404)
        return self.get_plan(identifier)


    def favorites(self) -> list[str]:
        with self.connection() as connection:
            return [row[0] for row in connection.execute("SELECT recipe_id FROM favorites ORDER BY recipe_id")]


    def set_favorite(self, identifier: str, saved: bool) -> list[str]:
        if type(saved) is not bool:
            raise ValidationError("The favorite state must be true or false.")
        with self.connection(write=True) as connection:
            if saved:
                connection.execute("INSERT OR IGNORE INTO favorites VALUES (?)", (identifier,))
            else:
                connection.execute("DELETE FROM favorites WHERE recipe_id = ?", (identifier,))
        return self.favorites()

