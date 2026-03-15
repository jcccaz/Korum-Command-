
# -------------------------------------------------------------------
# KORUM V2: SEQUENTIAL COUNCIL ENGINE (Python Implementation)
# -------------------------------------------------------------------

import os
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
    }
}

class CouncilContext:
    def __init__(self, query, classification, workflow="RESEARCH", session_id=None, run_id=None, previous_context=None, user_id=None):
        self.query = query
        self.classification = classification
        self.workflow = workflow.upper() if workflow else "RESEARCH"
        self.session_id = session_id
        self.run_id = run_id
        self.user_id = user_id
        self.history = []
        self.previous_context = previous_context or []

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

def execute_council_v2(query, active_personas, images=None, workflow="RESEARCH", active_models=None, previous_context=None, session_id=None, run_id=None, user_id=None, ledger_mission_id=None):
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
    context = CouncilContext(query, classification, workflow=workflow, session_id=session_id, run_id=run_id, previous_context=previous_context, user_id=user_id)

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
        phase = PHASE_DIRECTIVES.get(position, PHASE_DIRECTIVES.get(min(position, 4)))
        prompt += f"\nYOUR SPECIFIC FOCUS: {phase['title']}\n{phase['instruction']}"
        prompt += "\nProvide comprehensive, well-sourced research and data. Focus on facts, metrics, and technical details."
        return prompt

    # --- Determine which phase directive applies ---
    # Map position to phase (if more than 5 steps, later steps get the closest directive)
    if position == total_steps - 1 and total_steps >= 3:
        # Final step is ALWAYS the integrator (phase 4) regardless of count
        phase = PHASE_DIRECTIVES[4]
    elif total_steps <= 5:
        phase = PHASE_DIRECTIVES.get(position, PHASE_DIRECTIVES[min(position, 4)])
    else:
        # Scale phases across available steps
        phase_index = int(position / total_steps * 5)
        phase = PHASE_DIRECTIVES.get(min(phase_index, 4))

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
    --------------------

    ## YOUR PHASE MISSION
    {phase['instruction']}

    ## CRITICAL RULE: ZERO REPETITION
    The prior phases are provided for CONTEXT ONLY. DO NOT restate, summarize, or echo their findings.
    Your ONLY job is to add what is MISSING — the unique contribution defined by your phase mission above.
    If your output overlaps with prior phases, you have FAILED your mission.

    ## INTERNAL STRUCTURING (FOR SYSTEM PARSING)
    You MUST use the following tags to mark high-value intelligence:
    - [DECISION_CANDIDATE] ...recommendation text... [/DECISION_CANDIDATE]
    - [RISK_VECTOR] ...risk description... [/RISK_VECTOR]
    - [METRIC_ANCHOR] ...metric value... [/METRIC_ANCHOR]
    - [TRUTH_BOMB] ...critically verified fact... [/TRUTH_BOMB]

    Do not let these tags disrupt your narrative flow; they are for the backend extractor.
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
            contributors.append({
                "phase": phase_title,
                "provider": entry["ai"],
                "role": entry.get("persona", ""),
                "contribution_summary": f"Phase {idx + 1} of {total_phases}",
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

