
import sqlite3
import uuid
from flask import Flask
from db import db, init_db
from models import DecisionLedger, EvidenceArchive
from ledger import LedgerService

def smoke_test():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///korumos.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    init_db(app)

    with app.app_context():
        mission_id = str(uuid.uuid4())
        decision_id = str(uuid.uuid4())
        payload = {"role": "Strategist", "content": "This is a sensitive decision with secret data."}

        print(f"SMOKE TEST: Writing event for mission {mission_id[:8]}...")
        LedgerService.write_event("council_decision", mission_id, decision_id, payload)

        # 1. VERIFY THIN LEDGER
        ledger = DecisionLedger.query.filter_by(decision_id=decision_id).first()
        print(f"OK THIN CHECK: ledger.payload_hash = {ledger.payload_hash[:12]}...")
        
        # In a real environment, the ledger object would NOT have a .payload attr anymore.
        # But our current model might still have it as a placeholder. Let's check.
        try:
            val = getattr(ledger, 'payload', None)
            if val:
                print(f"ERR THIN CHECK FAILED: Found raw text in ledger column: {val[:20]}")
            else:
                print("OK THIN CHECK PASSED: No raw text in DecisionLedger.")
        except Exception as e:
            print("OK THIN CHECK PASSED: Attribute no longer exists.")

        # 2. VERIFY THICK EVIDENCE
        evidence = EvidenceArchive.query.filter_by(payload_hash=ledger.payload_hash).first()
        if evidence and "secret data" in evidence.content:
            print(f"OK THICK CHECK PASSED: Evidence Vault contains raw content.")
        else:
            print(f"ERR THICK CHECK FAILED: Evidence Vault is empty or corrupt.")

        # 3. VERIFY INTEGRITY (Intact)
        v_res = LedgerService.verify_chain(decision_id)
        if v_res["valid"]:
            print(f"OK INTEGRITY CHECK PASSED: Initial chain is valid.")
        else:
            print(f"ERR INTEGRITY CHECK FAILED: Initial chain broken: {v_res['details']}")

        # 4. SIMULATE TAMPERING
        print("WARN SIMULATING TAMPERING: Direct DB mutation...")
        conn = sqlite3.connect("instance/korumos.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE decision_ledger SET event_type = 'FRAUD_EVENT' WHERE decision_id = ?", (decision_id,))
        conn.commit()
        conn.close()

        # IMPORTANT: Force SQLAlchemy to reload objects from DB, bypassing the identity map
        db.session.expire_all()

        v_res_tamper = LedgerService.verify_chain(decision_id)
        if not v_res_tamper["valid"]:
            print(f"OK TAMPER DETECTION PASSED: system detected mutation: {v_res_tamper['details']}")
        else:
            print(f"ERR TAMPER DETECTION FAILED: system did not notice the record was changed!")

if __name__ == "__main__":
    smoke_test()
