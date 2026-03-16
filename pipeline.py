"""
KorumOS Async Document Pipeline — Celery Worker

Processes vault-uploaded documents through a sequential pipeline:
  uploaded → scanning → extracted → falcon_processed → ready

Each step writes a Decision Ledger event for full audit trail.
Requires: Redis (broker), S3 access, Flask app context for DB.
"""

import os
import sys
import time
import hashlib

# Ensure app directory is in Python path (Railway deploys to /app/ which
# collides with the module name 'app' — this resolves the ambiguity)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery import Celery

# ── Celery Configuration ─────────────────────────────────────────────────
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER = os.getenv('CELERY_BROKER_URL', REDIS_URL)

# Handle Railway's rediss:// SSL URLs
if CELERY_BROKER.startswith('rediss://') and 'ssl_cert_reqs' not in CELERY_BROKER:
    separator = '&' if '?' in CELERY_BROKER else '?'
    CELERY_BROKER = f'{CELERY_BROKER}{separator}ssl_cert_reqs=none'

celery_app = Celery('korum', broker=CELERY_BROKER)
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    task_track_started=True,
    task_acks_late=True,  # Don't ack until task completes — survives worker restarts
    worker_prefetch_multiplier=1,  # One task at a time per worker
)


def _get_flask_app():
    """Lazy-import Flask app for DB context in worker process."""
    from app import app
    return app


def _ledger_write(event_type, mission_id, decision_id, payload, operator_id=None):
    """Write a ledger event — non-blocking, errors logged but not raised."""
    try:
        from ledger import LedgerService
        LedgerService.write_event(
            event_type=event_type,
            mission_id=mission_id,
            decision_id=decision_id,
            payload=payload,
            operator_id=operator_id,
        )
    except Exception as e:
        print(f"[PIPELINE] Ledger write failed ({event_type}): {e}")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_vault_document(self, vault_doc_id):
    """Process an uploaded vault document through the full pipeline.

    Steps:
      1. Verify S3 upload (document_uploaded)
      2. Malware scan (document_scan_passed) — mock for now
      3. Text extraction (extraction_completed)
      4. Falcon PII redaction (falcon_processed)
      5. Mark ready for council

    Each step updates VaultDocument.status and writes a ledger event.
    On failure, status → 'failed' with error details.
    """
    flask_app = _get_flask_app()
    with flask_app.app_context():
        from models import VaultDocument
        from db import db

        vault_doc = VaultDocument.query.get(vault_doc_id)
        if not vault_doc:
            print(f"[PIPELINE] Document not found: {vault_doc_id}")
            return {'status': 'error', 'detail': 'Document not found'}

        mission_id = vault_doc.mission_id or 'unscoped'
        decision_id = vault_doc_id  # Use vault doc ID as decision_id for ledger chain

        try:
            # ── Step 1: Verify Upload ────────────────────────────────────
            _step_verify_upload(vault_doc, mission_id, decision_id, db)

            # ── Step 2: Malware Scan ─────────────────────────────────────
            _step_malware_scan(vault_doc, mission_id, decision_id, db)

            # ── Step 3: Text Extraction ──────────────────────────────────
            _step_extract_text(vault_doc, mission_id, decision_id, db)

            # ── Step 4: Falcon PII Redaction ─────────────────────────────
            _step_falcon_redact(vault_doc, mission_id, decision_id, db)

            # ── Done ─────────────────────────────────────────────────────
            vault_doc.status = 'ready'
            db.session.commit()
            print(f"[PIPELINE] Complete: {vault_doc_id[:8]} → ready")

            return {'status': 'ready', 'vault_doc_id': vault_doc_id}

        except Exception as e:
            vault_doc.status = 'failed'
            vault_doc.error_detail = f"{type(e).__name__}: {str(e)[:400]}"
            db.session.commit()

            _ledger_write('document_processing_failed', mission_id, decision_id, {
                'vault_key': vault_doc.s3_key,
                'failed_step': vault_doc.status,
                'error_type': type(e).__name__,
            }, operator_id=vault_doc.user_id)

            print(f"[PIPELINE] Failed: {vault_doc_id[:8]} — {e}")
            raise self.retry(exc=e)


def _step_verify_upload(vault_doc, mission_id, decision_id, db):
    """Verify the S3 object exists and record metadata."""
    from vault import stream_from_s3, _get_s3_client, S3_BUCKET

    s3 = _get_s3_client()
    head = s3.head_object(Bucket=S3_BUCKET, Key=vault_doc.s3_key)
    vault_doc.size_bytes = head.get('ContentLength', vault_doc.size_bytes)
    vault_doc.status = 'uploaded'
    db.session.commit()

    _ledger_write('document_uploaded', mission_id, decision_id, {
        'vault_key': vault_doc.s3_key,
        's3_etag': head.get('ETag', '').strip('"'),
        'size_bytes': vault_doc.size_bytes,
    }, operator_id=vault_doc.user_id)

    print(f"[PIPELINE] Step 1/4: Upload verified — {vault_doc.size_bytes} bytes")


def _step_malware_scan(vault_doc, mission_id, decision_id, db):
    """Run malware scan on the uploaded file.
    Currently a mock — always passes. Replace with ClamAV integration."""
    t0 = time.time()

    # TODO: Integrate pyclamd for real scanning
    # For now, mock scan that always passes
    scan_passed = True
    scan_ms = int((time.time() - t0) * 1000)

    if not scan_passed:
        raise RuntimeError("Malware scan failed — file quarantined")

    vault_doc.status = 'scanning'
    db.session.commit()

    _ledger_write('document_scan_passed', mission_id, decision_id, {
        'vault_key': vault_doc.s3_key,
        'scanner': 'mock_v1',
        'scan_duration_ms': scan_ms,
    }, operator_id=vault_doc.user_id)

    print(f"[PIPELINE] Step 2/4: Scan passed ({scan_ms}ms)")


def _step_extract_text(vault_doc, mission_id, decision_id, db):
    """Stream file from S3 and extract text content."""
    from vault import stream_from_s3
    from file_processor import process_from_bytes

    t0 = time.time()
    content = stream_from_s3(vault_doc.s3_key)

    # Derive filename from S3 key for extension detection
    filename = vault_doc.s3_key.rsplit('/', 1)[-1]
    result = process_from_bytes(content, filename)

    extracted = result.get('extracted_text', '')
    extract_ms = int((time.time() - t0) * 1000)

    vault_doc.extracted_text = extracted
    vault_doc.status = 'extracted'
    db.session.commit()

    _ledger_write('extraction_completed', mission_id, decision_id, {
        'vault_key': vault_doc.s3_key,
        'char_count': len(extracted) if extracted else 0,
        'extraction_method': 'process_from_bytes',
        'extraction_ms': extract_ms,
    }, operator_id=vault_doc.user_id)

    print(f"[PIPELINE] Step 3/4: Extracted {len(extracted)} chars ({extract_ms}ms)")


def _step_falcon_redact(vault_doc, mission_id, decision_id, db):
    """Run Falcon PII redaction on extracted text."""
    if not vault_doc.extracted_text:
        vault_doc.status = 'falcon_processed'
        db.session.commit()
        print("[PIPELINE] Step 4/4: No text to redact — skipped")
        return

    from falcon import falcon_preprocess
    import hashlib as _hl
    import time as _time

    t0 = _time.time()
    salt = _hl.sha256(f"vault:{vault_doc.id}:{_time.time_ns()}".encode()).hexdigest()[:12]
    falcon_result = falcon_preprocess(
        vault_doc.extracted_text,
        level='STANDARD',
        salt=salt,
        placeholder_cache={},
    )
    redact_ms = int((_time.time() - t0) * 1000)

    # Store the redacted text — placeholder map stays in memory only
    vault_doc.extracted_text = falcon_result.redacted_text
    vault_doc.status = 'falcon_processed'
    db.session.commit()

    meta = falcon_result.metadata
    _ledger_write('falcon_processed', mission_id, decision_id, {
        'vault_key': vault_doc.s3_key,
        'total_redactions': meta.get('total_redactions', 0),
        'categories': meta.get('counts_by_category', {}),
        'exposure_risk': meta.get('exposure_risk', 'none'),
        'redaction_ms': redact_ms,
    }, operator_id=vault_doc.user_id)

    print(f"[PIPELINE] Step 4/4: Falcon redacted {meta.get('total_redactions', 0)} entities ({redact_ms}ms)")
