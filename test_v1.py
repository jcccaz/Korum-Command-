
import os
from dotenv import load_dotenv
from app import app
from llm_core import call_openai_gpt4

load_dotenv()

def test_v1_minimal():
    print("=" * 50)
    print("KORUM OS: V1 LEGACY SANITY CHECK")
    print("=" * 50)
    
    with app.app_context():
        # Minimal V1 simulation (call_openai directly)
        try:
            res = call_openai_gpt4("Confirm status.", "analyst")
            if res.get('success'):
                print(f"✅ V1 CORE SUCCESS: {res.get('model')} responded.")
            else:
                print(f"❌ V1 CORE FAILURE: {res.get('response')}")
        except Exception as e:
            print(f"❌ V1 CORE EXCEPTION: {e}")

if __name__ == "__main__":
    test_v1_minimal()
