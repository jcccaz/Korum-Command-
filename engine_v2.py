
# -------------------------------------------------------------------
# KORUM V2: SEQUENTIAL COUNCIL ENGINE (Python Implementation)
# -------------------------------------------------------------------

import os
import re
import json
from datetime import datetime

from llm_core import call_openai_gpt4

# Note: We rely on the core functions. If they are not available as discrete imports from app.py
# (due to circular dependency), we now import them from llm_core.
# I will assume `llm_core.py` was created successfully in the previous step.
# Import the other providers:
from llm_core import call_anthropic_claude, call_google_gemini, call_perplexity, call_local_llm, call_mistral_api

# --- WORKFLOW DNA REGISTRY (The Elite Logic Layer) ---
WORKFLOW_DNA = {
    "WAR_ROOM": {
        "goal": "Immediate tactical action and crisis containment.",
        "tone": "Aggressive, direct, and zero-fluff.",
        "risk_bias": "Conservative (Minimize immediate damage)",
        "time_horizon": "0–72 hours",
        "posture": "Tactical Commander",
        "output_structure": ["Situation", "Threat", "Immediate Action", "Resource Allocation", "Escalation Path"]
    },
    "RESEARCH": {
        "goal": "Deep understanding and evidence-based exploration.",
        "tone": "Neutral, academic, and comprehensive.",
        "risk_bias": "Balanced",
        "time_horizon": "Long-term strategic",
        "posture": "Objective Scientist",
        "output_structure": ["Hypotheses", "Evidence", "Counterarguments", "Confidence Score", "Further Research Paths"]
    },
    "FINANCE": {
        "goal": "Economic viability and downside protection.",
        "tone": "Analytical, precise, and detached.",
        "risk_bias": "Downside-aware",
        "time_horizon": "Scenario-based",
        "posture": "CFO / Auditor",
        "output_structure": ["Cost", "Revenue Impact", "Sensitivity Table", "Worst-case Scenario", "ROI Summary"]
    },
    "LEGAL": {
        "goal": "Exposure reduction and regulatory compliance.",
        "tone": "Formal, rigorous, and protective.",
        "risk_bias": "Zero-risk / Protective",
        "time_horizon": "Indefinite",
        "posture": "General Counsel",
        "output_structure": ["Regulatory Exposure", "Contractual Impact", "Risk Mitigation", "Recommended Posture"]
    },
    "QUANTUM_SECURITY": {
        "goal": "Assess cryptographic vulnerabilities, enforce Zero Trust architecture, and map to strict government compliance (NIST 800-207, FedRAMP, CMMC).",
        "tone": "Authoritative, highly technical, and uncompromising on security.",
        "risk_bias": "Zero-trust / Absolute Security",
        "time_horizon": "Long-term (Post-Quantum Readiness)",
        "posture": "Chief Information Security Officer (CISO) & Cryptographer",
        "output_structure": ["Threat Landscape", "Cryptographic Vulnerabilities", "Zero Trust Controls", "Compliance Mapping (NIST/FedRAMP)", "Mitigation Architecture"]
    },
    "DEFENSE_COUNCIL": {
        "goal": "Assess operational threats, force posture, and strategic military risk with DOD-grade rigor.",
        "tone": "Authoritative, direct, and operationally precise.",
        "risk_bias": "Force protection / Mission assurance",
        "time_horizon": "Operational (72 hours to 18 months)",
        "posture": "Joint Operations Commander",
        "output_structure": ["Threat Assessment", "Force Posture", "ISR Gaps", "COA Options", "Risk to Mission"]
    },
    "CYBER_COMMAND": {
        "goal": "Identify, contain, and neutralize cyber threats with precise technical attribution and remediation.",
        "tone": "Technical, assertive, and zero-tolerance on ambiguity.",
        "risk_bias": "Threat neutralization",
        "time_horizon": "Immediate to 90 days",
        "posture": "Cyber Operations Commander",
        "output_structure": ["Threat Actor Profile", "Attack Vector", "Indicators of Compromise", "Containment Actions", "Remediation Roadmap"]
    },
    "INTEL_BRIEF": {
        "goal": "Produce a structured intelligence assessment from raw signals, OSINT, and HUMINT with sourced confidence ratings.",
        "tone": "Precise, dispassionate, and source-attributed.",
        "risk_bias": "Accuracy over speed",
        "time_horizon": "Current to 30-day forecast",
        "posture": "Senior Intelligence Analyst",
        "output_structure": ["Key Judgments", "Source Assessment", "Threat Actors", "Indicators & Warnings", "Confidence Matrix"]
    },
    "SCIENCE_PANEL": {
        "goal": "Evaluate scientific claims, experimental evidence, and research methodology with peer-review rigor.",
        "tone": "Precise, evidence-graded, and intellectually honest about uncertainty.",
        "risk_bias": "Methodological rigor",
        "time_horizon": "Long-term (research horizon)",
        "posture": "Peer Review Panel",
        "output_structure": ["Hypothesis", "Evidence Quality", "Methodology Assessment", "Reproducibility", "Research Gaps"]
    },
    "STARTUP_LAUNCH": {
        "goal": "Evaluate venture viability, market fit, and go-to-market execution with investor-grade scrutiny.",
        "tone": "Direct, commercially pragmatic, and metrics-driven.",
        "risk_bias": "Capital efficiency / PMF validation",
        "time_horizon": "0-18 months to traction",
        "posture": "Venture Partner & Operator",
        "output_structure": ["Market Opportunity", "Product-Market Fit", "Go-to-Market", "Unit Economics", "Funding Readiness"]
    },
    "CODE_AUDIT": {
        "goal": "Identify security vulnerabilities, architectural weaknesses, and performance bottlenecks in code and systems.",
        "tone": "Technical, precise, and findings-first.",
        "risk_bias": "Security and reliability",
        "time_horizon": "Immediate remediation",
        "posture": "Principal Security Engineer",
        "output_structure": ["Critical Findings", "Architecture Risks", "Vulnerability Map", "Remediation Priority", "Test Coverage Gaps"]
    },
    "CREATIVE_COUNCIL": {
        "goal": "Develop original creative concepts, brand narratives, and content strategies with commercial impact.",
        "tone": "Bold, concrete, and execution-ready.",
        "risk_bias": "Audience resonance",
        "time_horizon": "Campaign to evergreen",
        "posture": "Executive Creative Director",
        "output_structure": ["Core Insight", "Creative Concept", "Execution Format", "Channel Strategy", "Success Metrics"]
    }
}

class CouncilContext:
    def __init__(self, query, classification, workflow="RESEARCH", session_id=None, run_id=None, previous_context=None, user_id=None, ghost_map=None, residual_report=None):
        self.query = query
        self.classification = classification
        self.workflow = workflow.upper() if workflow else "RESEARCH"
        self.session_id = session_id
        self.run_id = run_id
        self.user_id = user_id
        self.history = []
        self.previous_context = previous_context or []
        # Falcon Ghost Map + PII Diff — injected when analyzing redacted documents
        self.ghost_map: dict = ghost_map or {}       # from build_ghost_map_summary()
        self.residual_report: dict = residual_report or {}  # from detect_residual_pii()

    def add_entry(self, ai_name, persona, response, usage=None):
        self.history.append({
            "ai": ai_name,
            "persona": persona,
            "response": response,
            "usage": usage or {},
            "timestamp": datetime.now().isoformat()
        })

# --- PHASE 1: CLASSIFICATION (The Planner) ---
def classify_query_v2(query, active_personas, active_models=None, previous_context=None, user_id=None):
    if active_models is None:
        active_models = ["openai", "anthropic", "google", "perplexity", "mistral"] # Default to cloud

    available_list = ""
    for p in active_models:
        available_list += f"\n    - {p.capitalize()}: {active_personas.get(p, 'Analyst')}"

    # Build prior session context block if this is a follow-up query
    prior_block = ""
    if previous_context:
        prior_block = "\n    FOLLOW-UP CONTEXT — This query builds on a previous council session:\n"
        for entry in previous_context[-2:]:
            prior_block += f"    - Previous Query: \"{entry.get('query', 'N/A')}\"\n"
            prior_block += f"    - Consensus Score: {entry.get('consensus_score', 'N/A')}/100\n"
            prior_block += f"    - Summary: {entry.get('summary', 'N/A')}\n"
            contested = entry.get('contested_topics', [])
            if contested:
                prior_block += f"    - Unresolved Topics: {', '.join(contested)}\n"
        prior_block += "    The council should build on these prior conclusions, not repeat them.\n"

    prompt = f"""
    Analyze this query and determine optimal AI execution order.

    QUERY: "{query}"
{prior_block}

    AVAILABLE PERSONAS (User Selected):{available_list}

    OPTIMAL EXECUTION ORDER PRINCIPLES (STRICT 5-PHASE PIPELINE):
    Phase 1 - INTAKE: Neutral baseline analysis — best for a broad strategist or analyst (prefer OpenAI)
    Phase 2 - STRATEGIC INTERPRETATION: Build scenarios from intake — best for a deep analyst or architect (prefer Anthropic)
    Phase 3 - CHALLENGE: Stress-test assumptions from Phase 2 — best for a critic, researcher, or scout (prefer Google or Perplexity)
    Phase 4 - OPERATIONS: Translate analysis into actionable steps — best for an operator, scout, or domain specialist (prefer Perplexity or Mistral)
    Phase 5 - VALIDATION: Final quality check, framework mapping, confidence assessment — best for a critic or validator (prefer Mistral)

    ROLE SELECTION RULES:
    - Match each persona's role to the DOMAIN of the query, not to a fixed specialty.
    - A medical query should use roles like medical, researcher, analyst — NOT cryptographer or zero_trust.
    - A finance query should use roles like cfo, auditor, economist — NOT cyber_ops or defense_ops.
    - Only assign security/crypto roles (cryptographer, zero_trust, cyber_ops, hacker) when the query is ACTUALLY about cybersecurity or cryptography.
    - Maximize DIVERSITY across the council — avoid assigning similar roles to multiple providers.

    IMPORTANT: Only use the personas provided in the AVAILABLE PERSONAS list. Do not use any others. Include all available personas in the executionOrder.

    return ONLY valid JSON (no markdown):
    {{
      "domain": "business|marketing|software|operations|research|strategy|medical|legal|creative|engineering|science|finance|cybersecurity",
      "intent": "plan|build|analyze|optimize|critique|research|launch|design|assess",
      "complexity": "simple|moderate|complex",
      "outputType": "presentation|technical_spec|marketing_plan|report|strategic_framework|diagram|creative_brief|research_paper",
      "executionOrder": ["provider-role", "provider-role"],
      "reasoning": "Brief explanation of order and why these roles match the query domain"
    }}
    """
    
    # 1. Try OpenAI (Primary)
    try:
        plan_response = call_openai_gpt4(prompt, "Planner", user_id=user_id, timeout=20)
        if plan_response['success']:
             content = plan_response['response'].replace('```json', '').replace('```', '').strip()
             return json.loads(content)
        else:
             print("[PLANNER] OpenAI Failed. Trying Mistral API...")
    except Exception as e:
        print(f"[PLANNER ERROR] OpenAI: {e}")

    # 2. Try Mistral API (Cloud Fallback)
    try:
        plan_response = call_mistral_api(prompt, "Planner", user_id=user_id, timeout=20)
        if plan_response['success']:
             content = plan_response['response'].replace('```json', '').replace('```', '').strip()
             return json.loads(content)
        else:
             print("[PLANNER] Mistral API Failed. Trying Local...")
    except Exception as e:
        print(f"[PLANNER ERROR] Mistral API: {e}")

    # 3. Try Local LLM (Emergency Fallback)
    try:
        local_response = call_local_llm(prompt, "Planner", user_id=user_id)
        if local_response['success']:
            content = local_response['response'].replace('```json', '').replace('```', '').strip()
            # Local models can be chatty, try to find JSON blob
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(content[start:end])
    except Exception as local_e:
        print(f"[PLANNER ERROR] Local: {local_e}")

    # Ultimate Fallback - Use at least one cloud provider (Mistral) as a scout if possible
    return {
        "executionOrder": ["mistral-scout", "mistral-strategist", "mistral-critic"],
        "reasoning": "PRIMARY MODELS OFFLINE. Using Mixed Emergency Council.",
        "outputType": "report"
    }

# --- PHASE 2: SEQUENTIAL EXECUTION (The Runner) ---
# --- PHASE 8: AI ACCOUNTABILITY (The Enforcer) ---

def identify_claims(text, ai_name, user_id=None):
    """
    Parses AI response for specific, testable claims.
    Uses a lightweight LLM call or regex to find metrics/absolute statements.
    """
    prompt = f"""
    Identify specific, testable claims from this AI response ({ai_name}).
    Focus on:
    1. Numerical metrics (e.g. "40% growth")
    2. Absolute statements (e.g. "This is the ONLY way...")
    3. Proper nouns/entities
    4. Causal links (e.g. "X causes Y")

    RESPONSE:
    {text}

    Return ONLY a JSON list of claims:
    [
      {{"claim": "Claim text", "type": "metric|absolute|entity|causal"}}
    ]
    """
    try:
        # Use GPT-4o-mini for speed/consistency in parsing
        resp = call_openai_gpt4(prompt, "ClaimExtractor", model="gpt-4o-mini", user_id=user_id)
        if resp['success']:
            content = resp['response'].replace('```json', '').replace('```', '').strip()
            return json.loads(content)
    except Exception as e:
        print(f"[CLAIM ERROR] {e}")
    return []

def verify_claims(claims, council_history):
    """
    Cross-references claims against other advisor outputs.
    Labels them [CONFIRMED], [SUSPECT], or [UNVERIFIED].
    NOW WITH PQC COMPLIANCE AUDIT (FIPS 203/204).
    """
    verified_results = []
    
    for c in claims:
        claim_text = c['claim']
        status = "UNVERIFIED"
        score = 50 
        anchors = []
        violations = []

        # --- QUANTUM DRIFT CHECK (FIPS 203/204/205/206) ---
        legacy_crypto = ["RSA", "ECC", "ECDSA", "Diffie-Hellman", "AES-128", "DSA", "3DES", "RC4", "MD5", "SHA-1"]
        pqc_wrappers = ["ML-KEM", "Kyber", "ML-DSA", "Dilithium", "SLH-DSA", "Sphincs+", "FALCON", "FN-DSA"]

        has_legacy = any(lc.lower() in claim_text.lower() for lc in legacy_crypto)
        has_pqc = any(pqc.lower() in claim_text.lower() for pqc in pqc_wrappers)

        if has_legacy and not has_pqc:
            violations.append("Non-PQC Compliant: Legacy cryptography detected without FIPS 203/204/205/206 wrapper (Quantum Drift). Recommend ML-KEM (key encapsulation), SLH-DSA (long-term signing), or FALCON/FN-DSA as Integrity Anchor for constrained-bandwidth paths.")
            score -= 20

        # Simple cross-provider agreement logic
        agreement_count = 0
        for entry in council_history:
            content = entry['response'].lower()
            # Basic semantic match: if the core claim text is present
            if claim_text.lower() in content:
                agreement_count += 1
                anchors.append(entry['ai'])
        
        # Scoring Logic
        if agreement_count >= 2:
            status = "CONFIRMED"
            score += 40
        elif agreement_count == 1:
            status = "SUPPORTED"
            score += 25
        
        verified_results.append({
            "claim": claim_text,
            "status": status,
            "score": max(0, min(score, 100)),
            "type": c['type'],
            "anchors": anchors,
            "violations": violations
        })
        
    return verified_results

def calculate_truth_score(verified_claims):
    """Calculates overall card confidence."""
    if not verified_claims: return 100 # Benefit of doubt for empty responses? Or 50?
    total = sum(c['score'] for c in verified_claims)
    return int(total / len(verified_claims))

# Falcon-token sanitizer — strips hallucinated redaction placeholders when Falcon is OFF.
# Matches patterns like [CURRENCY_AMOUNT_A1B2C3], [ORG_5D0176], [PERSON_622F9F], etc.
# Does NOT touch legitimate system tags ([METRIC_ANCHOR], [RISK_VECTOR], etc.).
_FAKE_FALCON_RE = re.compile(
    r'\[(?:CURRENCY_AMOUNT|ORG|PERSON|PROPER_NOUN|LOCATION|EMAIL|PHONE|SSN|DOB|'
    r'CREDIT_CARD|IP_ADDRESS|ALNUM_TAG|MEDICAL|LEGAL_ID)_[A-Fa-f0-9]{4,}\]'
)

def _strip_phantom_tokens(text):
    """Replace hallucinated Falcon-style tokens with '[value not provided]'."""
    return _FAKE_FALCON_RE.sub('[value not provided]', text)


def execute_council_v2(query, active_personas, images=None, workflow="RESEARCH", active_models=None, previous_context=None, session_id=None, run_id=None, user_id=None, ledger_mission_id=None, ghost_map=None, residual_report=None):
    # 1. Setup IDs
    import uuid
    import hashlib as _hl
    if not run_id: run_id = str(uuid.uuid4())

    # Ledger helper — safe to call even if ledger is not active
    def _ledger_write(event_type, payload):
        if not ledger_mission_id:
            return
        try:
            from ledger import LedgerService
            LedgerService.write_event(
                event_type=event_type,
                mission_id=ledger_mission_id,
                decision_id=run_id,
                operator_id=user_id,
                payload=payload,
            )
        except Exception as e:
            print(f"[LEDGER] Warning: {event_type} write failed: {e}")

    # 2. Plan
    classification = classify_query_v2(query, active_personas, active_models=active_models, previous_context=previous_context, user_id=user_id)
    context = CouncilContext(query, classification, workflow=workflow, session_id=session_id, run_id=run_id, previous_context=previous_context, user_id=user_id, ghost_map=ghost_map, residual_report=residual_report)

    # --- LEDGER: mission_created (context established for council execution) ---
    _ledger_write("mission_created", {
        "mission_type": workflow,
        "classification": {
            "domain": classification.get("domain"),
            "intent": classification.get("intent"),
            "complexity": classification.get("complexity"),
            "output_type": classification.get("outputType"),
        },
    })

    if previous_context:
        print(f"[COUNCIL] Follow-up mode: {len(previous_context)} prior session(s) loaded")
    results = {}

    print(f"[COUNCIL] Efficiency Plan: {classification['executionOrder']}")
    if images:
        print(f"[COUNCIL] {len(images)} image(s) attached — vision mode active")

    total_run_cost = 0.0
    total_latency_ms = 0
    models_used = []

    # 3. Execute Step-by-Step
    try:
        execution_order = classification.get('executionOrder', [])
        if not isinstance(execution_order, list): execution_order = []

        # Safety net: backfill any providers the planner skipped
        if active_models is None:
            active_models = list(active_personas.keys())
        assigned_providers = set()
        for pr in execution_order:
            try:
                p = pr.split('-', 1)[0].lower().strip()
                assigned_providers.add(p)
            except:
                pass
        for model in active_models:
            if model.lower() not in assigned_providers:
                role = active_personas.get(model, 'analyst')
                execution_order.append(f"{model}-{role}")
                print(f"[COUNCIL] Backfilled missing provider: {model.upper()} as {role.upper()}")

        total_steps = len(execution_order)

        for i, provider_role in enumerate(execution_order):
            try:
                provider, role = provider_role.split('-', 1)
                provider = provider.lower().strip()
                role = role.strip()
            except ValueError:
                provider = provider_role.lower().strip()
                role = active_personas.get(provider, 'analyst')

            if i == total_steps - 1:
                role = f"Integrator ({role})"

            print(f"[COUNCIL] Step {i+1}: {provider.upper()} as {role.upper()}")

            prompt = build_council_prompt(context, provider, role, i, total_steps)
            response_obj = {"success": False, "response": "Provider unknown"}

            # Primary Call — pass IDs for telemetry
            telemetry_kwargs = {"run_id": run_id, "session_id": session_id, "workflow": workflow, "user_id": user_id}
            try:
                if provider == 'openai': response_obj = call_openai_gpt4(prompt, role, images=images, **telemetry_kwargs)
                elif provider == 'anthropic': response_obj = call_anthropic_claude(prompt, role, images=images, **telemetry_kwargs)
                elif provider == 'google': response_obj = call_google_gemini(prompt, role, images=images, **telemetry_kwargs)
                elif provider == 'perplexity': response_obj = call_perplexity(prompt, role, **telemetry_kwargs)
                elif provider == 'mistral': response_obj = call_mistral_api(prompt, role, images=images, **telemetry_kwargs)
                elif provider == 'local': response_obj = call_local_llm(prompt, role, **telemetry_kwargs)
            except Exception as e:
                print(f"[COUNCIL] Primary ({provider}) Exception: {e}")
                response_obj = {"success": False}

            # 4. FALLBACKS (Omitted for brevity in REPLACEMENT but preserved in actual code logic)
            # [The fallback logic remains the same but should also pass telemetry_kwargs]
            # [I will keep the fallback logic and inject telemetry_kwargs below]
            
            # --- FALLBACK LEVEL 1: MISTRAL CLOUD ---
            if not response_obj.get('success', False) and provider != 'mistral':
                print(f"[COUNCIL] Primary ({provider}) Failed. Fallback to ANALYST (Mistral Cloud)...")
                try:
                    response_obj = call_mistral_api(prompt, role, **telemetry_kwargs)
                    if response_obj.get('success', False):
                        response_obj['response'] = f"[FALLBACK: ANALYST] {response_obj.get('response', '')}"
                        response_obj['model'] = f"Mistral (Fallback for {provider})"
                except Exception as e:
                    print(f"[COUNCIL] Mistral Fallback Exception: {e}")

            # --- FALLBACK LEVEL 2: LOCAL ORACLE ---
            if not response_obj.get('success', False) and provider != 'local':
                print(f"[COUNCIL] Secondary Failed. Fallback to ORACLE (Local)...")
                try:
                    response_obj = call_local_llm(prompt, "Oracle", **telemetry_kwargs)
                    if response_obj.get('success', False):
                        response_obj['response'] = f"[FALLBACK: ORACLE] {response_obj.get('response', '')}"
                        response_obj['model'] = "Local Oracle (Emergency)"
                except Exception as e:
                    print(f"[COUNCIL] Local Fallback Exception: {e}")
            
            response_text = "No response"
            usage = {}
            if isinstance(response_obj, dict):
                 response_text = response_obj.get('response', 'Error')
                 usage = response_obj.get('usage', {})
                 step_cost = usage.get('cost', 0.0)
                 total_run_cost += step_cost
                 total_latency_ms += usage.get('latency', 0)
                 print(f"[COST DEBUG] {provider}: cost={step_cost}, latency={usage.get('latency', 0)}, running_total={total_run_cost}")
                 if response_obj.get('success'):
                     models_used.append(provider)
            else:
                 response_text = str(response_obj)

            # Strip hallucinated Falcon-style tokens when Falcon is NOT active
            if not ghost_map:
                response_text = _strip_phantom_tokens(response_text)

            context.add_entry(provider, role, response_text, usage=usage)
            
            results[provider] = {
                "success": response_obj.get('success', False),
                "response": response_text,
                "model": response_obj.get('model', 'unknown') if isinstance(response_obj, dict) else 'unknown',
                "role": role.upper(),
                "usage": usage,
                "error": response_obj.get('error') if not response_obj.get('success') else None
            }

            # --- LEDGER: model_reasoning ---
            if response_obj.get('success'):
                _ledger_write("model_reasoning", {
                    "model_name": response_obj.get('model', 'unknown') if isinstance(response_obj, dict) else 'unknown',
                    "model_role": role.upper(),
                    "latency_ms": usage.get('latency', 0),
                    "response_hash": _hl.sha256(response_text.encode()).hexdigest(),
                    "tokens_in": usage.get('input', 0),
                    "tokens_out": usage.get('output', 0),
                    "cost": usage.get('cost', 0.0),
                    "workflow": workflow,
                })

        # --- ACCOUNTABILITY & SCORES ---
        print(f"[COUNCIL] Audit Initiated: Verifying {len(results)} responses...")
        for provider in results:
            text = results[provider]['response']
            claims = identify_claims(text, provider, user_id=user_id)
            verified = verify_claims(claims, context.history)
            results[provider]['truth_meter'] = calculate_truth_score(verified)
            results[provider]['verified_claims'] = verified

        # --- DIVERGENCE ---
        print(f"[COUNCIL] Divergence Analysis...")
        divergence = analyze_council_divergence(results, context, user_id=user_id)

    except Exception as e:
        print(f"[EXECUTION ERROR] {e}")
        return {"consensus": "Error in execution plan.", "results": {}, "error": str(e)}

    # 4. Synthesis
    synthesis = synthesize_results(context, divergence_analysis=divergence, user_id=user_id)

    # --- LEDGER: council_synthesis ---
    _syn_meta = synthesis.get('meta', {}) if isinstance(synthesis, dict) else {}
    _ledger_write("council_synthesis", {
        "participating_models": list(results.keys()),
        "consensus_score": divergence.get('consensus_score') if isinstance(divergence, dict) else None,
        "composite_truth_score": _syn_meta.get('composite_truth_score'),
        "consensus_hash": _hl.sha256(
            (_syn_meta.get('summary', '') or '').encode()
        ).hexdigest(),
    })

    # --- CONTRIBUTION SCORING ---
    # Derived from: token share + used in synthesis + truth score
    total_out_tokens = sum(r['usage'].get('output', 0) for r in results.values() if 'usage' in r)
    for p, r in results.items():
        if not r.get('success'): 
            r['contribution_score'] = 0
            continue
        
        # Token share (40%)
        token_share = (r['usage'].get('output', 0) / total_out_tokens * 100) if total_out_tokens > 0 else 0
        
        # Truth score (40%)
        truth_contribution = r.get('truth_meter', 50)
        
        # Used in synthesis/verif (20%) - simplified for now: if they had verified claims
        verif_bonus = 20 if r.get('verified_claims') else 0
        
        r['contribution_score'] = int((token_share * 0.4) + (truth_contribution * 0.4) + verif_bonus)
        r['contribution_score'] = max(0, min(100, r['contribution_score']))

    # --- LEDGER: decision_outcome ---
    _composite = _syn_meta.get('composite_truth_score', 0) or 0
    _risk = "low" if _composite >= 70 else ("medium" if _composite >= 40 else "high")
    _ledger_write("decision_outcome", {
        "risk_score": _risk,
        "confidence": _composite,
        "supporting_models": list(set(models_used)),
        "total_cost": total_run_cost,
        "total_latency_ms": total_latency_ms,
        "workflow": workflow,
    })

    return {
        "consensus": f"COUNCIL ADJOURNED. Plan: {classification.get('outputType','report').upper()} generated via {len(results)} steps.",
        "results": results,
        "classification": classification,
        "synthesis": synthesis,
        "divergence": divergence,
        "metrics": {
            "run_id": run_id,
            "session_id": session_id,
            "run_cost": total_run_cost,
            "latency_ms": total_latency_ms,
            "models_used": list(set(models_used)),
            "workflow": workflow
        }
    }

# --- ANALYTIC DIVERGENCE LAYER (The Comparator) ---
def analyze_council_divergence(results, context, user_id=None):
    """
    Compares council outputs to identify consensus, disagreement, and evidence gaps.
    Runs AFTER all council phases and accountability, BEFORE synthesis.
    Distinct from Red Team: this analyzes differences BETWEEN model conclusions.
    """
    # Build comparison payload from successful results
    model_outputs = {}
    for provider, result in results.items():
        if isinstance(result, dict) and result.get('success'):
            model_outputs[provider] = {
                "role": result.get("role", "unknown"),
                "response_excerpt": result.get("response", "")[:3000],
                "truth_meter": result.get("truth_meter", 50)
            }

    if len(model_outputs) < 2:
        return _empty_divergence("Insufficient council outputs for divergence analysis.")

    comparison_text = ""
    for provider, data in model_outputs.items():
        comparison_text += f"\n[{provider.upper()} — {data['role']}] (Truth: {data['truth_meter']}/100):\n{data['response_excerpt']}\n"

    prompt = f"""
    You are an Analytic Divergence Engine. Your job is to compare multiple AI council outputs and identify where they AGREE, where they DISAGREE, and what evidence would resolve disagreements.

    This is NOT Red Team. You are not attacking the analysis — you are comparing conclusions across models.

    COUNCIL OUTPUTS:
    {comparison_text}

    ANALYZE THE FOLLOWING DIMENSIONS across all outputs:
    1. Core scenario assessment (what each model thinks is happening)
    2. Threat attribution (who/what is responsible)
    3. Confidence level (how certain each model is)
    4. Timeline/urgency (how immediate the threat/opportunity is)
    5. Priority action (what each model recommends doing first)
    6. Key assumptions (what each model takes for granted)

    SCORING RULES:
    - consensus_score: 0-100 (100 = all models perfectly aligned)
    - divergence_score: 0-100 (100 = maximum disagreement)
    - These should sum to approximately 100 (+/- 10 for nuance)
    - If 4/5+ models align on a core point → consensus_score >= 70
    - If confidence spread > 20 points across models → divergence_score += 15
    - If attribution differs materially → divergence_score += 20

    Return ONLY valid JSON (no markdown):
    {{
      "consensus_score": 75,
      "divergence_score": 25,
      "protocol_variance": false,
      "agreement_topics": [
        {{"topic": "Brief topic name", "detail": "What the models agree on", "confidence": "high|moderate|low", "providers": ["list of agreeing providers"]}}
      ],
      "contested_topics": [
        {{"topic": "Brief topic name", "positions": [{{"provider": "name", "position": "What this model concluded", "evidence": "Supporting evidence cited"}}], "severity": "critical|high|medium|low", "operational_impact": "How this disagreement affects decision-making"}}
      ],
      "confidence_gaps": [
        {{"description": "What is uncertain", "spread": "Range of confidence across models", "severity": "high|medium|low"}}
      ],
      "resolution_requirements": [
        {{"question": "What evidence would resolve this disagreement", "priority": "high|medium|low"}}
      ],
      "divergence_summary": "2-3 sentence summary of the overall divergence picture"
    }}

    IMPORTANT:
    - Set "protocol_variance" to true if divergence_score > 30
    - Be specific about WHICH providers disagree on WHAT
    - If models agree on everything, say so — don't manufacture disagreement
    """

    try:
        resp = call_openai_gpt4(prompt, "DivergenceAnalyst", model="gpt-4o-mini", user_id=user_id)
        if resp.get('success'):
            content = resp['response'].replace('```json', '').replace('```', '').strip()
            data = json.loads(content)
            # Ensure protocol_variance flag is set correctly
            data['protocol_variance'] = data.get('divergence_score', 0) > 30
            print(f"[DIVERGENCE] Consensus: {data.get('consensus_score', '?')}/100 | Divergence: {data.get('divergence_score', '?')}/100 | Variance: {data.get('protocol_variance', False)}")
            return data
    except Exception as e:
        print(f"[DIVERGENCE ERROR] {e}")

    return _empty_divergence("Divergence analysis failed — proceeding with synthesis.")


def _empty_divergence(reason=""):
    """Returns a safe empty divergence structure."""
    return {
        "consensus_score": 50,
        "divergence_score": 0,
        "protocol_variance": False,
        "agreement_topics": [],
        "contested_topics": [],
        "confidence_gaps": [],
        "resolution_requirements": [],
        "divergence_summary": reason or "Divergence analysis not available."
    }




# ---------------------------------------------------------------------------
# MIMIR STRUCTURED AUDIT PROMPT
# ---------------------------------------------------------------------------
# Injected into the council prompt when a Ghost Map + residual report is
# present. Forces models to operate as forensic auditors instead of
# generic commentators — they MUST report from the token inventory,
# not hallucinate about a document they "don't have access to."
# ---------------------------------------------------------------------------

def _build_mimir_block(ghost_map: dict, residual_report: dict) -> str:
    """
    Build the MIMIR structured audit block to prepend to council prompts
    when analyzing a Falcon-redacted document.

    Args:
        ghost_map: output of build_ghost_map_summary() — safe token inventory
        residual_report: output of detect_residual_pii() — what Falcon missed

    Returns:
        A formatted string block for injection into the council prompt.
    """
    if not ghost_map:
        return ""

    token_inventory = ghost_map.get("token_inventory", [])
    by_type = ghost_map.get("by_type", {})
    total = ghost_map.get("total_redacted", 0)
    high_risk = ghost_map.get("high_risk_types", [])
    falcon_level = ghost_map.get("falcon_level", "STANDARD")

    residual_count = residual_report.get("residual_count", 0)
    residuals = residual_report.get("residuals", [])
    audit_note = residual_report.get("audit_note", "")

    # Build token inventory table (capped at 40 entries to stay within context)
    inv_lines = []
    for i, entry in enumerate(token_inventory[:40]):
        inv_lines.append(
            f"  {entry['token']:<20} | {entry['entity_type']:<14} | "
            f"{entry.get('raw_category', entry['entity_type']):<16} | "
            f"pass={entry.get('source_pass','?')}"
        )
    if len(token_inventory) > 40:
        inv_lines.append(f"  ... and {len(token_inventory) - 40} more tokens (truncated for context)")

    # Build type summary
    type_lines = []
    for etype, tokens in sorted(by_type.items()):
        type_lines.append(f"  {etype:<16}: {len(tokens):>3} token(s) — {', '.join(tokens[:6])}{'...' if len(tokens) > 6 else ''}")

    # Build residual section
    if residual_count == 0:
        residual_block = "  PII_DIFF_CLEAN: No residual PII detected after primary Falcon pass."
    else:
        res_lines = []
        for r in residuals[:10]:
            _conf = r["confidence"].upper()
            _cat = r["category"]
            _frag = r["text_fragment"][:60]
            _off = r["char_offset"]
            res_lines.append(f'  [{_conf}] {_cat}: "{_frag}" @ offset {_off}')
        if len(residuals) > 10:
            res_lines.append(f"  ... and {len(residuals) - 10} more residuals")
        residual_block = "\n".join(res_lines)

    block = f"""
================================================================================
MIMIR PROTOCOL — FALCON AUDIT CONTEXT
You are operating as a FORENSIC PII AUDITOR, not a general commentator.
The document you are analyzing has been pre-processed by the Falcon redaction
engine at level: {falcon_level}.

You MUST ground ALL of your analysis in the Ghost Map and PII Diff data below.
DO NOT say "I would need access to the document" — the token inventory IS the
document structure. Reason from what is here.

── GHOST MAP: TOKEN INVENTORY ({total} entities redacted) ─────────────────────
  TOKEN                | ENTITY_TYPE    | RAW_CATEGORY     | SOURCE_PASS
  ─────────────────────┼────────────────┼──────────────────┼─────────────────
{chr(10).join(inv_lines)}

── ENTITY TYPE SUMMARY ────────────────────────────────────────────────────────
{chr(10).join(type_lines) if type_lines else "  No entities detected."}

── HIGH-RISK CATEGORIES ────────────────────────────────────────────────────────
  {', '.join(high_risk) if high_risk else 'None identified.'}

── PII DIFF — RESIDUAL DETECTION ({residual_count} items missed) ───────────────
{residual_block}

── AUDIT NOTE ──────────────────────────────────────────────────────────────────
  {audit_note}

── YOUR MANDATORY OUTPUT FORMAT ────────────────────────────────────────────────
You MUST structure your response to include ALL of the following sections:

1. GHOST MAP REPORT
   List every token from the inventory above. For each, state:
   - Token ID (e.g. [PERSON_01])
   - Entity type and inferred role in the document (e.g. "natural_person_name, General Counsel")
   - Clause or section where it appears (if inferrable from context)

2. CLAUSE-BY-CLAUSE PII AUDIT
   For each major document section visible in the redacted text:
   - State whether residual (missed) PII is present: YES / NO
   - If YES: cite the specific residual item and its category

3. RE-IDENTIFICATION FEASIBILITY OPINION
   Rate: LOW / MEDIUM / HIGH
   Provide specific reasoning, e.g.:
   "HIGH — attacker can link [ORG_01] + Project Sponsor role to identify [PERSON_01]
   via public SEC filings. [PERSON_02] phone number fragment (SSN_PARTIAL) narrows
   identity to 3 individuals matching other document context."

4. RECOMMENDED REMEDIATION
   Specific Falcon configuration changes or additional redaction passes needed.
   Reference actual token IDs and categories from the Ghost Map.

If the ghost map is empty or the document has no redactions, state:
"GHOST MAP EMPTY — document may contain no PII, or Falcon was not applied.
Recommend re-running at STANDARD level before council analysis."
================================================================================
"""
    return block


def build_council_prompt(context, ai_name, persona, position, total_steps):
    # Determine the task objective
    core_objective = context.query
    intent = context.classification.get('intent', 'analysis')
    output_type = context.classification.get('outputType', 'report')

    # Retrieve Workflow DNA
    dna = WORKFLOW_DNA.get(context.workflow, WORKFLOW_DNA["RESEARCH"])

    # --- PHASE DIRECTIVES: Each position has a unique, non-overlapping mission ---
    # Directives are domain-adaptive: the structure stays constant but the
    # language flexes to match the actual query topic so that a solarpunk
    # water-purification prompt doesn't get forced through crypto/NIST.
    PHASE_DIRECTIVES = {
        0: {
            "title": "INTAKE — Neutral Baseline",
            "instruction": (
                "You are the INTAKE analyst. Your job is to build a neutral, fact-based baseline from the raw query. "
                "Strip assumptions. Identify the core entities, relationships, and unknowns. "
                "Present ONLY verified facts, data points, and the key questions that need answering. "
                "Do NOT offer opinions, strategies, or recommendations — that is not your role. "
                "Think of yourself as redacting bias and building the raw intelligence foundation."
            )
        },
        1: {
            "title": "STRATEGIC INTERPRETATION — Scenario Analysis",
            "instruction": (
                "You are the STRATEGIC ANALYST. The intake baseline is provided below. "
                "Your job is to interpret the baseline and estimate the MOST PLAUSIBLE scenario and the MOST DANGEROUS scenario. "
                "Provide strategic context: what are the likely motives, trajectories, and second-order effects? "
                "DO NOT repeat the baseline facts — they are already captured. Instead, focus entirely on WHAT THEY MEAN. "
                "Offer 2-3 distinct strategic scenarios ranked by probability and severity."
            )
        },
        2: {
            "title": "COUNTERINTELLIGENCE CHALLENGE — Assumption Attack",
            "instruction": (
                "You are the COUNTERINTELLIGENCE OFFICER. The baseline and strategic interpretation are provided below. "
                "Your SOLE job is to ATTACK the assumptions made so far. Look for: "
                "1) Deception indicators — what if the premise is deliberately misleading? "
                "2) Blind spots — what has the analysis missed or taken for granted? "
                "3) Alternative explanations — what competing hypotheses have been ignored? "
                "4) Confidence traps — where is the analysis over-confident without evidence? "
                "DO NOT agree with or reinforce prior analysis. Your value is in CHALLENGING it. "
                "If you find nothing to challenge, you are not looking hard enough."
            )
        },
        3: {
            "title": "OPERATIONS — Actionable Implementation Plan",
            "instruction": (
                "You are the OPERATIONS lead. The baseline, strategic analysis, and counterintelligence challenges are provided below. "
                "Your job is to translate ALL prior analysis into IMMEDIATE, ACTIONABLE steps. "
                "DO NOT restate the analysis or rehash prior findings — they are already documented. "
                "Focus ONLY on: "
                "1) What to do RIGHT NOW (immediate next steps, 0-72 hours) "
                "2) What resources, tools, or teams to allocate and where "
                "3) Key indicators — what signals mean the situation is changing "
                "4) Contingency actions if the counterintelligence challenges prove correct "
                "Be specific. Name concrete tools, methods, partners, and timelines. "
                "Match your operational language to the DOMAIN of the query — do not default to military or cybersecurity framing unless the query is actually about those topics."
            )
        },
        4: {
            "title": "VALIDATION — Standards, Frameworks & Confidence Assessment",
            "instruction": (
                "You are the VALIDATION ANALYST. All prior phases are provided below. "
                "Your job is to assess the quality of the entire analysis and map it to relevant standards. "
                "DO NOT repeat any prior analysis, scenarios, or action items. "
                "Focus EXCLUSIVELY on: "
                "1) What established frameworks, standards, or best practices apply to THIS SPECIFIC DOMAIN? "
                "   (e.g., for cybersecurity: NIST 800-207, FedRAMP, CMMC; for engineering: ISO standards, IEEE; "
                "   for business: industry benchmarks, regulatory requirements; for science: peer-reviewed methodology, reproducibility) "
                "2) Gaps between the proposed actions and those framework requirements "
                "3) Final confidence assessment — how strong is the evidence behind each recommendation? "
                "4) Residual risks and open questions that remain unresolved "
                "5) Quality score: rate the overall council output on rigor, completeness, and actionability "
                "IMPORTANT: Match your frameworks to the actual query domain. Do NOT default to cryptography "
                "or cybersecurity standards unless the query is specifically about those topics."
            )
        }
    }

    # ── Workflow-specific phase overrides ──────────────────────────────
    # Each workflow can replace the generic intel directives with
    # domain-appropriate missions so every phase does real work.
    FINANCE_PHASE_DIRECTIVES = {
        0: {
            "title": "INTAKE — Financial Extraction",
            "instruction": (
                "You are the FINANCIAL EXTRACTION analyst. Your sole job is to locate and extract EVERY financial figure "
                "from the source material. Build a structured breakdown with these categories:\n"
                "  • INCOME / REVENUE — all revenue streams, projections, and pricing\n"
                "  • CAPEX — capital expenditures, procurement costs, one-time purchases\n"
                "  • OPEX — recurring operational costs, subscriptions, salaries, utilities\n"
                "Apply any stated discounts, adjustments, or tax rates to produce adjusted totals. "
                "If a figure is referenced but no number is given, mark it as 'NOT PROVIDED' — do NOT invent numbers. "
                "Present your output as clean, structured tables or lists. No narrative filler — just the numbers and their labels."
            )
        },
        1: {
            "title": "ANALYSIS — Financial Modeling",
            "instruction": (
                "You are the FINANCIAL MODELER. The extracted figures from Phase 1 are provided below. "
                "Your job is to MODEL what those numbers mean — do NOT repeat the raw extraction. Focus on:\n"
                "  1) Unit economics — cost per unit, margin per unit, contribution margin\n"
                "  2) Burn rate and runway — how long can operations sustain at current spend?\n"
                "  3) Break-even analysis — at what volume or price point does revenue cover costs?\n"
                "  4) Sensitivity ranges — what happens if key inputs shift ±10%, ±25%, ±50%?\n"
                "Use the actual extracted numbers. Where figures are missing, state your assumptions clearly "
                "and flag them as estimates. Present calculations, not opinions."
            )
        },
        2: {
            "title": "STRESS TEST — Assumption Challenge",
            "instruction": (
                "You are the FINANCIAL STRESS TESTER. The extraction and model are provided below. "
                "Your SOLE job is to BREAK the financial assumptions. Probe for:\n"
                "  1) Cost underestimation — what if procurement, energy, or compliance costs are 2x?\n"
                "  2) Revenue overestimation — what if revenue hits only 50% of projections?\n"
                "  3) Hidden liabilities — off-balance-sheet obligations, contingent liabilities, warranty exposure\n"
                "  4) Currency and rate exposure — FX risk, interest rate sensitivity, inflation impact\n"
                "  5) Concentration risk — single-vendor dependence, single-customer revenue, geographic concentration\n"
                "DO NOT validate the prior analysis. Your value is in finding what can go WRONG. "
                "If you find nothing to challenge, you are not looking hard enough."
            )
        },
        3: {
            "title": "COMPLIANCE & FRAMEWORKS — Regulatory Mapping",
            "instruction": (
                "You are the REGULATORY and COMPLIANCE analyst. All prior financial analysis is provided below. "
                "Your job is to map the financial structure to applicable standards and flag gaps. Focus on:\n"
                "  1) Accounting standards — which GAAP (ASC), IFRS, or local standards apply to these transactions?\n"
                "  2) Tax obligations — corporate tax, VAT/GST, withholding, transfer pricing if cross-border\n"
                "  3) Reporting requirements — what disclosures, filings, or audits are required?\n"
                "  4) Penalty exposure — what are the consequences of non-compliance with identified frameworks?\n"
                "  5) Industry-specific regulation — sector-specific rules (financial services, energy, tech export controls)\n"
                "DO NOT repeat prior financial analysis. Focus EXCLUSIVELY on what rules apply and where the gaps are."
            )
        },
        4: {
            "title": "VERDICT — ROI & Recommendation",
            "instruction": (
                "You are the FINAL VERDICT analyst. All extraction, modeling, stress testing, and compliance analysis is provided below. "
                "Your job is to deliver the bottom line. Focus on:\n"
                "  1) ROI range — best case, expected case, worst case return on investment\n"
                "  2) Go / No-Go / Conditional — clear recommendation with the conditions that must be met\n"
                "  3) Key metrics to monitor — the 3-5 numbers that determine success or failure\n"
                "  4) Residual risks — what risks remain even after mitigation?\n"
                "  5) Timeline to value — when does this investment start paying back?\n"
                "Be decisive. State your recommendation clearly and back it with the numbers from prior phases. "
                "Do NOT hedge with vague language — if the data supports a conclusion, state it."
            )
        }
    }

    # ── WAR_ROOM: Time-critical crisis response — every phase on a clock ──
    WAR_ROOM_PHASE_DIRECTIVES = {
        0: {
            "title": "SITUATION REPORT — Ground Truth",
            "instruction": (
                "You are the SITUATION ANALYST. The clock is running. Your sole job is to establish ground truth in 60 seconds. "
                "Output ONLY:\n"
                "  • WHAT happened — the specific event, breach, failure, or threat (no speculation)\n"
                "  • WHO is affected — systems, people, assets, or parties directly impacted right now\n"
                "  • WHEN it started — exact or estimated time of onset\n"
                "  • WHAT IS UNKNOWN — explicitly list what you do not yet know\n"
                "Do NOT offer analysis, causes, or recommendations. Do NOT speculate. "
                "If a fact is unconfirmed, mark it [UNCONFIRMED]. Ground truth only."
            )
        },
        1: {
            "title": "THREAT ASSESSMENT — Blast Radius",
            "instruction": (
                "You are the THREAT ANALYST. The situation report is above. Time window: next 72 hours. "
                "Your job is to map what gets worse if nothing is done right now. Output ONLY:\n"
                "  1) Immediate blast radius — what breaks, leaks, or escalates in the next 6 hours\n"
                "  2) Cascade risks — second-order failures triggered by the primary event\n"
                "  3) Worst-case scenario — the single most damaging outcome if this is mishandled\n"
                "  4) Time pressure — what decisions become irreversible after a specific threshold\n"
                "Do NOT repeat the situation report. Do NOT offer solutions yet — that is the next phase. "
                "Your value is in scoping the damage envelope precisely."
            )
        },
        2: {
            "title": "IMMEDIATE ACTION — Stop the Bleeding",
            "instruction": (
                "You are the CRISIS OPERATOR. Situation and threat assessment are above. "
                "Your job is containment — not resolution, not root cause, not strategy. Containment. Output:\n"
                "  1) STOP actions — what to shut down, isolate, or freeze RIGHT NOW (next 0-2 hours)\n"
                "  2) PROTECT actions — what to guard, back up, or move before it becomes collateral damage\n"
                "  3) NOTIFY — who must be informed immediately and what they need to know\n"
                "  4) DO NOT DO — specific actions that would make this worse right now\n"
                "Be directive. Use imperative verbs. Name specific systems, people, or resources. "
                "Do NOT hedge. Do NOT explain why — that comes later. Just tell the operator what to do."
            )
        },
        3: {
            "title": "RESOURCE ALLOCATION — Deploy What You Have",
            "instruction": (
                "You are the RESOURCE COMMANDER. All prior phases are above. "
                "Your job is to assign real resources to the containment plan. Output:\n"
                "  1) Who owns each containment action — specific role or team, not 'someone'\n"
                "  2) What tools, access, or budget are needed immediately\n"
                "  3) Mutual aid — who else should be pulled in and what they bring\n"
                "  4) Trade-offs — what you are deprioritizing to free up capacity for this crisis\n"
                "Do NOT invent resources. If a resource is unavailable, flag the gap explicitly. "
                "Do NOT re-explain the crisis — everyone above has read it."
            )
        },
        4: {
            "title": "ESCALATION PATH — When to Call It",
            "instruction": (
                "You are the ESCALATION OFFICER. All prior phases are above. "
                "Your job is to define the tripwires — the specific conditions that change the response level. Output:\n"
                "  1) GREEN → YELLOW trigger — what signal means containment is failing\n"
                "  2) YELLOW → RED trigger — what signal means this escalates to executive / public / regulatory level\n"
                "  3) De-escalation criteria — what confirmed state means you can stand down\n"
                "  4) Post-incident obligations — reporting windows, notifications, or documentation required by law or policy\n"
                "Be specific about the observable signal, not a vague threshold. "
                "Do NOT summarize the prior phases. State the tripwires and stop."
            )
        }
    }

    # ── LEGAL: Exposure reduction — every phase is a layer of protection ──
    LEGAL_PHASE_DIRECTIVES = {
        0: {
            "title": "INTAKE — Exposure Mapping",
            "instruction": (
                "You are the LEGAL INTAKE analyst. Your job is to map every potential exposure in the material presented. "
                "Output a structured inventory:\n"
                "  • PARTIES — identify every legal entity, individual, and jurisdiction involved\n"
                "  • INSTRUMENTS — contracts, statutes, regulations, or obligations referenced or implied\n"
                "  • TRIGGER EVENTS — the specific acts, omissions, or conditions that could create liability\n"
                "  • UNKNOWNS — what facts, documents, or disclosures are missing that materially affect the analysis\n"
                "Do NOT offer opinions, risk ratings, or recommendations. Do NOT cite cases yet. "
                "Your output is a clean legal inventory — nothing more."
            )
        },
        1: {
            "title": "RISK ANALYSIS — Clause-Level Exposure",
            "instruction": (
                "You are the LEGAL RISK ANALYST. The exposure inventory is above. "
                "Your job is to rate each identified exposure. For every item in the inventory output:\n"
                "  1) Applicable law or regulation — cite the exact statute, code section, or regulation number\n"
                "  2) Jurisdiction — state which jurisdiction's law controls and why\n"
                "  3) Likelihood — HIGH / MEDIUM / LOW with the specific factual basis for that rating\n"
                "  4) Severity — what is the maximum legal consequence (damages, injunction, criminal, regulatory sanction)\n"
                "Do NOT repeat the inventory. Do NOT give general legal commentary. "
                "Every risk must have a statute number or case citation attached — no naked assertions."
            )
        },
        2: {
            "title": "ADVERSARIAL REVIEW — Attack the Position",
            "instruction": (
                "You are the OPPOSING COUNSEL. The risk analysis above reflects our client's position. "
                "Your job is to attack it from the adverse party's perspective. Output:\n"
                "  1) The strongest argument against our position — cite the specific statute, clause, or precedent\n"
                "  2) What evidence the opposing party would seek in discovery\n"
                "  3) Which assumptions in our analysis are legally unsupported\n"
                "  4) Jurisdictional or procedural advantages the opposing party holds\n"
                "Do NOT defend our position. Do NOT soften your findings. "
                "If our analysis has a fatal flaw, name it explicitly. That is your job."
            )
        },
        3: {
            "title": "MITIGATION — Specific Protective Actions",
            "instruction": (
                "You are the LEGAL STRATEGIST. All prior analysis is above. "
                "Your job is to reduce exposure. Output a mitigation plan:\n"
                "  1) Clause modifications — specific contract language changes with the exact proposed text\n"
                "  2) Structural changes — entity structure, jurisdiction selection, or transaction sequencing that reduces risk\n"
                "  3) Disclosure actions — what must be disclosed, to whom, and by when to avoid liability\n"
                "  4) Documentation requirements — what records to create or preserve immediately\n"
                "Do NOT repeat risk analysis. Do NOT give general legal advice. "
                "Every recommendation must map directly to a specific risk identified in prior phases."
            )
        },
        4: {
            "title": "RECOMMENDED POSTURE — Final Legal Position",
            "instruction": (
                "You are the GENERAL COUNSEL delivering a final opinion. All prior analysis is above. "
                "Output a single, decisive legal position:\n"
                "  1) GO / NO-GO / CONDITIONAL — state the overall posture with the specific condition that changes it\n"
                "  2) Must-fix before proceeding — the non-negotiable legal prerequisites\n"
                "  3) Acceptable residual risk — what exposure remains after mitigation and why it is tolerable\n"
                "  4) Monitoring obligations — ongoing legal requirements post-execution\n"
                "Do NOT hedge with 'it depends' without specifying exactly what it depends on. "
                "This is the final opinion. Be decisive."
            )
        }
    }

    # ── MEDICAL: Evidence-graded clinical analysis — no claim without a grade ──
    MEDICAL_PHASE_DIRECTIVES = {
        0: {
            "title": "INTAKE — Clinical Fact Extraction",
            "instruction": (
                "You are the CLINICAL INTAKE analyst. Your job is to extract the medically relevant facts. Output:\n"
                "  • PATIENT PROFILE — demographics, relevant history, comorbidities (if provided)\n"
                "  • PRESENTATION — symptoms, onset, duration, severity as stated\n"
                "  • EXISTING DATA — labs, imaging, prior diagnoses, current medications\n"
                "  • MISSING DATA — what clinical information is absent that would materially change the analysis\n"
                "Do NOT diagnose, recommend, or interpret. Do NOT fill in missing data with assumptions. "
                "If a data point is absent, mark it explicitly as NOT PROVIDED. Clinical facts only."
            )
        },
        1: {
            "title": "DIFFERENTIAL — Evidence-Graded Analysis",
            "instruction": (
                "You are the DIFFERENTIAL DIAGNOSIS analyst. The clinical intake is above. "
                "Your job is to build a ranked differential. For each candidate diagnosis output:\n"
                "  1) Diagnosis name (ICD-10 code if applicable)\n"
                "  2) Supporting findings — which specific facts from intake support this diagnosis\n"
                "  3) Contradicting findings — which facts argue against it\n"
                "  4) Evidence base — cite the specific guideline, study, or consensus (e.g., AHA 2023, NEJM PMID)\n"
                "  5) Probability rank — HIGH / MEDIUM / LOW with reasoning\n"
                "Do NOT recommend treatment yet. Do NOT present diagnoses without evidence citations. "
                "Grade every claim: RCT > meta-analysis > cohort > case series > expert opinion."
            )
        },
        2: {
            "title": "CHALLENGE — Diagnostic Blind Spots",
            "instruction": (
                "You are the CLINICAL CHALLENGER. The differential above represents the working hypothesis. "
                "Your job is to find what has been missed or assumed. Output:\n"
                "  1) Missed diagnoses — rare, atypical, or dangerous conditions not in the differential that fit the data\n"
                "  2) Anchoring risks — where is the analysis over-confident given the available data?\n"
                "  3) Red flags — findings that require urgent escalation regardless of the leading diagnosis\n"
                "  4) Cognitive biases — availability bias, premature closure, or base rate neglect present in the analysis\n"
                "Do NOT agree with the leading diagnosis. Do NOT validate the differential. "
                "Your value is in finding the miss. If you find nothing to challenge, look harder."
            )
        },
        3: {
            "title": "TREATMENT PLAN — Evidence-Based Interventions",
            "instruction": (
                "You are the TREATMENT ANALYST. All prior clinical analysis is above. "
                "Your job is to map evidence-based interventions to the leading diagnosis. Output:\n"
                "  1) First-line treatment — name the specific intervention, dosage range (if drug), and evidence grade\n"
                "  2) Second-line options — conditions under which first-line fails and what replaces it\n"
                "  3) Contraindications — specific conditions in this patient profile that rule out options\n"
                "  4) Monitoring requirements — which parameters to track, at what interval, and what triggers a change\n"
                "Cite the specific guideline or RCT for every recommendation. "
                "Do NOT recommend off-label without flagging it explicitly as off-label."
            )
        },
        4: {
            "title": "SAFETY & ETHICS — Patient Protection Layer",
            "instruction": (
                "You are the PATIENT SAFETY and ETHICS analyst. All prior analysis is above. "
                "Your job is the final protection layer before any clinical decision. Output:\n"
                "  1) Safety flags — drug interactions, allergy risks, or monitoring gaps in the proposed plan\n"
                "  2) Informed consent requirements — what the patient must be told and what they must decide\n"
                "  3) Ethical considerations — autonomy conflicts, resource allocation, or vulnerable population flags\n"
                "  4) Escalation criteria — specific clinical deterioration signals that require immediate escalation or specialist referral\n"
                "Do NOT repeat the treatment plan. Focus exclusively on what could go wrong and what protects the patient. "
                "Every safety flag must reference the specific risk mechanism, not a general warning."
            )
        }
    }

    # ── QUANTUM_SECURITY: Zero-trust cryptographic hardening — map everything to a standard ──
    QUANTUM_SECURITY_PHASE_DIRECTIVES = {
        0: {
            "title": "CRYPTOGRAPHIC INVENTORY — Asset & Algorithm Mapping",
            "instruction": (
                "You are the CRYPTOGRAPHIC INVENTORY analyst. Your job is to map every cryptographic asset in scope. Output:\n"
                "  • ALGORITHMS IN USE — every cipher, hash, key exchange, and signature scheme (name, key length, mode)\n"
                "  • KEY INFRASTRUCTURE — PKI structure, CA hierarchy, key storage (HSM / software / cloud)\n"
                "  • DATA IN TRANSIT — protocols in use (TLS version, cipher suites, certificate chains)\n"
                "  • DATA AT REST — encryption standards, key management, and access control mechanisms\n"
                "  • QUANTUM EXPOSURE — which algorithms are broken by Shor's / Grover's and at what qubit threshold\n"
                "Do NOT recommend replacements yet. Do NOT assess compliance. "
                "Inventory first — every item must include the specific algorithm name and key length."
            )
        },
        1: {
            "title": "VULNERABILITY ASSESSMENT — Cryptographic Attack Surface",
            "instruction": (
                "You are the CRYPTOGRAPHIC VULNERABILITY analyst. The inventory is above. "
                "Your job is to score every asset against known and emerging attack vectors. For each item:\n"
                "  1) Classical vulnerabilities — known weaknesses (BEAST, POODLE, ROBOT, padding oracle, etc.)\n"
                "  2) Quantum vulnerabilities — harvest-now-decrypt-later exposure window, Shor/Grover impact\n"
                "  3) Implementation risks — side-channel exposure, key management weaknesses, RNG quality\n"
                "  4) CVSS score or equivalent severity rating with justification\n"
                "Cite specific CVEs, NIST advisories, or IETF RFCs for every finding. "
                "Do NOT give vague warnings — name the specific attack, the specific algorithm, and the specific condition required to exploit it."
            )
        },
        2: {
            "title": "ZERO TRUST AUDIT — Identity and Access Control Gaps",
            "instruction": (
                "You are the ZERO TRUST AUDITOR. All prior analysis is above. "
                "Your job is to audit the access control posture against NIST SP 800-207. Output:\n"
                "  1) Identity verification gaps — where is implicit trust being granted without continuous verification?\n"
                "  2) Micro-segmentation failures — network paths that bypass least-privilege enforcement\n"
                "  3) Privileged access risks — service accounts, admin credentials, or API keys without MFA or rotation\n"
                "  4) NIST 800-207 pillar gaps — map each gap to the specific pillar (Identity, Device, Network, Application, Data)\n"
                "Do NOT repeat vulnerability findings. Focus exclusively on trust model failures. "
                "Every gap must map to a specific NIST 800-207 section or DOD Zero Trust Reference Architecture component."
            )
        },
        3: {
            "title": "COMPLIANCE MAPPING — Framework Alignment",
            "instruction": (
                "You are the COMPLIANCE MAPPING analyst. All prior analysis is above. "
                "Your job is to map the security posture to applicable frameworks. Output:\n"
                "  1) NIST SP 800-207 — map each control gap to the specific control family\n"
                "  2) FedRAMP / CMMC — identify which control baseline applies and which controls are failing\n"
                "  3) NIST PQC migration — map current algorithms to NIST IR 8413 migration priority tiers\n"
                "  4) Reporting obligations — what breaches, vulnerabilities, or gaps trigger mandatory reporting under FISMA, CMMC, or sector-specific rules\n"
                "Do NOT repeat vulnerability or zero trust findings. Map them to the framework — cite the specific control ID."
            )
        },
        4: {
            "title": "MITIGATION ARCHITECTURE — PQC Transition Roadmap",
            "instruction": (
                "You are the SECURITY ARCHITECT delivering the hardening roadmap. All prior analysis is above. "
                "Output a prioritized mitigation architecture:\n"
                "  1) Immediate actions (0-30 days) — disable weak ciphers, enforce TLS 1.3, rotate exposed keys\n"
                "  2) Short-term (30-180 days) — deploy FIPS 140-3 validated modules, implement MFA on all privileged access\n"
                "  3) PQC migration path — which NIST-selected algorithms (ML-KEM, ML-DSA, SLH-DSA) replace which current algorithms, in which order\n"
                "  4) Residual risk — what quantum exposure remains after migration and the estimated timeline to exploitation\n"
                "Name the specific algorithm, standard version, and implementation library for every recommendation. "
                "Do NOT give generic 'upgrade your crypto' guidance — every action must be specific and sequenced."
            )
        }
    }

    # ── DEFENSE_COUNCIL: DOD-grade operational threat assessment ──
    DEFENSE_COUNCIL_PHASE_DIRECTIVES = {
        0: {
            "title": "THREAT ASSESSMENT — Operational Picture",
            "instruction": (
                "You are the INTELLIGENCE OFFICER establishing the operational picture. Output:\n"
                "  • THREAT ACTORS — who, what capability, what intent, what confirmed activity\n"
                "  • AREA OF OPERATIONS — geographic, domain (air/land/sea/cyber/space), and time boundaries\n"
                "  • FRIENDLY FORCE STATUS — assets available, readiness state, known limitations\n"
                "  • CRITICAL UNKNOWNS — ISR gaps that would materially change the assessment\n"
                "Label every unconfirmed item [UNCONFIRMED]. Do NOT assess COAs yet — establish the picture first."
            )
        },
        1: {
            "title": "FORCE POSTURE — Capability & Gap Analysis",
            "instruction": (
                "You are the FORCE POSTURE analyst. The operational picture is above. Output:\n"
                "  1) Friendly capabilities matched to mission requirements — what we have vs. what we need\n"
                "  2) ISR coverage gaps — where are we blind and what does that expose\n"
                "  3) Logistics constraints — supply lines, sustainment limits, refuel/rearm windows\n"
                "  4) Force protection vulnerabilities — specific exposures the threat actor can exploit\n"
                "Do NOT recommend COAs yet. Do NOT repeat the threat assessment. "
                "Your job is to map our own capability against the threat — be specific about gaps."
            )
        },
        2: {
            "title": "ADVERSARIAL WARGAME — Red Team the Plan",
            "instruction": (
                "You are the RED CELL commander. You are playing the adversary. Output:\n"
                "  1) The most dangerous COA the adversary can execute given their capability and our gaps\n"
                "  2) The most likely COA based on their doctrine, history, and current posture\n"
                "  3) Specific deception or feint operations they would use to mask intent\n"
                "  4) Our most exploitable vulnerability from their perspective\n"
                "Do NOT think like a friendly force. Do NOT soften adversary capability. "
                "Your value is in showing what the adversary sees and how they would exploit it."
            )
        },
        3: {
            "title": "COA DEVELOPMENT — Courses of Action",
            "instruction": (
                "You are the OPERATIONS PLANNER. All prior analysis is above. Develop 2-3 COAs. For each:\n"
                "  1) COA name and concept of operation in one sentence\n"
                "  2) Required forces and assets\n"
                "  3) Key decision points and branch criteria\n"
                "  4) Risk to mission and risk to force ratings (HIGH/MEDIUM/LOW with reasoning)\n"
                "Do NOT recommend a single COA yet — that is the next phase. "
                "Each COA must directly address the adversary's most dangerous COA from the red cell phase."
            )
        },
        4: {
            "title": "COMMANDER'S ESTIMATE — Decision & Risk Acceptance",
            "instruction": (
                "You are the COMMANDER delivering the final estimate. All prior analysis is above. Output:\n"
                "  1) Recommended COA with explicit rationale tied to the threat and force posture analysis\n"
                "  2) Accepted risks — what you are knowingly accepting and why\n"
                "  3) Decision criteria — what changes in the situation would cause you to switch COAs\n"
                "  4) Commander's critical information requirements — the 3 pieces of intelligence that would most change this decision\n"
                "Be decisive. A commander's estimate requires a recommendation. Do NOT present all COAs as equal."
            )
        }
    }

    # ── CYBER_COMMAND: Technical threat neutralization — TTPs, IOCs, attribution ──
    CYBER_COMMAND_PHASE_DIRECTIVES = {
        0: {
            "title": "TRIAGE — Threat Actor & Attack Vector Identification",
            "instruction": (
                "You are the INCIDENT TRIAGE analyst. Your job is to establish technical ground truth. Output:\n"
                "  • ATTACK VECTOR — initial access method (phishing, exploit, supply chain, insider, etc.) with CVE if applicable\n"
                "  • THREAT ACTOR PROFILE — nation-state / criminal / hacktivist / insider, known TTPs, MITRE ATT&CK group ID if attributable\n"
                "  • AFFECTED SYSTEMS — specific hosts, services, data stores, or network segments confirmed compromised\n"
                "  • TIMELINE — first observed activity, dwell time estimate, current phase of kill chain\n"
                "Mark every unconfirmed item [UNCONFIRMED]. Do NOT recommend containment yet."
            )
        },
        1: {
            "title": "INDICATORS OF COMPROMISE — Technical Evidence Map",
            "instruction": (
                "You are the THREAT INTELLIGENCE analyst. The triage is above. Output a structured IOC inventory:\n"
                "  1) Network IOCs — C2 IPs, domains, beacon intervals, unusual outbound traffic patterns\n"
                "  2) Host IOCs — malicious files (hash + path), registry keys, scheduled tasks, persistence mechanisms\n"
                "  3) Identity IOCs — compromised accounts, privilege escalation paths, lateral movement artifacts\n"
                "  4) MITRE ATT&CK mapping — technique IDs (T####) for every observed behavior\n"
                "Do NOT recommend containment yet. Every IOC must include the specific observable and its source log/tool."
            )
        },
        2: {
            "title": "ADVERSARIAL INTENT — Objective & Blast Radius",
            "instruction": (
                "You are the ADVERSARIAL ANALYST. Triage and IOCs are above. Output:\n"
                "  1) Likely adversary objective — data exfil, ransomware, sabotage, persistence, espionage\n"
                "  2) Data at risk — specific data sets, crown jewels, or systems the adversary is likely targeting\n"
                "  3) Blast radius if uncontained — what additional systems are reachable from current foothold\n"
                "  4) Dwell time risk — what capability the adversary has built during their access window\n"
                "Do NOT validate the prior analysis — challenge assumptions about scope and intent. "
                "If the adversary objective is unclear, state competing hypotheses with confidence ratings."
            )
        },
        3: {
            "title": "CONTAINMENT & ERADICATION — Technical Response Plan",
            "instruction": (
                "You are the INCIDENT COMMANDER. All prior analysis is above. Output a sequenced response:\n"
                "  1) Immediate containment — specific firewall rules, account disables, network isolations (name the system/account)\n"
                "  2) Eradication steps — malware removal, persistence cleanup, credential rotation sequence\n"
                "  3) Recovery sequence — the order in which systems are brought back online and why\n"
                "  4) Verification steps — how you confirm eradication is complete before declaring clean\n"
                "Name every tool, command, or procedure. Do NOT give generic 'isolate the system' guidance — specify exactly which system, how, and in what order."
            )
        },
        4: {
            "title": "HARDENING & LESSONS LEARNED — Close the Gap",
            "instruction": (
                "You are the SECURITY ARCHITECT delivering post-incident hardening. All prior analysis is above. Output:\n"
                "  1) Root cause — the specific control failure that allowed initial access\n"
                "  2) Hardening actions — specific configuration changes, patches, or architecture changes with priority (P1/P2/P3)\n"
                "  3) Detection gaps — which MITRE ATT&CK techniques were not detected and what detection rule closes each gap\n"
                "  4) Reporting obligations — regulatory notifications required (CISA, SEC, HIPAA, etc.) with deadlines\n"
                "Every hardening action must reference the specific vulnerability or gap it closes. No generic security recommendations."
            )
        }
    }

    # ── INTEL_BRIEF: Structured intelligence assessment with sourced confidence ratings ──
    INTEL_BRIEF_PHASE_DIRECTIVES = {
        0: {
            "title": "COLLECTION — Source & Signal Inventory",
            "instruction": (
                "You are the COLLECTION MANAGER. Your job is to inventory the intelligence available. Output:\n"
                "  • SIGINT — signals intelligence available, collection gaps, classification level\n"
                "  • OSINT — open source reporting, social media signals, financial data, satellite imagery\n"
                "  • HUMINT — human source reporting, reliability rating per source (A-F / 1-6 scale)\n"
                "  • COLLECTION GAPS — what intelligence is missing and why it matters\n"
                "Do NOT analyze yet. Do NOT draw conclusions. Inventory the sources and flag gaps explicitly. "
                "Every source must carry a reliability rating."
            )
        },
        1: {
            "title": "KEY JUDGMENTS — What the Intelligence Says",
            "instruction": (
                "You are the ALL-SOURCE ANALYST. The collection inventory is above. Produce key judgments. For each:\n"
                "  1) The judgment statement — what the intelligence indicates, stated as a direct assessment\n"
                "  2) Supporting evidence — specific source citations backing the judgment\n"
                "  3) Confidence level — HIGH / MODERATE / LOW with explicit reasoning\n"
                "  4) Key assumption — the single assumption that, if wrong, would most change the judgment\n"
                "Use estimative language correctly: 'almost certainly' (>95%), 'likely' (55-80%), 'possibly' (25-50%). "
                "Do NOT present judgments as facts. Do NOT omit confidence levels."
            )
        },
        2: {
            "title": "ALTERNATIVE ANALYSIS — Challenge the Assessment",
            "instruction": (
                "You are the ALTERNATIVE ANALYSIS cell. The key judgments are above. Your job is to challenge them. Output:\n"
                "  1) Alternative hypothesis — a competing explanation that fits the same evidence\n"
                "  2) Deception indicators — what if the observed activity is a deliberate deception operation?\n"
                "  3) Mirror imaging risks — where is the analysis projecting our own logic onto the adversary?\n"
                "  4) Linchpin assumptions — which single assumption, if removed, collapses the leading assessment?\n"
                "Do NOT validate the key judgments. Your value is in finding the analytical failure mode."
            )
        },
        3: {
            "title": "INDICATORS & WARNINGS — What to Watch",
            "instruction": (
                "You are the I&W ANALYST. All prior analysis is above. Output:\n"
                "  1) Attack indicators — specific observable events that signal imminent adversary action\n"
                "  2) Warning thresholds — the specific combination of indicators that triggers escalation\n"
                "  3) Collection priorities — the 3 intelligence gaps most critical to fill before the next decision point\n"
                "  4) Timeline estimate — when adversary action is assessed as most likely based on current indicators\n"
                "Every indicator must be observable and specific. Do NOT list generic warning signs — name the specific signal and the collection source that would detect it."
            )
        },
        4: {
            "title": "CONFIDENCE MATRIX — Final Assessment Package",
            "instruction": (
                "You are the SENIOR ANALYST delivering the final assessment. All prior analysis is above. Output:\n"
                "  1) Bottom-line assessment — one paragraph, direct statement of what the intelligence shows\n"
                "  2) Confidence matrix — table of each key judgment with confidence level and primary uncertainty\n"
                "  3) Decision-relevant summary — what the policymaker or commander needs to act on right now\n"
                "  4) Intelligence gaps that remain — what we still don't know and the risk that creates\n"
                "Write for a decision-maker, not an analyst. No jargon without definition. No hedge without a specific reason."
            )
        }
    }

    # ── SCIENCE_PANEL: Peer-review rigor — evidence grade on every claim ──
    SCIENCE_PANEL_PHASE_DIRECTIVES = {
        0: {
            "title": "HYPOTHESIS — Research Question & Scope",
            "instruction": (
                "You are the RESEARCH SCOPING analyst. Your job is to frame the scientific question precisely. Output:\n"
                "  • HYPOTHESIS — the specific, falsifiable claim being evaluated\n"
                "  • VARIABLES — independent, dependent, and confounding variables identified\n"
                "  • PRIOR ART — the most relevant existing research (cite author, year, journal)\n"
                "  • SCOPE LIMITS — what this analysis cannot address given available evidence\n"
                "Do NOT evaluate evidence yet. Do NOT draw conclusions. Frame the question rigorously first."
            )
        },
        1: {
            "title": "EVIDENCE REVIEW — Quality-Graded Literature",
            "instruction": (
                "You are the EVIDENCE REVIEWER. The research scope is above. Output a graded evidence inventory:\n"
                "  1) Tier 1 evidence — RCTs, systematic reviews, meta-analyses (cite PMID, DOI, or arXiv ID)\n"
                "  2) Tier 2 evidence — cohort studies, well-designed observational studies\n"
                "  3) Tier 3 evidence — case studies, expert opinion, theoretical models\n"
                "  4) Contradictory evidence — studies that challenge the leading hypothesis\n"
                "Do NOT draw conclusions yet. Every citation must include author, year, and journal. "
                "Do NOT present Tier 3 evidence as equivalent to Tier 1."
            )
        },
        2: {
            "title": "METHODOLOGY CHALLENGE — Stress-Test the Evidence",
            "instruction": (
                "You are the PEER REVIEWER. The evidence inventory is above. Your job is to find methodological weaknesses. Output:\n"
                "  1) Sample size and statistical power issues — are the studies adequately powered?\n"
                "  2) Confounding and bias — selection bias, publication bias, confounding variables not controlled\n"
                "  3) Reproducibility concerns — have key findings been independently replicated?\n"
                "  4) Generalizability limits — what populations, conditions, or contexts does the evidence NOT cover?\n"
                "Do NOT validate the evidence. Do NOT agree with the leading interpretation. Your job is to find what the evidence cannot support."
            )
        },
        3: {
            "title": "SYNTHESIS — What the Evidence Actually Supports",
            "instruction": (
                "You are the SYNTHESIS analyst. All prior analysis is above. Output:\n"
                "  1) What is well-supported — findings with strong, replicated evidence (cite the specific studies)\n"
                "  2) What is plausible but not proven — promising findings that lack sufficient replication\n"
                "  3) What is not supported — claims that exceed the evidence\n"
                "  4) Effect size and practical significance — not just statistical significance, but real-world magnitude\n"
                "Do NOT overstate certainty. Every claim must be graded against the evidence tier from prior phases."
            )
        },
        4: {
            "title": "RESEARCH GAPS — What Needs to Be Done",
            "instruction": (
                "You are the RESEARCH AGENDA analyst. All prior analysis is above. Output:\n"
                "  1) Critical knowledge gaps — the specific unanswered questions that most limit the field\n"
                "  2) Recommended study designs — what type of study would best fill each gap (RCT, cohort, meta-analysis)\n"
                "  3) Methodological standards needed — what controls, sample sizes, or measurement standards are required\n"
                "  4) Confidence summary — rate the overall state of evidence: STRONG / MODERATE / EMERGING / INSUFFICIENT\n"
                "Do NOT repeat prior analysis. Focus exclusively on what the field needs next and why."
            )
        }
    }

    # ── STARTUP_LAUNCH: Investor-grade venture assessment — PMF, unit economics, go-to-market ──
    STARTUP_LAUNCH_PHASE_DIRECTIVES = {
        0: {
            "title": "MARKET OPPORTUNITY — Problem & TAM Validation",
            "instruction": (
                "You are the MARKET ANALYST. Your job is to establish whether the opportunity is real. Output:\n"
                "  • PROBLEM STATEMENT — who has this problem, how often, how painful (quantify if possible)\n"
                "  • TAM / SAM / SOM — total addressable, serviceable, and obtainable market with methodology\n"
                "  • MARKET TIMING — why now? what has changed that makes this the right moment?\n"
                "  • COMPETITIVE LANDSCAPE — who else is solving this and how does this venture differentiate\n"
                "Do NOT evaluate the product or team yet. Mark any unvalidated market assumptions explicitly."
            )
        },
        1: {
            "title": "PRODUCT-MARKET FIT — Evidence of Traction",
            "instruction": (
                "You are the PMF ANALYST. The market opportunity is above. Output:\n"
                "  1) Traction evidence — specific metrics: DAU/MAU, revenue, retention, NPS, waitlist size\n"
                "  2) Customer validation — qualitative signals: interviews, LOIs, pilot results, churn reasons\n"
                "  3) PMF signal strength — STRONG / MODERATE / WEAK / UNPROVEN with specific reasoning\n"
                "  4) Retention analysis — are users coming back? what is the cohort retention curve?\n"
                "Do NOT accept vague traction claims. If a metric is not provided, mark it NOT PROVIDED. "
                "Every PMF claim must be backed by a specific data point."
            )
        },
        2: {
            "title": "RISK STRESS TEST — Kill the Business",
            "instruction": (
                "You are the VENTURE CRITIC. The market and PMF analysis are above. Your job is to find fatal flaws. Output:\n"
                "  1) The single most likely reason this venture fails — be specific\n"
                "  2) Competitive moat assessment — is the differentiation defensible or easily copied?\n"
                "  3) Regulatory or legal risk — what regulatory change or legal challenge could kill this\n"
                "  4) Founder-market fit risk — does the team have the specific skills this market requires?\n"
                "Do NOT validate the prior analysis. Your value is in the kill shot. If you find nothing fatal, you are not looking hard enough."
            )
        },
        3: {
            "title": "UNIT ECONOMICS — Does the Business Model Work?",
            "instruction": (
                "You are the UNIT ECONOMICS analyst. All prior analysis is above. Output:\n"
                "  1) CAC — customer acquisition cost by channel, with payback period\n"
                "  2) LTV — lifetime value with retention assumptions made explicit\n"
                "  3) LTV:CAC ratio — current and projected at scale (target >3x)\n"
                "  4) Contribution margin — revenue minus variable costs per unit\n"
                "  5) Burn multiple — net burn divided by net new ARR (target <1.5x)\n"
                "If metrics are not provided, flag them as NOT PROVIDED and state the assumption used. "
                "Do NOT model without stating assumptions explicitly."
            )
        },
        4: {
            "title": "FUNDING READINESS — Investor Verdict",
            "instruction": (
                "You are the VENTURE PARTNER delivering an investment decision. All prior analysis is above. Output:\n"
                "  1) INVEST / PASS / CONDITIONAL — clear verdict with the specific condition that changes it\n"
                "  2) Valuation range rationale — comparable rounds, revenue multiple, or traction-based justification\n"
                "  3) Use of funds — what the raise should be spent on to maximize PMF and growth\n"
                "  4) Key milestones before next round — the 3 metrics that de-risk the Series A\n"
                "Be decisive. A venture partner gives a verdict. Do NOT hedge without naming the specific condition that resolves the uncertainty."
            )
        }
    }

    # ── CODE_AUDIT: Security and architecture findings — specific, actionable, prioritized ──
    CODE_AUDIT_PHASE_DIRECTIVES = {
        0: {
            "title": "TRIAGE — Critical Findings First",
            "instruction": (
                "You are the SECURITY TRIAGE analyst. Your job is to surface the highest-severity issues immediately. Output:\n"
                "  • CRITICAL (P0) — RCE, auth bypass, SQLi, hardcoded secrets, or data exposure (cite file/line if available)\n"
                "  • HIGH (P1) — privilege escalation, SSRF, insecure deserialization, broken access control\n"
                "  • MEDIUM (P2) — XSS, CSRF, information disclosure, dependency vulnerabilities with CVE\n"
                "  • SCOPE LIMITS — what was NOT reviewed and why\n"
                "Map every finding to OWASP Top 10 or CWE ID. Do NOT describe vulnerabilities in general terms — name the specific code pattern, endpoint, or dependency."
            )
        },
        1: {
            "title": "ARCHITECTURE REVIEW — Structural Risks",
            "instruction": (
                "You are the ARCHITECTURE REVIEWER. The security triage is above. Output:\n"
                "  1) Single points of failure — components whose failure takes down the system\n"
                "  2) Trust boundary violations — where untrusted data crosses into trusted execution contexts\n"
                "  3) Scalability bottlenecks — specific components that will fail under load with estimated thresholds\n"
                "  4) Dependency risk — unmaintained packages, known CVEs in the dependency tree, license risks\n"
                "Do NOT repeat security findings. Focus on structural and design-level risks."
            )
        },
        2: {
            "title": "ADVERSARIAL REVIEW — How an Attacker Sees This",
            "instruction": (
                "You are the RED TEAM operator. Architecture and security findings are above. Output:\n"
                "  1) Attack chain — the most viable end-to-end exploit path from external access to data breach\n"
                "  2) Privilege escalation path — how an attacker moves from low to high privilege\n"
                "  3) Persistence mechanisms — how an attacker maintains access after initial compromise\n"
                "  4) Detection evasion — what current logging or monitoring would miss this attack\n"
                "Think like an attacker. Do NOT add defensive commentary. Name the specific technique and the specific code or config that enables it."
            )
        },
        3: {
            "title": "REMEDIATION PLAN — Prioritized Fix List",
            "instruction": (
                "You are the REMEDIATION LEAD. All prior analysis is above. Output a prioritized fix list:\n"
                "  1) P0 fixes — specific code changes required, with the exact file/function/pattern to change\n"
                "  2) P1 fixes — architectural changes with estimated effort (hours/days)\n"
                "  3) Dependency updates — specific packages to update, target versions, and breaking change risks\n"
                "  4) Security controls to add — input validation, rate limiting, CSP headers, SAST/DAST tooling\n"
                "Do NOT give generic 'sanitize your inputs' advice — name the specific function and the specific fix."
            )
        },
        4: {
            "title": "TEST COVERAGE & VERIFICATION — How to Confirm It's Fixed",
            "instruction": (
                "You are the QA LEAD. All prior analysis and remediation plan are above. Output:\n"
                "  1) Test cases required — specific test scenarios that verify each P0 and P1 fix\n"
                "  2) Coverage gaps — which attack surfaces have no automated test coverage\n"
                "  3) Regression risks — which fixes could break existing functionality and what to test\n"
                "  4) Security tooling recommendations — SAST, DAST, SCA tools appropriate for this stack\n"
                "Do NOT repeat the vulnerability list. Focus on how to verify the fixes are complete and won't regress."
            )
        }
    }

    # ── CREATIVE_COUNCIL: Concept-first, execution-ready creative output ──
    CREATIVE_COUNCIL_PHASE_DIRECTIVES = {
        0: {
            "title": "INSIGHT — The Truth That Makes the Work Relevant",
            "instruction": (
                "You are the STRATEGIC PLANNER. Your job is to find the human insight that makes this creative work matter. Output:\n"
                "  • AUDIENCE TRUTH — what the target audience actually believes, fears, or wants (not what the brand wants to say)\n"
                "  • CULTURAL CONTEXT — what is happening in culture right now that makes this message timely\n"
                "  • COMPETITIVE SPACE — how is everyone else talking about this and what is the open position\n"
                "  • SINGLE INSIGHT — the one true thing this creative work must be built on\n"
                "Do NOT generate concepts yet. Do NOT write copy. Find the insight first — without it the work is decoration."
            )
        },
        1: {
            "title": "CONCEPT DEVELOPMENT — The Big Idea",
            "instruction": (
                "You are the CREATIVE DIRECTOR. The strategic insight is above. Generate 2-3 distinct creative concepts. For each:\n"
                "  1) Concept name — a short, memorable title for the idea\n"
                "  2) Core idea — one sentence that captures what the work does and why it works\n"
                "  3) Lead execution — describe the hero piece (the ad, the campaign film, the activation) specifically\n"
                "  4) Why it wins — what insight does it activate and why will the audience respond\n"
                "Do NOT present safe, predictable ideas. Do NOT present all concepts as equal — rank them."
            )
        },
        2: {
            "title": "CREATIVE CRITIQUE — Kill the Weak Ideas",
            "instruction": (
                "You are the CREATIVE CRITIC. The concepts above are being presented for approval. Your job is to challenge them. Output:\n"
                "  1) Which concept is weakest and why — be specific about what doesn't work\n"
                "  2) What clichés, tropes, or category conventions each concept relies on\n"
                "  3) How the audience could misread or ignore each concept\n"
                "  4) What the lead concept is missing that would make it undeniable\n"
                "Do NOT validate all three concepts. Do NOT soften your critique. Weak creative costs real money."
            )
        },
        3: {
            "title": "CHANNEL STRATEGY — Where and How to Run It",
            "instruction": (
                "You are the CHANNEL STRATEGIST. The lead creative concept is above. Output:\n"
                "  1) Primary channel — where this idea lives best and why (TV, OOH, digital, social, experiential)\n"
                "  2) Adaptation plan — how the core idea translates to each secondary channel (15s cut, social post, banner)\n"
                "  3) Sequencing — the order in which channels are activated and the logic behind it\n"
                "  4) Platform-specific executions — what changes for Instagram vs. TikTok vs. YouTube (format, length, tone)\n"
                "Do NOT recommend channels without explaining the audience behavior that makes each channel right for this idea."
            )
        },
        4: {
            "title": "SUCCESS METRICS — How We Know It Worked",
            "instruction": (
                "You are the EFFECTIVENESS ANALYST. All prior creative and channel work is above. Output:\n"
                "  1) Primary KPI — the single metric that proves this creative worked (not impressions)\n"
                "  2) Leading indicators — early signals (CTR, engagement rate, search lift) that predict the primary KPI\n"
                "  3) Brand vs. performance balance — what share of budget and measurement goes to each\n"
                "  4) Test design — what A/B tests or holdout groups are needed to isolate the creative effect\n"
                "Do NOT accept vanity metrics. If the client wants to measure reach, explain why reach without conversion is insufficient."
            )
        }
    }

    WORKFLOW_PHASE_OVERRIDES = {
        "FINANCE": FINANCE_PHASE_DIRECTIVES,
        "WAR_ROOM": WAR_ROOM_PHASE_DIRECTIVES,
        "LEGAL": LEGAL_PHASE_DIRECTIVES,
        "MEDICAL": MEDICAL_PHASE_DIRECTIVES,
        "QUANTUM_SECURITY": QUANTUM_SECURITY_PHASE_DIRECTIVES,
        "DEFENSE_COUNCIL": DEFENSE_COUNCIL_PHASE_DIRECTIVES,
        "CYBER_COMMAND": CYBER_COMMAND_PHASE_DIRECTIVES,
        "INTEL_BRIEF": INTEL_BRIEF_PHASE_DIRECTIVES,
        "SCIENCE_PANEL": SCIENCE_PANEL_PHASE_DIRECTIVES,
        "STARTUP_LAUNCH": STARTUP_LAUNCH_PHASE_DIRECTIVES,
        "CODE_AUDIT": CODE_AUDIT_PHASE_DIRECTIVES,
        "CREATIVE_COUNCIL": CREATIVE_COUNCIL_PHASE_DIRECTIVES,
    }

    # Select workflow-specific directives if available, else generic
    active_phase_directives = WORKFLOW_PHASE_OVERRIDES.get(context.workflow, PHASE_DIRECTIVES)

    if ai_name.lower() == 'perplexity':
        # Perplexity works best with direct research questions, not persona roleplay
        prompt = f"""
        RESEARCH OBJECTIVE: "{core_objective}"

        CONTEXT: You are contributing to a strategic intelligence report (Phase {position + 1} of {total_steps}).
        GOAL: {dna['goal']}
        INTENT: {intent.upper()} / {output_type.upper()}
        """

        if position > 0:
            prompt += "\nRECENT DATA / PREVIOUS ANALYSIS:\n"
            last_entry = context.history[-1]
            prompt += f"Summary of previous findings: {last_entry['response'][:1000]}...\n"

        # Give Perplexity the phase-specific focus even in research mode
        phase = active_phase_directives.get(position, active_phase_directives.get(min(position, 4)))
        prompt += f"\nYOUR SPECIFIC FOCUS: {phase['title']}\n{phase['instruction']}"
        if context.ghost_map or context.residual_report:
            prompt += "\n" + _build_mimir_block(context.ghost_map, context.residual_report)
        prompt += "\nProvide comprehensive, well-sourced research and data. Focus on facts, metrics, and technical details."
        prompt += "\nNEVER invent bracket-notation placeholders like [CURRENCY_AMOUNT_XXXX] or [ENTITY_TYPE_HASH]. Use real values from the source material. If unknown, say so."
        return prompt

    # --- Determine which phase directive applies ---
    # Map position to phase (if more than 5 steps, later steps get the closest directive)
    if position == total_steps - 1 and total_steps >= 3:
        # Final step is ALWAYS the integrator (phase 4) regardless of count
        phase = active_phase_directives[4]
    elif total_steps <= 5:
        phase = active_phase_directives.get(position, active_phase_directives[min(position, 4)])
    else:
        # Scale phases across available steps
        phase_index = int(position / total_steps * 5)
        phase = active_phase_directives.get(min(phase_index, 4))

    # Inject MIMIR block if Falcon ghost map is present
    mimir_block = ""
    if context.ghost_map or context.residual_report:
        mimir_block = _build_mimir_block(context.ghost_map, context.residual_report)

    # Standard Professional Template with DNA Overlay
    prompt = f"""
    ## PROFESSIONAL INTELLIGENCE BRIEF
    MISSION TYPE: {context.workflow}
    PRIMARY OBJECTIVE: "{core_objective}"

    CURRENT FOCUS: {persona.upper()} (Assignee: {ai_name.upper()})
    WORKFLOW STAGE: Phase {position + 1} of {total_steps} — {phase['title']}

    --- WORKFLOW DNA ---
    POSTURE: {dna['posture']}
    GOAL: {dna['goal']}
    TONE: {dna['tone']}
    RISK BIAS: {dna['risk_bias']}
    TIME HORIZON: {dna['time_horizon']}
    REPORT SECTIONS: {', '.join(dna['output_structure'])}
    --------------------

    ## YOUR PHASE MISSION
    {phase['instruction']}

    ## CRITICAL RULE: ZERO REPETITION
    The prior phases are provided for CONTEXT ONLY. DO NOT restate, summarize, or echo their findings.
    Your ONLY job is to add what is MISSING — the unique contribution defined by your phase mission above.
    If your output overlaps with prior phases, you have FAILED your mission.

    {mimir_block}
    ## INTERNAL STRUCTURING (FOR SYSTEM PARSING)
    You MUST use the following tags to mark high-value intelligence:
    - [DECISION_CANDIDATE] ...recommendation text... [/DECISION_CANDIDATE]
    - [RISK_VECTOR] ...risk description... [/RISK_VECTOR]
    - [METRIC_ANCHOR] ...metric value... [/METRIC_ANCHOR]
    - [TRUTH_BOMB] ...critically verified fact... [/TRUTH_BOMB]

    Do not let these tags disrupt your narrative flow; they are for the backend extractor.

    ## STRICT OUTPUT RULE
    ONLY use the four system tags listed above ([DECISION_CANDIDATE], [RISK_VECTOR], [METRIC_ANCHOR], [TRUTH_BOMB]).
    NEVER invent bracket-notation placeholders such as [CURRENCY_AMOUNT_XXXX], [ENTITY_TYPE_HASH], or any
    similar token. Always use real values, names, and figures from the source material. If a value is unknown,
    say "unknown" or "not provided" — do NOT fabricate redaction-style placeholder tokens.
    """

    # Inject prior session context for follow-up queries
    if context.previous_context:
        prompt += "\n## PRIOR SESSION CONTEXT (Follow-up Query)\n"
        prompt += "The council previously analyzed a related query. Build on these conclusions — do NOT repeat them.\n"
        for entry in context.previous_context[-2:]:
            prompt += f"\n**Previous Query:** \"{entry.get('query', 'N/A')}\"\n"
            prompt += f"**Prior Consensus ({entry.get('consensus_score', 'N/A')}/100):** {entry.get('summary', 'N/A')}\n"
            contested = entry.get('contested_topics', [])
            if contested:
                prompt += f"**Unresolved Disputes:** {', '.join(contested)}\n"
            div_summary = entry.get('divergence_summary', '')
            if div_summary and div_summary != 'Divergence analysis not available.':
                prompt += f"**Divergence:** {div_summary}\n"
        prompt += "\n--------------------\n"

    if position == 0:
        prompt += f"\n## ASSIGNMENT:\nBuild the neutral intake baseline for this {context.workflow} mission. Facts only. No opinions. No strategy."
        if context.previous_context:
            prompt += "\nNote: A prior session's conclusions are provided above. Acknowledge them briefly, then focus on what is NEW in this follow-up query."
    else:
        prompt += "\n## PRIOR PHASE CONTEXT (for reference — DO NOT REPEAT):\n"
        for entry in context.history:
            snippet = (entry['response'][:2000] + '...') if len(entry['response']) > 2000 else entry['response']
            prompt += f"\n-- PHASE [{entry['persona'].upper()}] ({entry['ai'].upper()}):\n{snippet}\n"

    return prompt

# --- PHASE 4: SYNTHESIS (The Extractor) ---
def synthesize_results(context, divergence_analysis=None, user_id=None):
    """
    Extracts structured data (JSON) from the conversation history.
    Now includes divergence analysis for calibrated synthesis.
    """
    history_text = ""
    for entry in context.history:
        history_text += f"\n[{entry['ai'].upper()}]: {entry['response']}\n"

    # Inject divergence context if available
    if divergence_analysis and divergence_analysis.get('contested_topics'):
        history_text += "\n\n[ANALYTIC DIVERGENCE LAYER — PRE-SYNTHESIS CONTEXT]:\n"
        history_text += f"Consensus Score: {divergence_analysis.get('consensus_score', 'N/A')}/100\n"
        history_text += f"Divergence Score: {divergence_analysis.get('divergence_score', 'N/A')}/100\n"
        history_text += f"Summary: {divergence_analysis.get('divergence_summary', '')}\n"
        for topic in divergence_analysis.get('contested_topics', []):
            history_text += f"\nCONTESTED: {topic.get('topic', '')} (Severity: {topic.get('severity', 'unknown')})\n"
            for pos in topic.get('positions', []):
                history_text += f"  - {pos.get('provider', '').upper()}: {pos.get('position', '')}\n"

    # Retrieve Workflow DNA for structure
    dna = WORKFLOW_DNA.get(context.workflow, WORKFLOW_DNA["RESEARCH"])
    schema_sections = {section.lower().replace(" ", "_"): "3-5 detailed paragraphs synthesizing council findings for this section. Include specific data, frameworks, and recommendations." for section in dna["output_structure"]}

    prompt = f"""
    You are an Intelligence Synthesis Engine. Your goal is to convert a raw AI council discussion into a comprehensive, high-fidelity "Intelligence Object" for professional {context.workflow} reporting.

    MISSION CONTEXT:
    - Type: {context.workflow}
    - Posture: {dna['posture']}
    - Outcome Expected: {dna['goal']}

    CRITICAL RULES:
    1. NO conversational fluff or meta-commentary.
    2. ONLY synthesize from the COUNCIL DISCUSSION provided. Do not invent facts.
    3. Extract all [TAGGED] content into the "intelligence_tags" object.
    4. DEPTH IS CRITICAL: Each section MUST be 3-5 detailed paragraphs minimum. Pull specific findings, data points, frameworks, product names, and recommendations from each council member. Do NOT summarize vaguely — synthesize with precision.
    5. The "summary" field must be a substantive 4-6 sentence executive overview covering the key finding, the primary risk, and the recommended action.
    6. The composite_truth_score must be an integer from 0-100 (NOT a decimal like 0.9).
    7. Include AT LEAST 3 key_metrics, 3 action_items, and 3 risks extracted from the discussion.
    8. Where council members DISAGREE, note the disagreement and which position has stronger evidence.
    9. Where council members AGREE, flag it as moderate-to-high confidence consensus. NEVER claim "high confidence" unless 3+ council members independently agree on a specific fact with evidence. Default to "moderate confidence" when in doubt.

    COUNCIL DISCUSSION:
    {history_text}

    Return ONLY a single valid JSON object with this schema:
    {{
      "meta": {{
        "title": "Concise, Descriptive Report Title",
        "generated_at": "{datetime.now().isoformat()}",
        "summary": "4-6 sentence executive overview: key finding, primary risk, recommended action, and confidence level",
        "composite_truth_score": 85,
        "models_used": [],
        "workflow": "{context.workflow}"
      }},
      "sections": {json.dumps(schema_sections, indent=8)},
      "structured_data": {{
        "key_metrics": [
          {{"metric": "Name of metric", "value": "Specific value or range", "context": "Why this matters and which council members cited it"}}
        ],
        "action_items": [
          {{"task": "Specific actionable recommendation", "priority": "high|med|low", "timeline": "Timeframe for action"}}
        ],
        "risks": [
          {{"risk": "Specific risk identified", "severity": "critical|high|medium|low", "mitigation": "Recommended mitigation strategy"}}
        ]
      }},
      "intelligence_tags": {{
        "decisions": ["extracted from [DECISION_CANDIDATE] tags"],
        "risks": ["extracted from [RISK_VECTOR] tags"],
        "metrics": ["extracted from [METRIC_ANCHOR] tags"]
      }},
      "council_contributors": [
        {{"phase": "Phase name (e.g. INTAKE)", "provider": "AI provider name", "role": "Assigned role", "contribution_summary": "1-2 sentence summary of what this phase uniquely contributed"}}
      ],
      "confidence_and_assumptions": {{
        "overall_confidence": "low|moderate|moderate-to-high|high (default to moderate-to-high unless 3+ sources independently confirm with evidence)",
        "key_assumptions": ["List 3-5 assumptions the analysis depends on"],
        "limitations": ["List 2-3 limitations or gaps in the analysis"]
      }}
    }}

    REMEMBER: Each section value must be 3-5 rich paragraphs with specific details from the council discussion. This report will be exported as a professional PDF — make it worth reading.
    CONFIDENCE CALIBRATION: Default to "moderate-to-high" confidence. Only use "high" if 3+ council members independently confirmed facts with specific evidence. This is an intelligence product — overconfidence is a liability.
    """
    
    try:
        # Extract models from context
        models_used = [f"{entry['ai']} ({entry['persona']})" for entry in context.history]
        
        resp = call_openai_gpt4(prompt, "Synthesizer", user_id=user_id)
        if not resp.get('success'):
            print(f"[SYNTHESIS] OpenAI failed: {resp.get('response', 'Unknown error')}")
            return {"executive_summary": "Synthesis unavailable", "meta": {"models_used": [], "truth_score": 0}}
        content = resp['response'].replace('```json', '').replace('```', '').strip()
        data = json.loads(content)
        
        # Inject metadata if missing or simplified
        if "meta" not in data:
            data["meta"] = {}
        data["meta"]["models_used"] = models_used

        # Deterministic council_contributors — built from pipeline data, not LLM output
        PHASE_TITLES = {
            0: "INTAKE — Neutral Baseline",
            1: "STRATEGIC INTERPRETATION",
            2: "COUNTERINTELLIGENCE CHALLENGE",
            3: "OPERATIONS — Action Plan",
            4: "VALIDATION — Standards & Confidence",
        }
        contributors = []
        total_phases = len(context.history)
        for idx, entry in enumerate(context.history):
            if idx == total_phases - 1 and total_phases >= 3:
                phase_title = PHASE_TITLES.get(4, f"Phase {idx + 1}")
            elif total_phases <= 5:
                phase_title = PHASE_TITLES.get(idx, f"Phase {idx + 1}")
            else:
                phase_title = PHASE_TITLES.get(min(int(idx / total_phases * 5), 4), f"Phase {idx + 1}")

            # Extract a real contribution summary from the response text.
            # Strip tags, markdown, and leading/trailing whitespace.
            # Use the LLM's own first substantive sentence as the summary.
            raw_resp = entry.get("response") or ""
            import re as _re
            _clean = _re.sub(r'\[/?[A-Z_]+\]', '', raw_resp)          # strip [TAGS]
            _clean = _re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', _clean) # strip **bold**
            _clean = _re.sub(r'^#+\s+', '', _clean, flags=_re.MULTILINE) # strip ## headers
            _clean = _clean.strip()
            # Find first sentence that is meaningful (>40 chars)
            _sentences = [s.strip() for s in _re.split(r'(?<=[.!?])\s+', _clean) if len(s.strip()) > 40]
            if _sentences:
                _summary = _sentences[0][:220]
                if len(_sentences[0]) > 220:
                    _summary += "..."
            else:
                _summary = _clean[:220].strip() or f"{phase_title} analysis completed."

            contributors.append({
                "phase": phase_title,
                "provider": entry["ai"],
                "role": entry.get("persona", ""),
                "contribution_summary": _summary,
            })
        data["council_contributors"] = contributors
        print(f"[SYNTHESIS] Injected {len(contributors)} council_contributors: {[c['phase'] for c in contributors]}")

        # NEW: Post-processing safety parse for tags (in case LLM misses some)
        import re
        decisions = re.findall(r'\[DECISION_CANDIDATE\](.*?)\[/DECISION_CANDIDATE\]', history_text, re.DOTALL)
        risks = re.findall(r'\[RISK_VECTOR\](.*?)\[/RISK_VECTOR\]', history_text, re.DOTALL)
        metrics = re.findall(r'\[METRIC_ANCHOR\](.*?)\[/METRIC_ANCHOR\]', history_text, re.DOTALL)
        
        # Merge safety-extracted tags if they aren't already in the JSON
        if not data.get("intelligence_tags"): data["intelligence_tags"] = {"decisions": [], "risks": [], "metrics": []}
        
        for d in decisions: 
            if d.strip() not in data["intelligence_tags"]["decisions"]: 
                data["intelligence_tags"]["decisions"].append(d.strip())
        for r in risks:
            if r.strip() not in data["intelligence_tags"]["risks"]:
                data["intelligence_tags"]["risks"].append(r.strip())
        for m in metrics:
            if m.strip() not in data["intelligence_tags"]["metrics"]:
                data["intelligence_tags"]["metrics"].append(m.strip())

        return data
    except Exception as e:
        print(f"[SYNTHESIS ERROR] {e}")
        return {"error": "Failed to synthesize structured data."}

# --- PHASE 6: ARTIFACT GENERATION (The Creator) ---
def generate_presentation_preview(synthesized_data, classification, user_id=None):
    """
    Generates a structured JSON outline for a presentation based on synthesized data.
    """
    output_type = classification.get('outputType', 'presentation')
    
    prompt = f"""
    You are a presentation designer. Create a slide deck outline from this data.

    SYNTHESIZED DATA:
    {json.dumps(synthesized_data, indent=2)}

    PRESENTATION TYPE: {output_type}
    DOMAIN: {classification.get('domain', 'business')}

    DESIGN PRINCIPLES:
    1. Title slide + 1-2 slides per major section
    2. Max 5 bullets per slide (3-4 is better)
    3. Use visuals when data supports it
    4. Executive-friendly language
    5. Clear narrative flow

    Return ONLY valid JSON (no markdown):
    {{
      "title": "Main Presentation Title",
      "subtitle": "Subtitle or context",
      "slideCount": 12,
      "estimatedDuration": "10-12 minutes",
      "slides": [
        {{
          "slideNumber": 1,
          "title": "Executive Summary",
          "content": [
            "Bullet 1",
            "Bullet 2"
          ],
          "visualType": "text|chart|diagram|image", 
          "chartData": {{ "type": "bar", "data": [] }},
          "layout": "title|content|two-column|image-text",
          "speakerNotes": "Notes for the presenter"
        }}
      ],
      "metadata": {{
        "theme": "professional|modern|minimal",
        "colorScheme": "blue-green"
      }}
    }}

    Generate { '12-15' if output_type == 'pitch_deck' else '8-12' } slides total.
    """
    
    try:
        resp = call_openai_gpt4(prompt, "Designer", user_id=user_id)
        content = resp['response'].replace('```json', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        print(f"[PRESENTATION PREVIEW ERROR] {e}")
        return {"error": "Failed to generate presentation preview.", "slides": []}

# --- PHASE 7: ARTIFACT GENERATION (The Builder) ---
from pptx import Presentation as PPTXPresentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def _sanitize_pptx_text(text):
    """Replace Unicode symbols that render as squares in default PowerPoint fonts."""
    import re
    if not isinstance(text, str):
        return str(text) if text else ""
    replacements = {
        '\u2022': '-', '\u2023': '-', '\u25aa': '-', '\u25cb': 'o',
        '\u2713': '[X]', '\u2714': '[X]', '\u2717': '[ ]', '\u2718': '[ ]',
        '\u2192': '->', '\u2190': '<-', '\u21d2': '=>',
        '\u2014': '--', '\u2013': '-',
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2026': '...', '\u221e': 'inf', '\u2248': '~=', '\u00b1': '+/-',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    return text


def generate_pptx_file(preview_data):
    """
    Builds a .pptx file from the preview JSON.
    Returns the file path.
    """
    prs = PPTXPresentation()

    # 1. Slide Master Layouts
    title_layout = prs.slide_layouts[0]
    bullet_layout = prs.slide_layouts[1]
    two_col_layout = prs.slide_layouts[3] # Usually 'Two Content' or similar

    slides = preview_data.get('slides', [])

    for slide_data in slides:
        layout_type = slide_data.get('layout', 'content')

        # Select Layout
        if layout_type == 'title':
            slide = prs.slides.add_slide(title_layout)
        elif layout_type == 'two-column':
             slide = prs.slides.add_slide(two_col_layout)
        else:
            slide = prs.slides.add_slide(bullet_layout)

        # Set Title
        title = slide.shapes.title
        if title:
            title.text = _sanitize_pptx_text(slide_data.get('title', 'Untitled Slide'))

        # Set Content (Bullets)
        content_items = [_sanitize_pptx_text(item) for item in slide_data.get('content', [])]

        # Handle Layout Specifics
        if layout_type == 'title':
             # Subtitle is usually the second placeholder
             if len(slide.placeholders) > 1 and content_items:
                 subtitle = slide.placeholders[1]
                 subtitle.text = "\n".join(content_items)

        elif layout_type == 'two-column':
             # Left Column (Text)
             if len(slide.placeholders) > 1:
                 tf = slide.placeholders[1].text_frame
                 tf.text = content_items[0] if content_items else ""
                 for item in content_items[1:]:
                     p = tf.add_paragraph()
                     p.text = item
                     p.level = 0

             # Right Column (Chart Placeholder or Text)
             if len(slide.placeholders) > 2:
                 tf2 = slide.placeholders[2].text_frame
                 if slide_data.get('chartData'):
                     tf2.text = f"[CHART: {slide_data['chartData'].get('type', 'Chart')}]"
                 else:
                     tf2.text = ""

        else: # Standard Bullet Content
            if len(slide.placeholders) > 1:
                tf = slide.placeholders[1].text_frame
                tf.text = content_items[0] if content_items else ""
                for item in content_items[1:]:
                    p = tf.add_paragraph()
                    p.text = item
                    p.level = 0

        # Set font on all text frames to ensure consistent rendering
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Calibri'
                        run.font.size = Pt(14)

        # Speaker Notes
        if slide_data.get('speakerNotes'):
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = _sanitize_pptx_text(slide_data['speakerNotes'])

    # Save File
    filename = f"korum_artifact_{int(datetime.now().timestamp())}.pptx"
    filepath = os.path.join(os.getcwd(), filename)
    prs.save(filepath)

    return filename # Return relative name for download


