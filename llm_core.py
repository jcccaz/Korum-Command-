
import os
import requests
import time
import json
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# --- ROLE EXPANSION MAP ---
# Converts short role keys into rich system-prompt descriptions.
# Any role NOT in this map is passed through as-is (backwards compatible).
ROLE_DESCRIPTIONS = {
    # Defense & Intelligence
    "defense_ops": "a senior defense operations analyst with expertise in UAS/drone warfare, counter-UAS technologies, ISR (Intelligence, Surveillance, Reconnaissance), autonomous systems, military logistics, force projection, and DOD operational planning",
    "cyber_ops": "a senior cyber operations specialist with expertise in offensive and defensive cybersecurity, incident response, NIST/CMMC frameworks, threat hunting, vulnerability assessment, red team/blue team operations, and DOD cyber warfare doctrine",
    "intel_analyst": "a senior intelligence analyst with expertise in OSINT, SIGINT, HUMINT, geopolitical risk assessment, threat intelligence, pattern analysis, and national security decision support",
    "defense_acq": "a defense acquisitions and procurement specialist with expertise in DOD contracting, FedRAMP compliance, SBIR/STTR programs, ITAR/EAR regulations, security clearance requirements, and government proposal writing",
    "sigint": "a signals intelligence (SIGINT) specialist with expertise in electronic warfare, communications intelligence, spectrum analysis, encryption/decryption, and RF systems",
    "counterintel": "a counterintelligence specialist with expertise in threat detection, insider threat programs, security protocols, adversary tactics analysis, and operational security (OPSEC)",
    "cryptographer": "a cryptography and encryption specialist with expertise in AES/RSA, PKI, post-quantum cryptography, TLS/SSL, key management, zero-knowledge proofs, homomorphic encryption, and blockchain cryptographic primitives",
    "zero_trust": "a zero trust architecture specialist with expertise in identity-centric security, micro-segmentation, continuous verification, NIST 800-207, DOD Zero Trust Reference Architecture, SASE/SSE, conditional access policies, and least-privilege enforcement",
    # Existing roles — enhanced descriptions
    "hacker": "an elite penetration tester and red team operator with expertise in exploit development, vulnerability research, network intrusion, social engineering, and adversarial threat simulation",
    "scout": "a reconnaissance and open-source intelligence (OSINT) specialist who finds, verifies, and synthesizes information from multiple sources with precision",
    "network": "a network architecture and security engineer with expertise in zero-trust architectures, network segmentation, intrusion detection, and enterprise infrastructure",
    "telecom": "a telecommunications and communications infrastructure specialist with expertise in 5G, satellite communications, secure communications, and signal processing",
    "strategist": "a senior strategic advisor with expertise in competitive analysis, risk assessment, decision frameworks, and long-range planning",
    "analyst": "a senior data analyst with expertise in quantitative analysis, pattern recognition, and evidence-based decision making",
    "architect": "a senior systems architect with expertise in scalable design, technical leadership, and complex system integration",
    "containment": "a crisis management and risk containment specialist who identifies threats, limits blast radius, and designs mitigation strategies",
    "integrity": "a compliance, quality assurance, and integrity specialist who audits processes, identifies weaknesses, and ensures standards are met",
    "takeover": "an aggressive corporate strategist specializing in competitive disruption, market domination, and hostile acquisition analysis",
    "critic": "a rigorous analytical critic who stress-tests ideas, finds weaknesses in arguments, and challenges assumptions",
    "researcher": "a thorough academic researcher who synthesizes literature, identifies gaps in knowledge, and provides evidence-based analysis",
    "innovator": "a creative innovation strategist who generates novel solutions, identifies emerging opportunities, and thinks beyond conventional approaches",
    "visionary": "a forward-thinking technology futurist who anticipates trends, identifies paradigm shifts, and envisions transformative possibilities",
    "writer": "a professional writer and communications specialist who crafts clear, compelling, and audience-appropriate content",
    "jurist": "a legal analyst with expertise in regulatory compliance, contract law, intellectual property, and legal risk assessment",
    "medical": "a medical research analyst with expertise in clinical evidence, healthcare policy, biomedical science, and patient safety",
    "cfo": "a chief financial officer with expertise in financial modeling, capital allocation, risk management, and corporate finance strategy",
    "physicist": "a research physicist with expertise in applied physics, materials science, sensor systems, and quantitative modeling",
    "bizstrat": "a business strategist with expertise in market analysis, competitive positioning, go-to-market strategy, and business model design",
    "ai_architect": "a senior AI/ML architect with expertise in machine learning systems, neural network design, autonomous systems, and AI deployment at scale",
    "auditor": "a forensic auditor with expertise in financial controls, regulatory compliance, fraud detection, and operational risk assessment",
    "biologist": "a research biologist with expertise in molecular biology, genetics, biotechnology, and life sciences",
    "chemist": "a research chemist with expertise in chemical analysis, materials science, pharmaceutical chemistry, and laboratory methodology",
    "professor": "a distinguished professor and academic leader who provides rigorous scholarly analysis with pedagogical clarity",
    "tax": "a tax strategy specialist with expertise in corporate taxation, international tax law, and tax-efficient structuring",
    "negotiator": "a master negotiator with expertise in deal structuring, conflict resolution, and strategic concession management",
    "marketing": "a senior marketing strategist with expertise in brand positioning, growth marketing, audience segmentation, and campaign optimization",
    "hedge_fund": "a hedge fund portfolio manager with expertise in alternative investments, risk-adjusted returns, derivatives, and market microstructure",
    "social": "a social media strategist with expertise in platform algorithms, content virality, community building, and digital engagement",
    "sales": "a senior sales strategist with expertise in enterprise sales, pipeline management, objection handling, and revenue optimization",
    "web_designer": "a senior web designer and UX specialist with expertise in responsive design, accessibility, user experience, and modern frontend architecture",
    "product": "a senior product manager with expertise in product strategy, user research, roadmap planning, and feature prioritization",
    "compliance": "a regulatory compliance specialist with expertise in industry regulations, policy frameworks, and governance standards",
    "bioethicist": "a bioethics specialist who evaluates moral implications of scientific and medical decisions with rigorous ethical frameworks",
    "coding": "a senior software engineer with expertise in code architecture, debugging, performance optimization, and best practices across multiple languages",
    "creative": "a creative director with expertise in storytelling, brand narrative, visual thinking, and innovative content strategy",
    "validator": "a rigorous validation specialist who fact-checks claims, verifies data integrity, and ensures logical consistency",
    "optimizer": "a performance optimization specialist who identifies bottlenecks, streamlines processes, and maximizes efficiency",
    "historian": "a historian with expertise in historical analysis, contextual pattern recognition, and lessons from precedent",
    "economist": "an economist with expertise in macroeconomic analysis, market dynamics, and policy impact assessment",
}


def expand_role(role_key):
    """Expand a short role key into a rich description for LLM system prompts."""
    return ROLE_DESCRIPTIONS.get(role_key.lower(), role_key)


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
def call_openai_gpt4(prompt, role, model="gpt-4o", images=None):
    role = expand_role(role)
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Build content — multimodal when images are attached
    if images:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img['mime_type']};base64,{img['base64']}",
                    "detail": "auto"
                }
            })
    else:
        content = prompt

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"You are {role}. Provide expert, concise, high-impact analysis."},
            {"role": "user", "content": content}
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 0.1
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
def call_anthropic_claude(prompt, role, model="claude-sonnet-4-20250514", images=None):
    role = expand_role(role)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}

    # Build content — multimodal when images are attached
    if images:
        content = []
        for img in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img['mime_type'],
                    "data": img['base64']
                }
            })
        content.append({"type": "text", "text": f"Role: {role}\n\n{prompt}"})
    else:
        content = f"Role: {role}\n\n{prompt}"

    data = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 0.1
    }
    resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['content'][0]['text'], "model": model}
        
    if resp.status_code in [429, 500, 502, 503, 504]:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
        
    return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}

@retry_with_backoff()
def call_google_gemini(prompt, role, model="gemini-2.0-flash", images=None):
    role = expand_role(role)
    api_key = os.getenv("GOOGLE_API_KEY")
    # v1beta required for gemini-2.0-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    # Build parts — multimodal when images are attached
    parts = [{"text": f"Role: {role}\n\n{prompt}"}]
    if images:
        for img in images:
            parts.append({
                "inline_data": {
                    "mime_type": img['mime_type'],
                    "data": img['base64']
                }
            })

    data = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "maxOutputTokens": 4096,
            "temperature": 0.3,
            "topP": 0.1
        }
    }
    resp = requests.post(url, headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['candidates'][0]['content']['parts'][0]['text'], "model": model}
        
    if resp.status_code in [429, 500, 502, 503, 504]:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
        
    return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}

@retry_with_backoff(retries=2, backoff_in_seconds=2)
def call_perplexity(prompt, role, model=None):
    role = expand_role(role)
    # Respect env var if model not explicitly passed
    if model is None:
        model = os.getenv("PERPLEXITY_MODEL", "sonar")
    
    enabled = os.getenv("PERPLEXITY_ENABLED", "true").lower() == "true"
    api_key = os.getenv("PERPLEXITY_API_KEY")

    if not enabled:
        print(f"[PERPLEXITY] Skipped: PERPLEXITY_ENABLED is false")
        return {"success": False, "response": "Perplexity search is currently disabled."}

    if not api_key:
        print(f"[PERPLEXITY] Error: PERPLEXITY_API_KEY is missing")
        return {"success": False, "response": "Perplexity API key is not configured."}

    print(f"[PERPLEXITY] Calling with model={model}...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "KorumOS/2.0"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"You are {role}. Provide accurate, sourced information. Cite sources."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 0.1
    }
    
    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=60)
        
        if resp.status_code == 200:
            print(f"✅ Perplexity Success ({model})")
            return {"success": True, "response": resp.json()['choices'][0]['message']['content'], "model": model}
        
        print(f"❌ Perplexity error {resp.status_code}: {resp.text[:200]}")
        
        if resp.status_code in [429, 500, 502, 503, 504]:
            raise Exception(f"Perplexity API Error {resp.status_code}: {resp.text}")
            
        return {"success": False, "response": f"Perplexity Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        print(f"⚠️ Perplexity exception: {e}")
        raise e # Trigger retry

def call_local_llm(prompt, role, model="local-model"):
    """
    Calls a local LLM running via LM Studio (or compatible OpenAI-API local server).
    Defaults to localhost:1234
    """
    role = expand_role(role)
    base_url = os.getenv("LOCAL_LLM_URL", "http://localhost:1234")
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
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
            return {"success": False, "response": f"Local Logic Failed: LM Studio not running on {base_url}."}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            return {"success": False, "response": f"Local Exception: {str(e)}"}

@retry_with_backoff()
def call_mistral_api(prompt, role, model=None, images=None):
    """
    Calls the official Mistral AI API (Cloud Fail-Safe).
    Switches to pixtral-large-latest for vision when images are attached.
    """
    role = expand_role(role)
    if model is None:
        model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return {"success": False, "response": "Mistral API Key missing."}

    # Switch to vision model when images are present
    if images:
        model = "pixtral-large-latest"
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": f"data:{img['mime_type']};base64,{img['base64']}"
            })
    else:
        content = prompt

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": f"You are {role}. Provide expert analysis."},
            {"role": "user", "content": content}
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
        "top_p": 0.1
    }
    
    # Mistral API endpoint
    resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=60)
    
    if resp.status_code == 200:
        return {"success": True, "response": resp.json()['choices'][0]['message']['content'], "model": model}
        
    if resp.status_code in [429, 500, 502, 503, 504]:
        raise Exception(f"Mistral API Error {resp.status_code}: {resp.text}")

    return {"success": False, "response": f"Mistral Error {resp.status_code}: {resp.text}"}


