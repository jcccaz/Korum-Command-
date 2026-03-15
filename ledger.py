"""
Decision Ledger — Immutable, tamper-evident flight recorder for KorumOS.

Every AI-assisted decision creates a hash-chained sequence of events.
Chain is scoped per decision_id. Each event includes SHA-256(payload + previous_hash).

PRIVACY RULE: Never store raw prompt text, raw model output, or raw Falcon token
mappings. Only hashes, counts, metadata, aggregate scores, and IDs.
"""

import hashlib
import json
from datetime import datetime, timezone

from db import db
from models import DecisionLedger

GENESIS_HASH = "GENESIS"


class LedgerService:
    """Append-only, hash-chained event writer and verifier."""

    @staticmethod
    def write_event(event_type, mission_id, decision_id, payload, operator_id=None):
        """Write a new event to the ledger, chaining it to the previous event for this decision_id.

        Args:
            event_type: One of the defined event types (prompt_received, falcon_redaction, etc.)
            mission_id: Thread/mission UUID
            decision_id: Run UUID (unique per council execution)
            payload: Dict of event-specific metadata (NO raw PII)
            operator_id: User ID of the operator (optional)

        Returns:
            The created DecisionLedger record
        """
        # Determine sequence: max(sequence) + 1 for this decision_id, starting at 1
        last = DecisionLedger.query.filter_by(decision_id=decision_id) \
            .order_by(DecisionLedger.sequence.desc()).first()
        sequence = (last.sequence + 1) if last else 1
        previous_hash = last.record_hash if last else GENESIS_HASH

        # Serialize payload deterministically (sorted keys for consistent hashing)
        payload_json = json.dumps(payload, sort_keys=True, default=str)

        # Compute hash: SHA-256(payload_json + previous_hash)
        record_hash = _compute_hash(payload_json, previous_hash)

        entry = DecisionLedger(
            event_type=event_type,
            mission_id=mission_id,
            decision_id=decision_id,
            sequence=sequence,
            timestamp=datetime.now(timezone.utc),
            operator_id=operator_id,
            payload=payload_json,
            record_hash=record_hash,
            previous_hash=previous_hash,
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
    def get_mission_events(mission_id):
        """Fetch all events across all decisions for a mission, ordered by timestamp."""
        return DecisionLedger.query.filter_by(mission_id=mission_id) \
            .order_by(DecisionLedger.timestamp.asc()).all()

    @staticmethod
    def verify_chain(decision_id):
        """Walk the chain for a decision_id and verify hash integrity.

        Returns:
            dict: {valid: bool, total_events: int, broken_at: int|None, details: str}
        """
        events = DecisionLedger.query.filter_by(decision_id=decision_id) \
            .order_by(DecisionLedger.sequence.asc()).all()

        if not events:
            return {"valid": True, "total_events": 0, "broken_at": None,
                    "details": "No events found for this decision."}

        for i, event in enumerate(events):
            expected_previous = events[i - 1].record_hash if i > 0 else GENESIS_HASH

            # Check previous_hash linkage
            if event.previous_hash != expected_previous:
                return {
                    "valid": False,
                    "total_events": len(events),
                    "broken_at": event.sequence,
                    "details": f"Chain broken at sequence {event.sequence}: "
                               f"previous_hash mismatch (expected {expected_previous[:12]}..., "
                               f"got {event.previous_hash[:12]}...)"
                }

            # Recompute record_hash from payload + previous_hash
            recomputed = _compute_hash(event.payload, event.previous_hash)
            if event.record_hash != recomputed:
                return {
                    "valid": False,
                    "total_events": len(events),
                    "broken_at": event.sequence,
                    "details": f"Payload tampered at sequence {event.sequence}: "
                               f"hash mismatch (stored {event.record_hash[:12]}..., "
                               f"recomputed {recomputed[:12]}...)"
                }

        return {
            "valid": True,
            "total_events": len(events),
            "broken_at": None,
            "details": f"All {len(events)} events verified. Chain intact."
        }

    @staticmethod
    def verify_mission(mission_id):
        """Verify all decision chains within a mission.

        Returns:
            dict: {valid: bool, decisions_checked: int, failures: [decision_id, ...]}
        """
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


def _compute_hash(payload_json, previous_hash):
    """SHA-256(payload_json + previous_hash) → 64-char hex string."""
    return hashlib.sha256((payload_json + previous_hash).encode()).hexdigest()
