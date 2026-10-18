"""SilverBridge data storage. Only this app's tables are created."""

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


def text_value(value: object, label: str, limit: int, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be text.")
    value = value.strip()
    if (required and not value) or len(value) > limit:
        raise ValidationError(f"{label} must not be empty and may contain at most {limit} characters." if required else f"{label} may contain at most {limit} characters.")
    return value


def media_value(value: object, kind: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValidationError("Invalid attachment format.")
    types = r"image/(?:png|jpeg|webp)" if kind == "image" else r"audio/(?:webm|ogg|wav|mp4|mpeg)"
    matched = re.fullmatch(r"data:(" + types + r")(?:;codecs=[a-zA-Z0-9.,_-]+)?;base64,([A-Za-z0-9+/=\r\n]+)", value)
    if not matched:
        raise ValidationError("Unsupported attachment. Use PNG/JPEG/WebP for images or a supported audio file.")
    try:
        decoded = base64.b64decode(matched.group(2), validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValidationError("The attachment encoding is damaged.") from error
    maximum = 800_000 if kind == "image" else 1_200_000
    if not decoded or len(decoded) > maximum:
        raise ValidationError("The attachment is empty or too large. Resize the image or shorten the recording.")
    return value


SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
    body TEXT NOT NULL, image TEXT, audio TEXT,
    status TEXT NOT NULL CHECK(status IN ('pending', 'active', 'done')),
    created_at TEXT NOT NULL, claimed_at TEXT, resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    body TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS replies_by_ticket ON replies(ticket_id, id);
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
    body TEXT NOT NULL, audio TEXT, created_at TEXT NOT NULL,
    publication_state TEXT NOT NULL DEFAULT 'local_draft'
);
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
    def _ticket(connection, identifier: int):
        row = connection.execute("SELECT * FROM tickets WHERE id = ?", (identifier,)).fetchone()
        if row is None:
            raise RecordError("Request not found.", 404)
        return row


    def create_ticket(self, payload: dict) -> dict:
        category = payload.get("category")
        if category not in ("手机操作", "视频通话", "办事步骤", "其他问题"):
            raise ValidationError("Choose a valid help topic.")
        body = text_value(payload.get("body", ""), "Question", 1200, required=False)
        image, audio = media_value(payload.get("image"), "image"), media_value(payload.get("audio"), "audio")
        if not body and not audio and not image:
            raise ValidationError("Type a question, upload a screenshot or record a message.")
        with self.connection(write=True) as connection:
            cursor = connection.execute(
                "INSERT INTO tickets(category, body, image, audio, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
                (category, body, image, audio, now()),
            )
            identifier = cursor.lastrowid
        return self.get_ticket(identifier)


    def get_ticket(self, identifier: int) -> dict:
        with self.connection() as connection:
            result = dict(self._ticket(connection, identifier))
            result["replies"] = [dict(row) for row in connection.execute(
                "SELECT body, created_at FROM replies WHERE ticket_id = ? ORDER BY id", (identifier,)
            )]
            return result


    def tickets(self) -> list[dict]:
        with self.connection() as connection:
            result = [dict(row) for row in connection.execute("SELECT * FROM tickets ORDER BY id DESC")]
            replies: dict[int, list] = {}
            for row in connection.execute("SELECT ticket_id, body, created_at FROM replies ORDER BY id"):
                replies.setdefault(row["ticket_id"], []).append({"body": row["body"], "created_at": row["created_at"]})
            for ticket in result:
                ticket["replies"] = replies.get(ticket["id"], [])
            return result


    def transition_ticket(self, identifier: int, action: str, payload: dict) -> dict:
        with self.connection(write=True) as connection:
            ticket = self._ticket(connection, identifier)
            status = ticket["status"]
            if action == "claim":
                if status != "pending":
                    raise RecordError("This request has already been claimed or solved. Refresh the list.", 409)
                connection.execute("UPDATE tickets SET status='active', claimed_at=? WHERE id=?", (now(), identifier))
            elif action == "reply":
                if status != "active":
                    raise RecordError("Claim the request first. Reopen a solved request before replying.", 409)
                body = text_value(payload.get("body", ""), "Reply", 1600)
                connection.execute("INSERT INTO replies(ticket_id, body, created_at) VALUES (?, ?, ?)", (identifier, body, now()))
            elif action == "resolve":
                replied = connection.execute("SELECT 1 FROM replies WHERE ticket_id=? LIMIT 1", (identifier,)).fetchone()
                if status != "active" or not replied:
                    raise RecordError("A request must receive a reply before it can be marked solved.", 409)
                connection.execute("UPDATE tickets SET status='done', resolved_at=? WHERE id=?", (now(), identifier))
            elif action == "reopen":
                if status != "done":
                    raise RecordError("Only solved requests can be reopened.", 409)
                connection.execute("UPDATE tickets SET status='active', resolved_at=NULL WHERE id=?", (identifier,))
            else:
                raise RecordError("Unsupported action.", 404)
        return self.get_ticket(identifier)


    def create_story(self, payload: dict) -> dict:
        title = text_value(payload.get("title", ""), "Story title", 60)
        body = text_value(payload.get("body", ""), "Story text", 4000, required=False)
        audio = media_value(payload.get("audio"), "audio")
        if not body and not audio:
            raise ValidationError("Write or record a story.")
        with self.connection(write=True) as connection:
            publication_state = "community_shared" if payload.get("share") is True else "local_draft"
            cursor = connection.execute("INSERT INTO stories(title, body, audio, created_at, publication_state) VALUES (?, ?, ?, ?, ?)", (title, body, audio, now(), publication_state))
            row = connection.execute("SELECT * FROM stories WHERE id=?", (cursor.lastrowid,)).fetchone()
            return dict(row)


    def stories(self) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM stories ORDER BY id DESC")]

