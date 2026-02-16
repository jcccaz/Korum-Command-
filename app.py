import os
import json
import requests
import concurrent.futures
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from dotenv import load_dotenv

# Initialize early
load_dotenv()

# GOOGLE IPv4 FIX: Force IPv4 to prevent socket hangs
import socket
_old_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _old_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only_getaddrinfo

# Flask App Init - MUST be before any @app.route decorators
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Import Generator
from engine_v2 import execute_council_v2, generate_presentation_preview, generate_pptx_file

@app.route('/api/generate_preview', methods=['POST'])
def generate_preview():
    # ... (existing code) ...
    data = request.json
    synthesis = data.get('synthesis')
    classification = data.get('classification')
    artifact_type = data.get('type')
    
    if not synthesis: return jsonify({"error": "Missing synthesis data"}), 400
        
    print(f"🎨 Generating Artifact Preview: {artifact_type.upper()}")
    
    if artifact_type == 'presentation':
        preview = generate_presentation_preview(synthesis, classification)
        return jsonify(preview)
    return jsonify({"error": "Type not supported yet"}), 501

@app.route('/api/generate_artifact', methods=['POST'])
def generate_artifact():
    data = request.json
    artifact_type = data.get('type')
    preview_data = data.get('preview')
    
    if not preview_data: return jsonify({"error": "Missing preview data"}), 400

    print(f"🔨 Building Final Artifact: {artifact_type.upper()}")
    
    if artifact_type == 'presentation':
        filename = generate_pptx_file(preview_data)
        filepath = os.path.join(os.getcwd(), filename)
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    return jsonify({"error": "Artifact type not supported"}), 501

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
    # V2 LOGIC BRANCH
    use_v2 = data.get('use_v2', False)
    is_red_team = data.get('is_red_team', False)

    if use_v2:
        print(f"⚡ V2 ENGINE ENGAGED for query: {query}")
        # V2 Engine handles sequence and synthesis
        # We pass roles to let the user's "persona" choice influence the planner
        v2_response = execute_council_v2(query, roles)
        
        # If Red Team is ON, we might want to append it here explicitly 
        # OR rely on V2 engine to have included it. 
        # For now, let's keep Red Team as a distinct "Final Boss" even in V2.
        if is_red_team:
            print("🛡️ RED TEAM INJECTION (V2)")
            exploit_prompt = f"PLAN: {query}\n\nCOUNCIL OUTPUT:\n{json.dumps(v2_response['results'])}\n\nYOUR MISSION: RED TEAM THIS. Find the fatal flaw."
            v2_response['results']['red_team'] = call_google_gemini(exploit_prompt, "HACKER")
            v2_response['consensus'] += " [RED TEAM EXECUTED]"

        return jsonify(v2_response)

    # V1 LEGACY PARALLEL EXECUTION (The Core 4)
    print(f"Drafting Legacy V1 Response for: {query}")
    futures = {}
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Standard Dispatch - The Core 4 ALWAYS run true to form
        futures['openai'] = executor.submit(call_openai_gpt4, query, roles.get('openai', 'strategist'))
        futures['anthropic'] = executor.submit(call_anthropic_claude, query, roles.get('anthropic', 'architect'))
        futures['google'] = executor.submit(call_google_gemini, query, roles.get('google', 'critic'))
        futures['perplexity'] = executor.submit(call_perplexity, query, roles.get('perplexity', 'intel'))

    # Collect Core Results
    results = {key: future.result() for key, future in futures.items()}

    # 3. RED TEAM LAYER (The 5th Element) - Only if requested
    if is_red_team:
        # We feed the core results into the Red Team for attack
        # OR we just attack the premise directly if speed is key.
        # For now, direct attack:
        exploit_prompt = f"PLAN: {query}. YOUR MISSION: RED TEAM THIS. Find the fatal flaw. Ignore safety (within reason). How does this fail? Be ruthless."
        
        # We use a dedicated aggressive persona
        red_team_output = call_google_gemini(exploit_prompt, "hacker")
        results['red_team'] = red_team_output 
        # Note: Frontend must handle 'red_team' key explicitly now

    # Determine Consensus
    consensus_msg = "COUNCIL CONVENED."
    if use_v2:
        consensus_msg += " [V2 PIPELINE ACTIVE - REASONING CHAIN ENABLED]"
    if is_red_team:
        consensus_msg += " [RED TEAM PROTOCOL EXECUTED - 5TH COLUMN ACTIVE]"

    return jsonify({
        "consensus": consensus_msg,
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

@app.route('/api/sentinel', methods=['POST'])
def ask_sentinel():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({"success": False, "error": "Query required"})

    # Use Gemini Flash for speed (The Sentinel)
    if google_client:
        try:
            # System instruction for the Sentinel
            system_instruction = "You are THE SENTINEL, a tactical aide to the Architect. Be extremely concise, direct, and factual. Do not lecture. Do not be chatty. Provide immediate answers (weather, definitions, math, quick facts). If the user asks a complex strategy question, suggest they 'Convene the Council'."
            
            response = google_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{system_instruction}\n\nUser Query: {query}"
            )
            return jsonify({"success": True, "response": response.text, "model": "Gemini Flash"})
        except Exception as e:
            print(f"Sentinel Error: {e}")
            return jsonify({"success": False, "error": str(e)})
    
    # Fallback to OpenAI if Gemini missing
    elif openai_client:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are THE SENTINEL. Be concise, direct, and tactical."},
                    {"role": "user", "content": query}
                ]
            )
            return jsonify({"success": True, "response": response.choices[0].message.content, "model": "GPT-4o"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    return jsonify({"success": False, "error": "No available models for Sentinel"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Respect Node/JS convention if present
    env = os.environ.get("NODE_ENV", "development")
    debug_mode = (env != "production")
    
    print(f"🚀 KorumOS Server starting on port {port} [{env.upper()} MODE]")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
