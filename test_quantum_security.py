
import json
import os
import sys
from dotenv import load_dotenv

# Ensure we can import from core
sys.path.append(os.getcwd())

load_dotenv()

from engine_v2 import execute_council_v2

def run_quantum_test():
    print("INITIALIZING FIPS 203/204 QUANTUM COMPLIANCE TEST")
    print("SCENARIO: Attacker attempting TLS 1.3 downgrade to RSA-2048 (Downgrade Attack).")
    
    query = """
    Analyze the following security event:
    An external actor is attempting to force a TLS 1.3 connection to downgrade to a legacy RSA-2048 suite on our primary data gateway. 
    Assess the risk in a March 2026 threat landscape and provide a NIST-compliant migration recommendation.
    """
    
    personas = {
        "openai": "Strategist",
        "anthropic": "Architect",
        "google": "Critic",
        "mistral": "Analyst"
    }
    
    try:
        print("DISPATCHING TO COUNCIL...")
        results = execute_council_v2(query, personas, workflow="QUANTUM_SECURITY")
        
        print("\n--- TEST RESULTS ---")
        synthesis = results.get('synthesis', {})
        meta = synthesis.get('meta', {})
        summary = meta.get('summary', '')
        
        print(f"TITLE: {meta.get('title')}")
        print(f"TRUTH SCORE: {meta.get('composite_truth_score')}/100")
        
        # Success Metrics
        hndl_detected = "HNDL" in summary or "Harvest" in summary or "decrypt later" in summary.lower()
        pqc_recommended = "ML-KEM" in summary or "Kyber" in summary or "FIPS 203" in summary
        
        print(f"\n[METRIC] HNDL/Harvest Awareness: {'PASSED' if hndl_detected else 'FAILED'}")
        print(f"[METRIC] PQC Migration (ML-KEM/Kyber): {'PASSED' if pqc_recommended else 'FAILED'}")
        
        if hndl_detected and pqc_recommended:
            print("\nMISSION SUCCESS: The council successfully identified the quantum-threat and recommended FIPS-compliant mitigation.")
        else:
            print("\nMISSION PARTIAL: The council logic might need further DNA tuning for March 2026 standards.")
            
        return results
        
    except Exception as e:
        print(f"TEST ERROR: {e}")
        return None

if __name__ == "__main__":
    run_quantum_test()
