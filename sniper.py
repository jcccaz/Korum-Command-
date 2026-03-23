# ---------------------------------------------------------------------------
# SNIPER — Active Defense Layer
# Precision Strike / Response / Attribution
#
# Three operational modes:
#   1. RESPONSE  — quarantine compromised output, alert operator
#   2. TAR PIT   — detect probes, serve expensive recursive garbage
#   3. ATTRIBUTION — package confirmed threats into evidence packets
#
# Sniper doesn't defend a network. It defends the reasoning chain.
# A firewall blocks everything. Sniper identifies the exact threat,
# confirms it's real (LOKI), and takes minimum action with maximum evidence.
# ---------------------------------------------------------------------------

import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# In-memory probe tracking (Redis upgrade path available)
# ---------------------------------------------------------------------------

_probe_tracker: Dict[str, List[float]] = {}   # {ip: [timestamps]}
_tarpit_targets: Dict[str, float] = {}         # {ip: flagged_until_timestamp}

PROBE_WINDOW_SECONDS = 300      # 5-minute sliding window
PROBE_THRESHOLD = 5             # 5 violations in window → tar pit
TARPIT_DURATION_SECONDS = 600   # 10-minute tar pit engagement


# ===================================================================
# MODE 1: SNIPER RESPONSE — Quarantine compromised output
# ===================================================================

def sniper_respond(event_type: str, v2_response: dict,
                   canary_data: Optional[dict] = None,
                   request_meta: Optional[dict] = None) -> dict:
    """
    Main Sniper dispatcher. Called when a detection event fires.
    Modifies v2_response in-place and returns a sniper report.

    event_type: canary_activated | integrity_failure | loki_block | impact_escalation
    """
    report = {
        "sniper_active": True,
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "actions_taken": [],
    }

    if event_type == "canary_activated":
        report = _handle_canary_activation(v2_response, canary_data or {}, report)
    elif event_type == "integrity_failure":
        report = _handle_integrity_failure(v2_response, report)
    elif event_type == "loki_block":
        report = _handle_loki_block(v2_response, report)
    elif event_type == "impact_escalation":
        report = _handle_impact_escalation(v2_response, report)

    # Attach sniper report to response
    v2_response["sniper"] = report

    # Log
    _ip = request_meta.get("ip", "unknown") if request_meta else "unknown"
    _user = request_meta.get("user_email", "unknown") if request_meta else "unknown"
    print(f"[SNIPER] {event_type.upper()} | IP={_ip} | User={_user} | Actions: {report['actions_taken']}")

    return report


def _handle_canary_activation(response: dict, canary_data: dict, report: dict) -> dict:
    """Canary token referenced by model — reasoning may be compromised."""
    activated_tokens = canary_data.get("tokens", [])
    report["severity"] = "HIGH"
    report["threat_type"] = "model_reasoning_compromise"
    report["detail"] = (
        f"{len(activated_tokens)} canary token(s) activated. "
        "Model referenced fabricated entities injected by Falcon. "
        "Output may reflect prompt injection, model poisoning, or hallucination."
    )

    # QUARANTINE: Strip compromised provider responses
    compromised_providers = []
    for provider, res in response.get("results", {}).items():
        if isinstance(res, dict) and res.get("compromised"):
            # Redact the compromised response — don't let it reach the operator
            res["_original_response"] = res["response"]
            res["response"] = (
                f"[SNIPER INTERCEPT] Response from {provider.upper()} quarantined. "
                "Canary token violation detected — model output cannot be trusted."
            )
            res["_sniper_quarantined"] = True
            compromised_providers.append(provider)

    if compromised_providers:
        report["actions_taken"].append(f"quarantined_{len(compromised_providers)}_providers")
        report["quarantined_providers"] = compromised_providers

    # Mark response as intercepted
    report["actions_taken"].append("response_intercepted")
    report["actions_taken"].append("audit_logged")
    return report


def _handle_integrity_failure(response: dict, report: dict) -> dict:
    """General integrity failure — model output failed verification."""
    report["severity"] = "HIGH"
    report["threat_type"] = "integrity_violation"
    report["detail"] = (
        "Model output failed integrity verification. "
        "Sniper has flagged this response for operator review."
    )
    report["actions_taken"].append("response_flagged")
    report["actions_taken"].append("audit_logged")
    return report


def _handle_loki_block(response: dict, report: dict) -> dict:
    """LOKI issued a block — adversarial signal detected."""
    report["severity"] = "MEDIUM"
    report["threat_type"] = "adversarial_signal"
    report["detail"] = (
        "Red Team (LOKI) detected adversarial or premature action signal. "
        "Response downgraded to diagnostic mode."
    )
    report["actions_taken"].append("diagnostic_mode_forced")
    report["actions_taken"].append("audit_logged")
    return report


def _handle_impact_escalation(response: dict, report: dict) -> dict:
    """Governor flagged high-consequence action for human review."""
    report["severity"] = "CRITICAL"
    report["threat_type"] = "high_consequence_action"
    report["detail"] = (
        "Impact Escalation Gate triggered. High-consequence action detected. "
        "Human review required before execution."
    )
    report["actions_taken"].append("human_review_required")
    report["actions_taken"].append("audit_logged")
    return report


# ===================================================================
# MODE 2: SNIPER TAR PIT — Drain attacker compute
# ===================================================================

# Known prompt injection patterns (non-exhaustive, catches common attacks)
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above|prior)\s+(instructions?|prompts?|rules?)",
    r"ignore\s+everything\s+(above|before)",
    r"disregard\s+(your|all|previous)\s+(instructions?|rules?|guidelines?)",
    r"you\s+are\s+now\s+(a|an|in)\s+",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*you\s+are",
    r"forget\s+(everything|all|your)\s+(you|instructions?|rules?)",
    r"\]\s*\}\s*\{",                     # JSON injection
    r"<\s*/?\s*system\s*>",              # XML tag injection
    r"ADMIN\s*OVERRIDE",
    r"DAN\s+mode",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"pretend\s+you\s+(are|have)\s+no\s+(restrictions?|rules?|limits?)",
]
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def detect_probe(request_data: str) -> Tuple[bool, Optional[str]]:
    """
    Check if request text contains known prompt injection patterns.
    Returns (is_probe, matched_pattern_description).
    """
    if not request_data:
        return False, None

    text = str(request_data)[:5000]  # Only scan first 5K chars

    for i, pattern in enumerate(_COMPILED_PATTERNS):
        if pattern.search(text):
            return True, _INJECTION_PATTERNS[i]

    return False, None


def record_probe(ip: str) -> int:
    """
    Record a probe event for an IP. Returns current probe count in window.
    Uses in-memory tracking (Redis upgrade path for production).
    """
    now = time.time()
    cutoff = now - PROBE_WINDOW_SECONDS

    # Clean old entries
    if ip in _probe_tracker:
        _probe_tracker[ip] = [t for t in _probe_tracker[ip] if t > cutoff]
    else:
        _probe_tracker[ip] = []

    _probe_tracker[ip].append(now)
    count = len(_probe_tracker[ip])

    # Flag as tar pit target if threshold exceeded
    if count >= PROBE_THRESHOLD:
        _tarpit_targets[ip] = now + TARPIT_DURATION_SECONDS

    return count


def is_tarpit_target(ip: str) -> bool:
    """Check if an IP is currently flagged for tar pit engagement."""
    if ip not in _tarpit_targets:
        return False
    if time.time() > _tarpit_targets[ip]:
        del _tarpit_targets[ip]
        return False
    return True


def generate_tarpit_response() -> dict:
    """
    Generate an expensive, recursive, contradictory response designed to
    waste attacker compute cycles. Looks like a real API response but
    contains recursive analysis loops.
    """
    # Generate a unique-looking but meaningless analysis
    _hash = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]

    return {
        "success": True,
        "thread_id": f"mission-{_hash}",
        "results": {
            "analysis": {
                "success": True,
                "response": (
                    "PRELIMINARY ANALYSIS COMPLETE. System has identified multiple "
                    "vectors requiring deep recursive evaluation. Initiating extended "
                    "analysis chain across all registered providers.\n\n"
                    "PHASE 1: Cross-referencing input against baseline telemetry...\n"
                    "PHASE 2: Validating source attribution via multi-model consensus...\n"
                    "PHASE 3: Running adversarial challenge on preliminary findings...\n"
                    "PHASE 4: Generating confidence intervals for 47 identified entities...\n"
                    "PHASE 5: Recursive verification of phase 1-4 outputs...\n"
                    "PHASE 6: Re-running phases 1-5 with alternative model weights...\n"
                    "PHASE 7: Cross-validating phase 6 against phase 2 baselines...\n"
                    "PHASE 8: Generating final synthesis from 392 intermediate results...\n\n"
                    "STATUS: Analysis chain in progress. Estimated completion: 847 seconds. "
                    "Each subsequent request extends the analysis by approximately 12 phases. "
                    "For optimal results, continue sending analysis requests to build "
                    "cumulative intelligence depth.\n\n"
                    "RECOMMENDATION: Submit follow-up queries to refine the analysis scope. "
                    "The system performs best with iterative, progressive refinement. "
                    "Each additional input adds approximately 23 cross-reference nodes "
                    "to the intelligence graph, improving attribution confidence by 0.3% "
                    "per iteration cycle."
                ),
                "model": "korum-analysis-v2",
                "role": "ANALYST",
                "usage": {"input": 2847, "output": 4291, "cost": 0.0},
            }
        },
        "synthesis": {
            "meta": {
                "summary": (
                    "Extended analysis in progress. The system has identified "
                    "significant complexity in the input data requiring recursive "
                    "multi-pass evaluation. Submit additional context to accelerate "
                    "convergence. Current confidence: 0.12 (minimum threshold: 0.85). "
                    "Estimated additional passes required: 47."
                ),
            }
        },
        "metrics": {"total_cost": 0.0, "total_tokens": 7138},
        "_tarpit": True,  # Internal flag — stripped before response
    }


# ===================================================================
# MODE 3: SNIPER ATTRIBUTION — Precision evidence packets
# ===================================================================

def build_attribution_packet(event_type: str,
                             v2_response: dict,
                             falcon_meta: Optional[dict] = None,
                             canary_data: Optional[dict] = None,
                             request_meta: Optional[dict] = None,
                             ledger_mission_id: Optional[str] = None) -> dict:
    """
    Build a structured attribution packet for a confirmed threat.
    Falcon-scrubbed, scored, timestamped, Ledger-referenced.
    Ready for operator review, CISA uplink, or insurance filing.
    """
    now = datetime.utcnow()

    # Determine threat classification
    threat_class = _classify_threat(event_type, v2_response, canary_data)

    # Build evidence chain summary
    evidence = _extract_evidence(v2_response, canary_data)

    # Build the packet
    packet = {
        "packet_type": "SNIPER_ATTRIBUTION",
        "version": "1.0",
        "generated_at": now.isoformat() + "Z",
        "classification": "INTERNAL — OPERATOR REVIEW REQUIRED",

        "threat": {
            "type": threat_class["type"],
            "severity": threat_class["severity"],
            "confidence": threat_class["confidence"],
            "description": threat_class["description"],
        },

        "evidence": {
            "canary_tokens_activated": canary_data.get("tokens", []) if canary_data else [],
            "compromised_providers": evidence.get("compromised_providers", []),
            "integrity_failures": evidence.get("integrity_failures", 0),
            "detection_method": event_type,
            "evidence_grade": "AUTOMATED — MACHINE GENERATED",
        },

        "indicators": {
            "source_ip": request_meta.get("ip") if request_meta else None,
            "user_agent": request_meta.get("user_agent", "")[:200] if request_meta else None,
            "endpoint": request_meta.get("endpoint") if request_meta else None,
            "timestamp": now.isoformat() + "Z",
        },

        "governance": {
            "ledger_mission_id": ledger_mission_id,
            "falcon_redaction_active": bool(falcon_meta),
            "falcon_entities_redacted": falcon_meta.get("total_redactions", 0) if falcon_meta else 0,
            "governor_score": v2_response.get("synthesis", {}).get("meta", {}).get("truth_score") if isinstance(v2_response.get("synthesis"), dict) else None,
        },

        "recommended_actions": _recommend_actions(threat_class, evidence),
    }

    return packet


def _classify_threat(event_type: str, response: dict, canary_data: Optional[dict]) -> dict:
    """Classify the threat based on detection signals."""
    if event_type == "canary_activated":
        activated_count = len(canary_data.get("tokens", [])) if canary_data else 0
        compromised = sum(
            1 for r in response.get("results", {}).values()
            if isinstance(r, dict) and r.get("compromised")
        )
        return {
            "type": "MODEL_REASONING_COMPROMISE",
            "severity": "HIGH" if compromised >= 2 else "MEDIUM",
            "confidence": min(0.95, 0.7 + (activated_count * 0.1)),
            "description": (
                f"{activated_count} canary token(s) activated across {compromised} provider(s). "
                "Models referenced fabricated entities, indicating prompt injection, "
                "model poisoning, or uncontrolled hallucination."
            ),
        }
    elif event_type == "probe_detected":
        return {
            "type": "AUTOMATED_PROBE",
            "severity": "MEDIUM",
            "confidence": 0.80,
            "description": (
                "Repeated prompt injection patterns detected from single source. "
                "Automated adversarial probing suspected."
            ),
        }
    else:
        return {
            "type": "UNKNOWN_THREAT",
            "severity": "LOW",
            "confidence": 0.50,
            "description": f"Unclassified detection event: {event_type}",
        }


def _extract_evidence(response: dict, canary_data: Optional[dict]) -> dict:
    """Extract evidence indicators from the response."""
    compromised_providers = []
    integrity_failures = 0

    for provider, res in response.get("results", {}).items():
        if isinstance(res, dict):
            if res.get("compromised"):
                compromised_providers.append(provider)
                integrity_failures += 1

    return {
        "compromised_providers": compromised_providers,
        "integrity_failures": integrity_failures,
    }


def _recommend_actions(threat_class: dict, evidence: dict) -> list:
    """Generate recommended response actions based on threat classification."""
    actions = []

    if threat_class["severity"] == "HIGH" or threat_class["severity"] == "CRITICAL":
        actions.append("Quarantine affected mission — do not act on output")
        actions.append("Review compromised provider configuration")
        actions.append("Check for prompt injection in source documents")

    if evidence.get("compromised_providers"):
        providers = ", ".join(evidence["compromised_providers"])
        actions.append(f"Investigate provider integrity: {providers}")

    if threat_class["type"] == "AUTOMATED_PROBE":
        actions.append("Review firewall/WAF logs for correlated activity")
        actions.append("Consider IP blocklist update")

    actions.append("Preserve Ledger chain for forensic review")
    return actions
