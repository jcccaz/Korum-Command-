
import sys
import logging
from flask import Flask
from db import db, init_db
from models import DecisionLedger
from ledger import LedgerService

# Set up simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ATL-Heartbeat")

def run_heartbeat():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///korumos.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    init_db(app)

    with app.app_context():
        logger.info("Audit Heartbeat: Starting chain verification...")
        
        # Get all distinct decision IDs
        decisions = db.session.query(DecisionLedger.decision_id).distinct().all()
        decision_ids = [d[0] for d in decisions]
        
        logger.info(f"Found {len(decision_ids)} unique decision chains.")
        
        failures = []
        for did in decision_ids:
            result = LedgerService.verify_chain(did)
            if not result["valid"]:
                logger.error(f"TAMPER DETECTED: Chain {did} failed verification!")
                logger.error(f"   Reason: {result['details']} at sequence {result['broken_at']}")
                failures.append({"id": did, "error": result["details"]})
            else:
                logger.debug(f"Chain {did} is intact.")

        if failures:
            logger.critical(f"FATAL: {len(failures)} decision chains have been compromised!")
            sys.exit(1)
        else:
            logger.info("All chains verified. Decision Integrity is intact.")
            sys.exit(0)

if __name__ == "__main__":
    run_heartbeat()
