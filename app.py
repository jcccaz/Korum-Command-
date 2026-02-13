import os
import json
import requests
import concurrent.futures
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

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
    openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
except ImportError:
    openai_client = None

try:
    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None
except ImportError:
    anthropic_client = None

try:
    import google.generativeai as genai
    if GOOGLE_KEY:
        genai.configure(api_key=GOOGLE_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp') 
    else:
        gemini_model = None
except ImportError:
    gemini_model = None

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
        return {"success": True, "response": response.choices[0].message.content, "model": "GPT-4o", "cost": 0.01}
    except Exception as e:
        return {"success": False, "error": str(e)}

def call_anthropic_claude(prompt, role="architect"):
    if not anthropic_client: return {"success": False, "error": "API Key Missing"}
    try:
        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=f"You are the {role.upper()}. Focus on structure, safety, and implementation details.",
            messages=[{"role": "user", "content": prompt}]
        )
        return {"success": True, "response": message.content[0].text, "model": "Claude 3.5 Sonnet", "cost": 0.01}
    except Exception as e:
        return {"success": False, "error": str(e)}

def call_google_gemini(prompt, role="critic"):
    if not gemini_model: return {"success": False, "error": "API Key Missing"}
    try:
        response = gemini_model.generate_content(f"Role: {role.upper()}. Task: {prompt}")
        return {"success": True, "response": response.text, "model": "Gemini 2.0 Flash", "cost": 0.00}
    except Exception as e:
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
            return {"success": True, "response": data["choices"][0]["message"]["content"], "model": "Perplexity Sonar", "cost": 0.00}
        return {"success": False, "error": "Invalid API Response"}
    except Exception as e:
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
