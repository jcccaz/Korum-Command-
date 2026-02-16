
import sys
import time
from unittest.mock import MagicMock, patch

# Mock the environment variables before importing anything that uses them
import os
os.environ["OPENAI_API_KEY"] = "fake-key"
os.environ["MISTRAL_API_KEY"] = "fake-mistral-key"

# Mocks for llm_core components
# We need to patch these BEFORE importing engine_v2 if it imports them at top level
# But engine_v2 imports them. 

print("\n--- TEST: UNIVERSAL FALLBACK SYSTEM ---\n")

# Import the engine
try:
    from engine_v2 import execute_council_v2
    import llm_core
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_fallback_chain():
    print("SCENARIO 1: Primary Fails -> Mistral Takes Over")
    
    # 1. Mock OpenAI to FAIL
    def mock_fail(*args, **kwargs):
        print("   [MOCK] OpenAI: FAILED (Simulated)")
        return {"success": False, "error": "Simulated outage"}

    # 2. Mock Mistral to SUCCEED
    def mock_mistral_success(*args, **kwargs):
        print("   [MOCK] Mistral: SUCCESS (Fallback Triggered!)")
        return {"success": True, "response": "Mistral Analysis (Fallback)", "model": "mistral-large"}

    # Apply patches
    with patch('engine_v2.call_openai_gpt4', side_effect=mock_fail), \
         patch('engine_v2.call_mistral_api', side_effect=mock_mistral_success), \
         patch('engine_v2.classify_query_v2', return_value={
             "executionOrder": ["openai-strategist"]
         }):
        
        # Execute
        result = execute_council_v2("Test Query", {})
        
        # Verify
        openai_res = result['results'].get('openai', {})
        res_text = openai_res.get('response', '')
        
        if "[FALLBACK: ANALYST]" in res_text:
            print("\n✅ PASS: Mistral took over when OpenAI failed.")
            print(f"   Response: {res_text}")
        else:
            print("\n❌ FAIL: Mistral did not take over.")
            print(f"   Result: {openai_res}")

    print("\n" + "="*30 + "\n")

    print("SCENARIO 2: Primary & Mistral Fail -> Local Oracle Takes Over")

    # 3. Mock Mistral to FAIL too
    def mock_mistral_fail(*args, **kwargs):
        print("   [MOCK] Mistral: FAILED (Simulated)")
        return {"success": False, "error": "Simulated Cloud Outage"}

    # 4. Mock Local to SUCCEED
    def mock_local_success(*args, **kwargs):
        print("   [MOCK] Local: SUCCESS (Emergency Triggered!)")
        return {"success": True, "response": "Local Oracle Analysis", "model": "local-mistral"}

    with patch('engine_v2.call_openai_gpt4', side_effect=mock_fail), \
         patch('engine_v2.call_mistral_api', side_effect=mock_mistral_fail), \
         patch('engine_v2.call_local_llm', side_effect=mock_local_success), \
         patch('engine_v2.classify_query_v2', return_value={
             "executionOrder": ["openai-strategist"]
         }):

        # Execute
        result = execute_council_v2("Test Query 2", {})
        
        # Verify
        openai_res = result['results'].get('openai', {})
        res_text = openai_res.get('response', '')
        
        if "[FALLBACK: ORACLE]" in res_text:
            print("\n✅ PASS: Local Oracle took over when Cloud failed.")
            print(f"   Response: {res_text}")
        else:
            print("\n❌ FAIL: Local Oracle did not take over.")
            print(f"   Result: {openai_res}")

if __name__ == "__main__":
    try:
        test_fallback_chain()
        print("\n--- TEST COMPLETE ---")
    except Exception as e:
        print(f"\nTEST CRASHED: {e}")
