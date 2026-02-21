
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PERPLEXITY_API_KEY")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

models = [
    "sonar", 
    "sonar-pro", 
    "sonar-reasoning", 
    "sonar-reasoning-pro",
    "llama-3.1-sonar-small-128k-online",
    "llama-3.1-sonar-large-128k-online",
]

for model in models:
    print(f"Testing {model}...", flush=True)
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    }
    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=10)
        print(f"  HTTP {resp.status_code}")
        if resp.status_code == 200:
            print(f"  SUCCESS")
        else:
            print(f"  Fail: {resp.text[:100]}")
    except Exception as e:
        print(f"  Exception: {e}")
