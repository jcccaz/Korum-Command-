import os
import sys
import json
import time
from engine_v2 import execute_council_v2, CouncilContext
from app import app

# KORUM PRODUCTION STABILIZATION - CONSISTENCY AUDIT (Section 11)
# -------------------------------------------------------------------
# Goal: Ensure 80-90% consistency across identical prompts.
# -------------------------------------------------------------------

QUERY = "Assess the risk of quantum decryption on legacy government databases by 2030."

def run_audit():
    print("=" * 70)
    print("KORUM OS: SYSTEM CONSISTENCY AUDIT")
    print("OBJECTIVE: Verify Deterministic Output and Decision Enforcement")
    print("=" * 70)
    
    results = []
    
    with app.app_context():
        for i in range(1, 4):
            print(f"\n[AUDIT] PASS {i}/3 Initiated...")
            
            # Setup Deterministic Context
            # Note: execute_council_v2 handles context internally, so we just pass params
            active_models = ["openai", "google", "mistral"]
            active_personas = {
                "openai": "ciso",
                "google": "security_auditor",
                "mistral": "compliance"
            }

            try:
                # Use a fresh run_id per pass but same session_id to test continuity
                run_id = f"audit_pass_{i}_{int(time.time())}"
                output = execute_council_v2(
                    QUERY,
                    active_personas,
                    workflow="QUANTUM_SECURITY",
                    active_models=active_models,
                    run_id=run_id,
                    session_id="audit_session_001"
                )
                results.append(output)
                print(f"[AUDIT] Pass {i} Completed successfully.")
            except Exception as e:
                print(f"[AUDIT ERROR] Pass {i} Failed: {e}")
                import traceback
                traceback.print_exc()
                return

    # ──── COMPARISON ENGINE ────
    if not results:
        print("❌ NO RESULTS TO ANALYZE.")
        return

    # 1. Structural Identity (Section Consistency)
    section_sets = []
    for r in results:
        synthesis = r.get('synthesis', {})
        if isinstance(synthesis, dict):
            section_sets.append(set(synthesis.get('sections', {}).keys()))

    if len(section_sets) == 3:
        if section_sets[0] == section_sets[1] == section_sets[2]:
            print(f"✅ STRUCTURAL IDENTITY (100%): All passes produced section headers: {list(section_sets[0])}")
        else:
            print(f"❌ STRUCTURAL DRIFT: Section headers do not match between passes.")

    # 2. Normalization Layer (Structured Data Check)
    table_counts = []
    for r in results:
        table_matches = str(r).count("[STRUCTURED_TABLE]")
        table_counts.append(table_matches)
    
    if all(c > 0 for c in table_counts):
        print(f"✅ NORMALIZATION LAYER ACTIVE: Structure tags detected {table_counts} times across passes.")
    else:
        print(f"❌ NORMALIZATION LAYER FAILURE: No [STRUCTURED_TABLE] tags found.")

    # 3. Decision Enforcement (Hedging Check)
    hedging_terms = ["might", "could", "perhaps", "possibly", "it depends", "not clear"]
    found_hedges = []
    for r in results:
        text = str(r).lower()
        for term in hedging_terms:
            if term in text:
                found_hedges.append(term)
    
    if not found_hedges:
        print(f"✅ DECISION ENFORCEMENT: No hedging and vague language detected.")
    else:
        print(f"⚠️ HEDGING DETECTED: Found tokens {set(found_hedges)}")

    # 4. Finalizer Pass Check (Mistral Exclusion)
    mistral_visible = [r.get('results', {}).get('mistral') for r in results]
    if all(m is None or not m.get('success') for m in mistral_visible):
        print(f"✅ HIDDEN FINALIZER: Mistral excluded from visible council results.")
    else:
        print(f"❌ HIDDEN FINALIZER FAILURE: Mistral detected in visible results map.")

    print("\n" + "=" * 70)
    print("CONSISTENCY AUDIT COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        run_audit()
    else:
        print("Script ready. To run full 3-pass audit, use: python consistency_audit.py --run")
        print("NOTE: This will consume API credits for all configured providers.")
