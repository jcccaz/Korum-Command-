
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

class CouncilContext:
    def __init__(self, query, classification):
        self.query = query
        self.classification = classification
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
    3. Implementation: Technical/tactical details (Anthropic/Architect)
    4. Validation: Critical analysis, risk assessment (Google/Critic)

    return ONLY valid JSON (no markdown):
    {{
      "domain": "business|marketing|software|operations|research|strategy",
      "intent": "plan|build|analyze|optimize|critique|research|launch",
      "complexity": "simple|moderate|complex",
      "outputType": "presentation|technical_spec|marketing_plan|report|strategic_framework|diagram",
      "executionOrder": ["perplexity-scout", "openai-strategist", "anthropic-architect", "google-critic"],
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

    # Ultimate Fallback
    return {
        "executionOrder": ["local-analyst", "local-strategist", "local-critic"],
        "reasoning": "ALL SYSTEMS OFFLINE. Using Local Emergency Council.",
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

def execute_council_v2(query, active_personas):
    # 1. Plan
    classification = classify_query_v2(query, active_personas)
    context = CouncilContext(query, classification)
    results = {}

    print(f"[COUNCIL] Efficiency Plan: {classification['executionOrder']}")

    # 2. Execute Step-by-Step
    try:
        execution_order = classification.get('executionOrder', [])
        if not isinstance(execution_order, list): execution_order = []
        
        for i, step in enumerate(execution_order):
            parts = step.split('-')
            provider = parts[0].lower()
            role = parts[1] if len(parts) > 1 else "advisor"

            print(f"[COUNCIL] Step {i+1}: {provider.upper()} as {role.upper()}")

            prompt = build_council_prompt(context, provider, role, i, len(execution_order))
            response_obj = {"success": False, "response": "Provider unknown"}
            
            # Primary Call
            try:
                if provider == 'openai': response_obj = call_openai_gpt4(prompt, role)
                elif provider == 'anthropic': response_obj = call_anthropic_claude(prompt, role)
                elif provider == 'google': response_obj = call_google_gemini(prompt, role)
                elif provider == 'perplexity': response_obj = call_perplexity(prompt, role)
                elif provider == 'mistral': response_obj = call_mistral_api(prompt, role)
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
            
            # Store base result
            results[provider] = {
                "success": True,
                "response": response_text,
                "model": response_obj.get('model', 'unknown') if isinstance(response_obj, dict) else 'unknown',
                "role": role.upper()
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
    prompt = f"""
    You are {ai_name.upper()}, acting as {persona.upper()}.
    
    ORIGINAL MISSION: "{context.query}"
    
    PLAN:
    - Intent: {context.classification.get('intent', 'analysis')}
    - Output: {context.classification.get('outputType', 'report')}
    
    YOUR ROLE: Step {position + 1} of {total_steps}.
    """

    if position == 0:
        prompt += "\nYou are the FIRST advisor. Lay the foundation. Provide facts, context, or initial strategy."
    else:
        prompt += "\nPREVIOUS COUNCIL OUTPUT:\n"
        for entry in context.history:
            # Add limited history to avoid blowing up context, or full history if supported
            # Truncating huge responses if needed is smart for V2
            snippet = (entry['response'][:2000] + '...') if len(entry['response']) > 2000 else entry['response']
            prompt += f"\n--- [ADVISOR: {entry['ai'].upper()} ({entry['persona']})] ---\n{snippet}\n"
        
        prompt += "\nINSTRUCTION: Review the previous output. Build upon it, refine it, or critique it. Do NOT repeat generic pleasantries. Focus on the next stage of the pipeline."
        
        if position == total_steps - 1:
            prompt += "\n\nAS THE FINAL ADVISOR: Synthesize the findings into the requested Output format."

    return prompt

# --- PHASE 4: SYNTHESIS (The Extractor) ---
def synthesize_results(context):
    """
    Extracts structured data (JSON) from the conversation history.
    """
    history_text = ""
    for entry in context.history:
        history_text += f"\n[{entry['ai'].upper()}]: {entry['response']}\n"

    prompt = f"""
    You are a data extraction specialist. Extract ONLY hard facts and structured data from this AI council discussion.

    CRITICAL RULES:
    1. NO conversational fluff ("As mentioned earlier", "Great point", "I agree")
    2. NO meta-commentary ("This is important because...")
    3. ONLY concrete facts, numbers, actions, and technical details
    4. Format for direct use in professional documents

    COUNCIL DISCUSSION:
    {history_text}

    EXTRACT the following (return ONLY valid JSON, no markdown):

    {{
      "keyPoints": [
        "Self-contained fact 1 (no pronouns, no references to 'we' or 'the team')",
        "Self-contained fact 2"
      ],
      
      "numericData": [
        {{
          "metric": "Gen Z crypto adoption rate",
          "value": 40,
          "unit": "percent",
          "context": "Weekly trading activity in 2025"
        }}
      ],
      
      "actionItems": [
        {{
          "task": "Register Delaware C-Corp for token entity",
          "timeline": "Months 1-3",
          "priority": "high"
        }}
      ],
      
      "technicalSpecs": {{
        "technologies": ["Ethereum Layer 2", "Polygon", "Solana"],
        "frameworks": ["ERC-20 standard", "Multi-sig wallets"],
        "integrations": ["Uniswap", "MetaMask", "Coinbase Wallet"]
      }},
      
      "narrativeStructure": {{
        "introduction": "Gen Z represents 40% of crypto traders with preference for social-good tokens",
        "problemStatement": "Traditional finance excludes values-driven investors",
        "solution": "Purpose-driven token with transparent impact metrics",
        "implementation": "Layer 2 deployment with gamified staking",
        "conclusion": "Projected 1M users in 18 months based on comparable launches"
      }},
      
      "citations": [
        {{
          "claim": "Gen Z crypto adoption at 40% weekly trading",
          "source": "Coinbase 2025 Demographics Report"
        }}
      ],
      
      "risks": [
        {{
          "risk": "SEC classification as unregistered security",
          "severity": "high",
          "mitigation": "Utility-focused design with legal review pre-launch"
        }}
      ]
    }}

    IMPORTANT: Extract ONLY what exists in the council discussion. If no numeric data mentioned, return empty array. If no risks discussed, omit the field.
    """
    
    try:
        # Use a smart model for extraction
        resp = call_openai_gpt4(prompt, "Synthesizer")
        content = resp['response'].replace('```json', '').replace('```', '').strip()
        return json.loads(content)
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
            title.text = slide_data.get('title', 'Untitled Slide')

        # Set Content (Bullets)
        content_items = slide_data.get('content', [])
        
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
             # For MVP, we just put text or a placeholder note about the chart
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

        # Speaker Notes
        if slide_data.get('speakerNotes'):
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = slide_data['speakerNotes']

    # Save File
    filename = f"korum_artifact_{int(datetime.now().timestamp())}.pptx"
    filepath = os.path.join(os.getcwd(), filename)
    prs.save(filepath)
    
    return filename # Return relative name for download

