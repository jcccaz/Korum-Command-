
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PERPLEXITY_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}

try:
    resp = requests.get("https://api.perplexity.ai/models", headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        models = resp.json().get('data', [])
        for m in models:
            print(f"- {m['id']}")
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")
