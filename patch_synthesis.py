
import re

file_path = r'c:\Users\carlo\Projects\KorumOS\engine_v2.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Restore the lost dictionary entries and fix the mangled JSON structure
# We'll replace the entire SECTION_DIRECTIVES block to be safe.

new_directives = """        "critical_challenges": (
            "Stress-test the decision. Present in two groups: "
            "HIGH IMPACT (2-3 items) and SECONDARY CONSIDERATIONS (2-3 items). "
            "For each challenge: state what it is, why it matters, and what would resolve it. "
            "End with a one-sentence synthesis: do the uncertainties outweigh the risk of inaction?"
        ),
        "tradeoffs": (
            "Build a structured comparison using [STRUCTURED_TABLE] format. "
            "Columns: Dimension | Short-Term Option | Long-Term Option. "
            "Dimensions: Operational, Financial, Customer/User, Strategic. "
            "Each cell: concise statement (1-2 sentences max). No paragraphs in cells."
        ),
        "decision": (
            "State the decision in ONE clear sentence. Then provide rationale as 3-5 bullet points. "
            "NO hedging. NO 'it depends'. This is the final call. "
            "Format: 'Decision: [Clear action statement]' followed by rationale bullets. "
            "NO fabricated cost figures or ROI percentages."
        ),
        "action_priorities": (
            "Break execution into 3 HIGH-LEVEL phases:\\n"
            "Immediate: 1-2 actions\\n"
            "Near-Term: 1-2 actions\\n"
            "Mid-Term: 1-2 actions\\n"
            "Actions must be executive-level decisions, NOT detailed playbooks. "
            "NO tool/vendor lists. NO day-by-day or month-by-month timelines. NO staffing plans. "
            "NO specific date ranges like '0-30 days' — use 'Immediate', 'Near-Term', 'Mid-Term'. "
            "Example good actions: "
            "'Identify and stabilize highest-risk network segments', "
            "'Upgrade core infrastructure in high-traffic areas', "
            "'Improve monitoring and network resilience'"
        ),
        "confidence": (
            "State the confidence band: High, Moderate-High, Moderate, or Low. "
            "KEY ASSUMPTIONS: 3-5 bullet points on what must hold true. "
            "LIMITATIONS: 2-3 bullet points on data gaps or unresolved questions. "
            "Confidence must reflect actual data quality, not optimism. "
            "If financial details or baselines are missing, confidence cannot be 'High' — use 'Moderate-High' at most. "
            "If UNKNOWNs outnumber VERIFIED facts, confidence cannot exceed Medium and score cannot exceed 70. "
            "If root cause, projected impact, or ROI claims are unverified, confidence must be Low and score must not exceed 45."
        ),"""

# Target the mangled version
pattern_directives = re.compile(r'        "critical_challenges": \(\s+"Actions must be executive-level decisions.*?Example good actions: "\s+\),', re.DOTALL)
content = pattern_directives.sub(new_directives, content)

# 2. Inject PRIMARY OBJECTIVE
old_mission = """    ## MISSION CONTEXT:
    - Type: {context.workflow}
    - Posture: {dna['posture']}
    - Outcome Expected: {dna['goal']}"""

new_mission = """    ## MISSION CONTEXT:
    - PRIMARY OBJECTIVE: {context.query}
    - Type: {context.workflow}
    - Posture: {dna['posture']}
    - Outcome Expected: {dna['goal']}"""

content = content.replace(old_mission, new_mission)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch Applied: Restored Directives and Injected Primary Objective.")
