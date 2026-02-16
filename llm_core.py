
import os
import requests
import time
import json
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# --- RETRY DECORATOR ---
def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        print(f"[{func.__name__}] Failed after {retries} retries: {e}")
                        return {"success": False, "response": str(e)}
                    sleep_time = (backoff_in_seconds * 2 ** x)
                    print(f"[{func.__name__}] Error: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    x += 1
        return wrapper
    return decorator

# --- PROVIDER HELPERS ---

@retry_with_backoff()
def call_openai_gpt4(prompt, role, model="gpt-4o"):
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"You are {role}. Provide expert, concise, high-impact analysis."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    # Increased timeout to 60s
    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['choices'][0]['message']['content'], "model": model}
    
    # Trigger retry for server errors or rate limits
    if resp.status_code in [429, 500, 502, 503, 504]:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
        
    return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}

@retry_with_backoff()
def call_anthropic_claude(prompt, role, model="claude-sonnet-4-20250514"):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": f"Role: {role}\n\n{prompt}"}],
        "max_tokens": 4096,
        "temperature": 0.7
    }
    resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['content'][0]['text'], "model": model}
        
    if resp.status_code in [429, 500, 502, 503, 504]:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
        
    return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}

@retry_with_backoff()
def call_google_gemini(prompt, role, model="gemini-2.0-flash"):
    api_key = os.getenv("GOOGLE_API_KEY")
    # v1beta required for gemini-2.0-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": f"Role: {role}\n\n{prompt}"}]}]
    }
    resp = requests.post(url, headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['candidates'][0]['content']['parts'][0]['text'], "model": model}
        
    if resp.status_code in [429, 500, 502, 503, 504]:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
        
    return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}

@retry_with_backoff()
def call_perplexity(prompt, role, model="llama-3.1-sonar-large-128k-online"):
    api_key = os.getenv("PERPLEXITY_API_KEY")
    # Added User-Agent to bypass Cloudflare bot protection
    headers = {
        "Authorization": f"Bearer {api_key}", 
        "Content-Type": "application/json",
        "User-Agent": "KorumOS/2.0 (Client)"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"You are {role}. Provide accurate, sourced information."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['choices'][0]['message']['content'], "model": model}
        
    if resp.status_code in [429, 500, 502, 503, 504]:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
        
    return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}

def call_local_llm(prompt, role, model="local-model"):
    """
    Calls a local LLM running via LM Studio (or compatible OpenAI-API local server).
    Defaults to localhost:1234
    """
    url = "http://localhost:1234/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Simple retry logic for local (sometimes it's just busy)
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are {role}. Provide clear, short answers."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            # Short timeout ensuring we don't hang if server is dead, but enough for processing
            resp = requests.post(url, headers=headers, json=data, timeout=120) 
            
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                return {"success": True, "response": content, "model": "local-mistral"}
            
            return {"success": False, "response": f"Local Error {resp.status_code}: {resp.text}"}
            
        except requests.exceptions.ConnectionError:
            return {"success": False, "response": "Local Logic Failed: LM Studio not running on port 1234."}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            return {"success": False, "response": f"Local Exception: {str(e)}"}

@retry_with_backoff()
def call_mistral_api(prompt, role, model="mistral-large-latest"):
    """
    Calls the official Mistral AI API (Cloud Fail-Safe).
    """
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return {"success": False, "response": "Mistral API Key missing."}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"You are {role}. Provide expert analysis."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    # Mistral API endpoint
    resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['choices'][0]['message']['content'], "model": model}
        
    if resp.status_code in [429, 500, 502, 503, 504]:
         raise Exception(f"Mistral API Error {resp.status_code}: {resp.text}")

    return {"success": False, "response": f"Mistral Error {resp.status_code}: {resp.text}"}


