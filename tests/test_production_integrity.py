
import os
import json
from engine_v2 import classify_query_v2, WORKFLOW_STEPS
from dotenv import load_dotenv

load_dotenv()

def test_deterministic_classification():
    print("\n--- TEST: DETERMINISTIC CLASSIFICATION ---")
    active_personas = {
        "openai": "Strategist",
        "anthropic": "Architect",
        "google": "Critic",
        "perplexity": "Scout",
        "mistral": "Analyst"
    }
    active_models = ["openai", "anthropic", "google", "perplexity", "mistral"]

    # Test FINANCE
    plan1 = classify_query_v2("What is our burn rate?", active_personas, active_models=active_models, workflow="FINANCE")
    plan2 = classify_query_v2("What is our burn rate?", active_personas, active_models=active_models, workflow="FINANCE")

    expected = WORKFLOW_STEPS["FINANCE"]
    
    print(f"FINANCE Plan 1: {plan1['executionOrder']}")
    print(f"FINANCE Plan 2: {plan2['executionOrder']}")
    
    assert plan1['executionOrder'] == expected, "Plan 1 mismatch"
    assert plan2['executionOrder'] == expected, "Plan 2 mismatch"
    assert plan1['executionOrder'] == plan2['executionOrder'], "Non-deterministic result!"
    print("✅ FINANCE Deterministic: PASS")

    # Test WAR_ROOM
    plan_war = classify_query_v2("Nuclear threat detected", active_personas, active_models=active_models, workflow="WAR_ROOM")
    print(f"WAR_ROOM Plan: {plan_war['executionOrder']}")
    assert plan_war['executionOrder'] == WORKFLOW_STEPS["WAR_ROOM"], "WAR_ROOM mismatch"
    print("✅ WAR_ROOM Deterministic: PASS")

def test_falcon_mimir_injection():
    print("\n--- TEST: FALCON MIMIR INJECTION ---")
    from engine_v2 import _build_mimir_block
    
    ghost_map = {
        "token_inventory": [{"token": "[PERSON_01]", "entity_type": "PERSON", "source_pass": 1}],
        "by_type": {"PERSON": ["[PERSON_01]"]},
        "total_redacted": 1,
        "high_risk_types": [],
        "falcon_level": "STANDARD"
    }
    residual_report = {"residual_count": 0, "residuals": [], "audit_note": "Clean"}
    
    block = _build_mimir_block(ghost_map, residual_report)
    print(block[:200] + "...")
    
    assert "MIMIR PROTOCOL" in block
    assert "[PERSON_01]" in block
    assert "PII_DIFF_CLEAN" in block
    print("✅ MIMIR Block Generation: PASS")

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    try:
        test_deterministic_classification()
        test_falcon_mimir_injection()
        print("\n" + "="*50)
        print("PRODUCTION INTEGRITY AUDIT: ALL CORE PASS")
        print("="*50)
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
