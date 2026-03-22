
import sqlite3
import hashlib
import os

DB_PATH = "instance/korumos.db"


def fix_schema():
    if not os.path.exists(DB_PATH):
        print("Database not found. Skipping.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Fixing decision_ledger schema: migrate legacy payload to evidence_archive, drop payload column...")

    try:
        # 0. Ensure evidence_archive table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_hash VARCHAR(64) UNIQUE NOT NULL,
                content TEXT NOT NULL,
                data_class VARCHAR(30),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 1. Migrate any legacy payload data to evidence_archive
        cursor.execute("PRAGMA table_info(decision_ledger)")
        cols = [c[1] for c in cursor.fetchall()]

        migrated = 0
        if 'payload' in cols:
            cursor.execute("SELECT id, payload, payload_hash FROM decision_ledger WHERE payload IS NOT NULL AND payload != ''")
            rows = cursor.fetchall()
            for row_id, payload_text, existing_hash in rows:
                # Compute hash from raw payload if no payload_hash exists
                p_hash = existing_hash
                if not p_hash:
                    p_hash = hashlib.sha256(payload_text.encode('utf-8')).hexdigest()

                # Insert into evidence_archive if not already there
                cursor.execute("SELECT 1 FROM evidence_archive WHERE payload_hash = ?", (p_hash,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO evidence_archive (payload_hash, content, data_class) VALUES (?, ?, ?)",
                        (p_hash, payload_text, 'LEGACY_MIGRATED')
                    )
                    migrated += 1

                # Ensure payload_hash is set on the ledger row
                if not existing_hash:
                    cursor.execute("UPDATE decision_ledger SET payload_hash = ? WHERE id = ?", (p_hash, row_id))

            print(f"  Migrated {migrated} legacy payloads to evidence_archive.")

        # 2. Recreate table without the payload column (SQLite ALTER TABLE limitation)
        cursor.execute("PRAGMA table_info(decision_ledger)")
        current_cols = [c[1] for c in cursor.fetchall()]

        if 'payload' in current_cols:
            cursor.execute("ALTER TABLE decision_ledger RENAME TO temp_ledger")

            cursor.execute("""
                CREATE TABLE decision_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ledger_id VARCHAR(36) UNIQUE,
                    tenant_id VARCHAR(50),
                    event_type VARCHAR(50) NOT NULL,
                    mission_id VARCHAR(36) NOT NULL,
                    decision_id VARCHAR(36) NOT NULL,
                    sequence INTEGER NOT NULL,
                    timestamp DATETIME,
                    operator_id INTEGER,
                    payload_hash VARCHAR(64) NOT NULL,
                    schema_version VARCHAR(10) DEFAULT '1.0',
                    large_artifact BOOLEAN DEFAULT 0,
                    record_hash VARCHAR(64) NOT NULL,
                    previous_hash VARCHAR(64) NOT NULL,
                    signature_hmac VARCHAR(128)
                )
            """)

            # Copy data — only columns that exist in both old and new
            new_cols = [
                'id', 'ledger_id', 'tenant_id', 'event_type', 'mission_id',
                'decision_id', 'sequence', 'timestamp', 'operator_id',
                'payload_hash', 'schema_version', 'large_artifact',
                'record_hash', 'previous_hash', 'signature_hmac'
            ]
            transfer_cols = [c for c in new_cols if c in current_cols]
            col_list = ", ".join(transfer_cols)
            cursor.execute(f"INSERT INTO decision_ledger ({col_list}) SELECT {col_list} FROM temp_ledger")

            # Recreate indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_ledger_decision_sequence ON decision_ledger (decision_id, sequence)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_ledger_event_type ON decision_ledger (event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_ledger_mission_id ON decision_ledger (mission_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_ledger_decision_id ON decision_ledger (decision_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_ledger_timestamp ON decision_ledger (timestamp)")

            cursor.execute("DROP TABLE temp_ledger")
            print("  Dropped legacy 'payload' column from decision_ledger.")
        else:
            print("  No 'payload' column found — schema already clean.")

        conn.commit()
        print("Schema fix complete.")
    except Exception as e:
        conn.rollback()
        print(f"Failed to fix schema: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    fix_schema()
