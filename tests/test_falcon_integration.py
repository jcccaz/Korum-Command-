import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
import time

# Simulation of what app.py does when Falcon is ON
def test_falcon_integration_flow():
    print("\n--- TEST: FALCON END-TO-END FLOW ---")
    
    # 1. User sends PII
    raw_query = "Contact Sarah Martinez at sarah.martinez@verizon.com or 443-555-0199 about account 770023891."
    
    # 2. Falcon Preprocess (Simulated server-side)
    from falcon import falcon_preprocess, build_ghost_map_summary, detect_residual_pii
    
    print("Pre-processing with Falcon (STANDARD)...")
    falcon_result = falcon_preprocess(raw_query, level="STANDARD")
    redacted_text = falcon_result.redacted_text
    placeholder_map = falcon_result.placeholder_map
    
    print(f"Redacted Text: {redacted_text}")
    
    # 3. Build Ghost Map
    ghost_map = build_ghost_map_summary(falcon_result)
    residual_report = detect_residual_pii(redacted_text, falcon_result)
    
    # 4. Run Council (Dry run - check prompt construction)
    from engine_v2 import execute_council_v2, build_council_prompt, CouncilContext
    
    # Mocking personas
    active_personas = {"openai": "Analyst", "anthropic": "Architect"}
    
    print("\nVerifying Prompt Construction with MIMIR...")
    classification = {"executionOrder": ["openai-analyst"], "intent": "analyze"}
    context = CouncilContext(redacted_text, classification, workflow="RESEARCH", 
                            ghost_map=ghost_map, residual_report=residual_report)
    
    prompt = build_council_prompt(context, "openai", "Analyst", 0, 1)
    
    # Verification
    if "MIMIR PROTOCOL" in prompt and "[PERSON_" in prompt:
        print("[PASS] SUCCESS: MIMIR block injected correctly with Ghost Map tokens.")
    else:
        print("[FAIL] FAILURE: MIMIR block or tokens missing from prompt.")
        print(f"PROMPT START: {prompt[:300]}")

    # 5. Re-hydration check
    from falcon import falcon_rehydrate
    rehydrated = falcon_rehydrate(redacted_text, placeholder_map)
    if rehydrated.strip() == raw_query.strip():
        print("[PASS] SUCCESS: Re-hydration restores original PII.")
    else:
        print("[FAIL] FAILURE: Re-hydration mismatch.")
        print(f"Original: {raw_query}")
        print(f"Hydrated: {rehydrated}")

if __name__ == "__main__":
    test_falcon_integration_flow()
