import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone

from db import db
from models import DecisionLedger, EvidenceArchive
from canonical import compute_payload_hash, canonical_json

GENESIS_HASH = "GENESIS"
_hmac_raw = os.getenv("LEDGER_HMAC_KEY")
if not _hmac_raw:
    if os.getenv("FLASK_ENV") == "production" or os.getenv("RAILWAY_ENVIRONMENT"):
        raise RuntimeError("LEDGER_HMAC_KEY must be set in production — refusing to start with default key")
    _hmac_raw = "dev_only_not_for_production"
HMAC_KEY = _hmac_raw.encode()
EVIDENCE_SIZE_LIMIT = 5 * 1024 * 1024  # 5MB


def _build_canonical_envelope(event_type, mission_id, decision_id, sequence,
                              timestamp_iso, operator_id, payload_hash, previous_hash, 
                              ledger_id, tenant_id=None, schema_version="1.0"):
    """Build a deterministic canonical string covering ALL witness metadata."""
    envelope_data = {
        "event_type": event_type,
        "mission_id": mission_id,
        "decision_id": decision_id,
        "ledger_id": ledger_id,
        "tenant_id": tenant_id,
        "sequence": sequence,
        "timestamp": timestamp_iso,
        "operator_id": operator_id,
        "payload_hash": payload_hash,
        "previous_hash": previous_hash,
        "schema_version": schema_version
    }
    return canonical_json(envelope_data)


def _compute_record_hash(canonical_envelope):
    """SHA-256(canonical_envelope) -> 64-char hex string."""
    return hashlib.sha256(canonical_envelope.encode('utf-8')).hexdigest()


def _compute_hmac(record_hash):
    """HMAC-SHA256(key, record_hash) -> 128-char hex string."""
    return hmac.new(HMAC_KEY, record_hash.encode('utf-8'), hashlib.sha256).hexdigest()


class LedgerService:
    """Append-only, hash-chained Witness Layer (Thin Ledger)."""

    @staticmethod
    def write_event(event_type, mission_id, decision_id, payload, operator_id=None, tenant_id=None, data_class=None):
        """Write a new Witness event, chaining it to the previous event.
        
        This implements the "Witness Layer" pattern:
        - Payload is hashed and stored in the Evidence Layer (EvidenceArchive).
        - Only the metadata and payload_hash are stored in the Ledger.
        """
        # Determine sequence
        last = DecisionLedger.query.filter_by(decision_id=decision_id) \
            .order_by(DecisionLedger.sequence.desc()).first()
        sequence = (last.sequence + 1) if last else 1
        previous_hash = last.record_hash if last else GENESIS_HASH

        # 1. Canonical Payload Hashing (The Witness Seal)
        schema_version = "1.0"
        payload_json = canonical_json(payload)
        p_hash = compute_payload_hash(payload) # Uses schema_version internally
        
        # 2. Evidence Persistence (Thick Layer) with Size Guard
        is_large = len(payload_json) > EVIDENCE_SIZE_LIMIT
        
        # Check if hash already exists (Deduplication)
        evidence = EvidenceArchive.query.filter_by(payload_hash=p_hash).first()
        if not evidence:
            archive_entry = EvidenceArchive(
                payload_hash=p_hash,
                content=payload_json,
                data_class=data_class
            )
            db.session.add(archive_entry)

        # 3. Ledger Metadata
        ledger_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).replace(tzinfo=None)  # Store naive UTC — SQLite strips tz
        ts_iso = ts.isoformat()  # e.g. "2026-03-22T15:30:00.123456" — no +00:00 suffix

        # 4. Integrity Chain (The Chain Link)
        envelope = _build_canonical_envelope(
            event_type, mission_id, decision_id, sequence,
            ts_iso, operator_id, p_hash, previous_hash,
            ledger_id, tenant_id, schema_version
        )
        record_hash = _compute_record_hash(envelope)
        sig_hmac = _compute_hmac(record_hash)

        entry = DecisionLedger(
            ledger_id=ledger_id,
            tenant_id=tenant_id,
            event_type=event_type,
            mission_id=mission_id,
            decision_id=decision_id,
            sequence=sequence,
            timestamp=ts,
            operator_id=operator_id,
            payload_hash=p_hash,
            schema_version=schema_version,
            large_artifact=is_large,
            record_hash=record_hash,
            previous_hash=previous_hash,
            signature_hmac=sig_hmac
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def get_chain(decision_id):
        """Fetch all events for a single decision, ordered by sequence."""
        return DecisionLedger.query.filter_by(decision_id=decision_id) \
            .order_by(DecisionLedger.sequence.asc()).all()

    @staticmethod
    def get_evidence(payload_hash):
        """Internal helper to retrieve raw evidence by its hash."""
        return EvidenceArchive.query.filter_by(payload_hash=payload_hash).first()

    @staticmethod
    def verify_chain(decision_id):
        """Walk the chain and verify hash and HMAC integrity."""
        events = DecisionLedger.query.filter_by(decision_id=decision_id) \
            .order_by(DecisionLedger.sequence.asc()).all()

        if not events:
            return {"valid": True, "total_events": 0, "broken_at": None, "details": "No events found."}

        for i, event in enumerate(events):
            expected_previous = events[i - 1].record_hash if i > 0 else GENESIS_HASH

            # 1. Check Linkage
            if event.previous_hash != expected_previous:
                return {"valid": False, "broken_at": event.sequence, "details": f"Chain leak at sequence {event.sequence}"}

            # 2. Recompute Witness Envelope (strip tz for SQLite consistency)
            _ts = event.timestamp.replace(tzinfo=None) if event.timestamp and event.timestamp.tzinfo else event.timestamp
            ts_iso = _ts.isoformat() if _ts else None
            envelope = _build_canonical_envelope(
                event.event_type, event.mission_id, event.decision_id,
                event.sequence, ts_iso, event.operator_id,
                event.payload_hash, event.previous_hash,
                event.ledger_id, event.tenant_id, event.schema_version
            )
            
            # 3. Verify Hash
            recomputed_hash = _compute_record_hash(envelope)
            if event.record_hash != recomputed_hash:
                return {"valid": False, "broken_at": event.sequence, "details": f"Tamper detected in metadata at sequence {event.sequence}"}

            # 4. Verify HMAC (Internal Authenticity)
            recomputed_hmac = _compute_hmac(event.record_hash)
            if event.signature_hmac and event.signature_hmac != recomputed_hmac:
                return {"valid": False, "broken_at": event.sequence, "details": f"Unauthorized record mutation (HMAC fail) at sequence {event.sequence}"}

        return {"valid": True, "total_events": len(events), "details": "All hashes and signatures verified."}

    @staticmethod
    def verify_mission(mission_id):
        """Verify all decision chains within a mission."""
        decision_ids = db.session.query(DecisionLedger.decision_id) \
            .filter_by(mission_id=mission_id).distinct().all()
        decision_ids = [d[0] for d in decision_ids]

        failures = []
        for did in decision_ids:
            result = LedgerService.verify_chain(did)
            if not result["valid"]:
                failures.append({"decision_id": did, **result})

        return {
            "valid": len(failures) == 0,
            "decisions_checked": len(decision_ids),
            "failures": failures,
        }
