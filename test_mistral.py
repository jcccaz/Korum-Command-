
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_mistral(model="mistral-large-latest"):
    api_key = os.getenv("MISTRAL_API_KEY")
    print(f"Testing Mistral model: {model}")
    print(f"Key: {api_key[:6]}...{api_key[-4:] if api_key else 'NONE'}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Say hello briefly."}
        ]
    }
    
    try:
        resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=10)
        print(f"HTTP {resp.status_code}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mistral("mistral-large-latest")
    print("\n--- Trying Small ---")
    test_mistral("mistral-small-latest")
    print("\n--- Trying 7B ---")
    test_mistral("open-mistral-7b")
