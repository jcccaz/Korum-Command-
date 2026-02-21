
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = os.getenv("MISTRAL_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get("https://api.mistral.ai/v1/models", headers=headers)
        if resp.status_code == 200:
            models = [m['id'] for m in resp.json()['data']]
            print("Available Models:")
            for m in sorted(models):
                print(f" - {m}")
        else:
            print(f"Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    list_models()
