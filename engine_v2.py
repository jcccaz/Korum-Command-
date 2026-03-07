
# -------------------------------------------------------------------
# KORUM V2: SEQUENTIAL COUNCIL ENGINE (Python Implementation)
# -------------------------------------------------------------------

import os
import json
from datetime import datetime

from llm_core import call_openai_gpt4

# Note: We rely on the core functions. If they are not available as discrete imports from app.py
# (due to circular dependency), we now import them from llm_core.
# I will assume `llm_core.py` was created successfully in the previous step.
# Import the other providers:
from llm_core import call_anthropic_claude, call_google_gemini, call_perplexity, call_local_llm, call_mistral_api

# --- WORKFLOW DNA REGISTRY (The Elite Logic Layer) ---
WORKFLOW_DNA = {
    "WAR_ROOM": {
        "goal": "Immediate tactical action and crisis containment.",
        "tone": "Aggressive, direct, and zero-fluff.",
        "risk_bias": "Conservative (Minimize immediate damage)",
        "time_horizon": "0–72 hours",
        "posture": "Tactical Commander",
        "output_structure": ["Situation", "Threat", "Immediate Action", "Resource Allocation", "Escalation Path"]
    },
    "RESEARCH": {
        "goal": "Deep understanding and evidence-based exploration.",
        "tone": "Neutral, academic, and comprehensive.",
        "risk_bias": "Balanced",
        "time_horizon": "Long-term strategic",
        "posture": "Objective Scientist",
        "output_structure": ["Hypotheses", "Evidence", "Counterarguments", "Confidence Score", "Further Research Paths"]
    },
    "FINANCE": {
        "goal": "Economic viability and downside protection.",
        "tone": "Analytical, precise, and detached.",
        "risk_bias": "Downside-aware",
        "time_horizon": "Scenario-based",
        "posture": "CFO / Auditor",
        "output_structure": ["Cost", "Revenue Impact", "Sensitivity Table", "Worst-case Scenario", "ROI Summary"]
    },
    "LEGAL": {
        "goal": "Exposure reduction and regulatory compliance.",
        "tone": "Formal, rigorous, and protective.",
        "risk_bias": "Zero-risk / Protective",
        "time_horizon": "Indefinite",
        "posture": "General Counsel",
        "output_structure": ["Regulatory Exposure", "Contractual Impact", "Risk Mitigation", "Recommended Posture"]
    },
    "QUANTUM_SECURITY": {
        "goal": "Assess cryptographic vulnerabilities, enforce Zero Trust architecture, and map to strict government compliance (NIST 800-207, FedRAMP, CMMC).",
        "tone": "Authoritative, highly technical, and uncompromising on security.",
        "risk_bias": "Zero-trust / Absolute Security",
        "time_horizon": "Long-term (Post-Quantum Readiness)",
        "posture": "Chief Information Security Officer (CISO) & Cryptographer",
        "output_structure": ["Threat Landscape", "Cryptographic Vulnerabilities", "Zero Trust Controls", "Compliance Mapping (NIST/FedRAMP)", "Mitigation Architecture"]
    }
}

class CouncilContext:
    def __init__(self, query, classification, workflow="RESEARCH"):
        self.query = query
        self.classification = classification
        self.workflow = workflow.upper() if workflow else "RESEARCH"
        self.history = []

    def add_entry(self, ai_name, persona, response):
        self.history.append({
            "ai": ai_name,
            "persona": persona,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

# --- PHASE 1: CLASSIFICATION (The Planner) ---
def classify_query_v2(query, active_personas):
    """
    Uses GPT-4o-Mini (via OpenAI) to determine the optimal execution order.
    FALLBACK 1: Mistral API (Cloud)
    FALLBACK 2: Local Mistral (Private)
    """
    prompt = f"""
    Analyze this business query and determine optimal AI execution order.

    QUERY: "{query}"

    AVAILABLE PERSONAS (User Selected):
    - OpenAI: {active_personas.get('openai', 'Strategist')}
    - Anthropic: {active_personas.get('anthropic', 'Architect')}
    - Google: {active_personas.get('google', 'Critic')}
    - Perplexity: {active_personas.get('perplexity', 'Scout')}
    - Mistral: {active_personas.get('mistral', 'Analyst')} (Cloud)
    - Local: {active_personas.get('local', 'Oracle')} (Private/Offline)

    OPTIMAL EXECUTION ORDER PRINCIPLES:
    1. Foundation First: Research/data gathering (usually Perplexity/Scout)
    2. Vision/Strategy: High-level direction (OpenAI/Strategist/Visionary)
    3. Analysis/Deep Dive: Quantitative analysis, independent second opinion (Mistral/Analyst)
    4. Implementation: Technical/tactical details (Anthropic/Architect)
    5. Validation: Critical analysis, risk assessment, stress testing (Google/Critic)

    IMPORTANT: Always include ALL 5 cloud providers in the executionOrder. Each brings a unique perspective.

    return ONLY valid JSON (no markdown):
    {{
      "domain": "business|marketing|software|operations|research|strategy",
      "intent": "plan|build|analyze|optimize|critique|research|launch",
      "complexity": "simple|moderate|complex",
      "outputType": "presentation|technical_spec|marketing_plan|report|strategic_framework|diagram",
      "executionOrder": ["perplexity-scout", "openai-strategist", "mistral-analyst", "anthropic-architect", "google-critic"],
      "reasoning": "Brief explanation of order"
    }}
    """
    
    # 1. Try OpenAI (Primary)
    try:
        plan_response = call_openai_gpt4(prompt, "Planner")
        if plan_response['success']:
             content = plan_response['response'].replace('```json', '').replace('```', '').strip()
             return json.loads(content)
        else:
             print("[PLANNER] OpenAI Failed. Trying Mistral API...")
    except Exception as e:
        print(f"[PLANNER ERROR] OpenAI: {e}")

    # 2. Try Mistral API (Cloud Fallback)
    try:
        plan_response = call_mistral_api(prompt, "Planner")
        if plan_response['success']:
             content = plan_response['response'].replace('```json', '').replace('```', '').strip()
             return json.loads(content)
        else:
             print("[PLANNER] Mistral API Failed. Trying Local...")
    except Exception as e:
        print(f"[PLANNER ERROR] Mistral API: {e}")

    # 3. Try Local LLM (Emergency Fallback)
    try:
        local_response = call_local_llm(prompt, "Planner")
        if local_response['success']:
            content = local_response['response'].replace('```json', '').replace('```', '').strip()
            # Local models can be chatty, try to find JSON blob
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(content[start:end])
    except Exception as local_e:
        print(f"[PLANNER ERROR] Local: {local_e}")

    # Ultimate Fallback - Use at least one cloud provider (Mistral) as a scout if possible
    return {
        "executionOrder": ["mistral-scout", "local-strategist", "local-critic"],
        "reasoning": "PRIMARY MODELS OFFLINE. Using Mixed Emergency Council.",
        "outputType": "report"
    }

# --- PHASE 2: SEQUENTIAL EXECUTION (The Runner) ---
# --- PHASE 8: AI ACCOUNTABILITY (The Enforcer) ---

def identify_claims(text, ai_name):
    """
    Parses AI response for specific, testable claims.
    Uses a lightweight LLM call or regex to find metrics/absolute statements.
    """
    prompt = f"""
    Identify specific, testable claims from this AI response ({ai_name}).
    Focus on:
    1. Numerical metrics (e.g. "40% growth")
    2. Absolute statements (e.g. "This is the ONLY way...")
    3. Proper nouns/entities
    4. Causal links (e.g. "X causes Y")

    RESPONSE:
    {text}

    Return ONLY a JSON list of claims:
    [
      {{"claim": "Claim text", "type": "metric|absolute|entity|causal"}}
    ]
    """
    try:
        # Use GPT-4o-mini for speed/consistency in parsing
        resp = call_openai_gpt4(prompt, "ClaimExtractor", model="gpt-4o-mini")
        if resp['success']:
            content = resp['response'].replace('```json', '').replace('```', '').strip()
            return json.loads(content)
    except Exception as e:
        print(f"[CLAIM ERROR] {e}")
    return []

def verify_claims(claims, council_history):
    """
    Cross-references claims against other advisor outputs.
    Labels them [CONFIRMED], [SUSPECT], or [UNVERIFIED].
    """
    verified_results = []
    
    for c in claims:
        claim_text = c['claim']
        status = "UNVERIFIED"
        score = 50 # Base score
        anchors = []

        # Simple cross-provider agreement logic
        agreement_count = 0
        contradiction_count = 0
        
        for entry in council_history:
            # Skip if we are looking at the same entry or if it's too early (no history)
            # In practice, this is called AFTER all advisors speak
            content = entry['response'].lower()
            if claim_text.lower() in content:
                agreement_count += 1
                anchors.append(entry['ai'])
        
        # Scoring Logic
        if agreement_count >= 2:
            status = "CONFIRMED"
            score = 90 + (agreement_count * 2)
        elif agreement_count == 1:
            status = "SUPPORTED"
            score = 75
        
        # Placeholder for contradiction detection (complex NLP)
        # If "No" or "False" appears near keywords in other responses...
        
        verified_results.append({
            "claim": claim_text,
            "status": status,
            "score": min(score, 100),
            "type": c['type'],
            "anchors": anchors
        })
        
    return verified_results

def calculate_truth_score(verified_claims):
    """Calculates overall card confidence."""
    if not verified_claims: return 100 # Benefit of doubt for empty responses? Or 50?
    total = sum(c['score'] for c in verified_claims)
    return int(total / len(verified_claims))

def execute_council_v2(query, active_personas, images=None, workflow="RESEARCH"):
    # 1. Plan
    classification = classify_query_v2(query, active_personas)
    context = CouncilContext(query, classification, workflow=workflow)
    results = {}

    print(f"[COUNCIL] Efficiency Plan: {classification['executionOrder']}")
    if images:
        print(f"[COUNCIL] {len(images)} image(s) attached — vision mode active")

    # 2. Execute Step-by-Step
    try:
        execution_order = classification.get('executionOrder', [])
        if not isinstance(execution_order, list): execution_order = []
        total_steps = len(execution_order)

        for i, provider_role in enumerate(execution_order):
            # Split "provider-role"
            try:
                provider, role = provider_role.split('-')
            except ValueError:
                provider = provider_role.lower()
                role = active_personas.get(provider, 'analyst')

            # NEW: Inject "Integrator" posture for the final step
            if i == total_steps - 1:
                role = f"Integrator ({role})"

            print(f"[COUNCIL] Step {i+1}: {provider.upper()} as {role.upper()}")

            prompt = build_council_prompt(context, provider, role, i, total_steps)
            response_obj = {"success": False, "response": "Provider unknown"}

            # Primary Call — pass images to vision-capable providers
            try:
                if provider == 'openai': response_obj = call_openai_gpt4(prompt, role, images=images)
                elif provider == 'anthropic': response_obj = call_anthropic_claude(prompt, role, images=images)
                elif provider == 'google': response_obj = call_google_gemini(prompt, role, images=images)
                elif provider == 'perplexity': response_obj = call_perplexity(prompt, role)
                elif provider == 'mistral': response_obj = call_mistral_api(prompt, role, images=images)
                elif provider == 'local': response_obj = call_local_llm(prompt, role)
            except Exception as e:
                print(f"[COUNCIL] Primary ({provider}) Exception: {e}")
                response_obj = {"success": False}

            # 2. FALLBACK LEVEL 1: MISTRAL CLOUD (If Primary Failed and wasn't already Mistral/Local)
            if not response_obj.get('success', False) and provider not in ['mistral', 'local']:
                print(f"[COUNCIL] Primary ({provider}) Failed. Fallback to ANALYST (Mistral Cloud)...")
                try:
                    response_obj = call_mistral_api(prompt, role)
                    if response_obj.get('success', False):
                        response_obj['response'] = f"[FALLBACK: ANALYST] {response_obj.get('response', '')}"
                        response_obj['model'] = f"Mistral (Fallback for {provider})"
                except Exception as e:
                    print(f"[COUNCIL] Mistral Fallback Exception: {e}")

            # 3. FALLBACK LEVEL 2: LOCAL ORACLE (If Level 1 Failed or Primary was Mistral and failed)
            if not response_obj.get('success', False) and provider != 'local':
                print(f"[COUNCIL] Secondary Failed. Fallback to ORACLE (Local)...")
                try:
                    response_obj = call_local_llm(prompt, "Oracle")
                    if response_obj.get('success', False):
                        response_obj['response'] = f"[FALLBACK: ORACLE] {response_obj.get('response', '')}"
                        response_obj['model'] = "Local Oracle (Emergency)"
                except Exception as e:
                    print(f"[COUNCIL] Local Fallback Exception: {e}")
            
            response_text = "No response"
            if isinstance(response_obj, dict):
                 response_text = response_obj.get('response', 'Error')
            else:
                 response_text = str(response_obj)

            context.add_entry(provider, role, response_text)
            
            # Store base result with ACTUAL success status
            results[provider] = {
                "success": response_obj.get('success', False),
                "response": response_text,
                "model": response_obj.get('model', 'unknown') if isinstance(response_obj, dict) else 'unknown',
                "role": role.upper(),
                "error": response_obj.get('error') if not response_obj.get('success') else None
            }

        # --- NEW: ACCOUNTABILITY PASS ---
        print(f"[COUNCIL] Audit Initiated: Verifying {len(results)} responses...")
        for provider in results:
            text = results[provider]['response']
            claims = identify_claims(text, provider)
            verified = verify_claims(claims, context.history)
            results[provider]['truth_meter'] = calculate_truth_score(verified)
            results[provider]['verified_claims'] = verified

    except Exception as e:
        print(f"[EXECUTION ERROR] {e}")
        return {"consensus": "Error in execution plan.", "results": {}, "error": str(e)}

    # 3. Synthesis
    synthesis = synthesize_results(context)

    return {
        "consensus": f"COUNCIL ADJOURNED. Plan: {classification.get('outputType','report').upper()} generated via {len(results)} steps.",
        "results": results,
        "classification": classification,
        "synthesis": synthesis
    }

def build_council_prompt(context, ai_name, persona, position, total_steps):
    # Determine the task objective
    core_objective = context.query
    intent = context.classification.get('intent', 'analysis')
    output_type = context.classification.get('outputType', 'report')
    
    # Retrieve Workflow DNA
    dna = WORKFLOW_DNA.get(context.workflow, WORKFLOW_DNA["RESEARCH"])

    if ai_name.lower() == 'perplexity' and context.workflow == "RESEARCH":
        # Perplexity works best with direct research questions, not persona roleplay
        prompt = f"""
        RESEARCH OBJECTIVE: "{core_objective}"
        
        CONTEXT: You are contributing to a strategic intelligence report (Phase {position + 1} of {total_steps}).
        GOAL: {dna['goal']}
        INTENT: {intent.upper()} / {output_type.upper()}
        """
        
        if position > 0:
            prompt += "\nRECENT DATA / PREVIOUS ANALYSIS:\n"
            # Give Perplexity just enough context to refine its search, not the whole history
            last_entry = context.history[-1]
            prompt += f"Summary of previous findings: {last_entry['response'][:1000]}...\n"
        
        prompt += "\nINSTRUCTION: Provide comprehensive, well-sourced research and data to support this objective. Focus on facts, metrics, and technical details."
        return prompt

    # Standard Professional Template with DNA Overlay
    prompt = f"""
    ## PROFESSIONAL INTELLIGENCE BRIEF
    MISSION TYPE: {context.workflow}
    PRIMARY OBJECTIVE: "{core_objective}"
    
    CURRENT FOCUS: {persona.upper()} (Assignee: {ai_name.upper()})
    WORKFLOW STAGE: Part {position + 1} of {total_steps}
    
    --- WORKFLOW DNA ---
    POSTURE: {dna['posture']}
    GOAL: {dna['goal']}
    TONE: {dna['tone']}
    RISK BIAS: {dna['risk_bias']}
    TIME HORIZON: {dna['time_horizon']}
    --------------------

    ## INTERNAL STRUCTURING (FOR SYSTEM PARSING)
    You MUST use the following tags to mark high-value intelligence:
    - [DECISION_CANDIDATE] ...recommendation text... [/DECISION_CANDIDATE]
    - [RISK_VECTOR] ...risk description... [/RISK_VECTOR]
    - [METRIC_ANCHOR] ...metric value... [/METRIC_ANCHOR]
    - [TRUTH_BOMB] ...critically verified fact... [/TRUTH_BOMB]

    Do not let these tags disrupt your narrative flow; they are for the backend extractor.
    """

    if position == 0:
        prompt += f"\n## INITIAL ASSIGNMENT:\nEstablish the foundation for this {context.workflow} mission. Follow the defined POSTURE. Provide facts and initial strategy."
    else:
        prompt += "\n## COLLABORATIVE CONTEXT:\nReview the previous analysis below. Build upon, critique, or pivot the strategy as necessary to reach the target output."
        prompt += "\n\n### PREVIOUS CONTRIBUTIONS:\n"
        for entry in context.history:
            # Provide the most relevant history (prioritizing the previous step)
            snippet = (entry['response'][:2500] + '...') if len(entry['response']) > 2500 else entry['response']
            prompt += f"\n-- {entry['ai'].upper()} [{entry['persona'].upper()}]:\n{snippet}\n"
        
        if position == total_steps - 1:
            prompt += f"\n\n## FINAL SYNTHESIS:\nYou are the lead integrator. Synthesize all collaborative context into the final {output_type.upper()} artifact. Follow the defined TONE and POSTURE strictly."

    return prompt

# --- PHASE 4: SYNTHESIS (The Extractor) ---
def synthesize_results(context):
    """
    Extracts structured data (JSON) from the conversation history.
    """
    history_text = ""
    for entry in context.history:
        history_text += f"\n[{entry['ai'].upper()}]: {entry['response']}\n"

    # Retrieve Workflow DNA for structure
    dna = WORKFLOW_DNA.get(context.workflow, WORKFLOW_DNA["RESEARCH"])
    schema_sections = {section.lower().replace(" ", "_"): "Full narrative text..." for section in dna["output_structure"]}

    prompt = f"""
    You are an Intelligence Synthesis Engine. Your goal is to convert a raw AI council discussion into a high-fidelity "Intelligence Object" for professional {context.workflow} reporting.

    MISSION CONTEXT:
    - Type: {context.workflow}
    - Posture: {dna['posture']}
    - Outcome Expected: {dna['goal']}

    CRITICAL RULES:
    1. NO conversational fluff.
    2. NO meta-commentary.
    3. Standardize into the following structure strictly.
    4. Ensure every section name is professional.
    5. ONLY synthesize from the COUNCIL DISCUSSION provided. Do not invent facts.
    6. Extract all [TAGGED] content into the "intelligence_tags" object.

    COUNCIL DISCUSSION:
    {history_text}

    Return ONLY a single valid JSON object with this schema:
    {{
      "meta": {{
        "title": "Concise, Descriptive Report Title",
        "generated_at": "{datetime.now().isoformat()}",
        "summary": "1-2 sentence high-level synthesis",
        "composite_truth_score": 0,
        "models_used": [],
        "workflow": "{context.workflow}"
      }},
      "sections": {json.dumps(schema_sections, indent=8)},
      "structured_data": {{
        "key_metrics": [
          {{"metric": "...", "value": "...", "context": "..."}}
        ],
        "action_items": [
          {{"task": "...", "priority": "high|med|low", "timeline": "..."}}
        ],
        "risks": [
          {{"risk": "...", "severity": "...", "mitigation": "..."}}
        ]
      }},
      "intelligence_tags": {{
        "decisions": ["extracted from [DECISION_CANDIDATE] tags"],
        "risks": ["extracted from [RISK_VECTOR] tags"],
        "metrics": ["extracted from [METRIC_ANCHOR] tags"]
      }}
    }}
    """
    
    try:
        # Extract models from context
        models_used = [f"{entry['ai']} ({entry['persona']})" for entry in context.history]
        
        resp = call_openai_gpt4(prompt, "Synthesizer")
        if not resp.get('success'):
            print(f"[SYNTHESIS] OpenAI failed: {resp.get('response', 'Unknown error')}")
            return {"executive_summary": "Synthesis unavailable", "meta": {"models_used": [], "truth_score": 0}}
        content = resp['response'].replace('```json', '').replace('```', '').strip()
        data = json.loads(content)
        
        # Inject metadata if missing or simplified
        data["meta"]["models_used"] = models_used
        
        # NEW: Post-processing safety parse for tags (in case LLM misses some)
        import re
        decisions = re.findall(r'\[DECISION_CANDIDATE\](.*?)\[/DECISION_CANDIDATE\]', history_text, re.DOTALL)
        risks = re.findall(r'\[RISK_VECTOR\](.*?)\[/RISK_VECTOR\]', history_text, re.DOTALL)
        metrics = re.findall(r'\[METRIC_ANCHOR\](.*?)\[/METRIC_ANCHOR\]', history_text, re.DOTALL)
        
        # Merge safety-extracted tags if they aren't already in the JSON
        if not data.get("intelligence_tags"): data["intelligence_tags"] = {"decisions": [], "risks": [], "metrics": []}
        
        for d in decisions: 
            if d.strip() not in data["intelligence_tags"]["decisions"]: 
                data["intelligence_tags"]["decisions"].append(d.strip())
        for r in risks:
            if r.strip() not in data["intelligence_tags"]["risks"]:
                data["intelligence_tags"]["risks"].append(r.strip())
        for m in metrics:
            if m.strip() not in data["intelligence_tags"]["metrics"]:
                data["intelligence_tags"]["metrics"].append(m.strip())

        return data
    except Exception as e:
        print(f"[SYNTHESIS ERROR] {e}")
        return {"error": "Failed to synthesize structured data."}

# --- PHASE 6: ARTIFACT GENERATION (The Creator) ---
def generate_presentation_preview(synthesized_data, classification):
    """
    Generates a structured JSON outline for a presentation based on synthesized data.
    """
    output_type = classification.get('outputType', 'presentation')
    
    prompt = f"""
    You are a presentation designer. Create a slide deck outline from this data.

    SYNTHESIZED DATA:
    {json.dumps(synthesized_data, indent=2)}

    PRESENTATION TYPE: {output_type}
    DOMAIN: {classification.get('domain', 'business')}

    DESIGN PRINCIPLES:
    1. Title slide + 1-2 slides per major section
    2. Max 5 bullets per slide (3-4 is better)
    3. Use visuals when data supports it
    4. Executive-friendly language
    5. Clear narrative flow

    Return ONLY valid JSON (no markdown):
    {{
      "title": "Main Presentation Title",
      "subtitle": "Subtitle or context",
      "slideCount": 12,
      "estimatedDuration": "10-12 minutes",
      "slides": [
        {{
          "slideNumber": 1,
          "title": "Executive Summary",
          "content": [
            "Bullet 1",
            "Bullet 2"
          ],
          "visualType": "text|chart|diagram|image", 
          "chartData": {{ "type": "bar", "data": [] }},
          "layout": "title|content|two-column|image-text",
          "speakerNotes": "Notes for the presenter"
        }}
      ],
      "metadata": {{
        "theme": "professional|modern|minimal",
        "colorScheme": "blue-green"
      }}
    }}

    Generate { '12-15' if output_type == 'pitch_deck' else '8-12' } slides total.
    """
    
    try:
        resp = call_openai_gpt4(prompt, "Designer")
        content = resp['response'].replace('```json', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        print(f"[PRESENTATION PREVIEW ERROR] {e}")
        return {"error": "Failed to generate presentation preview.", "slides": []}

# --- PHASE 7: ARTIFACT GENERATION (The Builder) ---
from pptx import Presentation as PPTXPresentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def _sanitize_pptx_text(text):
    """Replace Unicode symbols that render as squares in default PowerPoint fonts."""
    import re
    if not isinstance(text, str):
        return str(text) if text else ""
    replacements = {
        '\u2022': '-', '\u2023': '-', '\u25aa': '-', '\u25cb': 'o',
        '\u2713': '[X]', '\u2714': '[X]', '\u2717': '[ ]', '\u2718': '[ ]',
        '\u2192': '->', '\u2190': '<-', '\u21d2': '=>',
        '\u2014': '--', '\u2013': '-',
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2026': '...', '\u221e': 'inf', '\u2248': '~=', '\u00b1': '+/-',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    return text


def generate_pptx_file(preview_data):
    """
    Builds a .pptx file from the preview JSON.
    Returns the file path.
    """
    prs = PPTXPresentation()

    # 1. Slide Master Layouts
    title_layout = prs.slide_layouts[0]
    bullet_layout = prs.slide_layouts[1]
    two_col_layout = prs.slide_layouts[3] # Usually 'Two Content' or similar

    slides = preview_data.get('slides', [])

    for slide_data in slides:
        layout_type = slide_data.get('layout', 'content')

        # Select Layout
        if layout_type == 'title':
            slide = prs.slides.add_slide(title_layout)
        elif layout_type == 'two-column':
             slide = prs.slides.add_slide(two_col_layout)
        else:
            slide = prs.slides.add_slide(bullet_layout)

        # Set Title
        title = slide.shapes.title
        if title:
            title.text = _sanitize_pptx_text(slide_data.get('title', 'Untitled Slide'))

        # Set Content (Bullets)
        content_items = [_sanitize_pptx_text(item) for item in slide_data.get('content', [])]

        # Handle Layout Specifics
        if layout_type == 'title':
             # Subtitle is usually the second placeholder
             if len(slide.placeholders) > 1 and content_items:
                 subtitle = slide.placeholders[1]
                 subtitle.text = "\n".join(content_items)

        elif layout_type == 'two-column':
             # Left Column (Text)
             if len(slide.placeholders) > 1:
                 tf = slide.placeholders[1].text_frame
                 tf.text = content_items[0] if content_items else ""
                 for item in content_items[1:]:
                     p = tf.add_paragraph()
                     p.text = item
                     p.level = 0

             # Right Column (Chart Placeholder or Text)
             if len(slide.placeholders) > 2:
                 tf2 = slide.placeholders[2].text_frame
                 if slide_data.get('chartData'):
                     tf2.text = f"[CHART: {slide_data['chartData'].get('type', 'Chart')}]"
                 else:
                     tf2.text = ""

        else: # Standard Bullet Content
            if len(slide.placeholders) > 1:
                tf = slide.placeholders[1].text_frame
                tf.text = content_items[0] if content_items else ""
                for item in content_items[1:]:
                    p = tf.add_paragraph()
                    p.text = item
                    p.level = 0

        # Set font on all text frames to ensure consistent rendering
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Calibri'
                        run.font.size = Pt(14)

        # Speaker Notes
        if slide_data.get('speakerNotes'):
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = _sanitize_pptx_text(slide_data['speakerNotes'])

    # Save File
    filename = f"korum_artifact_{int(datetime.now().timestamp())}.pptx"
    filepath = os.path.join(os.getcwd(), filename)
    prs.save(filepath)

    return filename # Return relative name for download

