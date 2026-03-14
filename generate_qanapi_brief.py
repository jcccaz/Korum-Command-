"""
KORUM-OS x QANAPI — Demo Briefing Package Generator
Generates a professional PDF handout for the Qanapi demo.
Uses the full brief content with KORUM-OS dark styling.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak)
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CYAN = "#00E5FF"
GREEN = "#00FF9D"
DARK = "#0D1117"
DARK2 = "#161B22"
RED = "#FF4444"
GOLD = "#FFB020"


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('CoverTitle', parent=styles['Title'], fontSize=32, leading=38,
        textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle('CoverSub', parent=styles['Normal'], fontSize=11, leading=14,
        textColor=colors.HexColor(CYAN), fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle('CoverTagline', parent=styles['Normal'], fontSize=13, leading=16,
        textColor=colors.HexColor("#AAAAAA"), fontName='Helvetica', alignment=TA_CENTER, spaceAfter=20))
    styles.add(ParagraphStyle('SectionHead', parent=styles['Normal'], fontSize=14, leading=18,
        textColor=colors.HexColor(CYAN), fontName='Helvetica-Bold', spaceAfter=8, spaceBefore=16))
    styles.add(ParagraphStyle('SubHead', parent=styles['Normal'], fontSize=11, leading=14,
        textColor=colors.HexColor(GREEN), fontName='Helvetica-Bold', spaceAfter=4, spaceBefore=10))
    styles.add(ParagraphStyle('Body', parent=styles['Normal'], fontSize=9.5, leading=13.5,
        textColor=colors.HexColor("#2D2D2D"), fontName='Helvetica', spaceAfter=6))
    styles.add(ParagraphStyle('BodyBold', parent=styles['Normal'], fontSize=9.5, leading=13.5,
        textColor=colors.HexColor("#1A1A1A"), fontName='Helvetica-Bold', spaceAfter=6))
    styles.add(ParagraphStyle('BulletItem', parent=styles['Normal'], fontSize=9, leading=12.5,
        textColor=colors.HexColor("#333333"), fontName='Helvetica', leftIndent=18, spaceAfter=3, bulletIndent=6))
    styles.add(ParagraphStyle('SmallNote', parent=styles['Normal'], fontSize=8, leading=11,
        textColor=colors.HexColor("#666666"), fontName='Helvetica', spaceAfter=4))
    return styles


def dark_heading(text, styles, width=468):
    t = Table([[Paragraph(text.upper(), styles['SectionHead'])]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(DARK)),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return t


def sub_heading(text, styles, width=468):
    t = Table([[Paragraph(text.upper(), styles['SubHead'])]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(DARK2)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return t


def bullet(text, styles):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", styles['BulletItem'])


def make_table(data, col_widths, styles, hdr_bg=DARK, hdr_color=CYAN, alt_bg="#F6F8FA"):
    cell_s = ParagraphStyle('TC', parent=styles['Body'], fontSize=8.5, leading=11, wordWrap='CJK')
    hdr_s = ParagraphStyle('TH', parent=cell_s, textColor=colors.HexColor(hdr_color), fontName='Helvetica-Bold')
    rows = []
    for i, row in enumerate(data):
        s = hdr_s if i == 0 else cell_s
        rows.append([Paragraph(str(c), s) for c in row])
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(hdr_bg)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(alt_bg)]),
    ]))
    return t


def generate():
    filepath = os.path.join(OUTPUT_DIR, f"KORUM-OS_Qanapi_Brief_{datetime.now().strftime('%Y%m%d')}.pdf")
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            topMargin=0.6*inch, bottomMargin=0.5*inch,
                            leftMargin=0.7*inch, rightMargin=0.7*inch)
    styles = build_styles()
    story = []
    W = 468

    # ═══════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 60))
    cover = Table([
        [Paragraph("KORUM-OS  x  QANAPI", styles['CoverTitle'])],
        [Paragraph("Trusted Data.  Trusted Decisions.", styles['CoverTagline'])],
    ], colWidths=[W])
    cover.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(DARK)),
        ('TOPPADDING', (0, 0), (0, 0), 40),
        ('BOTTOMPADDING', (0, -1), (0, -1), 40),
    ]))
    story.append(cover)
    story.append(Spacer(1, 40))

    # Meta
    date_str = datetime.now().strftime("%B %d, %Y")
    meta = [["DATE", "CLASSIFICATION", "VERSION"],
            [date_str, "PROPRIETARY & CONFIDENTIAL", "2.0"]]
    mt = Table(meta, colWidths=[W/3]*3)
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(DARK)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(CYAN)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F6F8FA")),
        ('FONTSIZE', (0, 1), (-1, 1), 9),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(mt)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════
    story.append(dark_heading("Executive Summary", styles, W))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "In high-stakes security environments, the integrity of the <b>decision</b> is just as critical as the "
        "integrity of the <b>data</b>. Qanapi provides quantum-resistant data protection. KORUM-OS provides the "
        "intelligence orchestration layer to ensure that AI-driven analysis is cross-verified, auditable, and truthful.",
        styles['Body']))
    story.append(Paragraph(
        "Together, they deliver a <b>full-stack trusted intelligence pipeline</b> -- from cryptographically "
        "verified inputs to cross-verified, auditable AI outputs.",
        styles['BodyBold']))

    # ═══════════════════════════════════════════════════════════════
    # THE NEURAL COUNCIL
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 10))
    story.append(dark_heading("The Neural Council", styles, W))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "KORUM-OS does not rely on a single AI provider. It convenes a <b>Neural Council</b> of five independent, "
        "world-class models to analyze, verify, and stress-test intelligence in real time. Each AI runs "
        "<b>sequentially</b> -- not in parallel -- so the fifth model has the benefit of four expert perspectives "
        "before it speaks. This mirrors how real intelligence analysis works: iterative, layered, cross-referenced.",
        styles['Body']))
    story.append(Spacer(1, 6))

    council = [
        ["PROVIDER", "MODEL", "COUNCIL ROLE"],
        ["OpenAI", "GPT-4o", "Primary Strategist -- strong reasoning, broad knowledge"],
        ["Anthropic", "Claude Sonnet 4", "Deep Researcher -- nuanced, safety-conscious, thorough"],
        ["Google", "Gemini 2.0 Flash", "Fast Integrator -- speed, data analysis, current knowledge"],
        ["Perplexity", "Sonar Pro", "Live Intelligence -- real-time web search with citations"],
        ["Mistral", "Mistral Small", "Independent Validator -- European perspective, multilingual"],
    ]
    story.append(make_table(council, [80, 110, 278], styles))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "A sixth <b>local AI fallback</b> (via LM Studio) provides air-gapped operation -- no data leaves the network. "
        "This maps directly to classified environments where Qanapi's encryption is most critical.",
        styles['SmallNote']))

    # ═══════════════════════════════════════════════════════════════
    # CORE CAPABILITIES
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 10))
    story.append(dark_heading("Core Capabilities", styles, W))
    story.append(Spacer(1, 8))

    story.append(sub_heading("V2 Reasoning Pipeline", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "A sequential processing engine where five models build upon one another's logic, eliminating "
        "single-model hallucinations. Each AI sees what came before. Each one builds deeper.",
        styles['Body']))

    story.append(sub_heading("Consensus Truth-Scoring", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Every factual claim is cross-checked across all five providers and scored:",
        styles['Body']))
    scores = [
        ["SCORE", "LABEL", "MEANING"],
        ["90-100", "CONFIRMED", "Multiple AIs independently agree"],
        ["70-89", "SUPPORTED", "Majority agreement"],
        ["50-69", "UNVERIFIED", "Mixed signals -- requires investigation"],
        ["<50", "CONTESTED", "AIs disagree -- treat with caution"],
    ]
    story.append(make_table(scores, [70, 100, 298], styles))

    # ── HOW TRUTH SCORING WORKS ──
    story.append(Spacer(1, 8))
    story.append(sub_heading("How Truth Scoring Works — The Full Lifecycle", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Truth scores are not static. They are <b>living metrics</b> that evolve as the intelligence is "
        "tested, challenged, and verified. Here is the complete scoring lifecycle:",
        styles['Body']))
    story.append(Spacer(1, 4))

    # Phase 1: Initial Score
    story.append(Paragraph("<b>Phase 1: Accountability Pass (Automated)</b>", styles['Body']))
    story.append(bullet("After all 5 council phases complete, the <b>Accountability Engine</b> extracts every "
        "testable factual claim from each provider's response using GPT-4o-mini", styles))
    story.append(bullet("Each claim is cross-referenced against all other council members' outputs", styles))
    story.append(bullet("Claims agreed on by 2+ providers = <b>CONFIRMED (+40)</b>. One provider = <b>SUPPORTED (+25)</b>. "
        "No corroboration = <b>UNVERIFIED (baseline 50)</b>", styles))
    story.append(bullet("Legacy crypto without PQC wrappers (RSA, ECC, AES-128, SHA-1) = automatic <b>-20 penalty</b>", styles))
    story.append(bullet("Final score = average of all claim scores for that provider (0-100)", styles))
    story.append(Spacer(1, 4))

    # Phase 2: Interrogation
    story.append(Paragraph("<b>Phase 2: Interrogation Feedback (User-Triggered)</b>", styles['Body']))
    story.append(bullet("User selects a provider card and initiates adversarial cross-examination", styles))
    story.append(bullet("Attacker (GPT-4o) probes for logic gaps; Defender (Claude) must rebut or concede", styles))
    story.append(bullet("Defender concedes 1 point = <b>-5</b>. 2 concessions = <b>-10</b>. 3+ = <b>-15</b>", styles))
    story.append(bullet("Defender holds strong with evidence = <b>+3</b> (defense validated)", styles))
    story.append(bullet("Score updates <b>animate live</b> on the provider's card in real-time", styles))
    story.append(Spacer(1, 4))

    # Phase 3: Verification
    story.append(Paragraph("<b>Phase 3: Source Verification Feedback (User-Triggered)</b>", styles['Body']))
    story.append(bullet("User highlights a specific claim and sends it to Perplexity for fact-checking", styles))
    story.append(bullet("Claim verified as <b>ACCURATE</b> = <b>+5</b> to source provider", styles))
    story.append(bullet("<b>PARTIALLY ACCURATE</b> = <b>-3</b>", styles))
    story.append(bullet("<b>INACCURATE</b> = <b>-10</b>", styles))
    story.append(bullet("Citations from NIST, MITRE ATT&CK, CVE, RFC are included with each verdict", styles))
    story.append(Spacer(1, 4))

    # Phase 4: Export
    story.append(Paragraph("<b>Phase 4: Export & Attestation</b>", styles['Body']))
    story.append(bullet("Final truth scores are embedded in all exported reports (PDF, DOCX, Excel)", styles))
    story.append(bullet("Overall <b>Composite Truth Score</b> = weighted average across all providers", styles))
    story.append(bullet("Compliance attestation footer includes final score + audit date", styles))
    story.append(bullet("Scores that were adjusted by interrogation/verification are reflected in the export", styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>The result:</b> Every number in a KORUM-OS report has been tested. The score tells you not just what the "
        "AI thinks -- but how much the AI's own peers agree, how it held up under attack, and whether external "
        "sources confirmed it.",
        styles['BodyBold']))

    story.append(Spacer(1, 6))
    story.append(sub_heading("Analytic Divergence Layer", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "After all 5 phases complete, a dedicated <b>Divergence Engine</b> compares council outputs across "
        "6 dimensions. Produces consensus/divergence scores (0-100), contested topic analysis with per-provider "
        "positions, confidence gap detection, and resolution requirements. <b>Protocol Variance</b> is flagged "
        "when divergence exceeds 30%.",
        styles['Body']))

    story.append(sub_heading("Red Team Mode", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "After the council finishes, an additional AI runs with a <b>HACKER</b> persona to attack the council's "
        "own conclusions -- finding blind spots, fatal flaws, and exploitable weaknesses before they reach the user.",
        styles['Body']))

    story.append(sub_heading("Interrogation System", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Select any AI's response and cross-examine it. Pick an attacker persona, pick a defender -- "
        "KORUM-OS runs a targeted 2-API adversarial face-off on that specific claim. No full re-run. "
        "Surgical precision. <b>Results feed back into truth scores in real-time.</b>",
        styles['Body']))

    story.append(sub_heading("Verify Mode (Scalpel)", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Highlight any claim from any AI and send it to Perplexity for real-time source verification with "
        "citations. One click. One API call. Show me the receipts. <b>Verification adjusts provider truth scores.</b>",
        styles['Body']))

    story.append(sub_heading("Sentinel (Quick-Strike)", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Sub-2-second responses for follow-ups and quick lookups, with full conversation memory for "
        "multi-turn dialogue.",
        styles['Body']))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # QUANTUM SECURITY WORKFLOW
    # ═══════════════════════════════════════════════════════════════
    story.append(dark_heading("Quantum Security Workflow", styles, W))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Designed specifically for the Qanapi ecosystem, this workflow optimizes the council for post-quantum "
        "cryptography readiness, Zero Trust architecture enforcement, and compliance auditing:",
        styles['Body']))
    story.append(Spacer(1, 4))

    qw = [
        ["PROVIDER", "PERSONA", "FOCUS"],
        ["OpenAI", "Zero Trust Architect", "NIST 800-207, DoD ZTRA, identity-centric access controls"],
        ["Anthropic", "Cryptographer", "AES/RSA analysis, post-quantum crypto, key management"],
        ["Google", "Compliance Auditor", "FedRAMP, CMMC, NIST PQC standards mapping"],
        ["Perplexity", "AI Architect", "Live data on quantum computing timelines, emerging threats"],
        ["Mistral", "Red Team Hacker", "Attacks the deployment strategy -- surfaces the gaps"],
    ]
    story.append(make_table(qw, [80, 120, 268], styles))

    story.append(Spacer(1, 8))
    story.append(sub_heading("Quantum Drift Detection", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "The engine automatically flags legacy cryptographic algorithms (<b>RSA, ECC, ECDSA, AES-128, SHA-1, "
        "3DES, RC4, MD5</b>) that appear without post-quantum wrappers. Any unprotected legacy crypto in the "
        "analysis is surfaced as a risk vector.",
        styles['Body']))

    # ═══════════════════════════════════════════════════════════════
    # FIPS 203-206
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 10))
    story.append(dark_heading("FIPS 203-206 Integrity Anchor", styles, W))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "KORUM-OS already references NIST FIPS 203-206 standards across its analysis pipeline:",
        styles['Body']))

    fips = [
        ["STANDARD", "ALGORITHM", "PURPOSE"],
        ["FIPS 203", "ML-KEM (Kyber)", "Key encapsulation -- secure key exchange"],
        ["FIPS 204", "ML-DSA (Dilithium)", "Digital signatures -- general purpose"],
        ["FIPS 205", "SLH-DSA (SPHINCS+)", "Hash-based signatures -- conservative fallback"],
        ["FIPS 206 Draft", "FALCON (FN-DSA)", "Compact signatures -- Integrity Anchor for constrained links"],
    ]
    story.append(make_table(fips, [80, 130, 258], styles, hdr_bg="#0A1628", hdr_color="#00BFFF"))

    story.append(Spacer(1, 8))
    story.append(sub_heading("Why FALCON Matters", styles, W))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "ML-DSA signatures are approximately <b>2,420 bytes</b> -- larger than a standard network packet. On "
        "constrained-bandwidth links (satellites, remote sensors, legacy gateways with sub-1KB packet limits), "
        "this causes packet fragmentation, which creates a <b>denial-of-service risk</b>.",
        styles['Body']))
    story.append(Paragraph(
        "FALCON signatures are approximately <b>666 bytes</b> -- they fit inside existing packet limits without "
        "fragmentation. For constrained environments, FALCON is the <b>only quantum-resistant signature that works</b>.",
        styles['Body']))
    story.append(Paragraph(
        "KORUM-OS interrogation prompts automatically check for fragmentation risk. Exports auto-generate "
        "FIPS 203-206 compliance tables with signature size comparisons and integrity attestation.",
        styles['SmallNote']))

    # ═══════════════════════════════════════════════════════════════
    # PERSONAS & WORKFLOWS
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 10))
    story.append(dark_heading("62+ Expert Personas", styles, W))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Every AI can be assigned a specialized persona with deep system-level instructions. Key persona families:",
        styles['Body']))
    story.append(bullet("<b>Security & Crypto</b> -- Zero Trust, Cryptographer, Cyber Ops, SIGINT, Counterintel, Hacker", styles))
    story.append(bullet("<b>Defense & Intel</b> -- Defense Ops, Intel Analyst, Defense Acquisition", styles))
    story.append(bullet("<b>Strategy & Analysis</b> -- Strategist, Architect, Critic, Validator, Researcher", styles))
    story.append(bullet("<b>Business & Finance</b> -- CFO, Hedge Fund, Auditor, BizStrat, Product, Sales", styles))
    story.append(bullet("<b>Plus 40+ more</b> -- Science, Medical, Legal, Tech, Creative, Marketing, AI Architecture", styles))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Any persona can be assigned to any provider with one click, or let workflow presets auto-assign the optimal team.",
        styles['SmallNote']))

    story.append(Spacer(1, 10))
    story.append(dark_heading("14+ Workflow Presets", styles, W))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "One click configures the entire council -- preconfigured posture, tone, risk bias, and time horizon:",
        styles['Body']))
    wk = [
        ["CATEGORY", "WORKFLOWS"],
        ["Defense & Intel", "Defense Council - Cyber Command - Quantum Security - Intel Brief"],
        ["General", "War Room - Deep Research - Creative Council - Code Audit - System Core"],
        ["Domain", "Legal Review - Medical Council - Finance Desk - Science Panel - Tech Council"],
    ]
    story.append(make_table(wk, [120, 348], styles))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # ENTERPRISE READINESS
    # ═══════════════════════════════════════════════════════════════
    story.append(dark_heading("Enterprise Readiness", styles, W))
    story.append(Spacer(1, 8))

    ent = [
        ["CONTROL", "STATUS"],
        ["Authentication & Role-Based Access", "Implemented"],
        ["Full Audit Logging (every query, response, auth event)", "Implemented"],
        ["HTTPS/TLS + Security Headers (HSTS, CSP, XSS)", "Implemented"],
        ["Rate Limiting & Session Management", "Implemented"],
        ["Input Validation & Sanitization", "Implemented"],
        ["Air-Gapped Local Fallback", "Available"],
        ["FIPS-Validated Crypto (via Qanapi)", "Partnership"],
        ["Cryptographic Provenance (Armory Signatures)", "Integration Ready"],
        ["MFA / TOTP", "Infra Ready"],
        ["FedRAMP SSP Documentation", "Roadmap"],
    ]
    # Custom status coloring
    cs = ParagraphStyle('EC', parent=styles['Body'], fontSize=8.5, leading=11, wordWrap='CJK')
    hs = ParagraphStyle('EH', parent=cs, textColor=colors.HexColor(CYAN), fontName='Helvetica-Bold')
    gs = ParagraphStyle('EG', parent=cs, textColor=colors.HexColor("#00AA55"), fontName='Helvetica-Bold')
    os_ = ParagraphStyle('EO', parent=cs, textColor=colors.HexColor(GOLD), fontName='Helvetica-Bold')
    rows = []
    for i, row in enumerate(ent):
        if i == 0:
            rows.append([Paragraph(row[0], hs), Paragraph(row[1], hs)])
        else:
            status = row[1]
            if status == "Implemented":
                ss = gs
            elif status in ("Available", "Integration Ready", "Infra Ready"):
                ss = os_
            else:
                ss = cs
            rows.append([Paragraph(row[0], cs), Paragraph(status, ss)])
    et = Table(rows, colWidths=[340, 128], repeatRows=1)
    et.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(DARK)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
    ]))
    story.append(et)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>Architecture advantage:</b> KORUM-OS processes queries, not PII. No personal data enters the AI "
        "pipeline. Every event is logged and auditable -- aligning with the FedRAMP, CMMC, and SOC 2 frameworks "
        "Qanapi's customers already operate under.",
        styles['Body']))

    # ═══════════════════════════════════════════════════════════════
    # SECURITY & DATA FAQ
    # ═══════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(dark_heading("Security & Data Architecture FAQ", styles, W))
    story.append(Spacer(1, 8))

    # Q1
    story.append(Paragraph('<b>"Where does the data go?"</b>', styles['Body']))
    story.append(bullet("Queries are sent to cloud AI providers (OpenAI, Anthropic, Google, Perplexity, Mistral) "
        "via their official APIs over TLS 1.2+", styles))
    story.append(bullet("No data is stored by providers -- all 5 providers have enterprise data policies that "
        "prohibit training on API inputs", styles))
    story.append(bullet("KORUM-OS stores session data locally (SQLite) -- no cloud database, no third-party analytics", styles))
    story.append(bullet("The <b>Local LLM fallback</b> (LM Studio) runs 100% air-gapped -- zero data leaves the machine", styles))
    story.append(Spacer(1, 6))

    # Q2
    story.append(Paragraph('<b>"How are sessions secured?"</b>', styles['Body']))
    story.append(bullet("TLS-encrypted HTTPS connections for all API calls and user sessions", styles))
    story.append(bullet("Security headers enforced: HSTS, X-Frame-Options, X-Content-Type-Options, Content-Security-Policy", styles))
    story.append(bullet("Session management via signed cookies with configurable expiry", styles))
    story.append(bullet("Rate limiting: 30 requests/minute on interrogation and verification endpoints", styles))
    story.append(bullet("Input sanitization: 50K character limit with HTML entity stripping on all inputs", styles))
    story.append(bullet("<b>Qanapi integration opportunity:</b> AES-256 encrypted sessions via Qanapi SDK (architecture ready)", styles))
    story.append(Spacer(1, 6))

    # Q3
    story.append(Paragraph('<b>"Can it run on-prem or air-gapped?"</b>', styles['Body']))
    story.append(bullet("Yes. KORUM-OS includes a <b>Local LLM provider</b> via LM Studio that runs entirely on-premises", styles))
    story.append(bullet("The local provider serves as an automatic fallback if cloud APIs are unavailable", styles))
    story.append(bullet("In full air-gap mode, all 5 council seats can be filled by local models -- no internet required", styles))
    story.append(bullet("This maps directly to SCIF, classified, and regulated environments", styles))
    story.append(Spacer(1, 6))

    # Q4
    story.append(Paragraph('<b>"What gets logged and audited?"</b>', styles['Body']))
    story.append(bullet("<b>Every event</b> is logged: council queries, individual provider responses, interrogations, "
        "verifications, logins, failed logins, exports", styles))
    story.append(bullet("Audit log includes: timestamp, user ID, event type, provider, model used, query snippet", styles))
    story.append(bullet("Filterable by event type (Council Queries, Interrogations, Verifications, Auth Events)", styles))
    story.append(bullet("Provides chain-of-custody for intelligence products -- who asked what, when, and what the AI said", styles))
    story.append(bullet("Token usage, cost estimation, and spend alerts tracked per model per session", styles))
    story.append(Spacer(1, 6))

    # Q5
    story.append(Paragraph('<b>"What does the SIGN REPORT button do?"</b>', styles['Body']))
    story.append(bullet("Currently staged as an integration hook -- displays \"Cryptographic Signature Ready [STAGING]\"", styles))
    story.append(bullet("Designed for <b>Qanapi integration</b>: FN-DSA (FALCON) digital signature on exported reports", styles))
    story.append(bullet("Once connected to Qanapi's Armory, this button would cryptographically sign every intelligence "
        "product with a quantum-resistant signature", styles))
    story.append(bullet("Provides tamper-evident provenance -- anyone can verify the report hasn't been altered", styles))
    story.append(Spacer(1, 6))

    # Q6
    story.append(Paragraph('<b>"Does KORUM-OS process PII?"</b>', styles['Body']))
    story.append(bullet("<b>No.</b> KORUM-OS processes queries and generates analysis -- it does not ingest, store, "
        "or process personally identifiable information", styles))
    story.append(bullet("Users submit questions, not data files containing PII", styles))
    story.append(bullet("This dramatically simplifies compliance (GDPR, CCPA, HIPAA) -- the AI pipeline sees "
        "strategic questions, not personal records", styles))
    story.append(Spacer(1, 6))

    # Q7
    story.append(Paragraph('<b>"What happens if a provider goes down mid-council?"</b>', styles['Body']))
    story.append(bullet("Each provider has an automatic <b>fallback chain</b>: Primary -> Mistral Cloud -> Local LLM", styles))
    story.append(bullet("If OpenAI fails, the planner automatically routes to Mistral. If Mistral fails, it routes to Local", styles))
    story.append(bullet("The council continues with remaining providers -- partial results are still synthesized", styles))
    story.append(bullet("Provider health is monitored in real-time with color-coded status indicators (green/amber/red)", styles))
    story.append(Spacer(1, 6))

    # Q8
    story.append(Paragraph('<b>"How do you prevent hallucinations?"</b>', styles['Body']))
    story.append(bullet("5-phase sequential pipeline -- each AI builds on and corrects previous outputs", styles))
    story.append(bullet("Automated claim extraction + cross-provider verification (Accountability Pass)", styles))
    story.append(bullet("Analytic Divergence Layer identifies where models disagree -- disagreement is surfaced, not hidden", styles))
    story.append(bullet("User-triggered interrogation and verification provide human-in-the-loop validation", styles))
    story.append(bullet("Confidence calibration defaults to \"moderate-to-high\" -- never claims high confidence "
        "unless 3+ providers independently agree with evidence", styles))
    story.append(bullet("Red Team mode actively attacks the council's own conclusions before delivery", styles))

    # ═══════════════════════════════════════════════════════════════
    # THE PARTNERSHIP VALUE
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 10))
    story.append(dark_heading("The Partnership Value", styles, W))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "One platform encrypts and verifies the <b>data</b>. The other cross-verifies the <b>analysis</b>. "
        "Together: <b>end-to-end trusted intelligence</b> -- from source to decision.",
        styles['BodyBold']))
    story.append(Spacer(1, 6))

    pv = [
        ["QANAPI BRINGS", "KORUM-OS BRINGS"],
        ["Quantum-resistant encryption", "Multi-source AI analysis"],
        ["Zero Trust data protection", "Cross-verified truth scoring"],
        ["Cryptographic provenance", "Intelligence tagging & synthesis"],
        ["FIPS validation (203-206)", "FIPS compliance reporting"],
        ["Data-layer security", "Decision-layer security"],
        ["Trusted Data", "Trusted Decisions"],
    ]
    pvs = ParagraphStyle('PV', parent=styles['Body'], fontSize=9, leading=12, wordWrap='CJK', alignment=TA_CENTER)
    pvh = ParagraphStyle('PVH', parent=pvs, fontName='Helvetica-Bold')
    pvh_q = ParagraphStyle('PVQ', parent=pvh, textColor=colors.HexColor(CYAN))
    pvh_k = ParagraphStyle('PVK', parent=pvh, textColor=colors.HexColor(GREEN))
    pv_rows = []
    for i, row in enumerate(pv):
        if i == 0:
            pv_rows.append([Paragraph(row[0], pvh_q), Paragraph(row[1], pvh_k)])
        elif i == len(pv) - 1:
            # Last row bold
            pv_rows.append([Paragraph(f"<b>{row[0]}</b>", pvs), Paragraph(f"<b>{row[1]}</b>", pvs)])
        else:
            pv_rows.append([Paragraph(row[0], pvs), Paragraph(row[1], pvs)])
    pvt = Table(pv_rows, colWidths=[W/2]*2, repeatRows=1)
    pvt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor(DARK)),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor(DARK)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#F6F8FA")]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#0D1117")),
        ('TEXTCOLOR', (0, -1), (0, -1), colors.HexColor(CYAN)),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor(GREEN)),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(pvt)

    # ═══════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 30))
    # Tagline
    story.append(Paragraph("<b>Trusted Data.  Trusted Decisions.</b>",
        ParagraphStyle('FTag', parent=styles['Body'], fontSize=12, alignment=TA_CENTER,
                       textColor=colors.HexColor("#666666"), spaceAfter=8)))
    # Footer bar
    attest = Table([[
        "korum-os.com  |  Proprietary & Confidential"
    ]], colWidths=[W])
    attest.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#0080BF")),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(attest)

    doc.build(story)
    print(f"\nQanapi briefing package generated: {filepath}")
    return filepath


if __name__ == "__main__":
    generate()
