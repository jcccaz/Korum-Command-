
import os
import requests
from dotenv import load_dotenv

# Force load .env from current directory
load_dotenv(override=True)

def mask(key):
    if not key: return "MISSING"
    return f"{key[:6]}...{key[-4:]}"

print("\n--- API KEY DIAGNOSTICS ---\n")

# 1. OPENAI (The Strategist)
openai_key = os.getenv("OPENAI_API_KEY")
print(f"OPENAI_API_KEY: {mask(openai_key)}")

if openai_key:
    print("Testing OpenAI Connection...")
    headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-3.5-turbo", # Cheap model for ping
        "messages": [{"role": "user", "content": "Ping"}],
        "max_tokens": 5
    }
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            print("[OK] OpenAI: SUCCESS")
        else:
            print(f"[FAIL] OpenAI: ({resp.status_code}) - {resp.text[:100]}")
    except Exception as e:
        print(f"[FAIL] OpenAI: ERROR - {e}")
else:
    print("[FAIL] OpenAI: Key Missing")

print("-" * 20)

# 2. MISTRAL API (The Failsafe)
mistral_key = os.getenv("MISTRAL_API_KEY")
print(f"MISTRAL_API_KEY: {mask(mistral_key)}")

if mistral_key:
    print("Testing Mistral API Connection...")
    headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
    data = {
        "model": "mistral-tiny", # Fast model for ping
        "messages": [{"role": "user", "content": "Ping"}],
        "max_tokens": 5
    }
    try:
        resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            print("[OK] Mistral API: SUCCESS")
        else:
            print(f"[FAIL] Mistral API: ({resp.status_code}) - {resp.text[:100]}")
    except Exception as e:
        print(f"[FAIL] Mistral API: ERROR - {e}")
else:
    print("[WARN] Mistral API: Key Missing (Failsafe disabled)")

print("-" * 20)

# 3. PERPLEXITY
pplx_key = os.getenv("PERPLEXITY_API_KEY")
print(f"PERPLEXITY_API_KEY: {mask(pplx_key)}", flush=True)

if pplx_key:
    print("Testing Perplexity Connection...", flush=True)
    headers = {"Authorization": f"Bearer {pplx_key}", "Content-Type": "application/json"}
    data = {
        "model": "sonar",
        "messages": [{"role": "user", "content": "Ping"}]
    }
    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            print("[OK] Perplexity: SUCCESS", flush=True)
        else:
            print(f"[FAIL] Perplexity: ({resp.status_code}) - {resp.text[:100]}", flush=True)
    except Exception as e:
        print(f"[FAIL] Perplexity: ERROR - {e}", flush=True)
else:
    print("[FAIL] Perplexity: Key Missing", flush=True)

print("-" * 20)

# 2. ANTHROPIC
claude_key = os.getenv("ANTHROPIC_API_KEY")
print(f"ANTHROPIC_API_KEY: {mask(claude_key)}")

if claude_key:
    print("Testing Anthropic Connection...")
    headers = {"x-api-key": claude_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    data = {
        "model": "claude-3-haiku-20240307",
        "messages": [{"role": "user", "content": "Ping"}],
        "max_tokens": 10
    }
    try:
        resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            print("[OK] Anthropic: SUCCESS")
        else:
            print(f"[FAIL] Anthropic: ({resp.status_code}) - {resp.text[:100]}")
    except Exception as e:
        print(f"[FAIL] Anthropic: ERROR - {e}")
else:
    print("[FAIL] Anthropic: Key Missing")

print("-" * 20)

# 3. GEMINI
google_key = os.getenv("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY: {mask(google_key)}")

if google_key:
    print("Testing Gemini Connection...")
    # gemini-2.0-flash on v1beta is the working model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={google_key}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": "Ping"}]}]}
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        if resp.status_code == 200:
            print("[OK] Gemini (2.0 Flash): SUCCESS")
        else:
            print(f"[FAIL] Gemini: ({resp.status_code})")
    except Exception as e:
        print(f"[FAIL] Gemini: ERROR - {e}")
else:
    print("[FAIL] Gemini: Key Missing")

print("-" * 20)

# 4. LOCAL (LM STUDIO)
print("LOCAL (LM STUDIO) Connection Check:")
try:
    base_url = os.getenv("LOCAL_LLM_URL", "http://localhost:1234")
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "local-model",
        "messages": [{"role": "user", "content": "Ping"}],
        "temperature": 0.7,
        "max_tokens": 10
    }
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    if resp.status_code == 200:
        model_id = resp.json().get('model', 'unknown-local-model')
        print(f"[OK] Local Server: ONLINE (Model: {model_id})")
    else:
        print(f"[FAIL] Local Server: ERROR ({resp.status_code})")
except requests.exceptions.ConnectionError:
    print("[FAIL] Local Server: OFFLINE (LM Studio not running on port 1234)")
except Exception as e:
    print(f"[FAIL] Local Server: ERROR - {e}")

print("\n---------------------------\n")
