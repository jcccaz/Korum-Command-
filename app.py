import os
import json
import requests
import concurrent.futures
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# GOOGLE IPv4 FIX: Force IPv4 to prevent socket hangs
import socket
_old_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _old_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only_getaddrinfo

# Initialize
load_dotenv()
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- Configuration ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
PERPLEXITY_KEY = os.getenv("PERPLEXITY_API_KEY")

# --- Model Clients ---
# Initialize Clients lazily or per request to handle potential missing keys gracefully
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_KEY, timeout=90.0) if OPENAI_KEY else None
except ImportError:
    openai_client = None

try:
    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY, timeout=90.0) if ANTHROPIC_KEY else None
except ImportError:
    anthropic_client = None

try:
    from google import genai
    google_client = genai.Client(api_key=GOOGLE_KEY) if GOOGLE_KEY else None
except ImportError:
    google_client = None

# --- V1 Council Functions ---

def call_openai_gpt4(prompt, role="strategist"):
    if not openai_client: return {"success": False, "error": "API Key Missing"}
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are acting as the {role.upper()} of the Neural Council. Provide a direct, high-level strategic response."},
                {"role": "user", "content": prompt}
            ]
        )
        print(f"✅ OpenAI Success")
        return {"success": True, "response": response.choices[0].message.content, "model": "GPT-4o", "cost": 0.01}
    except Exception as e:
        print(f"❌ OpenAI Error: {str(e)}")
        return {"success": False, "error": str(e)}

def call_anthropic_claude(prompt, role="architect"):
    if not anthropic_client: return {"success": False, "error": "API Key Missing"}

    # Try models in order of preference
    models_to_try = [
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
    ]

    for model_id, display_name in models_to_try:
        try:
            message = anthropic_client.messages.create(
                model=model_id,
                max_tokens=1024,
                system=f"You are the {role.upper()}. Focus on structure, safety, and implementation details.",
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Anthropic Success (Model: {model_id})")
            return {"success": True, "response": message.content[0].text, "model": display_name, "cost": 0.01}
        except Exception as e:
            print(f"⚠️ Model {model_id} failed: {str(e)[:50]}, trying next...")
            continue

    return {"success": False, "error": "All Claude models failed"}

def call_google_gemini(prompt, role="critic"):
    if not google_client: return {"success": False, "error": "API Key Missing"}
    try:
        chosen_model = "gemini-2.0-flash"  # Current stable model

        response = google_client.models.generate_content(
            model=chosen_model,
            contents=f"Role: {role.upper()}. Task: {prompt}"
        )

        print(f"✅ Gemini Success (Model: {chosen_model})")
        return {"success": True, "response": response.text, "model": chosen_model, "cost": 0.00}
    except Exception as e:
        print(f"❌ Gemini Error: {str(e)}")
        return {"success": False, "error": str(e)}

def call_perplexity(prompt, role="intel"):
    if not PERPLEXITY_KEY: return {"success": False, "error": "API Key Missing"}
    try:
        headers = {"Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": f"You represent {role.upper()}. Be concise and factual. Cite sources if possible."},
                {"role": "user", "content": prompt}
            ]
        }
        response = requests.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers)
        data = response.json()
        if "choices" in data:
            print(f"✅ Perplexity Success")
            return {"success": True, "response": data["choices"][0]["message"]["content"], "model": "Perplexity Sonar", "cost": 0.00}
        print(f"❌ Perplexity Error: Invalid Response {data}")
        return {"success": False, "error": "Invalid API Response"}
    except Exception as e:
        print(f"❌ Perplexity Error: {str(e)}")
        return {"success": False, "error": str(e)}

# --- Routes ---

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/js/<path:path>')
def serve_js(path):
    return send_from_directory('js', path)

@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory('css', path)

@app.route('/api/ask', methods=['POST'])
def ask_council():
    data = request.json
    query = data.get('question')
    roles = data.get('council_roles', {})
    
    # Map roles to functions
    futures = {}
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures['openai'] = executor.submit(call_openai_gpt4, query, roles.get('openai', 'strategist'))
        futures['anthropic'] = executor.submit(call_anthropic_claude, query, roles.get('anthropic', 'architect'))
        futures['google'] = executor.submit(call_google_gemini, query, roles.get('google', 'critic'))
        futures['perplexity'] = executor.submit(call_perplexity, query, roles.get('perplexity', 'intel'))

        for key, future in futures.items():
            results[key] = future.result()

    # Determine Consensus (Simple Mock Logic for Standalone MVP)
    # Ideally, this would use another LLM call to synthesize based on results
    consensus = "COUNCIL CONVENED. Review individual agent outputs for detailed analysis. Synthesis pending V2 Integration."

    return jsonify({
        "consensus": consensus,
        "results": results
    })

@app.route('/api/v2/reasoning_chain', methods=['POST'])
def reasoning_chain():
    # Placeholder for V2 Logic - Connected to simple sequential calls for MVP Standalone
    data = request.json
    query = data.get('query')
    hacker_mode = data.get('hacker_mode', False)
    
    # Simulate chain for immediate responsiveness (Real logic requires complex orchestration)
    # Step 1: Deconstruct (Claude)
    r1 = call_anthropic_claude(f"DECONSTRUCT this request into core constraints and goals: {query}", "analyst")
    
    # Step 2: Architecture (GPT-4)
    r2 = call_openai_gpt4(f"Based on: {query}. Create a high-level solution ARCHITECTURE.", "architect")
    
    # Step 3: Stress Test (Gemini)
    r3 = call_google_gemini(f"STRESS TEST this concept: {query}. Identify failure modes.", "critic")
    
    # Step 4: Execution (GPT-4)
    r4 = call_openai_gpt4(f"Synthesize a final EXECUTION PLAN for: {query}", "executive")

    # Step optional: Hacker
    r3_5 = None
    if hacker_mode:
        r3_5 = call_google_gemini(f"RED TEAM EXPLOIT: {query}. How can this be broken?", "hacker")
    
    return jsonify({
        "success": True,
        "pipeline_result": {
            "constraints": r1.get('response', "Failed"),
            "standard_solution": r2.get('response', "Failed"),
            "failure_analysis": r3.get('response', "Failed"),
            "exploit_poc": r3_5.get('response') if r3_5 else None,
            "final_artifact": r4.get('response', "Failed"),
            "metrics": {
                "deconstruct": {"cost": 0.01, "time": 1.2},
                "build": {"cost": 0.01, "time": 1.5},
                "stress": {"cost": 0.00, "time": 0.8},
                "synthesize": {"cost": 0.02, "time": 2.0}
            }
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
