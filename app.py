# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

import os
import re
import json
import time
import logging
import secrets
import copy
import threading
import uuid
from datetime import datetime
from functools import wraps
import requests
import concurrent.futures
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
import redis
from dotenv import load_dotenv
from sqlalchemy import case, func
from db import db, init_db
from falcon import falcon_preprocess, falcon_rehydrate  # Falcon Protocol: secure redaction layer

# Initialize early
load_dotenv()

# --- Structured Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("korumos")
audit_logger = logging.getLogger("korumos.audit")

# GOOGLE IPv4 FIX: Force IPv4 to prevent socket hangs
import socket
_old_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _old_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only_getaddrinfo

# Flask App Init - MUST be before any @app.route decorators
app = Flask(__name__, static_folder='.', static_url_path='')

# --- Security Configuration ---
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

# --- Redis Configuration ---
REDIS_URL = os.getenv("REDIS_URL", None)
redis_client = None

if REDIS_URL:
    # Handling Railway/managed rediss:// URLs
    # We append ssl_cert_reqs=none to the URI for simple compatibility if using rediss
    modified_redis_url = REDIS_URL
    if REDIS_URL.startswith("rediss://") and "ssl_cert_reqs" not in REDIS_URL:
        separator = "&" if "?" in REDIS_URL else "?"
        modified_redis_url = f"{REDIS_URL}{separator}ssl_cert_reqs=none"
    
    try:
        redis_client = redis.from_url(modified_redis_url)
        app.config["SESSION_TYPE"] = "redis"
        app.config["SESSION_REDIS"] = redis_client
        app.config["SESSION_PERMANENT"] = True
        app.config["SESSION_KEY_PREFIX"] = "korum:"
        Session(app)
        logger.info(f"[REDIS] Session persistence enabled via Redis")
    except Exception as e:
        logger.error(f"[REDIS] Connection failed: {e}")
        redis_client = None
else:
    logger.warning("[REDIS] REDIS_URL not set — using default Flask sessions (non-persistent)")

# --- Council Job Store (async polling) ---
# In-memory fallback when Redis unavailable. Safe with --workers 1 (current config).
_council_jobs = {}  # {job_id: {"status": ..., "phase": ..., "result": ...}}

COUNCIL_JOB_TTL = 600  # 10 minutes — Redis key expiry for completed jobs

def _job_set_status(job_id, status, phase=None, error=None):
    """Update job status in Redis (or in-memory fallback)."""
    data = {"status": status}
    if phase:
        data["phase"] = phase
    if error:
        data["error"] = error
    payload = json.dumps(data)
    if redis_client:
        try:
            redis_client.setex(f"council:job:{job_id}", COUNCIL_JOB_TTL, payload)
            return
        except Exception as e:
            logger.warning(f"[JOB] Redis write failed, using memory: {e}")
    _council_jobs[job_id] = data

def _job_set_result(job_id, response_data):
    """Store completed job result in Redis (or in-memory fallback)."""
    result_json = json.dumps(response_data)
    _job_set_status(job_id, "complete", phase="done")
    if redis_client:
        try:
            redis_client.setex(f"council:result:{job_id}", COUNCIL_JOB_TTL, result_json)
            return
        except Exception as e:
            logger.warning(f"[JOB] Redis result write failed, using memory: {e}")
    _council_jobs.setdefault(job_id, {})["result"] = response_data

def _job_get(job_id):
    """Read job status + result. Returns (status_dict, result_json_or_None)."""
    if redis_client:
        try:
            status_raw = redis_client.get(f"council:job:{job_id}")
            if status_raw:
                status = json.loads(status_raw)
                result_raw = None
                if status.get("status") == "complete":
                    result_raw = redis_client.get(f"council:result:{job_id}")
                return status, result_raw
            # Fall through to memory check
        except Exception as e:
            logger.warning(f"[JOB] Redis read failed, checking memory: {e}")
    # In-memory fallback
    job = _council_jobs.get(job_id)
    if job:
        result = job.get("result")
        return job, json.dumps(result) if result else None
    return None, None

def _job_cleanup(job_id):
    """Remove job keys after result is delivered."""
    if redis_client:
        try:
            redis_client.delete(f"council:job:{job_id}", f"council:result:{job_id}")
        except Exception:
            pass
    _council_jobs.pop(job_id, None)

# Auth can be disabled for local dev via env var
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

CORS(app, supports_credentials=True)

# --- Rate Limiting ---
# Use the same modified URL for the limiter to ensure TLS compatibility
limiter_uri = "memory://"
if redis_client and REDIS_URL:
    # Flask-Limiter handles the connection itself, but needs the URL
    if REDIS_URL.startswith("rediss://") and "ssl_cert_reqs" not in REDIS_URL:
        separator = "&" if "?" in REDIS_URL else "?"
        limiter_uri = f"{REDIS_URL}{separator}ssl_cert_reqs=none"
    else:
        limiter_uri = REDIS_URL

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri=limiter_uri,
)

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)

# Database configuration (Railway/Postgres via DATABASE_URL)
database_url = os.getenv("DATABASE_URL", "sqlite:///korumos.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Register models so SQLAlchemy can create tables.
from models import User, UsageLog, AuditLog, Report, Thread, Message, DecisionLedger
from ledger import LedgerService

init_db(app)

# --- User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Audit Helper ---
def log_audit(event_type, user_id=None, user_email=None, details=None, success=True):
    try:
        entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            user_email=user_email,
            ip_address=request.remote_addr if request else None,
            user_agent=str(request.user_agent)[:500] if request else None,
            endpoint=request.path if request else None,
            details=details,
            success=success,
        )
        db.session.add(entry)
        db.session.commit()
        audit_logger.info(f"[{event_type}] user={user_email} ip={request.remote_addr if request else 'N/A'} success={success} {details or ''}")
    except Exception as e:
        db.session.rollback()
        audit_logger.error(f"Audit log write failed: {e}")

# --- Input Validation ---
def sanitize_input(text, max_length=50000):
    if not isinstance(text, str):
        return ""
    text = text[:max_length]
    return text

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password):
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain an uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain a lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain a number"
    return True, "OK"

# --- Auth-Required Decorator (respects AUTH_ENABLED) ---
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        if not current_user.is_authenticated:
            log_audit("access_denied", details="Unauthenticated request", success=False)
            return jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated

# --- HTTPS Enforcement ---
@app.before_request
def enforce_https():
    if os.getenv("FLASK_ENV") == "production":
        # Only enforce HTTPS if we are not on localhost (Railway/etc)
        # Check for both IPv4, IPv6, and hostname localhost to prevent local dev loops
        is_local = any(h in request.host for h in ["localhost", "127.0.0.1", "::1"])
        if request.headers.get("X-Forwarded-Proto", "http") == "http" and not is_local:
            url = request.url.replace("http://", "https://", 1)
            return jsonify({"error": "HTTPS required", "redirect": url}), 301

# --- Security Headers ---
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# --- Global Error Handlers (always return JSON, never HTML) ---
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found"}), 404
    return e

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"[500] {request.method} {request.path} — {e}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return e

@app.errorhandler(405)
def method_not_allowed(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Method not allowed"}), 405
    return e

# ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("20 per hour")
def register():
    return jsonify({"success": False, "error": "Registration is currently closed for the presentation."}), 403

    try:
        data = request.json or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password', '')

        if not email or not validate_email(email):
            return jsonify({"success": False, "error": "Valid email required"}), 400

        valid, msg = validate_password(password)
        if not valid:
            return jsonify({"success": False, "error": msg}), 400

        if User.query.filter_by(email=email).first():
            log_audit("register_failed", user_email=email, details="Email already exists", success=False)
            return jsonify({"success": False, "error": "Email already registered"}), 409

        # First user becomes admin
        user_count = User.query.count()
        role = "admin" if user_count == 0 else "user"

        user = User(email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=True)
        log_audit("register", user_id=user.id, user_email=email, details=f"role={role}")
        logger.info(f"New user registered: {email} (role={role})")

        return jsonify({
            "success": True,
            "user": {"id": user.id, "email": user.email, "role": user.role}
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Register error: {e}")
        return jsonify({"success": False, "error": "Registration failed — please try again"}), 500


@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    try:
        data = request.json or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not user.verify_password(password):
            log_audit("login_failed", user_email=email, details="Invalid credentials", success=False)
            return jsonify({"success": False, "error": "Invalid email or password"}), 401

        login_user(user, remember=True)
        user.last_login = datetime.utcnow()
        db.session.commit()
        log_audit("login", user_id=user.id, user_email=email)

        return jsonify({
            "success": True,
            "user": {"id": user.id, "email": user.email, "role": user.role}
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": "Login failed — please try again"}), 500


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    if current_user.is_authenticated:
        log_audit("logout", user_id=current_user.id, user_email=current_user.email)
    logout_user()
    return jsonify({"success": True})


@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "auth_enabled": AUTH_ENABLED,
            "user": {"id": current_user.id, "email": current_user.email, "role": current_user.role}
        })
    return jsonify({"authenticated": False, "auth_enabled": AUTH_ENABLED})


@app.route('/api/auth/audit', methods=['GET'])
@auth_required
def get_audit_log():
    if AUTH_ENABLED and (not current_user.is_authenticated or not current_user.is_admin()):
        return jsonify({"error": "Admin access required"}), 403
    limit = request.args.get('limit', default=100, type=int)
    limit = max(1, min(limit, 500))
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return jsonify({
        "success": True,
        "logs": [
            {
                "id": l.id,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                "event_type": l.event_type,
                "user_email": l.user_email,
                "ip_address": l.ip_address,
                "endpoint": l.endpoint,
                "details": l.details,
                "success": l.success,
            }
            for l in logs
        ]
    })


# ── DECISION LEDGER API ──────────────────────────────────────────────
@app.route('/api/ledger/<mission_id>', methods=['GET'])
@auth_required
def get_mission_ledger(mission_id):
    """Fetch all ledger events for a mission, ordered by timestamp."""
    # mission_id == thread_id — verify ownership
    thread = Thread.query.filter_by(thread_id=mission_id).first()
    if not thread:
        return jsonify({"error": "Mission not found"}), 404
    if thread.user_id != current_user.id and not getattr(current_user, 'role', '') == 'admin':
        return jsonify({"error": "Access denied"}), 403
    events = LedgerService.get_mission_events(mission_id)
    return jsonify({
        "success": True,
        "mission_id": mission_id,
        "total_events": len(events),
        "events": [e.to_dict() for e in events],
    })


@app.route('/api/ledger/<mission_id>/verify', methods=['GET'])
@auth_required
def verify_mission_ledger(mission_id):
    """Verify hash chain integrity for all decision chains in a mission."""
    thread = Thread.query.filter_by(thread_id=mission_id).first()
    if not thread:
        return jsonify({"error": "Mission not found"}), 404
    if thread.user_id != current_user.id and not getattr(current_user, 'role', '') == 'admin':
        return jsonify({"error": "Access denied"}), 403
    result = LedgerService.verify_mission(mission_id)
    return jsonify({"success": True, "mission_id": mission_id, **result})


@app.route('/api/ledger/decision/<decision_id>/chain', methods=['GET'])
@auth_required
def get_decision_chain(decision_id):
    """Fetch single decision chain, ordered by sequence."""
    # Look up mission_id from first event, then verify thread ownership
    events = LedgerService.get_chain(decision_id)
    if not events:
        return jsonify({"error": "Decision not found"}), 404
    mission_id = events[0].mission_id
    thread = Thread.query.filter_by(thread_id=mission_id).first()
    if not thread:
        return jsonify({"error": "Mission not found"}), 404
    if thread.user_id != current_user.id and not getattr(current_user, 'role', '') == 'admin':
        return jsonify({"error": "Access denied"}), 403
    verification = LedgerService.verify_chain(decision_id)
    return jsonify({
        "success": True,
        "decision_id": decision_id,
        "total_events": len(events),
        "chain_valid": verification["valid"],
        "events": [e.to_dict() for e in events],
    })


# Import Generator
from engine_v2 import execute_council_v2, generate_presentation_preview, generate_pptx_file, mediate_truth_scores

# Cost logic moved to llm_core.py for centralization.
from llm_core import MODEL_COST, estimate_cost


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# --- Configuration (must be before routes that use clients) ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
PERPLEXITY_KEY = os.getenv("PERPLEXITY_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY") or os.getenv("SerpApi_API_KEY")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar-pro")
PERPLEXITY_ENABLED = _env_bool("PERPLEXITY_ENABLED", True)
PERPLEXITY_MAX_INPUT_CHARS = int(os.getenv("PERPLEXITY_MAX_INPUT_CHARS", "12000"))
PERPLEXITY_MAX_TOKENS = int(os.getenv("PERPLEXITY_MAX_TOKENS", "700"))
PERPLEXITY_MAX_REQUEST_COST_USD = float(os.getenv("PERPLEXITY_MAX_REQUEST_COST_USD", "0.30"))
PERPLEXITY_DAILY_BUDGET_USD = float(os.getenv("PERPLEXITY_DAILY_BUDGET_USD", "5.00"))
PERPLEXITY_REQUEST_FEE_USD = float(os.getenv("PERPLEXITY_REQUEST_FEE_USD", "0.00"))
ALERT_BUDGET_AMBER_PCT = float(os.getenv("ALERT_BUDGET_AMBER_PCT", "0.70"))
ALERT_BUDGET_RED_PCT = float(os.getenv("ALERT_BUDGET_RED_PCT", "0.95"))

# --- Model Clients ---
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_KEY, timeout=90.0) if OPENAI_KEY else None
except ImportError:
    openai_client = None

try:
    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY, timeout=90.0) if ANTHROPIC_KEY else None
except ImportError:
    anthropic_client = None

try:
    from google import genai
    google_client = genai.Client(api_key=GOOGLE_KEY) if GOOGLE_KEY else None
except ImportError:
    google_client = None

# --- Exports Directory ---
EXPORTS_DIR = os.path.join(os.getcwd(), 'exports')
os.makedirs(EXPORTS_DIR, exist_ok=True)

@app.route('/api/deploy_intelligence', methods=['POST'])
@auth_required
def deploy_intelligence():
    data = request.json
    intelligence_object = data.get('intelligence_object')
    card_results = data.get('card_results', {})
    format_type = data.get('format', 'docx')
    mission_context = data.get('mission_context')

    if not intelligence_object:
        return jsonify({"error": "Missing intelligence data"}), 400

    # Attach card results so exporters can include per-provider analysis
    intelligence_object['_card_results'] = card_results

    # Attach mission context for dynamic report branding
    if mission_context:
        intelligence_object['_mission_context'] = mission_context

    div_data = intelligence_object.get("divergence_analysis")
    print(f"🚀 Deploying Intelligence Asset: {format_type.upper()} | Divergence present: {bool(div_data)} | Keys: {list(div_data.keys()) if isinstance(div_data, dict) else 'N/A'}")
    
    try:
        from exporters import (
            CSVExporter,
            ExcelExporter,
            ExecutiveMemoExporter,
            JSONExporter,
            MarkdownExporter,
            PDFExporter,
            PPTXExporter,
            ResearchPaperExporter,
            ResearchPaperWordExporter,
            TextExporter,
            WordExporter,
        )

        exporters = {
            'docx': WordExporter,
            'pptx': PPTXExporter,
            'xlsx': ExcelExporter,
            'csv': CSVExporter,
            'json': JSONExporter,
            'md': MarkdownExporter,
            'txt': TextExporter,
            'pdf': PDFExporter,
            'pdf-memo': ExecutiveMemoExporter,
            'paper': ResearchPaperExporter,
            'paper-docx': ResearchPaperWordExporter,
        }

        exporter = exporters.get(format_type)
        if not exporter:
            return jsonify({"error": f"Format {format_type} not supported"}), 501

        theme = data.get('theme', 'NEON_DESERT')
        if 'meta' not in intelligence_object:
            intelligence_object['meta'] = {}
        intelligence_object['meta']['theme'] = theme

        filepath = exporter.generate(intelligence_object, output_dir=EXPORTS_DIR)
        filepath = os.path.abspath(filepath)
        mime_types = {
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
            'pdf-memo': 'application/pdf',
            'paper': 'application/pdf',
            'paper-docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'csv': 'text/csv',
            'json': 'application/json',
            'md': 'text/markdown',
            'txt': 'text/plain',
        }
        mimetype = mime_types.get(format_type, 'application/octet-stream')
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath), mimetype=mimetype)

    except Exception as e:
        import traceback
        print(f"❌ Deployment Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_preview', methods=['POST'])
def generate_preview():
    # ... (existing code) ...
    data = request.json
    synthesis = data.get('synthesis')
    classification = data.get('classification')
    artifact_type = data.get('type')
    
    if not synthesis: return jsonify({"error": "Missing synthesis data"}), 400
        
    print(f"🎨 Generating Artifact Preview: {artifact_type.upper()}")
    
    if artifact_type == 'presentation':
        preview = generate_presentation_preview(synthesis, classification)
        return jsonify(preview)
    return jsonify({"error": "Type not supported yet"}), 501

# ── S3 VAULT — "Authorization, Not Carriage" ────────────────────────
@app.route('/api/vault/authorize', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def vault_authorize():
    """Authorize a direct-to-S3 upload. Returns presigned POST fields.
    File bytes never touch this server."""
    from vault import initialize_vault_upload, vault_available

    if not vault_available():
        return jsonify({"error": "Vault not configured — S3 credentials missing"}), 503

    data = request.json or {}
    filename = data.get('filename', '')
    content_type = data.get('content_type', '')
    size_bytes = data.get('size_bytes')
    mission_id = data.get('mission_id')

    if not filename or not content_type:
        # Log what was sent to help debug client-side MIME inference failures
        logger.warning(f"[VAULT] authorize rejected — filename={repr(filename)} content_type={repr(content_type)}")
        return jsonify({"error": f"filename and content_type required (got filename={repr(filename)}, content_type={repr(content_type)})"}), 400

    try:
        result = initialize_vault_upload(
            user_id=current_user.id,
            mission_id=mission_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        # Write ledger event
        try:
            import hashlib as _hl
            import uuid as _uuid
            from ledger import LedgerService
            LedgerService.write_event(
                event_type='document_upload_authorized',
                mission_id=mission_id or 'unscoped',
                decision_id=result['vault_doc_id'],
                payload={
                    'operator_id': current_user.id,
                    'filename_hash': _hl.sha256(filename.encode()).hexdigest(),
                    'content_type': content_type,
                    'size_bytes': size_bytes,
                    'vault_key': result['s3_key'],
                },
                operator_id=current_user.id,
            )
        except Exception as e:
            logger.warning(f"[VAULT] Ledger write failed: {e}")

        return jsonify({
            "success": True,
            "vault_doc_id": result['vault_doc_id'],
            "presigned_url": result['presigned_url'],
            "presigned_fields": result['presigned_fields'],
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"[VAULT] Authorization failed: {e}", exc_info=True)
        return jsonify({"error": "Vault authorization failed"}), 500


@app.route('/api/vault/complete', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def vault_complete():
    """Confirm upload landed in S3 and trigger async processing pipeline."""
    from vault import confirm_upload
    from pipeline import process_vault_document

    data = request.json or {}
    vault_doc_id = data.get('vault_doc_id')
    if not vault_doc_id:
        return jsonify({"error": "vault_doc_id required"}), 400

    try:
        vault_doc = confirm_upload(vault_doc_id)

        # Verify ownership
        if vault_doc.user_id != current_user.id and not current_user.is_admin():
            return jsonify({"error": "Access denied"}), 403

        # Dispatch async pipeline
        process_vault_document.delay(vault_doc_id)
        print(f"[VAULT] Pipeline dispatched for {vault_doc_id[:8]}")

        return jsonify({
            "success": True,
            "vault_doc_id": vault_doc_id,
            "status": vault_doc.status,
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"[VAULT] Complete failed: {e}", exc_info=True)
        return jsonify({"error": "Upload confirmation failed"}), 500


@app.route('/api/vault/status/<vault_doc_id>', methods=['GET'])
@auth_required
def vault_status(vault_doc_id):
    """Poll pipeline progress for a vault document."""
    from vault import get_vault_document

    vault_doc = get_vault_document(vault_doc_id)
    if not vault_doc:
        return jsonify({"error": "Document not found"}), 404

    # Verify ownership
    if vault_doc.user_id != current_user.id and not current_user.is_admin():
        return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "success": True,
        "vault_doc_id": vault_doc_id,
        "status": vault_doc.status,
        "error_detail": vault_doc.error_detail,
        "has_text": bool(vault_doc.extracted_text),
    })


# ── FALCON GHOST PREVIEW ─────────────────────────────────────────────
@app.route('/api/falcon/preview', methods=['POST'])
def falcon_preview():
    """Pre-flight check: run Falcon redaction and return the ghost text without calling any LLM."""
    from file_processor import process_uploaded_file

    # Support both JSON and FormData (multipart) for file attachments
    doc_count = 0
    if request.content_type and 'multipart/form-data' in request.content_type:
        import json as _json
        data = _json.loads(request.form.get('payload', '{}'))
        uploaded_files = request.files.getlist('files')
    else:
        data = request.json or {}
        uploaded_files = []

    raw_text = data.get('text', '').strip()

    # Extract text from uploaded documents and append to scan
    doc_texts = []
    for f in uploaded_files:
        try:
            result = process_uploaded_file(f)
            if result['type'] == 'document' and result.get('extracted_text'):
                doc_texts.append(f"[Document: {result['filename']}]\n{result['extracted_text']}")
        except (ValueError, Exception) as e:
            print(f"⚠️ Ghost Preview file error: {e}")
            continue

    # Also pull in Vault documents (uploaded via S3 pipeline)
    vault_document_ids = data.get('vault_document_ids', [])
    if vault_document_ids:
        from vault import get_vault_document
        for vdoc_id in vault_document_ids:
            try:
                vdoc = get_vault_document(vdoc_id)
                if not vdoc:
                    continue
                if vdoc.extracted_text:
                    doc_texts.append(f"[Vault Document: {vdoc_id[:8]}]\n{vdoc.extracted_text}")
                    print(f"👁️ Ghost Preview: attached vault doc {vdoc_id[:8]} ({len(vdoc.extracted_text)} chars)")
            except Exception as e:
                print(f"⚠️ Ghost Preview vault doc error: {e}")
                continue

    if doc_texts:
        doc_context = "\n\n--- ATTACHED DOCUMENTS ---\n" + "\n\n".join(doc_texts)
        raw_text = (raw_text + doc_context) if raw_text else doc_context.strip()
        doc_count = len(doc_texts)

    if not raw_text:
        return jsonify({"success": False, "error": "No text provided"}), 400

    level = data.get('level', 'STANDARD')
    custom_terms = data.get('custom_terms', [])

    try:
        import hashlib
        _salt = hashlib.sha256(f"ghost_preview:{time.time_ns()}".encode()).hexdigest()[:12]
        result = falcon_preprocess(
            raw_text,
            level=level,
            custom_terms=custom_terms or None,
            salt=_salt,
            placeholder_cache={}
        )

        print("--- FALCON GHOST PREVIEW ---")
        print(f"  ORIGINAL : {raw_text[:80]}{'...' if len(raw_text) > 80 else ''}")
        print(f"  GHOST    : {result.redacted_text[:80]}{'...' if len(result.redacted_text) > 80 else ''}")
        print(f"  KEYS     : {list(result.placeholder_map.keys())}")
        print("----------------------------")

        return jsonify({
            "success": True,
            "redacted_text": result.redacted_text,
            "total_redactions": result.metadata.get("total_redactions", 0),
            "counts_by_category": result.metadata.get("counts_by_category", {}),
            "categories_found": result.metadata.get("categories_found", []),
            "exposure_risk": result.metadata.get("exposure_risk", "none"),
            "execution_time_ms": result.metadata.get("execution_time_ms", 0),
            "documents_scanned": doc_count
        })
    except Exception as e:
        print(f"FALCON PREVIEW ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate_artifact', methods=['POST'])
def generate_artifact():
    data = request.json
    artifact_type = data.get('type')
    preview_data = data.get('preview')
    
    if not preview_data: return jsonify({"error": "Missing preview data"}), 400

    print(f"🔨 Building Final Artifact: {artifact_type.upper()}")
    
    if artifact_type == 'presentation':
        filename = generate_pptx_file(preview_data)
        filepath = os.path.join(os.getcwd(), filename)
        return send_file(filepath, as_attachment=True, download_name=filename,
                         mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')
    
    return jsonify({"error": "Artifact type not supported"}), 501

# --- Research Dock Persistence & Summarization ---

DOCK_DATA_PATH = os.path.join(os.getcwd(), 'data', 'research_dock.json')

@app.route('/api/dock/save', methods=['POST'])
def save_dock():
    data = request.json
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    snippets = data.get('snippets', [])

    # Validate: must be a list, capped at 50 snippets, max 500KB total
    if not isinstance(snippets, list):
        return jsonify({"success": False, "error": "Snippets must be a list"}), 400
    if len(snippets) > 50:
        return jsonify({"success": False, "error": "Too many snippets (max 50)"}), 400

    payload = json.dumps(snippets, indent=4)
    if len(payload) > 512_000:
        return jsonify({"success": False, "error": "Payload too large (max 500KB)"}), 400

    try:
        os.makedirs(os.path.dirname(DOCK_DATA_PATH), exist_ok=True)

        with open(DOCK_DATA_PATH, 'w', encoding='utf-8') as f:
            f.write(payload)

        print(f"💾 Dock saved: {len(snippets)} snippets")
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Dock save error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/dock/load', methods=['GET'])
def load_dock():
    try:
        if not os.path.exists(DOCK_DATA_PATH):
            return jsonify({"success": True, "snippets": []})
            
        with open(DOCK_DATA_PATH, 'r', encoding='utf-8') as f:
            snippets = json.load(f)
            
        print(f"📂 Dock loaded: {len(snippets)} snippets")
        return jsonify({"success": True, "snippets": snippets})
    except Exception as e:
        print(f"❌ Dock load error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/summarize_snippets', methods=['POST'])
def summarize_snippets():
    data = request.json
    snippets = data.get('snippets', [])
    
    if not snippets:
        return jsonify({"error": "No snippets provided"}), 400
        
    print(f"✨ Summarizing {len(snippets)} snippets...")
    
    # Construct prompt
    snippets_text = ""
    for i, snip in enumerate(snippets):
        snippets_text += f"\n--- SNIPPET {i+1} ({snip.get('label', 'Text')}) ---\n{snip.get('content', '')}\n"
    
    prompt = f"""
Summarize the following research snippets into a cohesive, professional executive brief. 
Identify key themes, critical metrics, and actionable insights. 
Use Markdown with headers and bullet points.

COLLECTED SNIPPETS:
{snippets_text}
"""

    if google_client:
        try:
            response = google_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return jsonify({"success": True, "summary": response.text})
        except Exception as e:
            print(f"❌ Summarization error (Gemini): {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify({"error": "Summarization engine unavailable"}), 501


@app.route('/api/chart', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def generate_chart():
    """Lightweight single-model chart generation. Returns Mermaid code only."""
    data = request.json or {}
    raw_data = data.get('data', '').strip()
    chart_type = data.get('chart_type', 'auto')

    if not raw_data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    CHART_PREAMBLE = (
        "You are a Mermaid.js chart generator. Output ONLY valid Mermaid code inside a ```mermaid``` code block. "
        "RULES: 1) No explanation or text outside the code block. "
        "2) Keep labels SHORT (max 20 chars) — abbreviate or truncate long names. "
        "3) Never use special characters in labels that break Mermaid syntax (no quotes, colons, or brackets inside node text). "
        "4) If data contains '[value not provided]' or 'NOT PROVIDED' or 'Unknown', EXCLUDE those entries from the chart entirely. "
        "5) Use only simple numeric values — strip currency symbols before plotting. "
    )
    CHART_PROMPTS = {
        "pie": CHART_PREAMBLE + "Create a Mermaid pie chart showing the proportional breakdown of the numeric values in this data.",
        "bar": CHART_PREAMBLE + "Create a Mermaid xychart-beta bar chart from the numeric values in this data.",
        "line": CHART_PREAMBLE + "Create a Mermaid xychart-beta line chart from the numeric values in this data.",
        "flowchart": CHART_PREAMBLE + "Create a Mermaid flowchart diagram showing the relationships and process flow in this data.",
        "auto": CHART_PREAMBLE + "Analyze this data and create the most appropriate Mermaid visualization (pie for proportions, xychart-beta bar for comparisons, xychart-beta line for trends, flowchart for processes).",
    }

    prompt = CHART_PROMPTS.get(chart_type, CHART_PROMPTS["auto"])
    prompt += f'\n\nDATA:\n{raw_data}'

    if not google_client:
        return jsonify({"success": False, "error": "Chart engine unavailable"}), 501

    try:
        response = google_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        mermaid_code = response.text.strip()
        # Extract just the mermaid code if wrapped in ```mermaid ... ```
        import re as _re
        m = _re.search(r'```mermaid\s*([\s\S]*?)```', mermaid_code)
        if m:
            mermaid_code = m.group(1).strip()

        return jsonify({
            "success": True,
            "mermaid_code": mermaid_code,
            "chart_type": chart_type,
        })
    except Exception as e:
        print(f"[CHART] Generation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- Thread Management (Persistent Conversation Memory) ---

@app.route('/api/threads', methods=['POST'])
@auth_required
def create_thread():
    data = request.json or {}
    title = data.get('title', 'New Analysis')
    user_id = current_user.id if hasattr(current_user, 'id') else None
    thread = Thread(title=title[:200], user_id=user_id)
    db.session.add(thread)
    db.session.commit()
    return jsonify({
        "thread_id": thread.thread_id,
        "title": thread.title,
        "created_at": thread.created_at.isoformat()
    })

@app.route('/api/threads', methods=['GET'])
@auth_required
def list_threads():
    user_id = current_user.id if hasattr(current_user, 'id') else None
    query = Thread.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    threads = query.order_by(Thread.last_activity.desc()).limit(50).all()
    result = []
    for t in threads:
        msg_count = Message.query.filter_by(thread_id=t.thread_id).count()
        result.append({
            "thread_id": t.thread_id,
            "title": t.title,
            "last_activity": t.last_activity.isoformat() if t.last_activity else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "message_count": msg_count
        })
    return jsonify(result)

@app.route('/api/threads/<thread_id>', methods=['GET'])
@auth_required
def get_thread(thread_id):
    thread = Thread.query.filter_by(thread_id=thread_id).first()
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    messages = Message.query.filter_by(thread_id=thread_id).order_by(Message.created_at.asc()).all()
    return jsonify({
        "thread_id": thread.thread_id,
        "title": thread.title,
        "created_at": thread.created_at.isoformat(),
        "last_activity": thread.last_activity.isoformat() if thread.last_activity else None,
        "messages": [{
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "metadata": m.metadata_,
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in messages]
    })

@app.route('/api/threads/<thread_id>', methods=['DELETE'])
@auth_required
def delete_thread(thread_id):
    thread = Thread.query.filter_by(thread_id=thread_id).first()
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    db.session.delete(thread)  # cascade deletes messages
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/threads/<thread_id>/title', methods=['PATCH'])
@auth_required
def rename_thread(thread_id):
    thread = Thread.query.filter_by(thread_id=thread_id).first()
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    data = request.json or {}
    thread.title = data.get('title', thread.title)[:200]
    db.session.commit()
    return jsonify({"success": True, "title": thread.title})


def _thread_build_previous_context(thread_id):
    """
    Build previous_context array from the last 2 council messages in a thread.
    Also includes a summary of interrogation/verification events so follow-up
    phases see the full A→C intelligence loop (Full Loop Integrity).
    """
    council_msgs = Message.query.filter_by(thread_id=thread_id, role='council') \
        .order_by(Message.created_at.desc()).limit(2).all()
    council_msgs.reverse()  # oldest first
    context = []
    for msg in council_msgs:
        try:
            meta = json.loads(msg.metadata_) if msg.metadata_ else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}
        context.append({
            "query": meta.get("query", ""),
            "summary": meta.get("summary", ""),
            "consensus_score": meta.get("consensus_score"),
            "contested_topics": meta.get("contested_topics", []),
            "divergence_summary": meta.get("divergence_summary", "")
        })

    # --- FULL LOOP INTEGRITY: Append interrogation/verification summary ---
    # So follow-up phases know what was challenged, what held, and what broke.
    score_events = _thread_get_score_events(thread_id)
    if score_events and context:
        loop_summary_parts = []
        for evt in score_events:
            sign = '+' if evt['score_delta'] > 0 else ''
            loop_summary_parts.append(
                f"{evt['type'].upper()}: {evt['verdict']} ({sign}{evt['score_delta']}) targeting {evt['provider']}"
            )
        # Attach to the most recent context entry so the synthesis sees it
        context[-1]["interrogation_history"] = "; ".join(loop_summary_parts)

    return context if context else None


def _thread_get_score_events(thread_id):
    """
    Pull prior interrogation/verification events from thread for score mediation.
    Returns list of dicts suitable for mediate_truth_scores().
    """
    score_msgs = Message.query.filter(
        Message.thread_id == thread_id,
        Message.role.in_(['interrogation', 'verification'])
    ).order_by(Message.created_at.asc()).all()

    events = []
    for msg in score_msgs:
        try:
            meta = json.loads(msg.metadata_) if msg.metadata_ else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}
        delta = meta.get('score_delta')
        if delta is None:
            continue  # legacy event without score data — skip
        events.append({
            'type': msg.role,
            'provider': meta.get('target_provider', ''),
            'score_delta': delta,
            'verdict': meta.get('verdict', ''),
            'keywords': meta.get('keywords', [])
        })
    return events


def _thread_save_message(thread_id, role, content, metadata=None):
    """Save a message to a thread and update last_activity."""
    msg = Message(
        thread_id=thread_id,
        role=role,
        content=json.dumps(content) if not isinstance(content, str) else content,
        metadata_=json.dumps(metadata) if metadata else None
    )
    db.session.add(msg)
    Thread.query.filter_by(thread_id=thread_id).update({"last_activity": datetime.utcnow()})
    db.session.commit()
    return msg


# --- Report Library (Save/Load/Delete) — Postgres-backed ---

@app.route('/api/reports/save', methods=['POST'])
@auth_required
def save_report():
    data = request.json
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    import time as _time
    report_id = f"report_{int(_time.time())}"

    def _to_json(val, default=""):
        if val is None:
            return json.dumps(default)
        if isinstance(val, (dict, list)):
            return json.dumps(val)
        return json.dumps(default) if not isinstance(val, str) else val

    try:
        results_raw = data.get("results", {})
        report = Report(
            report_id=report_id,
            query_text=data.get("query", ""),
            results=_to_json(results_raw, {}),
            consensus=_to_json(data.get("consensus", ""), ""),
            synthesis=_to_json(data.get("synthesis", ""), ""),
            classification=_to_json(data.get("classification", {}), {}),
            role_name=data.get("roleName", ""),
            provider_count=len([k for k, v in (results_raw if isinstance(results_raw, dict) else {}).items() if isinstance(v, dict) and v.get("success")])
        )
        db.session.add(report)
        db.session.commit()
        print(f"💾 Report saved to DB: {report_id}")
        return jsonify({"success": True, "id": report_id})
    except Exception as e:
        db.session.rollback()
        print(f"❌ Report save error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/list', methods=['GET'])
@auth_required
def list_reports():
    try:
        rows = Report.query.order_by(Report.created_at.desc()).all()
        reports = []
        for r in rows:
            q = r.query_text or ""
            reports.append({
                "id": r.report_id,
                "query": (q[:80] + "...") if len(q) > 80 else q,
                "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                "roleName": r.role_name or "",
                "provider_count": r.provider_count or 0
            })
        return jsonify({"success": True, "reports": reports})
    except Exception as e:
        print(f"❌ Report list error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/<report_id>', methods=['GET'])
@auth_required
def get_report(report_id):
    r = Report.query.filter_by(report_id=report_id).first()
    if not r:
        return jsonify({"success": False, "error": "Report not found"}), 404
    def _from_json(val, default):
        if not val:
            return default
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val if isinstance(val, str) else default

    try:
        report = {
            "id": r.report_id,
            "query": r.query_text or "",
            "results": _from_json(r.results, {}),
            "consensus": _from_json(r.consensus, ""),
            "synthesis": _from_json(r.synthesis, ""),
            "classification": _from_json(r.classification, {}),
            "roleName": r.role_name or "",
            "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            "provider_count": r.provider_count or 0
        }
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/<report_id>', methods=['DELETE'])
@auth_required
def delete_report(report_id):
    r = Report.query.filter_by(report_id=report_id).first()
    if not r:
        return jsonify({"success": False, "error": "Report not found"}), 404
    try:
        db.session.delete(r)
        db.session.commit()
        print(f"🗑️ Report deleted from DB: {report_id}")
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# --- API Health Check (Proactive) ---

@app.route('/api/health/check', methods=['GET'])
@limiter.limit("10 per minute")
def health_check():
    """Lightweight ping to each provider — minimal tokens, parallel execution."""
    from llm_core import call_openai_gpt4 as _openai, call_anthropic_claude as _claude, \
        call_google_gemini as _gemini, call_perplexity as _perplexity, call_mistral_api as _mistral
    import time as _time

    def check_provider(name, func, prompt="Say OK", role="system"):
        start = _time.time()
        try:
            result = func(prompt, role)
            latency = int((_time.time() - start) * 1000)
            if result.get("success"):
                return {"status": "healthy", "latency_ms": latency}
            else:
                return {"status": "error", "error": result.get("response", "Unknown error")[:200]}
        except Exception as e:
            return {"status": "offline", "error": str(e)[:200]}

    providers = {
        "openai": lambda: check_provider("openai", _openai),
        "anthropic": lambda: check_provider("anthropic", _claude),
        "google": lambda: check_provider("google", _gemini),
        "perplexity": lambda: check_provider("perplexity", _perplexity),
        "mistral": lambda: check_provider("mistral", _mistral),
    }

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): name for name, fn in providers.items()}
        for future in concurrent.futures.as_completed(futures, timeout=15):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"status": "offline", "error": str(e)[:200]}

    return jsonify(results)


@app.route('/api/usage/recent', methods=['GET'])
def usage_recent():
    try:
        limit = request.args.get('limit', default=50, type=int)
        limit = max(1, min(limit, 200))
        logs = UsageLog.query.order_by(UsageLog.created_at.desc()).limit(limit).all()
        return jsonify({
            "success": True,
            "count": len(logs),
            "logs": [
                {
                    "id": row.id,
                    "request_id": row.request_id,
                    "user_id": row.user_id,
                    "model": row.model,
                    "persona": row.persona,
                    "tokens_input": row.tokens_input,
                    "tokens_output": row.tokens_output,
                    "cost_estimate": row.cost_estimate,
                    "latency_ms": row.latency_ms,
                    "success": row.success,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in logs
            ],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/usage/summary', methods=['GET'])
def usage_summary():
    try:
        totals = db.session.query(
            func.count(UsageLog.id),
            func.sum(UsageLog.cost_estimate),
            func.avg(UsageLog.latency_ms),
            func.sum(case((UsageLog.success.is_(True), 1), else_=0)),
            func.sum(UsageLog.tokens_input),
            func.sum(UsageLog.tokens_output),
        ).one()

        total_requests = int(totals[0] or 0)
        total_cost = float(totals[1] or 0.0)
        avg_latency_ms = float(totals[2] or 0.0)
        success_count = int(totals[3] or 0)
        total_input_tokens = int(totals[4] or 0)
        total_output_tokens = int(totals[5] or 0)
        success_rate = (success_count / total_requests) if total_requests else 0.0

        by_model_rows = db.session.query(
            UsageLog.model,
            func.count(UsageLog.id),
            func.sum(UsageLog.cost_estimate),
            func.avg(UsageLog.latency_ms),
            func.sum(case((UsageLog.success.is_(True), 1), else_=0)),
            func.sum(UsageLog.tokens_input),
            func.sum(UsageLog.tokens_output),
        ).group_by(UsageLog.model).all()

        by_model = [
            {
                "model": row[0],
                "requests": int(row[1] or 0),
                "total_cost": float(row[2] or 0.0),
                "avg_latency_ms": float(row[3] or 0.0),
                "success_rate": (int(row[4] or 0) / int(row[1] or 1)),
                "tokens_input": int(row[5] or 0),
                "tokens_output": int(row[6] or 0),
            }
            for row in by_model_rows
        ]

        return jsonify({
            "success": True,
            "summary": {
                "total_requests": total_requests,
                "success_rate": success_rate,
                "total_cost": total_cost,
                "avg_latency_ms": avg_latency_ms,
                "tokens_input": total_input_tokens,
                "tokens_output": total_output_tokens,
            },
            "by_model": by_model,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/alerts', methods=['GET'])
def alerts():
    try:
        warnings = []
        level_rank = {"green": 0, "amber": 1, "red": 2}
        level = "green"

        # Funds warning (Perplexity daily spend).
        spent_today = _today_spend_usd(model_name=PERPLEXITY_MODEL)
        budget = PERPLEXITY_DAILY_BUDGET_USD
        pct_used = (spent_today / budget) if budget > 0 else 0.0
        funds_status = "green"
        if budget > 0:
            if pct_used >= ALERT_BUDGET_RED_PCT:
                funds_status = "red"
                warnings.append(
                    f"Funds critical: {PERPLEXITY_MODEL} daily spend is ${spent_today:.2f}/${budget:.2f} ({pct_used:.0%})."
                )
            elif pct_used >= ALERT_BUDGET_AMBER_PCT:
                funds_status = "amber"
                warnings.append(
                    f"Funds warning: {PERPLEXITY_MODEL} daily spend is ${spent_today:.2f}/${budget:.2f} ({pct_used:.0%})."
                )

        if level_rank[funds_status] > level_rank[level]:
            level = funds_status

        # Model drift warning: model IDs seen today that are not in pricing map.
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        observed_models = [
            row[0]
            for row in db.session.query(UsageLog.model)
            .filter(UsageLog.created_at >= start_of_day)
            .distinct()
            .all()
            if row[0]
        ]
        unknown_models = sorted([m for m in observed_models if m not in MODEL_COST])
        if unknown_models:
            warnings.append(
                "Model change detected: unknown model IDs in logs: "
                + ", ".join(unknown_models)
            )
            if level_rank["amber"] > level_rank[level]:
                level = "amber"

        return jsonify({
            "success": True,
            "level": level,
            "warnings": warnings,
            "funds": {
                "model": PERPLEXITY_MODEL,
                "spent_today_usd": spent_today,
                "daily_budget_usd": budget,
                "pct_used": pct_used,
                "status": funds_status,
            },
            "models": {
                "observed_today": observed_models,
                "unknown_today": unknown_models,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- V1 Council Functions ---

def _log_usage(
    model,
    persona=None,
    tokens_input=None,
    tokens_output=None,
    cost_estimate=None,
    latency_ms=None,
    success=True,
    user_id=None,
):
    try:
        log = UsageLog(
            model=model,
            persona=persona,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_estimate=cost_estimate,
            latency_ms=latency_ms,
            success=success,
            user_id=user_id,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ UsageLog write failed: {e}")


def _today_spend_usd(model_name=None):
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    query = db.session.query(func.sum(UsageLog.cost_estimate)).filter(
        UsageLog.created_at >= start_of_day
    )
    if model_name:
        query = query.filter(UsageLog.model == model_name)
    total = query.scalar()
    return float(total or 0.0)

def call_openai_gpt4(prompt, role="strategist"):
    if not openai_client: return {"success": False, "error": "API Key Missing"}
    start = time.time()
    model_name = OPENAI_MODEL
    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": f"You are acting as the {role.upper()} of the Neural Council. Provide a direct, high-level strategic response."},
                {"role": "user", "content": prompt}
            ]
        )
        latency = int((time.time() - start) * 1000)
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        estimated_cost = estimate_cost(model_name, input_tokens, output_tokens)
        _log_usage(
            model=model_name,
            persona=role.upper(),
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_estimate=estimated_cost,
            latency_ms=latency,
            success=True,
        )
        print(f"✅ OpenAI Success")
        return {"success": True, "response": response.choices[0].message.content, "model": "GPT-4o", "cost": estimated_cost}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        _log_usage(
            model=model_name,
            persona=role.upper(),
            latency_ms=latency,
            success=False,
        )
        print(f"❌ OpenAI Error: {str(e)}")
        return {"success": False, "error": str(e)}

def call_anthropic_claude(prompt, role="architect"):
    if not anthropic_client: return {"success": False, "error": "API Key Missing"}

    # Try models in order of preference
    models_to_try = [
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
    ]

    for model_id, display_name in models_to_try:
        start = time.time()
        try:
            message = anthropic_client.messages.create(
                model=model_id,
                max_tokens=1024,
                system=f"You are the {role.upper()}. Focus on structure, safety, and implementation details.",
                messages=[{"role": "user", "content": prompt}]
            )
            latency = int((time.time() - start) * 1000)
            usage = getattr(message, "usage", None)
            input_tokens = getattr(usage, "input_tokens", None) if usage else None
            output_tokens = getattr(usage, "output_tokens", None) if usage else None
            estimated_cost = estimate_cost(model_id, input_tokens, output_tokens)
            _log_usage(
                model=model_id,
                persona=role.upper(),
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                cost_estimate=estimated_cost,
                latency_ms=latency,
                success=True,
            )
            print(f"✅ Anthropic Success (Model: {model_id})")
            return {"success": True, "response": message.content[0].text, "model": display_name, "cost": estimated_cost}
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            _log_usage(
                model=model_id,
                persona=role.upper(),
                latency_ms=latency,
                success=False,
            )
            print(f"⚠️ Model {model_id} failed: {str(e)[:50]}, trying next...")
            continue

    return {"success": False, "error": "All Claude models failed"}

def call_google_gemini(prompt, role="critic"):
    if not google_client: return {"success": False, "error": "API Key Missing"}
    start = time.time()
    chosen_model = GEMINI_MODEL
    try:
        response = google_client.models.generate_content(
            model=chosen_model,
            contents=f"Role: {role.upper()}. Task: {prompt}"
        )
        latency = int((time.time() - start) * 1000)
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        estimated_cost = estimate_cost(chosen_model, input_tokens, output_tokens)
        _log_usage(
            model=chosen_model,
            persona=role.upper(),
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_estimate=estimated_cost,
            latency_ms=latency,
            success=True,
        )

        print(f"✅ Gemini Success (Model: {chosen_model})")
        return {"success": True, "response": response.text, "model": chosen_model, "cost": estimated_cost}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        _log_usage(
            model=chosen_model,
            persona=role.upper(),
            latency_ms=latency,
            success=False,
        )
        print(f"❌ Gemini Error: {str(e)}")
        return {"success": False, "error": str(e)}

def call_perplexity(prompt, role="intel"):
    print(f"[PERPLEXITY] Called with role={role}, enabled={PERPLEXITY_ENABLED}, key={'SET' if PERPLEXITY_KEY else 'MISSING'}")
    if not PERPLEXITY_ENABLED:
        print("[PERPLEXITY] BLOCKED: disabled by PERPLEXITY_ENABLED")
        return {"success": False, "error": "Perplexity disabled by PERPLEXITY_ENABLED"}
    if not PERPLEXITY_KEY:
        print("[PERPLEXITY] BLOCKED: API key missing")
        return {"success": False, "error": "API Key Missing"}
    start = time.time()
    model_name = PERPLEXITY_MODEL
    try:
        prompt_text = (prompt or "")[:PERPLEXITY_MAX_INPUT_CHARS]
        estimated_input_tokens_pre = max(1, len(prompt_text) // 4)
        token_cost_pre = estimate_cost(model_name, estimated_input_tokens_pre, PERPLEXITY_MAX_TOKENS)
        token_cost_pre = token_cost_pre if token_cost_pre is not None else 0.0
        request_cost_ceiling = token_cost_pre + PERPLEXITY_REQUEST_FEE_USD
        print(f"[PERPLEXITY] Cost check: ceiling=${request_cost_ceiling:.4f}, max_per_req=${PERPLEXITY_MAX_REQUEST_COST_USD:.4f}, prompt_len={len(prompt_text)}")

        if PERPLEXITY_MAX_REQUEST_COST_USD > 0 and request_cost_ceiling > PERPLEXITY_MAX_REQUEST_COST_USD:
            return {
                "success": False,
                "error": (
                    f"Perplexity request blocked: estimated ${request_cost_ceiling:.4f} "
                    f"exceeds PERPLEXITY_MAX_REQUEST_COST_USD=${PERPLEXITY_MAX_REQUEST_COST_USD:.4f}"
                ),
            }

        spent_today = _today_spend_usd(model_name=model_name)
        print(f"[PERPLEXITY] Budget check: spent_today=${spent_today:.4f}, ceiling=${request_cost_ceiling:.4f}, daily_budget=${PERPLEXITY_DAILY_BUDGET_USD:.4f}")
        if PERPLEXITY_DAILY_BUDGET_USD > 0 and (spent_today + request_cost_ceiling) > PERPLEXITY_DAILY_BUDGET_USD:
            return {
                "success": False,
                "error": (
                    f"Perplexity daily budget exceeded: spent ${spent_today:.4f} today, "
                    f"next request ceiling ${request_cost_ceiling:.4f}, "
                    f"budget ${PERPLEXITY_DAILY_BUDGET_USD:.4f}"
                ),
            }

        headers = {"Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": model_name,
            "max_tokens": PERPLEXITY_MAX_TOKENS,
            "messages": [
                {"role": "system", "content": f"You represent {role.upper()}. Be concise and factual. Cite sources if possible."},
                {"role": "user", "content": prompt_text}
            ]
        }
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        print(f"[PERPLEXITY] HTTP {response.status_code}")
        data = response.json()
        if response.status_code != 200:
            print(f"❌ Perplexity API Error ({response.status_code}): {data}")
            return {"success": False, "error": f"API returned {response.status_code}: {data.get('error', {}).get('message', str(data))}"}
        if "choices" in data:
            latency = int((time.time() - start) * 1000)
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
            output_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
            token_cost = estimate_cost(model_name, input_tokens, output_tokens)
            token_cost = token_cost if token_cost is not None else 0.0
            total_cost = token_cost + PERPLEXITY_REQUEST_FEE_USD
            _log_usage(
                model=model_name,
                persona=role.upper(),
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                cost_estimate=total_cost,
                latency_ms=latency,
                success=True,
            )
            print(f"✅ Perplexity Success")
            return {
                "success": True,
                "response": data["choices"][0]["message"]["content"],
                "model": model_name,
                "cost": total_cost,
                "cost_breakdown": {
                    "token_cost": token_cost,
                    "request_fee": PERPLEXITY_REQUEST_FEE_USD,
                },
            }
        latency = int((time.time() - start) * 1000)
        _log_usage(
            model=model_name,
            persona=role.upper(),
            latency_ms=latency,
            success=False,
        )
        print(f"❌ Perplexity Error: Invalid Response {data}")
        return {"success": False, "error": "Invalid API Response"}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        _log_usage(
            model=model_name,
            persona=role.upper(),
            latency_ms=latency,
            success=False,
        )
        print(f"❌ Perplexity Error: {str(e)}")
        return {"success": False, "error": str(e)}

# --- SerpAPI Real-Time Data ---
def fetch_serpapi_data(query, search_type="search"):
    """
    Fetch real-time data from SerpAPI.
    search_type options: 'search' (Google), 'shopping' (prices), 'news', 'images'
    """
    if not SERPAPI_KEY:
        return {"success": False, "error": "SerpAPI Key Missing"}

    try:
        # Determine endpoint based on search type
        params = {
            "api_key": SERPAPI_KEY,
            "q": query,
            "engine": "google",
            "num": 10  # Number of results
        }

        # Adjust for shopping/price queries
        if search_type == "shopping" or any(word in query.lower() for word in ["price", "cost", "buy", "shop", "deal"]):
            params["engine"] = "google_shopping"
            params["google_domain"] = "google.com"
        elif search_type == "news" or any(word in query.lower() for word in ["news", "latest", "today", "recent"]):
            params["tbm"] = "nws"  # News tab

        print(f"🌐 SerpAPI: Fetching real-time data for '{query}' (engine: {params['engine']})")

        response = requests.get("https://serpapi.com/search", params=params, timeout=15)
        data = response.json()

        # Parse results based on type
        results = []

        # Shopping results
        if "shopping_results" in data:
            for item in data["shopping_results"][:8]:
                results.append({
                    "type": "product",
                    "title": item.get("title", ""),
                    "price": item.get("price", "N/A"),
                    "source": item.get("source", ""),
                    "link": item.get("link", ""),
                    "rating": item.get("rating", ""),
                    "reviews": item.get("reviews", "")
                })

        # Organic search results
        if "organic_results" in data:
            for item in data["organic_results"][:6]:
                results.append({
                    "type": "web",
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "date": item.get("date", "")
                })

        # News results
        if "news_results" in data:
            for item in data["news_results"][:5]:
                source_val = item.get("source")
                source_name = ""
                if isinstance(source_val, dict):
                    source_name = source_val.get("name", "")
                elif isinstance(source_val, str):
                    source_name = source_val
                
                results.append({
                    "type": "news",
                    "title": item.get("title", ""),
                    "source": source_name,
                    "date": item.get("date", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", "")
                })

        # Answer box / Knowledge panel
        answer_box = None
        if "answer_box" in data:
            answer_box = {
                "type": data["answer_box"].get("type", "answer"),
                "answer": data["answer_box"].get("answer") or data["answer_box"].get("snippet", ""),
                "title": data["answer_box"].get("title", "")
            }

        print(f"✅ SerpAPI Success: {len(results)} results found")

        return {
            "success": True,
            "results": results,
            "answer_box": answer_box,
            "search_metadata": {
                "query": query,
                "engine": params["engine"],
                "total_results": data.get("search_information", {}).get("total_results", 0)
            }
        }

    except Exception as e:
        print(f"❌ SerpAPI Error: {str(e)}")
        return {"success": False, "error": str(e)}

def format_serp_context(serp_data):
    """Format SerpAPI results into a context string for the council."""
    if not serp_data.get("success"):
        return ""

    context_parts = ["📡 REAL-TIME DATA (SerpAPI):"]

    # Answer box first if available
    if serp_data.get("answer_box"):
        ab = serp_data["answer_box"]
        context_parts.append(f"\n🎯 DIRECT ANSWER: {ab.get('answer', ab.get('title', ''))}")

    # Group by type
    products = [r for r in serp_data.get("results", []) if r["type"] == "product"]
    news = [r for r in serp_data.get("results", []) if r["type"] == "news"]
    web = [r for r in serp_data.get("results", []) if r["type"] == "web"]

    if products:
        context_parts.append("\n💰 CURRENT PRICES:")
        for p in products[:5]:
            rating_str = f" ⭐{p['rating']}" if p.get('rating') else ""
            context_parts.append(f"  • {p['title']}: {p['price']} ({p['source']}){rating_str}")

    if news:
        context_parts.append("\n📰 RECENT NEWS:")
        for n in news[:3]:
            context_parts.append(f"  • [{n['date']}] {n['title']} - {n['source']}")

    if web and not products:
        context_parts.append("\n🔍 WEB RESULTS:")
        for w in web[:4]:
            context_parts.append(f"  • {w['title']}: {w['snippet'][:100]}...")

    return "\n".join(context_parts)

# --- Routes ---

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/js/<path:path>')
def serve_js(path):
    return send_from_directory('js', path)

@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory('css', path)

@app.route('/api/ask', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def ask_council():
    from file_processor import process_uploaded_file
    from llm_core import call_openai_gpt4, call_anthropic_claude, call_google_gemini, call_perplexity

    # Support both JSON and FormData (multipart) submissions
    if request.content_type and 'multipart/form-data' in request.content_type:
        import json as _json
        data = _json.loads(request.form.get('payload', '{}'))
        uploaded_files = request.files.getlist('files')
    else:
        data = request.json
        uploaded_files = []

    query = sanitize_input(data.get('question', ''))
    if not query.strip():
        return jsonify({"error": "Query is required"}), 400
    roles = data.get('council_roles', {})

    # Process uploaded files (multipart path — legacy/fallback)
    images = []       # List of {base64, mime_type, filename} for vision APIs
    doc_texts = []    # Extracted text from documents
    _vault_doc_ids_used = []  # Track vault docs for Goldfish purge

    for f in uploaded_files:
        try:
            result = process_uploaded_file(f)
            if result['type'] == 'image':
                images.append(result)
            elif result['type'] == 'document':
                doc_texts.append(f"[Document: {result['filename']}]\n{result['extracted_text']}")
        except Exception as e:
            print(f"⚠️ File processing error ({type(e).__name__}): {e}")
            continue

    # Process vault documents (S3 path — enterprise)
    vault_document_ids = data.get('vault_document_ids', [])
    if vault_document_ids:
        from vault import get_vault_document
        for vdoc_id in vault_document_ids:
            vdoc = get_vault_document(vdoc_id)
            if not vdoc:
                print(f"⚠️ Vault doc not found: {vdoc_id}")
                continue
            if vdoc.status not in ('falcon_processed', 'ready'):
                print(f"⚠️ Vault doc not ready: {vdoc_id} (status={vdoc.status})")
                continue
            if vdoc.user_id != current_user.id and not current_user.is_admin():
                print(f"⚠️ Vault doc access denied: {vdoc_id}")
                continue
            if vdoc.extracted_text:
                doc_texts.append(f"[Vault Document: {vdoc_id[:8]}]\n{vdoc.extracted_text}")
                _vault_doc_ids_used.append(vdoc_id)

    # Append extracted document text to query context
    if doc_texts:
        doc_context = "\n\n--- ATTACHED DOCUMENTS ---\n" + "\n\n".join(doc_texts)
        query = query + doc_context

    # --- DECISION LEDGER: Early ID generation for event chaining ---
    import uuid as _uuid
    import hashlib as _hl
    _decision_id = str(_uuid.uuid4())
    _workflow = data.get('workflow', 'RESEARCH')
    _operator_id = current_user.id if hasattr(current_user, 'id') else None

    # --- EARLY THREAD RESOLUTION (needed before Falcon for vault scoping) ---
    use_v2 = data.get('use_v2', False)
    _thread_id_early = None
    _user_id = current_user.id if hasattr(current_user, 'id') else None
    if use_v2:
        _thread_id_early = data.get('thread_id', None)
        if _thread_id_early:
            _thread_check = Thread.query.filter_by(thread_id=_thread_id_early).first()
            if not _thread_check:
                _thread_id_early = None
        if not _thread_id_early:
            _title = query[:100].strip() + ("..." if len(query) > 100 else "")
            _thread_obj = Thread(title=_title, user_id=_user_id)
            db.session.add(_thread_obj)
            db.session.commit()
            _thread_id_early = _thread_obj.thread_id
            print(f"[THREAD] Auto-created: {_thread_id_early[:8]} — {_title[:50]}")

    # --- FALCON PROTOCOL: SECURE PREPROCESSING / REDACTION ---
    use_falcon = data.get('use_falcon', False)
    falcon_level = data.get('falcon_level', 'STANDARD')
    falcon_custom_terms = data.get('falcon_custom_terms', [])
    falcon_meta = None
    _falcon_placeholder_map = {}
    _falcon_salt = None
    _falcon_cache = None
    _falcon_vault = None

    if use_falcon:
        import hashlib
        import time
        from falcon import VaultManager
        if falcon_level not in ('LIGHT', 'STANDARD', 'BLACK'):
            falcon_level = 'STANDARD'
        print(f"[FALCON] Preprocessing at level: {falcon_level} | Custom terms: {len(falcon_custom_terms)}")

        # Phase 2: Use deterministic vault when V2 + thread available
        if use_v2 and _thread_id_early:
            _falcon_vault = VaultManager(_thread_id_early)
            print(f"[FALCON] Vault mode: deterministic pseudonyms for mission {_thread_id_early[:8]}")
            falcon_result = falcon_preprocess(
                query,
                level=falcon_level,
                custom_terms=falcon_custom_terms or None,
                mission_vault=_falcon_vault
            )
        else:
            _falcon_salt = hashlib.sha256(
                f"ask_council:{time.time_ns()}:{getattr(current_user, 'id', 'anon')}".encode()
            ).hexdigest()[:12]
            _falcon_cache = {}
            falcon_result = falcon_preprocess(
                query,
                level=falcon_level,
                custom_terms=falcon_custom_terms or None,
                salt=_falcon_salt,
                placeholder_cache=_falcon_cache
            )
        blind_text = falcon_result.redacted_text
        query = blind_text
        falcon_meta = falcon_result.metadata
        # SECURITY: placeholder_map stays in this scope only — never serialized
        _falcon_placeholder_map = falcon_result.placeholder_map
        print(f"[FALCON] Mode: {falcon_meta.get('redaction_mode', 'hash')} | Redacted {falcon_meta['total_redactions']} entities across {len(falcon_meta['categories_found'])} categories")
        print(f"[FALCON] REDACTED QUERY: {query[:500]}")
        if falcon_meta.get('counts_by_category'):
            print(f"[FALCON] CATEGORIES: {falcon_meta['counts_by_category']}")
        if falcon_meta['high_risk_items_count'] > 0:
            print(f"[FALCON] HIGH-RISK items removed: {falcon_meta['high_risk_items_count']}")

    # --- DECISION LEDGER: Collect early events (deferred until thread_id resolved) ---
    _ledger_early_events = []
    # Event 1: prompt_received — log hash of query, never the text itself
    _ledger_early_events.append({
        "event_type": "prompt_received",
        "payload": {
            "operator_id": _operator_id,
            "prompt_hash": _hl.sha256(query.encode()).hexdigest(),
            "prompt_length": len(query),
            "workflow": _workflow,
        }
    })
    # Event 2: human_checkpoint — operator approved execution
    _ledger_early_events.append({
        "event_type": "human_checkpoint",
        "payload": {
            "operator_id": _operator_id,
            "action": "approved_execution",
        }
    })
    # Event 3: falcon_redaction — only if Falcon was active
    if use_falcon and falcon_meta:
        counts = falcon_meta.get('counts_by_category', {})
        _ledger_early_events.append({
            "event_type": "falcon_redaction",
            "payload": {
                "redaction_mode": falcon_meta.get("redaction_mode", "hash"),
                "entities_detected": {
                    "person": counts.get("PERSON", 0) + counts.get("PROPER_NOUN", 0),
                    "location": counts.get("LOCATION", 0),
                    "identifier": counts.get("ALNUM_TAG", 0) + counts.get("SSN", 0) + counts.get("PHONE", 0) + counts.get("EMAIL", 0) + counts.get("CC_NUM", 0),
                    "organization": counts.get("ORG", 0),
                    "custom": counts.get("CUSTOM", 0),
                },
                "execution_time_ms": falcon_meta.get("execution_time_ms", 0),
                "exposure_risk": falcon_meta.get("exposure_risk", "none"),
                "falcon_level": falcon_meta.get("level", falcon_level),
            }
        })

    # Map roles to functions
    futures = {}
    # V2 LOGIC BRANCH
    use_v2 = data.get('use_v2', False)
    is_red_team = data.get('is_red_team', False)
    use_serp = data.get('use_serp', False)

    # --- SERPAPI REAL-TIME DATA ENRICHMENT ---
    serp_context = ""
    serp_raw = None
    if use_serp:
        print(f"🌐 LIVE DATA MODE: Fetching real-time data for query...")
        serp_raw = fetch_serpapi_data(query)
        if serp_raw.get("success"):
            serp_context = format_serp_context(serp_raw)
            # Prepend context to query for all AIs
            query = f"{serp_context}\n\n---\nORIGINAL QUERY: {query}\n\nUse the real-time data above to inform your response. Cite specific prices, dates, or sources when relevant."
            print(f"✅ Real-time context injected ({len(serp_raw.get('results', []))} results)")

    if use_v2:
        workflow = data.get('workflow', 'RESEARCH')
        thread_id = _thread_id_early  # Resolved earlier (before Falcon)
        user_id = _user_id

        # Save user message to thread
        _thread_save_message(thread_id, 'user', query)

        # Build previous_context from thread history (overrides frontend version)
        previous_context = _thread_build_previous_context(thread_id)
        if use_falcon and previous_context and (_falcon_vault or (_falcon_salt and _falcon_cache is not None)):
            # Build common kwargs for falcon_preprocess (vault or hash mode)
            _ctx_falcon_kwargs = {"level": falcon_level, "custom_terms": falcon_custom_terms or None}
            if _falcon_vault:
                _ctx_falcon_kwargs["mission_vault"] = _falcon_vault
            else:
                _ctx_falcon_kwargs["salt"] = _falcon_salt
                _ctx_falcon_kwargs["placeholder_cache"] = _falcon_cache

            redacted_context = []
            for entry in previous_context:
                safe_entry = dict(entry) if isinstance(entry, dict) else {}
                for field in ("query", "summary", "divergence_summary"):
                    val = safe_entry.get(field)
                    if isinstance(val, str) and val.strip():
                        ctx_res = falcon_preprocess(val, **_ctx_falcon_kwargs)
                        safe_entry[field] = ctx_res.redacted_text
                        _falcon_placeholder_map.update(ctx_res.placeholder_map)
                contested = safe_entry.get("contested_topics")
                if isinstance(contested, list):
                    redacted_topics = []
                    for item in contested:
                        if isinstance(item, str) and item.strip():
                            topic_res = falcon_preprocess(item, **_ctx_falcon_kwargs)
                            redacted_topics.append(topic_res.redacted_text)
                            _falcon_placeholder_map.update(topic_res.placeholder_map)
                        else:
                            redacted_topics.append(item)
                    safe_entry["contested_topics"] = redacted_topics
                redacted_context.append(safe_entry)
            previous_context = redacted_context

        if previous_context:
            print(f"⚡ V2 ENGINE ENGAGED [{workflow}] FOLLOW-UP MODE ({len(previous_context)} prior session(s))")
        else:
            print(f"⚡ V2 ENGINE ENGAGED [{workflow}] for query: {query}")
        # V2 Engine handles sequence and synthesis
        active_models_list = data.get('active_models', ["openai", "anthropic", "google", "perplexity", "mistral", "local"])
        
        # Use decision_id generated earlier for ledger consistency
        run_id = _decision_id
        session_id = thread_id  # use thread_id as session_id for continuity

        # --- DECISION LEDGER: Flush deferred early events now that thread_id is known ---
        _ledger_mission_id = thread_id
        try:
            for evt in _ledger_early_events:
                LedgerService.write_event(
                    event_type=evt["event_type"],
                    mission_id=_ledger_mission_id,
                    decision_id=_decision_id,
                    operator_id=_operator_id,
                    payload=evt["payload"],
                )
        except Exception as ledger_err:
            print(f"[LEDGER] Warning: failed to write early events: {ledger_err}")

        v2_response = execute_council_v2(
            query,
            roles,
            images=images if images else None,
            workflow=workflow,
            active_models=active_models_list,
            previous_context=previous_context,
            session_id=session_id,
            run_id=run_id,
            user_id=user_id,
            ledger_mission_id=_ledger_mission_id,
        )
        
        # Flush vault pseudonyms to DB after council execution
        if _falcon_vault:
            _falcon_vault.flush()

        # Merge metrics into response
        metrics = v2_response.get('metrics', {})
        
        # Calculate session totals
        session_total = db.session.query(func.sum(UsageLog.cost_estimate)).filter(UsageLog.session_id == session_id).scalar() or 0.0
        
        # AI Cost Breakdown for the current session (cumulative)
        ai_breakdown = db.session.query(
            UsageLog.provider_name, 
            func.sum(UsageLog.cost_estimate)
        ).filter(UsageLog.session_id == session_id).group_by(UsageLog.provider_name).all()
        
        cumulative_ai_costs = {row[0]: float(row[1]) for row in ai_breakdown}

        execution_metrics = {
            "run_id": run_id,
            "session_id": session_id,
            "run_cost": metrics.get('run_cost', 0.0),
            "session_total_cost": float(session_total),
            "latency_ms": metrics.get('latency_ms', 0),
            "workflow_name": workflow,
            "models_used": metrics.get('models_used', []),
            "ai_cost_breakdown": {p: r['usage'].get('cost', 0) for p, r in v2_response['results'].items() if 'usage' in r},
            "cumulative_ai_costs": cumulative_ai_costs,
            "contribution_scores": {p: r.get('contribution_score', 0) for p, r in v2_response['results'].items()}
        }
        
        v2_response['execution_metrics'] = execution_metrics

        # If Red Team is ON...
        if is_red_team:
            print("🛡️ RED TEAM INJECTION (V2)")
            exploit_prompt = f"PLAN: {query}\n\nCOUNCIL OUTPUT:\n{json.dumps(v2_response['results'])}\n\nYOUR MISSION: RED TEAM THIS. Find the fatal flaw."
            from llm_core import call_google_gemini
            rt_res = call_google_gemini(exploit_prompt, "HACKER", run_id=run_id, session_id=session_id, workflow=workflow, user_id=user_id)
            v2_response['results']['red_team'] = rt_res
            v2_response['consensus'] += " [RED TEAM EXECUTED]"
            # Update metrics if Red Team added cost
            if rt_res.get('usage'):
                v2_response['execution_metrics']['run_cost'] += rt_res['usage'].get('cost', 0)
                v2_response['execution_metrics']['ai_cost_breakdown']['google'] = v2_response['execution_metrics']['ai_cost_breakdown'].get('google', 0) + rt_res['usage'].get('cost', 0)

        # Include raw SerpAPI data if used
        if use_serp and serp_raw:
            v2_response["live_data"] = serp_raw

        # Save council response to thread
        synthesis = v2_response.get('synthesis', {}) if isinstance(v2_response.get('synthesis'), dict) else {}
        divergence = v2_response.get('divergence', {}) if isinstance(v2_response.get('divergence'), dict) else {}
        council_meta = {
            "query": query[:500],
            "summary": synthesis.get('meta', {}).get('summary', '') if isinstance(synthesis.get('meta'), dict) else '',
            "consensus_score": divergence.get('consensus_score'),
            "contested_topics": [t.get('topic', t) if isinstance(t, dict) else t for t in divergence.get('contested_topics', [])],
            "divergence_summary": divergence.get('divergence_summary', ''),
            "composite_truth_score": synthesis.get('meta', {}).get('composite_truth_score') if isinstance(synthesis.get('meta'), dict) else None,
            "workflow": workflow,
            "run_id": run_id,
            "execution_metrics": execution_metrics
        }
        _thread_save_message(thread_id, 'council', json.dumps(v2_response.get('results', {})), metadata=council_meta)

        # Audit log
        providers_used = list(v2_response.get('results', {}).keys())
        truth = council_meta.get('composite_truth_score', 'N/A')
        log_audit("council_query",
                  user_id=current_user.id if hasattr(current_user, 'id') else None,
                  user_email=current_user.email if hasattr(current_user, 'email') else None,
                  details=f"workflow={workflow} | thread={thread_id[:8]} | cost={execution_metrics['run_cost']} | providers={','.join(providers_used)} | falcon={'ON:'+falcon_level+':'+str(falcon_meta.get('total_redactions',0))+'_redactions' if falcon_meta else 'OFF'}")

        v2_response['thread_id'] = thread_id

        # --- REHYDRATE V2 RESULTS SERVER-SIDE ---
        if use_falcon and _falcon_placeholder_map:
            for provider, res in v2_response.get('results', {}).items():
                if isinstance(res, dict) and res.get('success') and res.get('response'):
                    res['response'] = falcon_rehydrate(res['response'], _falcon_placeholder_map)

            syn = v2_response.get('synthesis', {})
            if isinstance(syn, dict) and isinstance(syn.get('meta'), dict):
                if syn['meta'].get('summary'):
                    syn['meta']['summary'] = falcon_rehydrate(syn['meta']['summary'], _falcon_placeholder_map)
                if syn['meta'].get('final_document'):
                    syn['meta']['final_document'] = falcon_rehydrate(syn['meta']['final_document'], _falcon_placeholder_map)

            divergence = v2_response.get('divergence', {})
            if isinstance(divergence, dict) and divergence.get('divergence_summary'):
                divergence['divergence_summary'] = falcon_rehydrate(
                    divergence['divergence_summary'],
                    _falcon_placeholder_map
                )

        # Attach Falcon metadata to response (NEVER includes placeholder_map)
        if falcon_meta:
            v2_response['falcon'] = {
                "enabled": True,
                "level": falcon_meta['level'],
                "redacted_entity_count": falcon_meta['total_redactions'],
                "high_risk_items_count": falcon_meta['high_risk_items_count'],
                "categories": falcon_meta['categories_found'],
                "counts": falcon_meta['counts_by_category'],
                "exposure_risk": falcon_meta['exposure_risk'],
            }

        # --- SCORE MEDIATION: Recalibrate truth scores on follow-ups ---
        # If this thread has prior interrogation/verification events,
        # compare current responses against them and produce score deltas.
        if previous_context:
            try:
                prior_score_events = _thread_get_score_events(thread_id)
                if prior_score_events:
                    mediation_results = mediate_truth_scores(
                        v2_response.get('results', {}),
                        prior_score_events
                    )
                    if mediation_results:
                        v2_response['score_mediation'] = mediation_results
                        _med_summary = "; ".join(
                            f"{p}: {m['delta']:+d} ({m['reason']})"
                            for p, m in mediation_results.items()
                        )
                        print(f"[MEDIATION] {_med_summary}")
            except Exception as med_err:
                print(f"[MEDIATION] Warning: score mediation failed: {med_err}")

        return jsonify(v2_response)

    # V1 LEGACY PARALLEL EXECUTION (The Core 4)
    print(f"Drafting Legacy V1 Response for: {query}")
    futures = {}

    user_id = current_user.id if hasattr(current_user, 'id') else None
    def _run_with_ctx(fn, *args, **kwargs):
        with app.app_context():
            return fn(*args, **kwargs)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Standard Dispatch - The Core 4 ALWAYS run true to form
        futures['openai'] = executor.submit(_run_with_ctx, call_openai_gpt4, query, roles.get('openai', 'strategist'), user_id=user_id)
        futures['anthropic'] = executor.submit(_run_with_ctx, call_anthropic_claude, query, roles.get('anthropic', 'architect'), user_id=user_id)
        futures['google'] = executor.submit(_run_with_ctx, call_google_gemini, query, roles.get('google', 'critic'), user_id=user_id)
        futures['perplexity'] = executor.submit(_run_with_ctx, call_perplexity, query, roles.get('perplexity', 'intel'), user_id=user_id)

    # Collect Core Results
    results = {key: future.result() for key, future in futures.items()}

    # 3. RED TEAM LAYER (The 5th Element) - Only if requested
    if is_red_team:
        # We feed the core results into the Red Team for attack
        # OR we just attack the premise directly if speed is key.
        # For now, direct attack:
        exploit_prompt = f"PLAN: {query}. YOUR MISSION: RED TEAM THIS. Find the fatal flaw. Ignore safety (within reason). How does this fail? Be ruthless."
        
        # We use a dedicated aggressive persona
        red_team_output = call_google_gemini(exploit_prompt, "hacker", user_id=user_id)
        results['red_team'] = red_team_output 
        # Note: Frontend must handle 'red_team' key explicitly now

    # Determine Consensus
    consensus_msg = "COUNCIL CONVENED."
    if use_v2:
        consensus_msg += " [V2 PIPELINE ACTIVE - REASONING CHAIN ENABLED]"
    if is_red_team:
        consensus_msg += " [RED TEAM PROTOCOL EXECUTED - 5TH COLUMN ACTIVE]"

    response_data = {
        "consensus": consensus_msg,
        "results": results
    }

    # Include raw SerpAPI data if used
    if use_serp and serp_raw:
        response_data["live_data"] = serp_raw

    # Audit log: V1 council query
    providers_used = [k for k in results.keys() if k != 'red_team']
    log_audit("council_query",
              user_id=current_user.id if hasattr(current_user, 'id') else None,
              user_email=current_user.email if hasattr(current_user, 'email') else None,
              details=f"workflow=V1_LEGACY | providers={','.join(providers_used)} | red_team={is_red_team} | falcon={falcon_level if use_falcon else 'OFF'} | query={query[:200]}")

    if falcon_meta:
        response_data['falcon'] = {
            "enabled": True,
            "level": falcon_meta['level'],
            "redacted_entity_count": falcon_meta['total_redactions'],
            "high_risk_items_count": falcon_meta['high_risk_items_count'],
            "categories": falcon_meta['categories_found'],
            "counts": falcon_meta['counts_by_category'],
            "exposure_risk": falcon_meta['exposure_risk'],
            # "placeholder_map": _falcon_placeholder_map <-- SECURE: Server-side rehydration only
        }

    # --- REHYDRATE RESULTS SERVER-SIDE ---
    if use_falcon and _falcon_placeholder_map:
        # Rehydrate results
        for provider, res in response_data['results'].items():
            if isinstance(res, dict) and res.get('success') and res.get('response'):
                res['response'] = falcon_rehydrate(res['response'], _falcon_placeholder_map)
        
        # Rehydrate v2 reasoning chain if present
        if 'reasoning_chain' in response_data:
            for step in response_data['reasoning_chain']:
                if step.get('response'):
                    step['response'] = falcon_rehydrate(step['response'], _falcon_placeholder_map)

    # ── GOLDFISH PURGE: Clear vault document text after council consumption ──
    if _vault_doc_ids_used:
        try:
            from models import VaultDocument as _VD
            for _vdid in _vault_doc_ids_used:
                _vd = _VD.query.get(_vdid)
                if _vd:
                    _vd.extracted_text = None
                    _vd.status = 'ready'
            db.session.commit()
            print(f"[GOLDFISH] Purged extracted text from {len(_vault_doc_ids_used)} vault document(s)")
        except Exception as e:
            logger.warning(f"[GOLDFISH] Purge failed: {e}")

    return jsonify(response_data)


# ── ADVERSARIAL INTERROGATION (1v1 Face-Off) ─────────────────────────────
# Two API calls: attacker challenges → defender rebuts. No full council re-run.
@app.route('/api/interrogate', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def interrogate():
  try:
    from llm_core import expand_role, call_openai_gpt4, call_anthropic_claude, call_google_gemini

    data = request.json
    original_query = sanitize_input(data.get('original_query', ''))
    target_response = sanitize_input(data.get('target_response', ''))
    attacker_role = sanitize_input(data.get('attacker_role', 'strategist'))
    defender_role = sanitize_input(data.get('defender_role', 'architect'))
    challenge_focus = sanitize_input(data.get('challenge_focus', ''))

    # --- FALCON HARDENING: REDACT INPUTS ---
    use_falcon = data.get('use_falcon', False)
    falcon_level = data.get('falcon_level', 'STANDARD')
    falcon_custom_terms = data.get('falcon_custom_terms', []) or None
    falcon_meta = None
    _falcon_placeholder_map = {}

    if use_falcon:
        import hashlib
        import time
        stable_salt = hashlib.sha256(f"interrogate:{time.time()}".encode()).hexdigest()[:12]
        placeholder_cache = {}

        combined_text = f"QUERY: {original_query}\nTARGET: {target_response}"
        falcon_res = falcon_preprocess(combined_text, level=falcon_level, salt=stable_salt, placeholder_cache=placeholder_cache, custom_terms=falcon_custom_terms)
        falcon_meta = falcon_res.metadata
        _falcon_placeholder_map = falcon_res.placeholder_map

        original_query = falcon_preprocess(original_query, level=falcon_level, salt=stable_salt, placeholder_cache=placeholder_cache, custom_terms=falcon_custom_terms).redacted_text
        target_response = falcon_preprocess(target_response, level=falcon_level, salt=stable_salt, placeholder_cache=placeholder_cache, custom_terms=falcon_custom_terms).redacted_text

    if not target_response.strip():
        return jsonify({"error": "Target response is required"}), 400

    attacker_desc = expand_role(attacker_role)
    defender_desc = expand_role(defender_role)

    # Round 1: Attacker tears apart the defender's response
    attacker_prompt = (
        f"You are the Korum-OS Sentinel. You have been provided a single claim from a larger security report.\n\n"
        f"ORIGINAL QUESTION: {original_query}\n"
        f"THE {defender_role.upper()}'S RESPONSE:\n{target_response}\n\n"
        f"PROVENANCE CONTEXT: {data.get('provenance_hash', data.get('qanapi_hash', 'Standard Provenance Enabled'))}\n\n"
        f"YOUR MISSION: You are {attacker_desc}. Find the 1% chance this claim is incorrect. "
        f"Identify logic bypasses, technical inaccuracies, or hidden risks. Be ruthless. "
        f"Cite the exact claim you're attacking. Match your analysis to the DOMAIN of the original question — "
        f"do not inject unrelated frameworks or standards."
    )

    # Pick provider: use OpenAI for attacker (fast, aggressive), Anthropic for defender (precise, thorough)
    print(f"⚔️ INTERROGATION: {attacker_role.upper()} vs {defender_role.upper()}")
    user_id = current_user.id if hasattr(current_user, 'id') else None
    attacker_result = call_openai_gpt4(attacker_prompt, attacker_role, user_id=user_id)

    if not attacker_result.get('success'):
        attacker_result = call_google_gemini(attacker_prompt, attacker_role, user_id=user_id)

    attacker_text = attacker_result.get('response', 'Attack failed.')

    # Round 2: Defender rebuts the attacker's challenges
    defender_prompt = (
        f"ORIGINAL QUESTION: {original_query}\n\n"
        f"YOUR ORIGINAL RESPONSE:\n{target_response}\n\n"
        f"THE {attacker_role.upper()}'S CHALLENGE:\n{attacker_text}\n\n"
        f"YOUR MISSION: You are {defender_desc}. Defend your logic or concede. "
        f"If the attacker found a valid weakness, propose concrete fixes using standards relevant to the domain. "
        f"No hand-waving. Cite evidence."
    )

    defender_result = call_anthropic_claude(defender_prompt, defender_role, user_id=user_id)

    if not defender_result.get('success'):
        defender_result = call_google_gemini(defender_prompt, defender_role, user_id=user_id)

    defender_text = defender_result.get('response', 'Defense failed.')

    # --- REHYDRATE INTERROGATION SERVER-SIDE ---
    if use_falcon and _falcon_placeholder_map:
        attacker_text = falcon_rehydrate(attacker_text, _falcon_placeholder_map)
        defender_text = falcon_rehydrate(defender_text, _falcon_placeholder_map)

    # Audit log: interrogation
    log_audit("interrogation",
              user_id=current_user.id if hasattr(current_user, 'id') else None,
              user_email=current_user.email if hasattr(current_user, 'email') else None,
              details=f"attacker={attacker_role} | defender={defender_role} | attacker_model={attacker_result.get('model', 'unknown')} | defender_model={defender_result.get('model', 'unknown')} | falcon={falcon_level if use_falcon else 'OFF'} | query={original_query[:200]}")

    # ── SERVER-SIDE VERDICT ANALYSIS ──────────────────────────────────────
    # Analyze attacker + defender texts to produce a reliable score delta.
    # This replaces brittle client-side keyword matching.
    def _interrogation_verdict(atk_text: str, def_text: str):
        atk = atk_text.lower()
        defn = def_text.lower()

        # --- Component-level impact tracking ---
        impact_components = []

        # 1. Assumption failures
        assumption_signals = [
            'assumption', 'assumed', 'presuppose', 'taken for granted',
            'failed to account', 'overlooked', 'did not consider'
        ]
        assumption_hits = sum(1 for w in assumption_signals if w in atk or w in defn)
        if assumption_hits:
            penalty = -(assumption_hits * 2)
            impact_components.append({"type": "ASSUMPTION_FAILURE", "delta": penalty,
                                      "detail": f"{assumption_hits} assumption challenge(s) detected"})

        # 2. Missing data / evidence gaps
        missing_data_signals = [
            'no data', 'missing data', 'no evidence', 'lacks evidence', 'unsubstantiated',
            'insufficient data', 'no source', 'unsupported', 'without evidence', 'gap in'
        ]
        missing_hits = sum(1 for w in missing_data_signals if w in atk or w in defn)
        if missing_hits:
            penalty = -(missing_hits * 2)
            impact_components.append({"type": "MISSING_DATA", "delta": penalty,
                                      "detail": f"{missing_hits} evidence gap(s) identified"})

        # 3. Overconfidence penalty
        overconfidence_signals = [
            'overstated', 'overconfident', 'too certain', 'exaggerated',
            'inflated', 'unrealistic', 'unjustified certainty'
        ]
        oc_hits = sum(1 for w in overconfidence_signals if w in atk or w in defn)
        if oc_hits:
            penalty = -(oc_hits * 3)
            impact_components.append({"type": "OVERCONFIDENCE", "delta": penalty,
                                      "detail": f"{oc_hits} overconfidence flag(s)"})

        # 4. Concessions (defender acknowledges weakness)
        concession_signals = [
            'concede', 'concession', 'acknowledged', 'valid point', 'correctly identifies',
            'fair criticism', 'legitimate concern', 'understated',
            'you are correct', 'i was wrong', 'error in',
            'incomplete', 'inaccurate', 'i acknowledge', 'the attacker is right',
            'this criticism is valid', 'cannot dispute', 'stands corrected'
        ]
        concessions = sum(1 for w in concession_signals if w in defn)
        if concessions:
            penalty = -(concessions * 3)
            impact_components.append({"type": "CONCESSION", "delta": penalty,
                                      "detail": f"{concessions} concession(s) from defender"})

        # 5. Strong defense (positive — defender holds ground)
        defense_signals = [
            'my analysis stands', 'maintains', 'logic maintained', 'evidence supports',
            'rebuttal', 'refuted', 'incorrect assumption', 'the original assessment holds',
            'i stand by', 'the criticism is flawed', 'my original position',
            'remains valid', 'not a valid'
        ]
        holds = sum(1 for w in defense_signals if w in defn or w in atk)
        if holds:
            bonus = holds * 3
            impact_components.append({"type": "DEFENSE_HELD", "delta": bonus,
                                      "detail": f"{holds} defense point(s) maintained"})

        # 6. Attacker critical hits
        atk_critical = sum(1 for w in ['critical flaw', 'fatal error', 'clearly wrong',
                                        'demonstrably false', 'significant error', 'major gap'] if w in atk)
        if atk_critical:
            penalty = -(atk_critical * 4)
            impact_components.append({"type": "CRITICAL_HIT", "delta": penalty,
                                      "detail": f"{atk_critical} critical flaw(s) identified by attacker"})

        # Compute net delta from components
        net_delta = sum(c['delta'] for c in impact_components) if impact_components else -2

        # Determine verdict label
        if net_delta <= -15:
            verdict = 'CRITICAL CONCESSION'
        elif net_delta <= -8:
            verdict = 'SIGNIFICANT WEAKNESS'
        elif net_delta <= -3:
            verdict = 'CONCESSION'
        elif net_delta < 0:
            verdict = 'CHALLENGED — INCONCLUSIVE'
        elif net_delta == 0:
            verdict = 'CONTESTED — NEUTRAL'
        elif net_delta <= 5:
            verdict = 'DEFENSE HELD'
        else:
            verdict = 'STRONG DEFENSE'

        return net_delta, verdict, impact_components

    interrogation_delta, interrogation_verdict, impact_components = _interrogation_verdict(attacker_text, defender_text)

    response_data = {
        "success": True,
        "attacker": {
            "role": attacker_role,
            "role_display": attacker_desc.split(' with expertise')[0],
            "response": attacker_text,
            "model": attacker_result.get('model', 'unknown'),
        },
        "defender": {
            "role": defender_role,
            "role_display": defender_desc.split(' with expertise')[0],
            "response": defender_text,
            "model": defender_result.get('model', 'unknown'),
        },
        "original_query": original_query,
        "score_delta": interrogation_delta,
        "verdict": interrogation_verdict,
        "impact_report": impact_components,
        "falcon": {
            "enabled": use_falcon,
            "level": falcon_level,
            "metadata": falcon_meta,
        } if use_falcon else None
    }

    # Save interrogation to thread if thread_id provided
    thread_id = data.get('thread_id')
    if thread_id:
        try:
            # Extract key terms from the original query for mediation keyword matching
            _interrog_keywords = [w for w in original_query.lower().split() if len(w) > 4][:10]
            _thread_save_message(thread_id, 'interrogation',
                                 json.dumps({"attacker": attacker_text[:2000], "defender": defender_text[:2000]}),
                                 metadata={"attacker_role": attacker_role, "defender_role": defender_role,
                                           "attacker_model": attacker_result.get('model'), "defender_model": defender_result.get('model'),
                                           "score_delta": interrogation_delta,
                                           "verdict": interrogation_verdict,
                                           "target_provider": data.get('target_provider', defender_role),
                                           "keywords": _interrog_keywords})
        except Exception as thread_err:
            logger.error(f"[INTERROGATION] Thread save failed: {thread_err}")

    return jsonify(response_data)

  except Exception as e:
    logger.error(f"[INTERROGATION] Error: {e}", exc_info=True)
    return jsonify({"success": False, "error": f"Interrogation failed: {str(e)}"}), 500


@app.route('/api/verify', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def verify_claim():
    """
    Scalpel Mode: Send a single claim to Perplexity for source verification.
    Returns cited sources and evidence assessment. 1 API call only.
    """
    from llm_core import call_perplexity, call_google_gemini
    data = request.json
    claim = sanitize_input(data.get('claim', ''))
    original_query = sanitize_input(data.get('original_query', ''))

    # --- FALCON HARDENING: REDACT INPUTS ---
    use_falcon = data.get('use_falcon', False)
    falcon_level = data.get('falcon_level', 'STANDARD')
    falcon_custom_terms = data.get('falcon_custom_terms', []) or None
    falcon_meta = None
    _falcon_placeholder_map = {}

    if use_falcon:
        claim_res = falcon_preprocess(claim, level=falcon_level, custom_terms=falcon_custom_terms)
        claim = claim_res.redacted_text
        original_query = falcon_preprocess(original_query, level=falcon_level, custom_terms=falcon_custom_terms).redacted_text
        falcon_meta = claim_res.metadata
        _falcon_placeholder_map = claim_res.placeholder_map

    if not claim.strip():
        return jsonify({"error": "No claim provided"}), 400

    verify_prompt = (
        f"VERIFY THIS SPECIFIC CLAIM with authoritative sources:\n\n"
        f"\"{claim}\"\n\n"
        f"CONTEXT: This claim was made in response to: {original_query}\n\n"
        f"YOUR TASK:\n"
        f"1. Is this claim ACCURATE, PARTIALLY ACCURATE, or INACCURATE?\n"
        f"2. Cite specific sources (URLs, papers, standards) that confirm or contradict it.\n"
        f"3. If partially accurate, state exactly what is correct and what is wrong.\n"
        f"4. Provide the authoritative reference relevant to the domain (e.g., NIST, RFC, ISO, IEEE, FDA, SEC filings, peer-reviewed papers).\n\n"
        f"Be precise. No filler. Sources are mandatory. Match your references to the domain of the claim."
    )

    try:
        user_id = current_user.id if hasattr(current_user, 'id') else None
        result = call_perplexity(verify_prompt, "fact_checker", user_id=user_id)
        if not result.get('success'):
            # Fallback to Google if Perplexity is down
            result = call_google_gemini(verify_prompt, "fact_checker", user_id=user_id)

        if result.get('success'):
            verification_text = result['response']

            # --- REHYDRATE VERIFICATION SERVER-SIDE ---
            if use_falcon and _falcon_placeholder_map:
                verification_text = falcon_rehydrate(verification_text, _falcon_placeholder_map)

            # Audit log: verification
            log_audit("verify_claim",
                      user_id=current_user.id if hasattr(current_user, 'id') else None,
                      user_email=current_user.email if hasattr(current_user, 'email') else None,
                      details=f"model={result.get('model', 'unknown')} | falcon={falcon_level if use_falcon else 'OFF'} | claim={claim[:200]}")
            # Extract structured verdict from the LLM response text
            vtext_upper = verification_text.upper()
            if 'INACCURATE' in vtext_upper and 'PARTIALLY' not in vtext_upper:
                verify_verdict = 'INACCURATE'
                verify_score_delta = -12
            elif 'PARTIALLY ACCURATE' in vtext_upper or 'PARTIALLY' in vtext_upper:
                verify_verdict = 'PARTIALLY_ACCURATE'
                verify_score_delta = -4
            elif any(w in vtext_upper for w in ('ACCURATE', 'CONFIRMED', 'VERIFIED', 'CORRECT', 'SUPPORTED')):
                verify_verdict = 'ACCURATE'
                verify_score_delta = 6
            else:
                verify_verdict = 'UNRESOLVED'
                verify_score_delta = 0

            verify_response = {
                "success": True,
                "claim": claim,
                "verification": verification_text,
                "verdict": verify_verdict,
                "score_delta": verify_score_delta,
                "model": result.get('model', 'unknown'),
                "provider": "perplexity",
                "falcon": {
                    "enabled": use_falcon,
                    "level": falcon_level,
                    "metadata": falcon_meta,
                    # "placeholder_map": _falcon_placeholder_map <-- SECURE: Never sent to client
                } if use_falcon else None
            }

            # Save verification to thread if thread_id provided
            thread_id = data.get('thread_id')
            if thread_id:
                _verify_keywords = [w for w in claim.lower().split() if len(w) > 4][:10]
                _thread_save_message(thread_id, 'verification',
                                     json.dumps({"claim": claim[:500], "verification": result['response'][:2000]}),
                                     metadata={"model": result.get('model'), "provider": "perplexity",
                                               "score_delta": verify_score_delta,
                                               "verdict": verify_verdict,
                                               "target_provider": data.get('provider_name', 'unknown'),
                                               "keywords": _verify_keywords})

            return jsonify(verify_response)
        else:
            return jsonify({"success": False, "error": "Verification failed"}), 500
    except Exception as e:
        print(f"[VERIFY] Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _run_council_job(job_id, query, personas, workflow, active_models, user_id,
                     hacker_mode, use_falcon, falcon_level, falcon_meta,
                     _falcon_placeholder_map, _ghost_map_summary, _residual_report,
                     _vault_doc_ids_used):
    """Background thread: runs the full council pipeline and stores result in Redis."""
    import sys
    import traceback
    with app.app_context():
        try:
            from llm_core import call_google_gemini

            # --- Phase: Council Execution ---
            _job_set_status(job_id, "processing", phase="council")
            print(f"[JOB {job_id[:8]}] Council execution starting...")
            sys.stdout.flush()

            results = execute_council_v2(query, personas, workflow=workflow,
                                         active_models=active_models, user_id=user_id,
                                         ghost_map=_ghost_map_summary, residual_report=_residual_report)

            # Red Team injection if requested
            if hacker_mode:
                print("🛡️ RED TEAM INJECTION (Chain)")
                exploit_prompt = f"PLAN: {query}\n\nCOUNCIL OUTPUT:\n{json.dumps(results['results'])}\n\nMISSION: RED TEAM THIS."
                results['results']['red_team'] = call_google_gemini(exploit_prompt, "HACKER", user_id=user_id)

            # --- Phase: Response Assembly ---
            _job_set_status(job_id, "processing", phase="finalizing")
            print(f"[JOB {job_id[:8]}] Assembling response...")
            sys.stdout.flush()

            res_map = results.get('results', {})

            # --- FALCON REHYDRATION ---
            if use_falcon and _falcon_placeholder_map:
                for provider_key, provider_result in res_map.items():
                    if isinstance(provider_result, dict) and provider_result.get('response'):
                        provider_result['response'] = falcon_rehydrate(provider_result['response'], _falcon_placeholder_map)
                syn = results.get('synthesis', {})
                if isinstance(syn, dict) and syn.get('meta', {}).get('summary'):
                    syn['meta']['summary'] = falcon_rehydrate(syn['meta']['summary'], _falcon_placeholder_map)
                if isinstance(syn, dict) and syn.get('meta', {}).get('final_document'):
                    syn['meta']['final_document'] = falcon_rehydrate(syn['meta']['final_document'], _falcon_placeholder_map)

            # --- Payload slimming helpers ---
            def _trim_text(value, max_chars=320):
                if not isinstance(value, str):
                    return value
                value = value.strip()
                if len(value) <= max_chars:
                    return value
                return value[:max_chars].rstrip() + "..."

            def _slim_verified_claims(claims, limit=12):
                slim_claims = []
                for claim in (claims or [])[:limit]:
                    if not isinstance(claim, dict):
                        continue
                    slim_claims.append({
                        "claim": _trim_text(claim.get("claim", ""), 240),
                        "status": claim.get("status", "UNVERIFIED"),
                        "score": claim.get("score", 50),
                        "type": claim.get("type", "claim"),
                        "anchors": list(claim.get("anchors", [])[:4]),
                        "violations": [_trim_text(v, 200) for v in claim.get("violations", [])[:3]]
                    })
                return slim_claims

            def _slim_result_map(raw_results):
                slim_results = {}
                for provider_key, provider_result in (raw_results or {}).items():
                    if not isinstance(provider_result, dict):
                        continue
                    slim_entry = {
                        "success": bool(provider_result.get("success", False)),
                        "truth_meter": provider_result.get("truth_meter", 50),
                        "contribution_score": provider_result.get("contribution_score", 0),
                    }
                    model_name = provider_result.get("model")
                    if isinstance(model_name, str) and model_name.strip():
                        slim_entry["model"] = model_name.strip()
                    role_name = provider_result.get("role")
                    if isinstance(role_name, str) and role_name.strip():
                        slim_entry["role"] = role_name.strip()
                    response_text = provider_result.get("response")
                    if isinstance(response_text, str) and response_text.strip():
                        # Preserve the answer body for report library recall without
                        # sending the entire raw provider payload back to the client.
                        slim_entry["response"] = _trim_text(response_text, 12000)
                    error_text = provider_result.get("error")
                    if isinstance(error_text, str) and error_text.strip():
                        slim_entry["error"] = _trim_text(error_text, 500)
                    usage = provider_result.get("usage")
                    if isinstance(usage, dict):
                        slim_entry["cost"] = usage.get("cost", 0)
                        slim_entry["time"] = usage.get("latency", 0) / 1000
                        slim_entry["usage"] = {
                            "cost": usage.get("cost", 0),
                            "latency": usage.get("latency", 0),
                            "input": usage.get("input", 0),
                            "output": usage.get("output", 0),
                        }
                    citations = provider_result.get("citations")
                    if isinstance(citations, list) and citations:
                        slim_entry["citations"] = [
                            c for c in citations[:8]
                            if isinstance(c, str) and c.strip()
                        ]
                    verified_claims = provider_result.get("verified_claims")
                    if isinstance(verified_claims, list) and verified_claims:
                        slim_entry["verified_claims"] = _slim_verified_claims(verified_claims)
                    slim_results[provider_key] = slim_entry
                return slim_results

            def _prepare_frontend_synthesis(raw_synthesis):
                if not isinstance(raw_synthesis, dict):
                    return raw_synthesis
                synthesis_copy = copy.deepcopy(raw_synthesis)
                meta = synthesis_copy.get("meta")
                if isinstance(meta, dict) and "finalizer_review" in meta:
                    meta.pop("finalizer_review", None)
                    print("[V2 CHAIN] Removed hidden finalizer_review from frontend payload.")
                return synthesis_copy

            frontend_results = _slim_result_map(res_map)
            frontend_synthesis = _prepare_frontend_synthesis(results.get('synthesis'))

            def _f_metric(provider_key):
                return res_map.get(provider_key, {}).get('usage', {})

            pipeline_result = {
                "constraints": res_map.get('anthropic', {}).get('response', "Extraction Failed"),
                "standard_solution": res_map.get('openai', {}).get('response', "Generation Failed"),
                "failure_analysis": res_map.get('google', {}).get('response', "Analysis Failed"),
                "scout_intel": res_map.get('perplexity', {}).get('response') if res_map.get('perplexity', {}).get('success') else None,
                "exploit_poc": res_map.get('red_team', {}).get('response') if hacker_mode else None,
                "final_artifact": results.get('synthesis', {}).get('meta', {}).get('final_document') or results.get('synthesis', {}).get('meta', {}).get('summary', "Synthesis Failed"),
                "consensus": results.get('consensus', ''),
                "classification": results.get('classification', {}),
                "divergence": results.get('divergence', {}),
                "results": frontend_results,
                "synthesis": frontend_synthesis,
                "metrics": {
                    "deconstruct": {"cost": _f_metric('anthropic').get('cost', 0.0), "time": _f_metric('anthropic').get('latency', 0) / 1000},
                    "build": {"cost": _f_metric('openai').get('cost', 0.0), "time": _f_metric('openai').get('latency', 0) / 1000},
                    "stress": {"cost": _f_metric('google').get('cost', 0.0), "time": _f_metric('google').get('latency', 0) / 1000},
                    "scout": {"cost": _f_metric('perplexity').get('cost', 0.0), "time": _f_metric('perplexity').get('latency', 0) / 1000},
                    "synthesize": {"cost": results.get('metrics', {}).get('run_cost', 0.0), "time": results.get('metrics', {}).get('latency_ms', 0) / 1000}
                },
                "execution_metrics": results.get('metrics', {})
            }

            response_data = {
                "success": True,
                "pipeline_result": pipeline_result
            }

            # Attach Falcon metadata if active
            if use_falcon and falcon_meta:
                pipeline_result["falcon"] = {
                    "enabled": True,
                    "level": falcon_level,
                    "redacted_entity_count": falcon_meta['total_redactions'],
                    "high_risk_items_count": falcon_meta['high_risk_items_count'],
                    "categories": falcon_meta['categories_found'],
                    "counts": falcon_meta['counts_by_category'],
                    "exposure_risk": falcon_meta['exposure_risk'],
                }
                response_data["falcon"] = {
                    "enabled": True,
                    "level": falcon_level,
                    "redacted_entity_count": falcon_meta['total_redactions'],
                    "high_risk_items_count": falcon_meta['high_risk_items_count'],
                    "categories": falcon_meta['categories_found'],
                    "counts": falcon_meta['counts_by_category'],
                    "exposure_risk": falcon_meta['exposure_risk'],
                }

            # --- GOLDFISH: Purge extracted text after council consumption ---
            if _vault_doc_ids_used:
                from vault import get_vault_document as _gvd
                for _vid in _vault_doc_ids_used:
                    _vd = _gvd(_vid)
                    if _vd:
                        _vd.extracted_text = None
                        _vd.status = 'consumed'
                db.session.commit()
                print(f"🐟 GOLDFISH: Purged extracted text from {len(_vault_doc_ids_used)} vault doc(s)")

            # --- Store result ---
            _resp_bytes = len(json.dumps(response_data).encode('utf-8'))
            print(f"[JOB {job_id[:8]}] Pipeline complete — {_resp_bytes:,} bytes ({_resp_bytes / 1024:.1f} KB)")
            sys.stdout.flush()
            _job_set_result(job_id, response_data)

        except Exception as e:
            traceback.print_exc()
            print(f"❌ [JOB {job_id[:8]}] Pipeline failed: {e}")
            sys.stdout.flush()
            _job_set_status(job_id, "error", error=str(e))


@app.route('/api/v2/reasoning_chain', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def reasoning_chain():
    """
    V2 Orchestration Route — Async Job Pattern.
    Starts the council pipeline in a background thread, returns a job_id immediately.
    Frontend polls /api/v2/reasoning_chain/status/<job_id> for results.
    """
    data = request.json
    query = data.get('query')
    hacker_mode = data.get('hacker_mode', False)
    workflow = data.get('workflow', 'RESEARCH')

    if not query:
        return jsonify({"success": False, "error": "Query required"}), 400

    # --- VAULT DOCUMENTS: Attach extracted text from S3 pipeline ---
    vault_document_ids = data.get('vault_document_ids', [])
    _vault_doc_ids_used = []
    if vault_document_ids:
        from vault import get_vault_document
        doc_texts = []
        for vdoc_id in vault_document_ids:
            vdoc = get_vault_document(vdoc_id)
            if not vdoc:
                print(f"⚠️ V2 Vault doc not found: {vdoc_id}")
                continue
            if vdoc.status not in ('falcon_processed', 'ready'):
                print(f"⚠️ V2 Vault doc not ready: {vdoc_id} (status={vdoc.status})")
                continue
            if vdoc.user_id != current_user.id and not current_user.is_admin():
                print(f"⚠️ V2 Vault doc access denied: {vdoc_id}")
                continue
            if vdoc.extracted_text:
                doc_texts.append(f"[Vault Document: {vdoc_id[:8]}]\n{vdoc.extracted_text}")
                _vault_doc_ids_used.append(vdoc_id)
        if doc_texts:
            MAX_DOC_CHARS = 12000
            combined = "\n\n".join(doc_texts)
            if len(combined) > MAX_DOC_CHARS:
                combined = combined[:MAX_DOC_CHARS] + f"\n\n[DOCUMENT TRUNCATED — {len(combined) - MAX_DOC_CHARS} chars omitted to prevent timeout. Run with a shorter document or use chunking.]"
                print(f"📎 V2: document text truncated to {MAX_DOC_CHARS} chars (was {sum(len(t) for t in doc_texts)})")
            query = query + "\n\n--- ATTACHED DOCUMENTS ---\n" + combined
            print(f"📎 V2: {len(doc_texts)} vault document(s) attached ({sum(len(t) for t in doc_texts)} chars total, {len(combined)} sent)")

    # --- FALCON PROTOCOL: SECURE PREPROCESSING ---
    use_falcon = data.get('use_falcon', False)
    falcon_level = data.get('falcon_level', 'STANDARD')
    falcon_custom_terms = data.get('falcon_custom_terms', []) or None
    falcon_meta = None
    _falcon_placeholder_map = {}
    _ghost_map_summary = {}
    _residual_report = {}

    if use_falcon:
        if falcon_level not in ('LIGHT', 'STANDARD', 'BLACK'):
            falcon_level = 'STANDARD'
        falcon_res = falcon_preprocess(query, level=falcon_level, custom_terms=falcon_custom_terms)
        query = falcon_res.redacted_text
        falcon_meta = falcon_res.metadata
        _falcon_placeholder_map = falcon_res.placeholder_map
        print(f"🦅 FALCON [{falcon_level}]: {falcon_meta['total_redactions']} entities redacted, risk={falcon_meta['exposure_risk']}")
        print(f"🦅 FALCON REDACTED QUERY: {query[:500]}")
        if falcon_meta.get('counts_by_category'):
            print(f"🦅 FALCON CATEGORIES: {falcon_meta['counts_by_category']}")

        from falcon import build_ghost_map_summary, detect_residual_pii
        _ghost_map_summary = build_ghost_map_summary(falcon_res)
        _residual_report = detect_residual_pii(query, falcon_res)
        print(f"🔍 PII DIFF: {_residual_report.get('residual_count', 0)} residual(s) — {'CLEAN' if _residual_report.get('pii_diff_clean') else 'ALERT'}")

    print(f"⚡ V2 REASONING CHAIN [{workflow}] — async job")

    personas = data.get('council_roles', {
        "openai": "Strategist",
        "anthropic": "Architect",
        "google": "Critic",
        "perplexity": "Scout",
        "mistral": "Analyst"
    })
    active_models = data.get('active_models', list(personas.keys()))
    user_id = current_user.id if hasattr(current_user, 'id') else None

    # --- Spawn background thread ---
    job_id = str(uuid.uuid4())
    _job_set_status(job_id, "processing", phase="starting")

    thread = threading.Thread(
        target=_run_council_job,
        args=(job_id, query, personas, workflow, active_models, user_id,
              hacker_mode, use_falcon, falcon_level, falcon_meta,
              _falcon_placeholder_map, _ghost_map_summary, _residual_report,
              _vault_doc_ids_used),
        daemon=True
    )
    thread.start()
    print(f"[JOB {job_id[:8]}] Thread spawned for V2 chain")

    return jsonify({"success": True, "job_id": job_id})


@app.route('/api/v2/reasoning_chain/status/<job_id>', methods=['GET'])
@auth_required
def reasoning_chain_status(job_id):
    """Poll endpoint for async V2 pipeline jobs."""
    status, result_raw = _job_get(job_id)

    if not status:
        return jsonify({"success": False, "error": "Job not found"}), 404

    job_status = status.get("status", "unknown")

    if job_status == "complete" and result_raw:
        # Deliver result and clean up
        result_data = json.loads(result_raw) if isinstance(result_raw, (str, bytes)) else result_raw
        _job_cleanup(job_id)
        return jsonify(result_data)

    if job_status == "error":
        _job_cleanup(job_id)
        return jsonify({"success": False, "error": status.get("error", "Pipeline failed")}), 500

    # Still processing
    return jsonify({
        "success": True,
        "status": "processing",
        "phase": status.get("phase", "unknown")
    })

@app.route('/api/enhance_prompt', methods=['POST'])
@auth_required
def enhance_prompt():
    data = request.json
    draft = data.get('draft')
    
    if not draft:
        return jsonify({"success": False, "error": "Draft text required"}), 400

    print(f"🪄 Enhancing Prompt: {draft[:50]}...")

    # Use Gemini Flash (Sentinel) for speed, or GPT-4o as fallback
    system_instruction = """You are an expert Prompt Engineer for an elite AI Council. 
    Your goal is to rewrite the user's rough, unstructured input into a clear, strategic, and high-quality prompt.
    
    RULES:
    1. Fix grammar and clarity.
    2. Structure the request logically.
    3. Add necessary context placeholders if vague (e.g. [Insert Company Name]).
    4. Maintain the user's original intent but make it professional.
    5. RETURN ONLY THE REWRITTEN PROMPT. NO INTRO/OUTRO."""

    user_id = current_user.id if hasattr(current_user, 'id') else None
    from llm_core import call_google_gemini, call_openai_gpt4
    
    full_prompt = f"{system_instruction}\n\nUser Input: {draft}"
    
    # Try Gemini First
    res = call_google_gemini(full_prompt, "PromptEngineer", model="gemini-2.0-flash", user_id=user_id)
    if res.get('success'):
        return jsonify({"success": True, "enhanced_text": res['response'], "model": "Gemini Flash"})
    
    # Fallback to OpenAI
    res = call_openai_gpt4(full_prompt, "PromptEngineer", model="gpt-4o", user_id=user_id)
    if res.get('success'):
        return jsonify({"success": True, "enhanced_text": res['response'], "model": "GPT-4o"})

    return jsonify({"success": False, "error": "Enhancement services unavailable"}), 503
    
    return jsonify({"success": False, "error": "Enhancement services unavailable"}), 503

@app.route('/api/usage/stats', methods=['GET'])
@auth_required
def get_usage_stats():
    """Returns aggregated usage statistics for the billing ledger."""
    try:
        # Total spend (all time)
        total_spend = db.session.query(func.sum(UsageLog.cost_estimate)).filter(UsageLog.user_id == current_user.id).scalar() or 0.0

        # Daily spend (last 7 days)
        from datetime import timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        daily_stats_query = db.session.query(
            func.date(UsageLog.created_at).label('date'),
            func.sum(UsageLog.cost_estimate).label('cost')
        ).filter(
            UsageLog.user_id == current_user.id,
            UsageLog.created_at >= seven_days_ago
        ).group_by(func.date(UsageLog.created_at)).order_by('date').all()
        
        daily_stats = [{"date": str(row.date), "cost": float(row.cost)} for row in daily_stats_query]

        # Provider breakdown (last 30 days) agg
        provider_stats_query = db.session.query(
            UsageLog.provider_name,
            func.sum(UsageLog.cost_estimate).label('cost')
        ).filter(
            UsageLog.user_id == current_user.id
        ).group_by(UsageLog.provider_name).all()
        
        provider_stats = {row[0] or "unknown": float(row[1]) for row in provider_stats_query}

        return jsonify({
            "total_spend": float(total_spend),
            "daily_stats": daily_stats,
            "provider_breakdown": provider_stats,
            "currency": "USD"
        })
    except Exception as e:
        print(f"Usage stats error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sentinel', methods=['POST'])
@auth_required
def ask_sentinel():
    data = request.json
    query = data.get('query')
    history = data.get('history', [])

    if not query:
        return jsonify({"success": False, "error": "Query required"})

    system_instruction = "You are THE SENTINEL, a tactical aide inside a decision intelligence platform called KORUM-OS. Be concise, direct, and factual. ALWAYS answer the user's question to the best of your ability — provide research, analysis, examples, product names, frameworks, and specifics. You have conversation memory — use prior exchanges for context when the user references earlier questions or asks follow-ups. Only suggest 'Convene the Council' if the user explicitly asks for a multi-provider consensus analysis. Never deflect, never refuse to answer, never say a question is too complex. You are a knowledgeable assistant — act like one."

    user_id = current_user.id if hasattr(current_user, 'id') else None
    # Use Gemini Flash for speed (The Sentinel)
    from llm_core import call_google_gemini, call_openai_gpt4
    
    try:
        # Build conversation thread/prompt for Gemini
        # We'll prepend history to the query for the wrapper
        full_prompt = f"{system_instruction}\n\n"
        for msg in history[:-1]:
            role_label = "User" if msg.get('role') == 'user' else "Sentinel"
            full_prompt += f"{role_label}: {msg.get('content', '')}\n\n"
        full_prompt += f"User: {query}"

        # Try Gemini First
        res = call_google_gemini(full_prompt, "Sentinel", model="gemini-2.0-flash", user_id=user_id)
        if res.get('success'):
            return jsonify({"success": True, "response": res['response'], "model": "Gemini Flash"})
        
        # Fallback to OpenAI if Gemini fails
        res = call_openai_gpt4(full_prompt, "Sentinel", model="gpt-4o", user_id=user_id)
        if res.get('success'):
            return jsonify({"success": True, "response": res['response'], "model": "GPT-4o"})
            
        return jsonify({"success": False, "error": res.get('response', 'Sentinel failed')})

    except Exception as e:
        print(f"Sentinel Error: {e}")
        return jsonify({"success": False, "error": str(e)})

    return jsonify({"success": False, "error": "No available models for Sentinel"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Respect Node/JS convention if present
    env = os.environ.get("NODE_ENV", "development")
    debug_mode = (env != "production")

    print(f"🚀 KorumOS Server starting on port {port} [{env.upper()} MODE]")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
