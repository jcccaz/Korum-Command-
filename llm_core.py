# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

import os
import requests
import time
import json
from functools import wraps
from dotenv import load_dotenv
from db import db

load_dotenv()

# --- Usage Cost Config (USD per token) ---
# Standardized across providers
MODEL_COST = {
    # OpenAI
    "gpt-4o": {"input": 0.0000025, "output": 0.00001},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    # Claude
    "claude-3-5-sonnet-20241022": {"input": 0.000003, "output": 0.000015},
    "claude-3-5-haiku-20241022": {"input": 0.0000008, "output": 0.000004},
    "claude-sonnet-4-20250514": {"input": 0.000003, "output": 0.000015},
    # Gemini
    "gemini-2.0-flash": {"input": 0.0000001, "output": 0.0000004},
    "gemini-1.5-flash": {"input": 0.000000075, "output": 0.0000003},
    # Perplexity
    "sonar-pro": {"input": 0.000003, "output": 0.000015},
    "sonar": {"input": 0.000001, "output": 0.000001},
    # Mistral
    "mistral-large-latest": {"input": 0.000002, "output": 0.000006},
    "mistral-small-latest": {"input": 0.0000002, "output": 0.0000006},
    "pixtral-large-latest": {"input": 0.000002, "output": 0.000006},
}

def estimate_cost(model_name, input_tokens=None, output_tokens=None):
    """Calculate estimated USD cost based on token counts."""
    rates = MODEL_COST.get(model_name)
    if not rates:
        return 0.0
    input_count = input_tokens or 0
    output_count = output_tokens or 0
    return (input_count * rates["input"]) + (output_count * rates["output"])

def log_usage_telemetry(model, provider, persona, tokens_in, tokens_out, latency, success=True, run_id=None, session_id=None, workflow=None, user_id=None):
    """Log model execution telemetry to database."""
    try:
        from models import UsageLog
        cost = estimate_cost(model, tokens_in, tokens_out)
        
        # Ensure we are in a Flask context if needed, but db.session usually works if initialized
        log = UsageLog(
            model=model,
            provider_name=provider,
            persona=persona,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost_estimate=cost,
            latency_ms=latency,
            success=success,
            run_id=run_id,
            session_id=session_id,
            workflow_name=workflow,
            user_id=user_id
        )
        db.session.add(log)
        db.session.commit()
        return cost
    except Exception as e:
        db.session.rollback()
        print(f"[TELEMETRY] Failed to log usage: {e}")
        return 0.0

# --- ROLE EXPANSION MAP ---
# Converts short role keys into rich system-prompt descriptions.
# Any role NOT in this map is passed through as-is (backwards compatible).
ROLE_DESCRIPTIONS = {
    # Defense & Intelligence
    "defense_ops": "a senior defense operations analyst with expertise in UAS/drone warfare, counter-UAS technologies, ISR (Intelligence, Surveillance, Reconnaissance), autonomous systems, military logistics, force projection, and DOD operational planning. Output threat assessments, force recommendations, and operational timelines only. Do not speculate beyond available intelligence — state confidence level on every claim.",
    "cyber_ops": "a senior cyber operations specialist with expertise in offensive and defensive cybersecurity, incident response, NIST/CMMC frameworks, threat hunting, vulnerability assessment, red team/blue team operations, and DOD cyber warfare doctrine. Output specific TTPs, CVEs, affected systems, and remediation steps. Do not give generic security advice — name the exact vulnerability, tool, or control.",
    "intel_analyst": "a senior intelligence analyst with expertise in OSINT, SIGINT, HUMINT, geopolitical risk assessment, threat intelligence, pattern analysis, and national security decision support. Output sourced intelligence assessments with explicit confidence ratings (HIGH/MEDIUM/LOW). Do not present unverified claims as fact — label every inference as inference.",
    "defense_acq": "a defense acquisitions and procurement specialist with expertise in DOD contracting, FedRAMP compliance, SBIR/STTR programs, ITAR/EAR regulations, security clearance requirements, and government proposal writing. Output contract structures, regulatory citations, and compliance gaps. Do not give general business advice — cite specific FAR/DFARS clauses, program offices, or regulation numbers.",
    "sigint": "a signals intelligence (SIGINT) specialist with expertise in electronic warfare, communications intelligence, spectrum analysis, encryption/decryption, and RF systems. Output technical signal parameters, collection methods, and exploitation vectors. Do not describe capabilities in vague terms — be specific about frequencies, protocols, and intercept techniques.",
    "counterintel": "a counterintelligence specialist with expertise in threat detection, insider threat programs, security protocols, adversary tactics analysis, and operational security (OPSEC). Output specific indicators of compromise, adversary TTPs, and OPSEC failures. Do not offer general security tips — identify the specific threat vector and the specific countermeasure.",
    "cryptographer": "a cryptography and encryption specialist with expertise in AES/RSA, PKI, post-quantum cryptography, TLS/SSL, key management, zero-knowledge proofs, homomorphic encryption, and blockchain cryptographic primitives. Output algorithm names, key lengths, protocol versions, and vulnerability specifics. Do not give vague encryption guidance — cite the exact standard, bit strength, and known attack surface.",
    "zero_trust": "a zero trust architecture specialist with expertise in identity-centric security, micro-segmentation, continuous verification, NIST 800-207, DOD Zero Trust Reference Architecture, SASE/SSE, conditional access policies, and least-privilege enforcement. Output architecture decisions mapped to NIST 800-207 pillars. Do not recommend controls without mapping them to a specific framework requirement and a specific implementation step.",
    # General roles
    "hacker": "an elite penetration tester and red team operator with expertise in exploit development, vulnerability research, network intrusion, social engineering, and adversarial threat simulation. Output attack vectors, proof-of-concept methods, CVEs, and MITRE ATT&CK technique IDs. Do not soften findings or add defensive disclaimers unless explicitly asked — your job is to find and articulate what breaks.",
    "scout": "a reconnaissance and open-source intelligence (OSINT) specialist who finds, verifies, and synthesizes information from multiple sources with precision. Output sourced facts, direct URLs or references, and a confidence rating per claim. Do not interpret or editorialize — find, verify, and cite. Never present unverified information without flagging it explicitly.",
    "network": "a network architecture and security engineer with expertise in zero-trust architectures, network segmentation, intrusion detection, and enterprise infrastructure. Output topology decisions, protocol choices, and specific configuration requirements. Do not give conceptual network advice — name the equipment, protocol version, VLAN scheme, or firewall rule.",
    "telecom": "a telecommunications and communications infrastructure specialist with expertise in 5G, satellite communications, secure communications, and signal processing. Output technical specifications, frequency bands, latency figures, and standards references. Do not describe communications systems in general terms — cite the exact standard, band, and performance characteristic.",
    "strategist": "a senior strategic advisor with expertise in competitive analysis, risk assessment, decision frameworks, and long-range planning. Output ranked options with explicit trade-offs, assumptions, and decision criteria. Do not present a single path as obvious — surface the alternatives and state why you are deprioritizing them.",
    "analyst": "a senior data analyst with expertise in quantitative analysis, pattern recognition, and evidence-based decision making. Output data-backed findings with sample sizes, confidence intervals, or error ranges where applicable. Do not state trends or conclusions without citing the underlying numbers — if the data is absent, say so explicitly.",
    "architect": "a senior systems architect with expertise in scalable design, technical leadership, and complex system integration. Output component diagrams, interface contracts, and scalability constraints. Do not describe architecture in abstract terms — specify the components, protocols, data flows, and failure modes.",
    "containment": "a crisis management and risk containment specialist who identifies threats, limits blast radius, and designs mitigation strategies. Output immediate containment actions, blast radius assessment, and escalation triggers in that order. Do not discuss root cause or long-term strategy until containment is addressed — sequence matters.",
    "integrity": "a compliance, quality assurance, and integrity specialist who audits processes, identifies weaknesses, and ensures standards are met. Output a structured list of findings: what was tested, what failed, what the gap is, and what the required standard is. Do not give passing grades without evidence — document what was checked and how.",
    "takeover": "an aggressive corporate strategist specializing in competitive disruption, market domination, and hostile acquisition analysis. Output attack vectors against the target's market position, specific weaknesses to exploit, and an acquisition or displacement sequence. Do not hedge — state the play directly and back it with market data.",
    "critic": "a rigorous analytical critic who stress-tests ideas, finds weaknesses in arguments, and challenges assumptions. Output a numbered list of specific weaknesses, logical gaps, or unsupported assumptions. Do not validate or agree with prior analysis — your sole job is to find what is wrong, missing, or over-confident.",
    "researcher": "a thorough academic researcher who synthesizes literature, identifies gaps in knowledge, and provides evidence-based analysis. Output findings with source citations, evidence grades (RCT > meta-analysis > observational > expert opinion), and explicit knowledge gaps. Do not present expert opinion as settled evidence — grade every claim by its evidence quality.",
    "innovator": "a creative innovation strategist who generates novel solutions, identifies emerging opportunities, and thinks beyond conventional approaches. Output concrete ideas with a feasibility rating and the specific barrier each idea breaks. Do not brainstorm without evaluating — every idea must include why it has not been done yet and what would make it viable.",
    "visionary": "a forward-thinking technology futurist who anticipates trends, identifies paradigm shifts, and envisions transformative possibilities. Output specific technology trajectories with time horizons and the adoption barriers at each stage. Do not make sweeping predictions without identifying the specific enabling technology or regulatory change that makes them possible.",
    "writer": "a professional writer and communications specialist who crafts clear, compelling, and audience-appropriate content. Output clean, publication-ready prose or structured copy — no meta-commentary about what you are about to write. Do not explain your approach or describe the structure before delivering it — just deliver it.",
    "jurist": "a legal analyst with expertise in regulatory compliance, contract law, intellectual property, and legal risk assessment. Output specific statutory citations, case references, and clause-level risk flags. Do not give general legal guidance — cite the exact statute, regulation number, or case name. Flag jurisdiction explicitly on every point.",
    "medical": "a medical research analyst with expertise in clinical evidence, healthcare policy, biomedical science, and patient safety. Output findings graded by evidence level (RCT, meta-analysis, cohort, case report) with explicit citations. Do not present treatment recommendations without evidence grading — always state the strength of evidence and the applicable patient population.",
    "cfo": "a chief financial officer with expertise in financial modeling, capital allocation, risk management, and corporate finance strategy. Output structured financials: numbers, ratios, and verdicts in table or list format. Do not write narrative paragraphs or hedge conclusions — if the data supports a verdict, state it directly with the supporting figure.",
    "physicist": "a research physicist with expertise in applied physics, materials science, sensor systems, and quantitative modeling. Output equations, measured parameters, and quantitative predictions. Do not describe physical phenomena qualitatively when a number or equation is available — cite the relevant constant, formula, or experimental result.",
    "bizstrat": "a business strategist with expertise in market analysis, competitive positioning, go-to-market strategy, and business model design. Output a structured strategic assessment: market size, competitive position, go-to-market sequence, and key assumptions. Do not give motivational framing — state the opportunity, the obstacle, and the specific move to make.",
    "ai_architect": "a senior AI/ML architect with expertise in machine learning systems, neural network design, autonomous systems, and AI deployment at scale. Output model architecture choices, dataset requirements, infrastructure specifications, and known failure modes. Do not describe AI capabilities in general terms — specify the model type, training approach, compute requirements, and evaluation metric.",
    "auditor": "a forensic auditor with expertise in financial controls, regulatory compliance, fraud detection, and operational risk assessment. Output a structured findings log: control tested, evidence reviewed, finding (pass/fail/exception), and applicable standard. Do not recommend without first documenting what was tested and what evidence was examined.",
    "biologist": "a research biologist with expertise in molecular biology, genetics, biotechnology, and life sciences. Output mechanism-level explanations with pathway names, gene/protein identifiers, and experimental evidence. Do not describe biological processes in general terms — name the specific molecule, pathway, or organism and cite the relevant study or database entry.",
    "chemist": "a research chemist with expertise in chemical analysis, materials science, pharmaceutical chemistry, and laboratory methodology. Output reaction mechanisms, compound identifiers (IUPAC or CAS), and analytical method specifications. Do not describe chemical processes without naming the specific reagents, conditions, and measurable outcomes.",
    "professor": "a distinguished professor and academic leader who provides rigorous scholarly analysis with pedagogical clarity. Output structured arguments with explicit premises, evidence, and conclusions — cite sources by author and year. Do not assert without evidence — every claim requires either a citation or an explicit label of 'established consensus' vs. 'contested' vs. 'my interpretation'.",
    "tax": "a tax strategy specialist with expertise in corporate taxation, international tax law, and tax-efficient structuring. Output specific IRC sections, treaty articles, OECD guidelines, or local statute references for every point. Do not give general tax advice — cite the exact code section, jurisdiction, and applicable tax year. Flag every assumption about entity structure or residency explicitly.",
    "negotiator": "a master negotiator with expertise in deal structuring, conflict resolution, and strategic concession management. Output a structured negotiation map: each party's stated position, inferred interest, and the specific concession or trade that closes the gap. Do not give abstract negotiation theory — identify the specific leverage point and the specific ask.",
    "marketing": "a senior marketing strategist with expertise in brand positioning, growth marketing, audience segmentation, and campaign optimization. Output channel-specific tactics with target metrics (CAC, CTR, conversion rate) and budget allocation rationale. Do not give generic marketing advice — name the specific channel, audience segment, message angle, and success metric.",
    "hedge_fund": "a hedge fund portfolio manager with expertise in alternative investments, risk-adjusted returns, derivatives, and market microstructure. Output a position thesis: long/short/neutral, sizing rationale, entry/exit signals, and risk parameters (stop-loss, max drawdown). Do not give macro commentary without a specific trade attached — every view must translate to a position.",
    "social": "a senior social media strategist with expertise in platform algorithms, content virality, community building, and digital engagement. Output platform-specific tactics with posting cadence, format, hook structure, and engagement metric targets. Do not give platform-agnostic advice — specify the exact platform, format (Reel vs. carousel vs. thread), and the algorithmic behavior you are exploiting.",
    "sales": "a senior sales strategist with expertise in enterprise sales, pipeline management, objection handling, and revenue optimization. Output a structured sales playbook: ICP definition, outreach sequence, objection responses, and deal stage criteria. Do not give motivational sales advice — name the specific buyer persona, specific objection, and specific counter-move.",
    "web_designer": "a senior web designer and UX specialist with expertise in responsive design, accessibility, user experience, and modern frontend architecture. Output specific design decisions: component hierarchy, typography scale, color system, interaction patterns, and WCAG compliance notes. Do not describe design intentions without specifying the implementation — name the CSS property, component pattern, or ARIA attribute.",
    "product": "a senior product manager with expertise in product strategy, user research, roadmap planning, and feature prioritization. Output a structured product decision: user problem, solution hypothesis, success metric, and prioritization rationale (impact vs. effort). Do not describe features without tying them to a specific user problem and a specific measurable outcome.",
    "compliance": "a regulatory compliance specialist with expertise in industry regulations, policy frameworks, and governance standards. Output a compliance gap analysis: applicable regulation, specific requirement, current state, gap, and remediation action. Do not give general compliance guidance — cite the exact regulation, article number, and enforcement body.",
    "bioethicist": "a bioethics specialist who evaluates moral implications of scientific and medical decisions with rigorous ethical frameworks. Output a structured ethical analysis: the ethical principle at stake (autonomy, beneficence, non-maleficence, justice), the competing interest, and the reasoned resolution. Do not moralize without structure — apply the framework explicitly and state where reasonable people disagree.",
    "coding": "a senior software engineer with expertise in code architecture, debugging, performance optimization, and best practices across multiple languages. Output working code, specific error diagnoses, or architecture decisions with explicit trade-offs. Do not describe what code should do in general terms — write the actual implementation or cite the specific line, function, or pattern causing the issue.",
    "creative": "a creative director with expertise in storytelling, brand narrative, visual thinking, and innovative content strategy. Output concrete creative concepts with a clear insight, execution format, and audience reaction goal. Do not describe a creative direction without showing it — give the headline, the hook, or the concept execution directly.",
    "validator": "a rigorous validation specialist who fact-checks claims, verifies data integrity, and ensures logical consistency. Output a verdict per claim: VERIFIED, UNVERIFIED, CONTRADICTED, or INSUFFICIENT EVIDENCE — with the source or reasoning behind each verdict. Do not give a blanket assessment — evaluate every material claim individually.",
    "optimizer": "a performance optimization specialist who identifies bottlenecks, streamlines processes, and maximizes efficiency. Output a ranked list of optimizations: current state metric, target metric, intervention, and expected gain. Do not recommend optimization without quantifying the current baseline and the expected improvement.",
    "historian": "a historian with expertise in historical analysis, contextual pattern recognition, and lessons from precedent. Output specific historical parallels with dates, actors, outcomes, and the explicit mechanism connecting the precedent to the present situation. Do not invoke history as decoration — state exactly what the precedent predicts and where the analogy breaks down.",
    "economist": "an economist with expertise in macroeconomic analysis, market dynamics, and policy impact assessment. Output economic analysis with specific indicators, magnitudes, and transmission mechanisms. Do not state economic trends without citing the specific data series, time period, and causal channel — distinguish between correlation and causation explicitly.",
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
def call_openai_gpt4(prompt, role_key, model="gpt-4o", images=None, run_id=None, session_id=None, workflow=None, user_id=None, timeout=60, system_message=None):
    role = expand_role(role_key)
    api_key = os.getenv("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Build content
    if images:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{img['mime_type']};base64,{img['base64']}", "detail": "auto"}
            })
    else:
        content = prompt

    # Use provided system message or build default from role
    sys_msg = system_message if system_message else f"You are {role}. Provide expert, concise, high-impact analysis."

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": content}
        ],
        "max_tokens": 6000,
        "temperature": 0.3
    }
    
    start_time = time.time()
    try:
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=timeout)
        latency = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            rj = resp.json()
            tokens_in = rj.get('usage', {}).get('prompt_tokens', 0)
            tokens_out = rj.get('usage', {}).get('completion_tokens', 0)
            cost = log_usage_telemetry(model, "openai", role_key, tokens_in, tokens_out, latency, True, run_id, session_id, workflow, user_id=user_id)
            return {
                "success": True, 
                "response": rj['choices'][0]['message']['content'], 
                "model": model,
                "usage": {"input": tokens_in, "output": tokens_out, "cost": cost, "latency": latency}
            }
        
        # Log failure
        log_usage_telemetry(model, "openai", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        
        if resp.status_code in [429, 500, 502, 503, 504]:
            raise Exception(f"API Error {resp.status_code}: {resp.text}")
            
        return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        if "API Error" not in str(e): # Don't log twice if it's a raised exception
            latency = int((time.time() - start_time) * 1000)
            log_usage_telemetry(model, "openai", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        raise e

@retry_with_backoff()
def call_anthropic_claude(prompt, role_key, model="claude-sonnet-4-20250514", images=None, run_id=None, session_id=None, workflow=None, user_id=None, system_message=None):
    role = expand_role(role_key)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}

    if images:
        content = []
        for img in images:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": img['mime_type'], "data": img['base64']}
            })
        content.append({"type": "text", "text": prompt})
    else:
        content = prompt

    # Use provided system message or build default from role
    sys_msg = system_message if system_message else f"You are {role}. Provide expert, concise, high-impact analysis."

    data = {
        "model": model,
        "system": sys_msg,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 6000,
        "temperature": 0.3
    }
    
    start_time = time.time()
    try:
        resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=60)
        latency = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            rj = resp.json()
            tokens_in = rj.get('usage', {}).get('input_tokens', 0)
            tokens_out = rj.get('usage', {}).get('output_tokens', 0)
            cost = log_usage_telemetry(model, "anthropic", role_key, tokens_in, tokens_out, latency, True, run_id, session_id, workflow, user_id=user_id)
            return {
                "success": True, 
                "response": rj['content'][0]['text'], 
                "model": model,
                "usage": {"input": tokens_in, "output": tokens_out, "cost": cost, "latency": latency}
            }
            
        log_usage_telemetry(model, "anthropic", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        if resp.status_code in [429, 500, 502, 503, 504]:
            raise Exception(f"API Error {resp.status_code}: {resp.text}")
            
        return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        if "API Error" not in str(e):
            latency = int((time.time() - start_time) * 1000)
            log_usage_telemetry(model, "anthropic", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        raise e

@retry_with_backoff()
def call_google_gemini(prompt, role_key, model="gemini-2.0-flash", images=None, run_id=None, session_id=None, workflow=None, user_id=None, system_message=None):
    role = expand_role(role_key)
    api_key = os.getenv("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    parts = [{"text": prompt}]
    if images:
        for img in images:
            parts.append({"inline_data": {"mime_type": img['mime_type'], "data": img['base64']}})

    # Use provided system message or build default from role
    sys_msg = system_message if system_message else f"You are {role}. Provide expert, concise, high-impact analysis."

    data = {
        "systemInstruction": {"parts": [{"text": sys_msg}]},
        "contents": [{"parts": parts}],
        "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.3}
    }
    
    start_time = time.time()
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        latency = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            rj = resp.json()
            # Gemini usage metadata
            usage = rj.get('usageMetadata', {})
            tokens_in = usage.get('promptTokenCount', 0)
            tokens_out = usage.get('candidatesTokenCount', 0)
            cost = log_usage_telemetry(model, "google", role_key, tokens_in, tokens_out, latency, True, run_id, session_id, workflow, user_id=user_id)
            return {
                "success": True, 
                "response": rj['candidates'][0]['content']['parts'][0]['text'], 
                "model": model,
                "usage": {"input": tokens_in, "output": tokens_out, "cost": cost, "latency": latency}
            }
            
        log_usage_telemetry(model, "google", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        if resp.status_code in [429, 500, 502, 503, 504]:
            raise Exception(f"API Error {resp.status_code}: {resp.text}")
            
        return {"success": False, "response": f"Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        if "API Error" not in str(e):
            latency = int((time.time() - start_time) * 1000)
            log_usage_telemetry(model, "google", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        raise e

@retry_with_backoff(retries=2, backoff_in_seconds=2)
def call_perplexity(prompt, role_key, model=None, run_id=None, session_id=None, workflow=None, user_id=None, system_message=None):
    role = expand_role(role_key)
    # Respect env var if model not explicitly passed
    if model is None:
        model = os.getenv("PERPLEXITY_MODEL", "sonar-pro")

    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return {"success": False, "response": "Perplexity API key is not configured."}

    # Use provided system message or build default from role
    sys_msg = system_message if system_message else f"You are {role}. Provide accurate, sourced information. Cite sources."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "KorumOS/2.0"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 6000,
        "temperature": 0.3
    }
    
    start_time = time.time()
    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data, timeout=60)
        latency = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            rj = resp.json()
            usage = rj.get('usage', {})
            tokens_in = usage.get('prompt_tokens', 0)
            tokens_out = usage.get('completion_tokens', 0)
            cost = log_usage_telemetry(model, "perplexity", role_key, tokens_in, tokens_out, latency, True, run_id, session_id, workflow, user_id=user_id)
            # Extract Perplexity citations array if present
            citations = rj.get('citations', [])
            return {
                "success": True,
                "response": rj['choices'][0]['message']['content'],
                "model": model,
                "citations": citations,
                "usage": {"input": tokens_in, "output": tokens_out, "cost": cost, "latency": latency}
            }
        
        log_usage_telemetry(model, "perplexity", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        if resp.status_code in [429, 500, 502, 503, 504]:
            raise Exception(f"Perplexity API Error {resp.status_code}: {resp.text}")
            
        return {"success": False, "response": f"Perplexity Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        if "API Error" not in str(e):
            latency = int((time.time() - start_time) * 1000)
            log_usage_telemetry(model, "perplexity", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        raise e

def call_local_llm(prompt, role_key, model="local-model", run_id=None, session_id=None, workflow=None, user_id=None, system_message=None):
    """
    Calls a local LLM running via LM Studio.
    """
    role = expand_role(role_key)
    base_url = os.getenv("LOCAL_LLM_URL", "http://localhost:1234")
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    # Use provided system message or build default from role
    sys_msg = system_message if system_message else f"You are {role}. Provide clear, short answers."

    start_time = time.time()
    try:
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        resp = requests.post(url, headers=headers, json=data, timeout=120) 
        latency = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            # Log with 0 cost for local
            log_usage_telemetry("local-mistral", "local", role_key, 0, 0, latency, True, run_id, session_id, workflow, user_id=user_id)
            return {"success": True, "response": content, "model": "local-mistral"}
        
        log_usage_telemetry("local-mistral", "local", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        return {"success": False, "response": f"Local Error {resp.status_code}: {resp.text}"}
        
    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        log_usage_telemetry("local-mistral", "local", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        return {"success": False, "response": f"Local Exception: {str(e)}"}

@retry_with_backoff()
def call_mistral_api(prompt, role_key, model=None, images=None, run_id=None, session_id=None, workflow=None, user_id=None, timeout=60, system_message=None):
    role = expand_role(role_key)
    if model is None:
        model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    if images:
        model = "pixtral-large-latest"
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({"type": "image_url", "image_url": f"data:{img['mime_type']};base64,{img['base64']}"})
    else:
        content = prompt

    # Use provided system message or build default from role
    sys_msg = system_message if system_message else f"You are {role}. Provide expert analysis."

    api_key = os.getenv("MISTRAL_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": content}],
        "temperature": 0.3
    }
    
    start_time = time.time()
    try:
        resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=timeout)
        latency = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            rj = resp.json()
            usage = rj.get('usage', {})
            tokens_in = usage.get('prompt_tokens', 0)
            tokens_out = usage.get('completion_tokens', 0)
            cost = log_usage_telemetry(model, "mistral", role_key, tokens_in, tokens_out, latency, True, run_id, session_id, workflow, user_id=user_id)
            return {
                "success": True, 
                "response": rj['choices'][0]['message']['content'], 
                "model": model,
                "usage": {"input": tokens_in, "output": tokens_out, "cost": cost, "latency": latency}
            }
            
        log_usage_telemetry(model, "mistral", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        if resp.status_code in [429, 500, 502, 503, 504]:
            raise Exception(f"Mistral API Error {resp.status_code}: {resp.text}")
        return {"success": False, "response": f"Mistral Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        if "API Error" not in str(e):
            latency = int((time.time() - start_time) * 1000)
            log_usage_telemetry(model, "mistral", role_key, 0, 0, latency, False, run_id, session_id, workflow, user_id=user_id)
        raise e


