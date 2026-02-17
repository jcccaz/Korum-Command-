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

# --- Configuration (must be before routes that use clients) ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
PERPLEXITY_KEY = os.getenv("PERPLEXITY_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

# --- Model Clients ---
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

# --- Exports Directory ---
EXPORTS_DIR = os.path.join(os.getcwd(), 'exports')
os.makedirs(EXPORTS_DIR, exist_ok=True)

@app.route('/api/deploy_intelligence', methods=['POST'])
def deploy_intelligence():
    data = request.json
    intelligence_object = data.get('intelligence_object')
    format_type = data.get('format', 'docx')
    
    if not intelligence_object:
        return jsonify({"error": "Missing intelligence data"}), 400
        
    print(f"🚀 Deploying Intelligence Asset: {format_type.upper()}")
    
    try:
        from exporters import (
            CSVExporter,
            ExcelExporter,
            JSONExporter,
            MarkdownExporter,
            PDFExporter,
            PPTXExporter,
            TextExporter,
            WordExporter,
        )

        exporters = {
            'docx': WordExporter,
            'pptx': PPTXExporter,
            'xlsx': ExcelExporter,
            'csv': CSVExporter,
            'json': JSONExporter,
            'md': MarkdownExporter,
            'txt': TextExporter,
            'pdf': PDFExporter,
        }

        exporter = exporters.get(format_type)
        if not exporter:
            return jsonify({"error": f"Format {format_type} not supported"}), 501

        filename = exporter.generate(intelligence_object, output_dir=EXPORTS_DIR)
        filepath = os.path.abspath(filename)
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filename))

    except Exception as e:
        print(f"❌ Deployment Error: {e}")
        return jsonify({"error": str(e)}), 500

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

# --- Research Dock Persistence & Summarization ---

DOCK_DATA_PATH = os.path.join(os.getcwd(), 'data', 'research_dock.json')

@app.route('/api/dock/save', methods=['POST'])
def save_dock():
    data = request.json
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    snippets = data.get('snippets', [])

    # Validate: must be a list, capped at 50 snippets, max 500KB total
    if not isinstance(snippets, list):
        return jsonify({"success": False, "error": "Snippets must be a list"}), 400
    if len(snippets) > 50:
        return jsonify({"success": False, "error": "Too many snippets (max 50)"}), 400

    payload = json.dumps(snippets, indent=4)
    if len(payload) > 512_000:
        return jsonify({"success": False, "error": "Payload too large (max 500KB)"}), 400

    try:
        os.makedirs(os.path.dirname(DOCK_DATA_PATH), exist_ok=True)

        with open(DOCK_DATA_PATH, 'w', encoding='utf-8') as f:
            f.write(payload)

        print(f"💾 Dock saved: {len(snippets)} snippets")
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Dock save error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/dock/load', methods=['GET'])
def load_dock():
    try:
        if not os.path.exists(DOCK_DATA_PATH):
            return jsonify({"success": True, "snippets": []})
            
        with open(DOCK_DATA_PATH, 'r', encoding='utf-8') as f:
            snippets = json.load(f)
            
        print(f"📂 Dock loaded: {len(snippets)} snippets")
        return jsonify({"success": True, "snippets": snippets})
    except Exception as e:
        print(f"❌ Dock load error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/summarize_snippets', methods=['POST'])
def summarize_snippets():
    data = request.json
    snippets = data.get('snippets', [])
    
    if not snippets:
        return jsonify({"error": "No snippets provided"}), 400
        
    print(f"✨ Summarizing {len(snippets)} snippets...")
    
    # Construct prompt
    snippets_text = ""
    for i, snip in enumerate(snippets):
        snippets_text += f"\n--- SNIPPET {i+1} ({snip.get('label', 'Text')}) ---\n{snip.get('content', '')}\n"
    
    prompt = f"""
Summarize the following research snippets into a cohesive, professional executive brief. 
Identify key themes, critical metrics, and actionable insights. 
Use Markdown with headers and bullet points.

COLLECTED SNIPPETS:
{snippets_text}
"""

    if google_client:
        try:
            response = google_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return jsonify({"success": True, "summary": response.text})
        except Exception as e:
            print(f"❌ Summarization error (Gemini): {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify({"error": "Summarization engine unavailable"}), 501

# --- Report Library (Save/Load/Delete) ---

REPORTS_DIR = os.path.join(os.getcwd(), 'data', 'reports')

@app.route('/api/reports/save', methods=['POST'])
def save_report():
    data = request.json
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    import time as _time
    report_id = f"report_{int(_time.time())}"
    report = {
        "id": report_id,
        "query": data.get("query", ""),
        "results": data.get("results", {}),
        "consensus": data.get("consensus", ""),
        "synthesis": data.get("synthesis", ""),
        "classification": data.get("classification", {}),
        "roleName": data.get("roleName", ""),
        "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S"),
        "provider_count": len([k for k, v in data.get("results", {}).items() if isinstance(v, dict) and v.get("success")])
    }

    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filepath = os.path.join(REPORTS_DIR, f"{report_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"💾 Report saved: {report_id}")
        return jsonify({"success": True, "id": report_id})
    except Exception as e:
        print(f"❌ Report save error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/list', methods=['GET'])
def list_reports():
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        reports = []
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if not fname.endswith('.json'):
                continue
            filepath = os.path.join(REPORTS_DIR, fname)
            with open(filepath, 'r', encoding='utf-8') as f:
                r = json.load(f)
            reports.append({
                "id": r.get("id", fname.replace('.json', '')),
                "query": (r.get("query", "")[:80] + "...") if len(r.get("query", "")) > 80 else r.get("query", ""),
                "timestamp": r.get("timestamp", ""),
                "roleName": r.get("roleName", ""),
                "provider_count": r.get("provider_count", 0)
            })
        return jsonify({"success": True, "reports": reports})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    filepath = os.path.join(REPORTS_DIR, f"{report_id}.json")
    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Report not found"}), 404
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            report = json.load(f)
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    filepath = os.path.join(REPORTS_DIR, f"{report_id}.json")
    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Report not found"}), 404
    try:
        os.remove(filepath)
        print(f"🗑️ Report deleted: {report_id}")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- API Health Check (Proactive) ---

@app.route('/api/health/check', methods=['GET'])
def health_check():
    """Lightweight ping to each provider — minimal tokens, parallel execution."""
    from llm_core import call_openai_gpt4 as _openai, call_anthropic_claude as _claude, \
        call_google_gemini as _gemini, call_perplexity as _perplexity, call_mistral_api as _mistral
    import time as _time

    def check_provider(name, func, prompt="Say OK", role="system"):
        start = _time.time()
        try:
            result = func(prompt, role)
            latency = int((_time.time() - start) * 1000)
            if result.get("success"):
                return {"status": "healthy", "latency_ms": latency}
            else:
                return {"status": "error", "error": result.get("response", "Unknown error")[:200]}
        except Exception as e:
            return {"status": "offline", "error": str(e)[:200]}

    providers = {
        "openai": lambda: check_provider("openai", _openai),
        "anthropic": lambda: check_provider("anthropic", _claude),
        "google": lambda: check_provider("google", _gemini),
        "perplexity": lambda: check_provider("perplexity", _perplexity),
        "mistral": lambda: check_provider("mistral", _mistral),
    }

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): name for name, fn in providers.items()}
        for future in concurrent.futures.as_completed(futures, timeout=15):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"status": "offline", "error": str(e)[:200]}

    return jsonify(results)

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

# --- SerpAPI Real-Time Data ---
def fetch_serpapi_data(query, search_type="search"):
    """
    Fetch real-time data from SerpAPI.
    search_type options: 'search' (Google), 'shopping' (prices), 'news', 'images'
    """
    if not SERPAPI_KEY:
        return {"success": False, "error": "SerpAPI Key Missing"}

    try:
        # Determine endpoint based on search type
        params = {
            "api_key": SERPAPI_KEY,
            "q": query,
            "engine": "google",
            "num": 10  # Number of results
        }

        # Adjust for shopping/price queries
        if search_type == "shopping" or any(word in query.lower() for word in ["price", "cost", "buy", "shop", "deal"]):
            params["engine"] = "google_shopping"
            params["google_domain"] = "google.com"
        elif search_type == "news" or any(word in query.lower() for word in ["news", "latest", "today", "recent"]):
            params["tbm"] = "nws"  # News tab

        print(f"🌐 SerpAPI: Fetching real-time data for '{query}' (engine: {params['engine']})")

        response = requests.get("https://serpapi.com/search", params=params, timeout=15)
        data = response.json()

        # Parse results based on type
        results = []

        # Shopping results
        if "shopping_results" in data:
            for item in data["shopping_results"][:8]:
                results.append({
                    "type": "product",
                    "title": item.get("title", ""),
                    "price": item.get("price", "N/A"),
                    "source": item.get("source", ""),
                    "link": item.get("link", ""),
                    "rating": item.get("rating", ""),
                    "reviews": item.get("reviews", "")
                })

        # Organic search results
        if "organic_results" in data:
            for item in data["organic_results"][:6]:
                results.append({
                    "type": "web",
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "date": item.get("date", "")
                })

        # News results
        if "news_results" in data:
            for item in data["news_results"][:5]:
                results.append({
                    "type": "news",
                    "title": item.get("title", ""),
                    "source": item.get("source", {}).get("name", ""),
                    "date": item.get("date", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", "")
                })

        # Answer box / Knowledge panel
        answer_box = None
        if "answer_box" in data:
            answer_box = {
                "type": data["answer_box"].get("type", "answer"),
                "answer": data["answer_box"].get("answer") or data["answer_box"].get("snippet", ""),
                "title": data["answer_box"].get("title", "")
            }

        print(f"✅ SerpAPI Success: {len(results)} results found")

        return {
            "success": True,
            "results": results,
            "answer_box": answer_box,
            "search_metadata": {
                "query": query,
                "engine": params["engine"],
                "total_results": data.get("search_information", {}).get("total_results", 0)
            }
        }

    except Exception as e:
        print(f"❌ SerpAPI Error: {str(e)}")
        return {"success": False, "error": str(e)}

def format_serp_context(serp_data):
    """Format SerpAPI results into a context string for the council."""
    if not serp_data.get("success"):
        return ""

    context_parts = ["📡 REAL-TIME DATA (SerpAPI):"]

    # Answer box first if available
    if serp_data.get("answer_box"):
        ab = serp_data["answer_box"]
        context_parts.append(f"\n🎯 DIRECT ANSWER: {ab.get('answer', ab.get('title', ''))}")

    # Group by type
    products = [r for r in serp_data.get("results", []) if r["type"] == "product"]
    news = [r for r in serp_data.get("results", []) if r["type"] == "news"]
    web = [r for r in serp_data.get("results", []) if r["type"] == "web"]

    if products:
        context_parts.append("\n💰 CURRENT PRICES:")
        for p in products[:5]:
            rating_str = f" ⭐{p['rating']}" if p.get('rating') else ""
            context_parts.append(f"  • {p['title']}: {p['price']} ({p['source']}){rating_str}")

    if news:
        context_parts.append("\n📰 RECENT NEWS:")
        for n in news[:3]:
            context_parts.append(f"  • [{n['date']}] {n['title']} - {n['source']}")

    if web and not products:
        context_parts.append("\n🔍 WEB RESULTS:")
        for w in web[:4]:
            context_parts.append(f"  • {w['title']}: {w['snippet'][:100]}...")

    return "\n".join(context_parts)

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
    from file_processor import process_uploaded_file

    # Support both JSON and FormData (multipart) submissions
    if request.content_type and 'multipart/form-data' in request.content_type:
        import json as _json
        data = _json.loads(request.form.get('payload', '{}'))
        uploaded_files = request.files.getlist('files')
    else:
        data = request.json
        uploaded_files = []

    query = data.get('question')
    roles = data.get('council_roles', {})

    # Process uploaded files
    images = []       # List of {base64, mime_type, filename} for vision APIs
    doc_texts = []    # Extracted text from documents

    for f in uploaded_files:
        try:
            result = process_uploaded_file(f)
            if result['type'] == 'image':
                images.append(result)
            elif result['type'] == 'document':
                doc_texts.append(f"[Document: {result['filename']}]\n{result['extracted_text']}")
        except ValueError as e:
            print(f"⚠️ File processing error: {e}")
            continue

    # Append extracted document text to query context
    if doc_texts:
        doc_context = "\n\n--- ATTACHED DOCUMENTS ---\n" + "\n\n".join(doc_texts)
        query = query + doc_context

    # Map roles to functions
    futures = {}
    # V2 LOGIC BRANCH
    use_v2 = data.get('use_v2', False)
    is_red_team = data.get('is_red_team', False)
    use_serp = data.get('use_serp', False)

    # --- SERPAPI REAL-TIME DATA ENRICHMENT ---
    serp_context = ""
    serp_raw = None
    if use_serp:
        print(f"🌐 LIVE DATA MODE: Fetching real-time data for query...")
        serp_raw = fetch_serpapi_data(query)
        if serp_raw.get("success"):
            serp_context = format_serp_context(serp_raw)
            # Prepend context to query for all AIs
            query = f"{serp_context}\n\n---\nORIGINAL QUERY: {query}\n\nUse the real-time data above to inform your response. Cite specific prices, dates, or sources when relevant."
            print(f"✅ Real-time context injected ({len(serp_raw.get('results', []))} results)")

    if use_v2:
        print(f"⚡ V2 ENGINE ENGAGED for query: {query}")
        # V2 Engine handles sequence and synthesis
        # We pass roles to let the user's "persona" choice influence the planner
        v2_response = execute_council_v2(query, roles, images=images if images else None)
        
        # If Red Team is ON, we might want to append it here explicitly 
        # OR rely on V2 engine to have included it. 
        # For now, let's keep Red Team as a distinct "Final Boss" even in V2.
        if is_red_team:
            print("🛡️ RED TEAM INJECTION (V2)")
            exploit_prompt = f"PLAN: {query}\n\nCOUNCIL OUTPUT:\n{json.dumps(v2_response['results'])}\n\nYOUR MISSION: RED TEAM THIS. Find the fatal flaw."
            v2_response['results']['red_team'] = call_google_gemini(exploit_prompt, "HACKER")
            v2_response['consensus'] += " [RED TEAM EXECUTED]"

        # Include raw SerpAPI data if used
        if use_serp and serp_raw:
            v2_response["live_data"] = serp_raw

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

    response_data = {
        "consensus": consensus_msg,
        "results": results
    }

    # Include raw SerpAPI data if used
    if use_serp and serp_raw:
        response_data["live_data"] = serp_raw

    return jsonify(response_data)

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
