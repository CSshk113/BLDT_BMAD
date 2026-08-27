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
            approved_at TEXT,
            approved_by TEXT
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
            processing_run_id TEXT,
            source_artifact_id TEXT,
            applicant_label TEXT NOT NULL,
            criterion_item_id TEXT NOT NULL REFERENCES criteria_items(id),
            citation TEXT NOT NULL,
            location TEXT NOT NULL,
            location_kind TEXT NOT NULL DEFAULT 'EXACT' CHECK(location_kind IN ('EXACT', 'FALLBACK', 'NONE')),
            evidence_status TEXT NOT NULL,
            mapping_status TEXT NOT NULL CHECK(mapping_status IN ('RECEIVED', 'COMPLETED', 'INVALIDATED'))
        );
        CREATE TABLE IF NOT EXISTS review_logs (
            id TEXT PRIMARY KEY,
            criteria_version_id TEXT NOT NULL REFERENCES criteria_versions(id),
            application_id TEXT NOT NULL,
            criterion_item_id TEXT NOT NULL REFERENCES criteria_items(id),
            reviewer_role TEXT NOT NULL CHECK(reviewer_role IN ('HR', 'HM')),
            review_status TEXT NOT NULL CHECK(review_status IN ('FULFILLED', 'PARTIALLY_FULFILLED', 'UNFULFILLED', 'UNVERIFIABLE')),
            reason_text TEXT NOT NULL,
            source_location TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(criteria_version_id, application_id, criterion_item_id, reviewer_role)
        );
        CREATE TABLE IF NOT EXISTS conflict_resolutions (
            id TEXT PRIMARY KEY,
            criteria_version_id TEXT NOT NULL REFERENCES criteria_versions(id),
            application_id TEXT NOT NULL,
            criterion_item_id TEXT NOT NULL REFERENCES criteria_items(id),
            status TEXT NOT NULL CHECK(status IN ('RESOLVED')),
            resolved_by TEXT NOT NULL CHECK(resolved_by IN ('HR')),
            resolved_at TEXT NOT NULL,
            resolution_reason TEXT NOT NULL,
            UNIQUE(criteria_version_id, application_id, criterion_item_id)
        );

        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            candidate_token TEXT NOT NULL,
            position_name TEXT NOT NULL,
            criteria_version_id TEXT NOT NULL REFERENCES criteria_versions(id),
            source_type TEXT NOT NULL CHECK(source_type IN ('UPLOAD', 'SAMPLE', 'LEDGER_ONLY')),
            ledger_metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS processing_runs (
            id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL REFERENCES applications(id),
            criteria_version_id TEXT NOT NULL REFERENCES criteria_versions(id),
            status TEXT NOT NULL CHECK(status IN ('RECEIVED', 'PARSING', 'MAPPING', 'COMPLETED', 'FAILED')),
            current_step TEXT NOT NULL,
            parser_model TEXT NOT NULL,
            received_at TEXT NOT NULL,
            parsing_started_at TEXT,
            mapping_started_at TEXT,
            completed_at TEXT,
            failed_at TEXT,
            failure_step TEXT,
            failure_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS processing_run_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processing_run_id TEXT NOT NULL REFERENCES processing_runs(id),
            status TEXT NOT NULL CHECK(status IN ('RECEIVED', 'PARSING', 'MAPPING', 'COMPLETED', 'FAILED')),
            step TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            detail TEXT
        );

        CREATE TABLE IF NOT EXISTS application_artifacts (
            id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL REFERENCES applications(id),
            processing_run_id TEXT REFERENCES processing_runs(id),
            artifact_type TEXT NOT NULL CHECK(artifact_type IN ('ORIGINAL_PDF', 'LLAMAPARSE_MARKDOWN', 'NORMALIZED_MARKDOWN')),
            storage_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            is_current INTEGER NOT NULL DEFAULT 0 CHECK(is_current IN (0, 1)),
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_processing_runs_application
            ON processing_runs(application_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_application_artifacts_application
            ON application_artifacts(application_id, artifact_type, created_at DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_current_artifact
            ON application_artifacts(application_id, artifact_type) WHERE is_current = 1;

        CREATE TRIGGER IF NOT EXISTS validate_processing_run_application
        BEFORE INSERT ON processing_runs
        WHEN NOT EXISTS (
            SELECT 1 FROM applications
            WHERE applications.id = NEW.application_id
              AND applications.criteria_version_id = NEW.criteria_version_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'processing run application/version mismatch');
        END;

        CREATE TRIGGER IF NOT EXISTS validate_processing_run_application_update
        BEFORE UPDATE OF application_id, criteria_version_id ON processing_runs
        WHEN NOT EXISTS (
            SELECT 1 FROM applications
            WHERE applications.id = NEW.application_id
              AND applications.criteria_version_id = NEW.criteria_version_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'processing run application/version mismatch');
        END;

        CREATE TRIGGER IF NOT EXISTS validate_application_artifact_link
        BEFORE INSERT ON application_artifacts
        WHEN (NEW.artifact_type <> 'ORIGINAL_PDF' AND NEW.processing_run_id IS NULL)
          OR (NEW.processing_run_id IS NOT NULL AND NOT EXISTS (
              SELECT 1 FROM processing_runs
              WHERE processing_runs.id = NEW.processing_run_id
                AND processing_runs.application_id = NEW.application_id
          ))
        BEGIN
            SELECT RAISE(ABORT, 'application artifact/run mismatch');
        END;

        CREATE TRIGGER IF NOT EXISTS validate_application_artifact_link_update
        BEFORE UPDATE OF application_id, processing_run_id, artifact_type ON application_artifacts
        WHEN (NEW.artifact_type <> 'ORIGINAL_PDF' AND NEW.processing_run_id IS NULL)
          OR (NEW.processing_run_id IS NOT NULL AND NOT EXISTS (
              SELECT 1 FROM processing_runs
              WHERE processing_runs.id = NEW.processing_run_id
                AND processing_runs.application_id = NEW.application_id
          ))
        BEGIN
            SELECT RAISE(ABORT, 'application artifact/run mismatch');
        END;
        """
    )
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(criteria_versions)").fetchall()}
    if "approved_by" not in columns:
        connection.execute("ALTER TABLE criteria_versions ADD COLUMN approved_by TEXT")
    mapping_columns = {row["name"] for row in connection.execute("PRAGMA table_info(mapping_results)").fetchall()}
    if "processing_run_id" not in mapping_columns:
        connection.execute("ALTER TABLE mapping_results ADD COLUMN processing_run_id TEXT")
    if "source_artifact_id" not in mapping_columns:
        connection.execute("ALTER TABLE mapping_results ADD COLUMN source_artifact_id TEXT")
    if "location_kind" not in mapping_columns:
        connection.execute("ALTER TABLE mapping_results ADD COLUMN location_kind TEXT NOT NULL DEFAULT 'EXACT'")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_mapping_results_application_version "
        "ON mapping_results(application_id, criteria_version_id, mapping_status, id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_mapping_results_processing_run "
        "ON mapping_results(processing_run_id, criterion_item_id)"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_results_completed_run_criterion "
        "ON mapping_results(processing_run_id, criterion_item_id) WHERE mapping_status = 'COMPLETED' AND processing_run_id IS NOT NULL"
    )
    connection.commit()
