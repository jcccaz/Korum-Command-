# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect


db = SQLAlchemy()


def _safe_add_column(conn, table, column, col_type, default=None):
    """Add a column to a table if it doesn't exist (safe migration)."""
    inspector = inspect(conn)
    existing = [c['name'] for c in inspector.get_columns(table)]
    if column not in existing:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"))
        print(f"[DB] Added column {table}.{column}")


def init_db(app) -> None:
    """Initialize SQLAlchemy, create tables, and run safe migrations."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # Migrate existing tables — add columns that create_all won't add
        with db.engine.connect() as conn:
            try:
                _safe_add_column(conn, 'users', 'role', "VARCHAR(20)", "'user'")
                _safe_add_column(conn, 'users', 'mfa_secret', "VARCHAR(32)")
                _safe_add_column(conn, 'users', 'mfa_enabled', "BOOLEAN", "false")
                _safe_add_column(conn, 'users', 'created_at', "TIMESTAMP")
                _safe_add_column(conn, 'users', 'last_login', "TIMESTAMP")
                _safe_add_column(conn, 'users', 'preferences', "TEXT", "'{}'")
                
                # UsageLog extensions
                _safe_add_column(conn, 'usage_logs', 'run_id', "VARCHAR(36)")
                _safe_add_column(conn, 'usage_logs', 'session_id', "VARCHAR(36)")
                _safe_add_column(conn, 'usage_logs', 'workflow_name', "VARCHAR(50)")
                _safe_add_column(conn, 'usage_logs', 'provider_name', "VARCHAR(50)")

                # Report extensions
                _safe_add_column(conn, 'reports', 'docked_snippets', "TEXT")
                
                conn.commit()
            except Exception as e:
                print(f"[DB] Migration note: {e}")
