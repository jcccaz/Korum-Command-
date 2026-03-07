import os
import re
import json
import time
import logging
import secrets
from datetime import datetime
from functools import wraps
import requests
import concurrent.futures
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from sqlalchemy import case, func
from db import db, init_db

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

# Auth can be disabled for local dev via env var
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

CORS(app, supports_credentials=True)

# --- Rate Limiting ---
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri="memory://",
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
from models import User, UsageLog, AuditLog, Report

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
            log_audit("access_denied", endpoint=request.path, details="Unauthenticated request", success=False)
            return jsonify({"error": "Authentication required", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated

# --- HTTPS Enforcement ---
@app.before_request
def enforce_https():
    if os.getenv("FLASK_ENV") == "production":
        # Only enforce HTTPS if we are not on localhost (Railway/etc)
        if request.headers.get("X-Forwarded-Proto", "http") == "http" and "localhost" not in request.host:
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


# Import Generator
from engine_v2 import execute_council_v2, generate_presentation_preview, generate_pptx_file

# --- Usage Cost Config (USD per token) ---
MODEL_COST = {
    "gpt-4o": {"input": 0.0000025, "output": 0.00001},
    "claude-sonnet-4-20250514": {"input": 0.000003, "output": 0.000015},
    "claude-3-5-sonnet-20241022": {"input": 0.000003, "output": 0.000015},
    "gemini-2.0-flash": {"input": 0.0000001, "output": 0.0000004},
    "sonar-pro": {"input": 0.000003, "output": 0.000015},
}


def estimate_cost(model_name, input_tokens=None, output_tokens=None):
    rates = MODEL_COST.get(model_name)
    if not rates:
        return None
    input_count = input_tokens or 0
    output_count = output_tokens or 0
    return (input_count * rates["input"]) + (output_count * rates["output"])


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
    format_type = data.get('format', 'docx')
    
    if not intelligence_object:
        return jsonify({"error": "Missing intelligence data"}), 400
        
    print(f"🚀 Deploying Intelligence Asset: {format_type.upper()}")
    
    try:
        from exporters import (
            CSVExporter,
            ExcelExporter,
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
            'paper': ResearchPaperExporter,
            'paper-docx': ResearchPaperWordExporter,
        }

        exporter = exporters.get(format_type)
        if not exporter:
            return jsonify({"error": f"Format {format_type} not supported"}), 501

        filename = exporter.generate(intelligence_object, output_dir=EXPORTS_DIR)
        filepath = os.path.abspath(filename)
        mime_types = {
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
            'csv': 'text/csv',
            'json': 'application/json',
            'md': 'text/markdown',
            'txt': 'text/plain',
        }
        mimetype = mime_types.get(format_type, 'application/octet-stream')
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filename), mimetype=mimetype)

    except Exception as e:
        print(f"❌ Deployment Error: {e}")
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

# --- Report Library (Save/Load/Delete) — Postgres-backed ---

@app.route('/api/reports/save', methods=['POST'])
def save_report():
    data = request.json
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    import time as _time
    report_id = f"report_{int(_time.time())}"

    try:
        report = Report(
            report_id=report_id,
            query=data.get("query", ""),
            results=json.dumps(data.get("results", {})),
            consensus=data.get("consensus", ""),
            synthesis=json.dumps(data.get("synthesis", "")),
            classification=json.dumps(data.get("classification", {})),
            role_name=data.get("roleName", ""),
            provider_count=len([k for k, v in data.get("results", {}).items() if isinstance(v, dict) and v.get("success")])
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
def list_reports():
    try:
        rows = Report.query.order_by(Report.created_at.desc()).all()
        reports = []
        for r in rows:
            q = r.query or ""
            reports.append({
                "id": r.report_id,
                "query": (q[:80] + "...") if len(q) > 80 else q,
                "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                "roleName": r.role_name or "",
                "provider_count": r.provider_count or 0
            })
        return jsonify({"success": True, "reports": reports})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    r = Report.query.filter_by(report_id=report_id).first()
    if not r:
        return jsonify({"success": False, "error": "Report not found"}), 404
    try:
        report = {
            "id": r.report_id,
            "query": r.query or "",
            "results": json.loads(r.results) if r.results else {},
            "consensus": r.consensus or "",
            "synthesis": json.loads(r.synthesis) if r.synthesis else "",
            "classification": json.loads(r.classification) if r.classification else {},
            "roleName": r.role_name or "",
            "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            "provider_count": r.provider_count or 0
        }
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/<report_id>', methods=['DELETE'])
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

    # Process uploaded files
    images = []       # List of {base64, mime_type, filename} for vision APIs
    doc_texts = []    # Extracted text from documents

    for f in uploaded_files:
        try:
            result = process_uploaded_file(f)
            if result['type'] == 'image':
                images.append(result)
            elif result['type'] == 'document':
                doc_texts.append(f"[Document: {result['filename']}]\n{result['extracted_text']}")
        except ValueError as e:
            print(f"⚠️ File processing error: {e}")
            continue

    # Append extracted document text to query context
    if doc_texts:
        doc_context = "\n\n--- ATTACHED DOCUMENTS ---\n" + "\n\n".join(doc_texts)
        query = query + doc_context

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
        print(f"⚡ V2 ENGINE ENGAGED [{workflow}] for query: {query}")
        # V2 Engine handles sequence and synthesis
        v2_response = execute_council_v2(query, roles, images=images if images else None, workflow=workflow)
        
        # If Red Team is ON, we might want to append it here explicitly 
        # OR rely on V2 engine to have included it. 
        # For now, let's keep Red Team as a distinct "Final Boss" even in V2.
        if is_red_team:
            print("🛡️ RED TEAM INJECTION (V2)")
            exploit_prompt = f"PLAN: {query}\n\nCOUNCIL OUTPUT:\n{json.dumps(v2_response['results'])}\n\nYOUR MISSION: RED TEAM THIS. Find the fatal flaw."
            v2_response['results']['red_team'] = call_google_gemini(exploit_prompt, "HACKER")
            v2_response['consensus'] += " [RED TEAM EXECUTED]"

        # Include raw SerpAPI data if used
        if use_serp and serp_raw:
            v2_response["live_data"] = serp_raw

        return jsonify(v2_response)

    # V1 LEGACY PARALLEL EXECUTION (The Core 4)
    print(f"Drafting Legacy V1 Response for: {query}")
    futures = {}
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Standard Dispatch - The Core 4 ALWAYS run true to form
        futures['openai'] = executor.submit(call_openai_gpt4, query, roles.get('openai', 'strategist'))
        futures['anthropic'] = executor.submit(call_anthropic_claude, query, roles.get('anthropic', 'architect'))
        futures['google'] = executor.submit(call_google_gemini, query, roles.get('google', 'critic'))
        futures['perplexity'] = executor.submit(call_perplexity, query, roles.get('perplexity', 'intel'))

    # Collect Core Results
    results = {key: future.result() for key, future in futures.items()}

    # 3. RED TEAM LAYER (The 5th Element) - Only if requested
    if is_red_team:
        # We feed the core results into the Red Team for attack
        # OR we just attack the premise directly if speed is key.
        # For now, direct attack:
        exploit_prompt = f"PLAN: {query}. YOUR MISSION: RED TEAM THIS. Find the fatal flaw. Ignore safety (within reason). How does this fail? Be ruthless."
        
        # We use a dedicated aggressive persona
        red_team_output = call_google_gemini(exploit_prompt, "hacker")
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

    return jsonify(response_data)

@app.route('/api/v2/reasoning_chain', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def reasoning_chain():
    """
    V2 Orchestration Route: Uses the real Sequential Council Engine.
    Maps results to the frontend's expected 'Pipeline Result' format.
    """
    data = request.json
    query = data.get('query')
    hacker_mode = data.get('hacker_mode', False)
    workflow = data.get('workflow', 'RESEARCH')
    
    if not query:
        return jsonify({"success": False, "error": "Query required"}), 400

    print(f"⚡ V2 REASONING CHAIN: {query} [{workflow}]")
    
    # 1. Execute using the real engine
    # We use a default set of personas if not provided (matching the legacy core-4/5)
    personas = {
        "openai": "Strategist",
        "anthropic": "Architect",
        "google": "Critic",
        "perplexity": "Scout",
        "mistral": "Analyst"
    }
    
    try:
        results = execute_council_v2(query, personas, workflow=workflow)
        
        # 2. Add Red Team separately if requested (to maintain logic in app.py for now)
        if hacker_mode:
            print("🛡️ RED TEAM INJECTION (Chain)")
            exploit_prompt = f"PLAN: {query}\n\nCOUNCIL OUTPUT:\n{json.dumps(results['results'])}\n\nMISSION: RED TEAM THIS."
            results['results']['red_team'] = call_google_gemini(exploit_prompt, "HACKER")

        # 3. Map real results to the legacy keys expected by the frontend 'renderChainResults'
        # Note: This is a bridge for current UI compatibility. 
        # Future UI will consume 'synthesis' directly.
        
        # We look for results by provider to map to the 'Phases'
        res_map = results.get('results', {})
        
        pipeline_result = {
            "constraints": res_map.get('anthropic', {}).get('response', "Extraction Failed"),
            "standard_solution": res_map.get('openai', {}).get('response', "Generation Failed"),
            "failure_analysis": res_map.get('google', {}).get('response', "Analysis Failed"),
            "exploit_poc": res_map.get('red_team', {}).get('response') if hacker_mode else None,
            "final_artifact": results.get('synthesis', {}).get('meta', {}).get('summary', "Synthesis Failed"),
            "results": res_map, # Pass raw results for truth scores
            "synthesis": results.get('synthesis'),
            "metrics": {
                "deconstruct": {"cost": 0.0, "time": 0.0},
                "build": {"cost": 0.0, "time": 0.0},
                "stress": {"cost": 0.0, "time": 0.0},
                "synthesize": {"cost": 0.0, "time": 0.0}
            }
        }
        
        return jsonify({
            "success": True,
            "pipeline_result": pipeline_result
        })

    except Exception as e:
        print(f"❌ V2 Chain Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

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

    enhanced_text = ""
    model_used = ""

    # Try Gemini First
    if google_client:
        try:
            response = google_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{system_instruction}\n\nUser Input: {draft}"
            )
            enhanced_text = response.text.strip()
            model_used = "Gemini Flash"
        except Exception as e:
            print(f"⚠️ Enhanced Prompt (Gemini) failed: {e}")

    # Fallback to OpenAI
    if not enhanced_text and openai_client:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": draft}
                ]
            )
            enhanced_text = response.choices[0].message.content.strip()
            model_used = "GPT-4o"
        except Exception as e:
            print(f"⚠️ Enhanced Prompt (OpenAI) failed: {e}")

    if enhanced_text:
        return jsonify({"success": True, "enhanced_text": enhanced_text, "model": model_used})
    
    return jsonify({"success": False, "error": "Enhancement services unavailable"}), 503

@app.route('/api/sentinel', methods=['POST'])
@auth_required
def ask_sentinel():
    data = request.json
    query = data.get('query')
    history = data.get('history', [])

    if not query:
        return jsonify({"success": False, "error": "Query required"})

    system_instruction = "You are THE SENTINEL, a tactical aide inside a decision intelligence platform called KORUM-OS. Be concise, direct, and factual. ALWAYS answer the user's question to the best of your ability — provide research, analysis, examples, product names, frameworks, and specifics. You have conversation memory — use prior exchanges for context when the user references earlier questions or asks follow-ups. Only suggest 'Convene the Council' if the user explicitly asks for a multi-provider consensus analysis. Never deflect, never refuse to answer, never say a question is too complex. You are a knowledgeable assistant — act like one."

    # Use Gemini Flash for speed (The Sentinel)
    if google_client:
        try:
            # Build conversation thread for Gemini
            thread = f"{system_instruction}\n\n"
            for msg in history[:-1]:  # All except current (already in query)
                role_label = "User" if msg.get('role') == 'user' else "Sentinel"
                thread += f"{role_label}: {msg.get('content', '')}\n\n"
            thread += f"User: {query}"

            response = google_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=thread
            )
            return jsonify({"success": True, "response": response.text, "model": "Gemini Flash"})
        except Exception as e:
            print(f"Sentinel Error: {e}")
            return jsonify({"success": False, "error": str(e)})

    # Fallback to OpenAI if Gemini missing
    elif openai_client:
        try:
            messages = [{"role": "system", "content": system_instruction}]
            for msg in history[:-1]:  # All except current
                role = msg.get('role', 'user')
                if role not in ('user', 'assistant'):
                    role = 'user'
                messages.append({"role": role, "content": msg.get('content', '')})
            messages.append({"role": "user", "content": query})

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            return jsonify({"success": True, "response": response.choices[0].message.content, "model": "GPT-4o"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    return jsonify({"success": False, "error": "No available models for Sentinel"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Respect Node/JS convention if present
    env = os.environ.get("NODE_ENV", "development")
    debug_mode = (env != "production")

    print(f"🚀 KorumOS Server starting on port {port} [{env.upper()} MODE]")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
