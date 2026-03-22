
import sqlite3
import os

DB_PATH = "instance/korumos.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🚀 Starting ATL Schema Migration...")

    # 1. Update User table
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
        print("✅ Added 'role' to user table.")
    except sqlite3.OperationalError:
        print("ℹ️ 'role' column already exists in user table.")

    # 2. Update DecisionLedger table
    ledger_cols = [
        ("ledger_id", "VARCHAR(36)"),
        ("tenant_id", "VARCHAR(50)"),
        ("payload_hash", "VARCHAR(64)"),
        ("schema_version", "VARCHAR(10) DEFAULT '1.0'"),
        ("large_artifact", "BOOLEAN DEFAULT 0"),
        ("signature_hmac", "VARCHAR(128)")
    ]

    for col_name, col_type in ledger_cols:
        try:
            cursor.execute(f"ALTER TABLE decision_ledger ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added '{col_name}' to decision_ledger.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"ℹ️ '{col_name}' already exists in decision_ledger.")
            else:
                print(f"❌ Failed to add '{col_name}': {e}")

    # 3. Create EvidenceArchive table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_hash VARCHAR(64) UNIQUE NOT NULL,
                content TEXT NOT NULL,
                data_class VARCHAR(30),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created evidence_archive table.")
    except sqlite3.OperationalError as e:
        print(f"❌ Failed to create evidence_archive: {e}")

    conn.commit()
    conn.close()
    print("✨ Migration Complete.")

if __name__ == "__main__":
    migrate()
