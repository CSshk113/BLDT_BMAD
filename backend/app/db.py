"""Tiny SQLite boundary used by the MVP."""

from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "app.db"


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS criteria_versions (
            id TEXT PRIMARY KEY,
            position_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('DRAFT', 'APPROVED', 'ARCHIVED')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            approved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS criteria_items (
            id TEXT PRIMARY KEY,
            criteria_version_id TEXT NOT NULL REFERENCES criteria_versions(id),
            criterion_text TEXT NOT NULL,
            requirement_type TEXT NOT NULL CHECK(requirement_type IN ('필수', '우대')),
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS mapping_results (
            id TEXT PRIMARY KEY,
            criteria_version_id TEXT NOT NULL REFERENCES criteria_versions(id),
            application_id TEXT NOT NULL,
            applicant_label TEXT NOT NULL,
            criterion_item_id TEXT NOT NULL REFERENCES criteria_items(id),
            citation TEXT NOT NULL,
            location TEXT NOT NULL,
            evidence_status TEXT NOT NULL,
            mapping_status TEXT NOT NULL CHECK(mapping_status IN ('RECEIVED', 'COMPLETED', 'INVALIDATED'))
        );
        """
    )
    connection.commit()

