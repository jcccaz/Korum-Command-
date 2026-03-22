# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

from db import db
from datetime import datetime
import uuid
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # admin, compliance, user
    mfa_secret = db.Column(db.String(32), nullable=True)  # TOTP secret for MFA
    mfa_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, raw_password: str) -> None:
        self.hashed_password = generate_password_hash(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return check_password_hash(self.hashed_password, raw_password)

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_compliance(self) -> bool:
        return self.role in ("admin", "compliance")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)  # login, logout, login_failed, access_denied, etc.
    user_id = db.Column(db.Integer, nullable=True)
    user_email = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 max length
    user_agent = db.Column(db.String(500), nullable=True)
    endpoint = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)
    success = db.Column(db.Boolean, default=True)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True)
    query_text = db.Column("query", db.Text, nullable=True)
    results = db.Column(db.Text, nullable=True)       # JSON string
    consensus = db.Column(db.Text, nullable=True)
    synthesis = db.Column(db.Text, nullable=True)      # JSON string
    classification = db.Column(db.Text, nullable=True) # JSON string
    docked_snippets = db.Column(db.Text, nullable=True) # JSON string
    role_name = db.Column(db.String(100), nullable=True)
    provider_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Thread(db.Model):
    __tablename__ = "threads"

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(36), unique=True, nullable=False, index=True,
                          default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(200), nullable=False, default="New Analysis")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    messages = db.relationship('Message', backref='thread', lazy='dynamic',
                               cascade='all, delete-orphan',
                               foreign_keys='Message.thread_id',
                               primaryjoin='Thread.thread_id == Message.thread_id')

    def __repr__(self):
        return f"<Thread {self.thread_id[:8]} — {self.title}>"


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(36), db.ForeignKey('threads.thread_id'),
                          nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # user | council | interrogation | verification | system
    content = db.Column(db.Text, nullable=True)       # JSON string
    metadata_ = db.Column("metadata", db.Text, nullable=True)  # JSON string (scores, etc.)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Message {self.role} in {self.thread_id[:8]}>"


class DecisionLedger(db.Model):
    """Witness Layer (Thin Ledger) — Cryptographic proof of every decision.
    NEVER stores raw PII or prompt/response text.
    Hmac-protected and hash-chained per decision_id."""
    __tablename__ = "decision_ledger"

    id = db.Column(db.Integer, primary_key=True)
    ledger_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    tenant_id = db.Column(db.String(50), nullable=True, index=True) # Organization ID
    event_type = db.Column(db.String(50), nullable=False, index=True)
    mission_id = db.Column(db.String(36), nullable=False, index=True)
    decision_id = db.Column(db.String(36), nullable=False, index=True)
    sequence = db.Column(db.Integer, nullable=False)  # Logical, per decision_id, starts at 1
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    operator_id = db.Column(db.Integer, nullable=True)
    
    # CONTENT HASING
    payload_hash = db.Column(db.String(64), nullable=False)  # SHA-256 of the canonical EvidenceArchive
    schema_version = db.Column(db.String(10), nullable=False, default="1.0")
    large_artifact = db.Column(db.Boolean, default=False)  # Flaged if evidence > 5MB
    
    # INTEGRITY
    record_hash = db.Column(db.String(64), nullable=False)  # SHA-256 hex link
    previous_hash = db.Column(db.String(64), nullable=False)  # SHA-256 hex, "GENESIS" for first
    signature_hmac = db.Column(db.String(128), nullable=True)  # Record integrity protection

    __table_args__ = (
        db.Index('ix_ledger_decision_sequence', 'decision_id', 'sequence'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "ledger_id": self.ledger_id,
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "mission_id": self.mission_id,
            "decision_id": self.decision_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "operator_id": self.operator_id,
            "payload_hash": self.payload_hash,
            "schema_version": self.schema_version,
            "large_artifact": self.large_artifact,
            "record_hash": self.record_hash,
            "previous_hash": self.previous_hash,
            "signature_hmac": self.signature_hmac
        }


class EvidenceArchive(db.Model):
    """Evidence Layer (Thick Vault) — Stores raw payloads behind the hash seal.
    Access to this table must be audited and restricted to the 'compliance' role."""
    __tablename__ = "evidence_archive"

    id = db.Column(db.Integer, primary_key=True)
    payload_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)  # Canonical JSON
    data_class = db.Column(db.String(30), nullable=True)  # e.g. 'SENSITIVE', 'FINANCIAL'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MissionVault(db.Model):
    """Per-mission pseudonym vault for Falcon deterministic pseudonymization (Phase 2).
    Maps (mission_id, category, entity_hash) -> sequential pseudonym (e.g. PERSON_01).
    Stores entity hashes only — raw PII is NEVER persisted."""
    __tablename__ = "mission_vault"

    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.String(36), nullable=False, index=True)
    category = db.Column(db.String(30), nullable=False)
    entity_hash = db.Column(db.String(64), nullable=False)
    pseudonym = db.Column(db.String(30), nullable=False)
    sequence_num = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('mission_id', 'category', 'entity_hash', name='uq_vault_entity'),
        db.UniqueConstraint('mission_id', 'category', 'sequence_num', name='uq_vault_sequence'),
        db.Index('ix_vault_mission_category', 'mission_id', 'category'),
    )


class VaultDocument(db.Model):
    """Tracks documents uploaded via the S3 Vault pipeline.
    File bytes never touch Flask — only metadata and extracted text stored here."""
    __tablename__ = "vault_documents"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id = db.Column(db.String(36), nullable=True, index=True)
    user_id = db.Column(db.Integer, nullable=True)
    s3_key = db.Column(db.String(500), nullable=False)
    filename_hash = db.Column(db.String(64), nullable=False)  # SHA-256, never store raw filename
    content_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='authorized', index=True)
    # Statuses: authorized → uploaded → scanning → extracted → falcon_processed → ready | failed
    extracted_text = db.Column(db.Text, nullable=True)  # Cleared after council use (Goldfish)
    error_detail = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "status": self.status,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "error_detail": self.error_detail,
        }


class UsageLog(db.Model):
    __tablename__ = "usage_logs"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(
        db.String(36), default=lambda: str(uuid.uuid4()), index=True
    )
    run_id = db.Column(db.String(36), index=True, nullable=True)
    session_id = db.Column(db.String(36), index=True, nullable=True)
    user_id = db.Column(db.Integer, nullable=True)
    workflow_name = db.Column(db.String(50), nullable=True)
    provider_name = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=False)
    persona = db.Column(db.String(100), nullable=True)
    tokens_input = db.Column(db.Integer, nullable=True)
    tokens_output = db.Column(db.Integer, nullable=True)
    cost_estimate = db.Column(db.Float, nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    success = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
