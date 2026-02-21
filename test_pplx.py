
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PERPLEXITY_API_KEY")
print(f"Testing Perplexity with key: {api_key[:10]}...")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Testing with sonar which is the basic model, or sonar-pro
models = ["sonar-pro", "sonar", "llama-3.1-sonar-small-128k-online"]

for model in models:
    print(f"\n--- Testing model: {model} ---")
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Be precise."},
            {"role": "user", "content": "How many fingers does a human have?"}
        ]
    }
    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=30)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print("Response:", resp.json()['choices'][0]['message']['content'][:100])
        else:
            print("Error:", resp.text)
    except Exception as e:
        print(f"Exception: {e}")
