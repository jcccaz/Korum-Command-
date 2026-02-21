
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_model(model):
    api_key = os.getenv("MISTRAL_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}]
    }
    try:
        resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=10)
        return resp.status_code, resp.text
    except Exception as e:
        return 0, str(e)

models = ["mistral-small-latest", "mistral-medium-latest", "open-mistral-7b", "mistral-large-latest"]
for m in models:
    status, text = test_model(m)
    print(f"Model: {m} -> Status: {status}")
    if status != 200:
        print(f"  Response: {text}")
    else:
        print(f"  Success!")
