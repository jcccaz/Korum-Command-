# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

import csv
import io
import json
import os
import re
from datetime import datetime
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches, RGBColor
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from openpyxl import Workbook
from pptx import Presentation as PPTXPresentation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _output_path(filename: str, output_dir: str | None = None) -> str:
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, filename)
    return filename

# --- INTERNAL HELPERS ---

def _as_text(value):
    if value is None: return ""
    if isinstance(value, (dict, list)): return json.dumps(value, ensure_ascii=False)
    return str(value)

def _safe_filename_part(value, fallback="Intelligence"):
    text = _as_text(value).strip()
    if not text:
        text = fallback
    # Remove invalid Windows filename characters
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', '_', text)
    text = re.sub(r'\s+', ' ', text).strip().rstrip('. ')
    return text[:120] or fallback

def _clean_tags(text, strip_markdown=True):
    text = _as_text(text)
    # Strip KOS directive tags
    text = re.sub(r'\[\/?(?:DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]', '', text)
    if strip_markdown:
        # Simple markdown stripper for clean text output
        text = re.sub(r'#+\s', '', text)
        text = re.sub(r'\*\*', '', text)
        text = re.sub(r'__', '', text)
        text = re.sub(r'`', '', text)
    return text.strip()

def _extract_parts(o):
    """Deep extraction helper for Korum intelligence objects - robust legacy support."""
    if not o: return {}, {}, {}, [], []
    meta = o.get("meta", {}) or {}
    sections = o.get("sections", {}) or {}
    # Handle both new 'structured_data' and legacy 'structured' keys
    structured = o.get("structured_data") or o.get("structured") or {}
    interrogations = o.get("interrogations", [])
    verifications = o.get("verifications", [])
    return meta, sections, structured, interrogations, verifications

def _report_artifacts(o):
    """Extracts docked artifacts or snippets for exhibit rendering."""
    if not o: return []
    # Check 'docked_snippets' first (passed from JS ResearchDock)
    snippets = o.get("docked_snippets") or []
    if snippets:
        # Filter for includes if specifically flagged, else take all
        selected = [s for s in snippets if s.get("includeInReport")]
        return selected or snippets
    # Fallback to research_results or data_lake for legacy missions
    return o.get("research_results") or o.get("data_lake") or []

def _artifact_label(art):
    """Returns a clean display name for an artifact."""
    if not art: return "UNNAMED EXHIBIT"
    return (art.get("title") or art.get("label") or art.get("filename") or "UNNAMED EXHIBIT").upper()

def _convert_mermaid_to_table(text):
    """Placeholder for eventual Mermaid-to-Grid rendering."""
    # (Helper logic for Mermaid integration)
    return text

# --- AGENT ACCENT COLORS (fixed across all themes) ---
AGENT_COLORS = {
    'OPENAI': '#273C75',
    'ANTHROPIC': '#8B3A00',
    'GOOGLE': '#2A5C1A',
    'PERPLEXITY': '#4A2A8A',
    'MISTRAL': '#1A4A5C',
}

# Circled number glyphs for numbered prose lists
_CIRCLED_NUMS = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧']

def _dark_page_bg(canvas, doc):
    canvas.saveState()
    # Get current theme background from doc if available, else default
    bg_color = getattr(doc, '_bg_color', "#0D0D0D")
    canvas.setFillColor(colors.HexColor(bg_color))
    canvas.rect(0, 0, 612, 792, fill=True, stroke=False)
    canvas.restoreState()

def _sanitize_for_csv(value):
    text = _as_text(value)
    text = re.sub(r'\[\/?(?:DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]', '', text)
    if text and text[0] in ('=', '+', '-', '@'): text = "'" + text
    return text

class PDFExporter:
    """Executive-Grade Intelligence Dossier — Decision Intelligence Standard."""

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)

        # --- THEME PALETTES ---
        THEMES = {
            'NEON_DESERT': {"bg": "#0F172A", "accent": "#2DD4BF", "gold": "#FBBF24", "text": "#94A3B8", "dim": "#475569"},
            'CARBON_STEEL':{"bg": "#1A1A1A", "accent": "#D1D5DB", "gold": "#BC2F32", "text": "#D1D5DB", "dim": "#4B5563"},
            'ARCHITECT':   {"bg": "#2D3436", "accent": "#F2F1EF", "gold": "#A65E46", "text": "#F2F1EF", "dim": "#636E72"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES: theme_id = "NEON_DESERT"

        t = THEMES[theme_id]
        BG_PAGE, ACCENT, GOLD, TXT_MAIN, TXT_DIM = t['bg'], t['accent'], t['gold'], t['text'], t['dim']

        # --- SEMANTIC COLORS (fixed across all themes — layout spec) ---
        RACING_GREEN = "#1B4332"
        FORENSIC_RED = "#8B1A1A"
        MUTED_AMBER = "#C8922A"
        INKWELL = "#273C75"
        VERIFIED_BG = "#0D2818"
        FLAGGED_BG = "#2A0A0A"
        CONTEXTUAL_BG = "#0F1A3D"

        safe_title = _safe_filename_part(meta.get('title', 'Intelligence'))
        filename = f"KORUM-OS_DOSSIER_{safe_title}_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)

        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=35, bottomMargin=45, leftMargin=35, rightMargin=35)
        doc._bg_color = BG_PAGE

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('ExecTitle', parent=styles['Normal'], fontSize=38, textColor=colors.HexColor(ACCENT), leading=42, fontName='Helvetica-Bold', spaceAfter=20))
        styles.add(ParagraphStyle('ExecLabel', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor(GOLD), fontName='Helvetica-Bold', leading=10))
        styles.add(ParagraphStyle('ExecValue', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor(TXT_MAIN), fontName='Helvetica', leading=13))
        styles.add(ParagraphStyle('ExecBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor(TXT_MAIN), leading=16, fontName='Helvetica'))
        styles.add(ParagraphStyle('ExecAudit', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor(TXT_DIM), fontName='Courier-Bold'))
        styles.add(ParagraphStyle('ExecImpact', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor(TXT_MAIN), leading=20, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ExecSig', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor(ACCENT), alignment=2, fontName='Helvetica-Bold'))
        # Layout spec styles
        styles.add(ParagraphStyle('StatBig', parent=styles['Normal'], fontSize=26, textColor=colors.HexColor(ACCENT), fontName='Helvetica-Bold', alignment=1, leading=30))
        styles.add(ParagraphStyle('StatCaption', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor(TXT_DIM), fontName='Helvetica-Bold', alignment=1, leading=9))
        styles.add(ParagraphStyle('PullQuote', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor(TXT_MAIN), fontName='Helvetica-Oblique', leading=14))
        styles.add(ParagraphStyle('ProviderBadge', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor(TXT_MAIN), fontName='Helvetica-Bold', leading=10))
        styles.add(ParagraphStyle('ConsensusBody', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor(TXT_MAIN), fontName='Helvetica-Oblique', leading=16, alignment=1))

        story = []

        # --- Extract reusable data early ---
        card_results = intelligence_object.get("_card_results") or {}
        contributors = intelligence_object.get("council_contributors") or []
        confidence = intelligence_object.get("confidence_and_assumptions") or {}
        divergence = intelligence_object.get("divergence_analysis") or {}

        # Mission context: client name, industry, etc.
        mission_ctx = intelligence_object.get("_mission_context") or {}
        client_name = _as_text(mission_ctx.get("client", "")).strip() or "DECISION COMMANDER ALPHA"

        # Build contributor attribution map: section index → provider info
        contrib_map = {}
        for c in contributors:
            phase_str = _as_text(c.get('phase', ''))
            m = re.search(r'(\d+)', phase_str)
            if m:
                contrib_map[int(m.group(1)) - 1] = c

        # 1. --- CONFIDENTIAL BANNER + LOGO ---
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo light.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo.png")

        conf_banner = Table([[Paragraph(f"<font color='{GOLD}'>CONFIDENTIAL</font> &mdash; PROPRIETARY INTELLIGENCE PRODUCT", styles['ExecAudit'])]], colWidths=[540])
        conf_banner.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BOTTOMPADDING', (0,0), (-1,-1), 12)]))
        story.append(conf_banner)

        header_tab_data = []
        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=160, height=40)
            header_tab_data = [[img, Paragraph("INTELLIGENCE DOSSIER", styles['ExecSig'])]]
        else:
            header_tab_data = [[Paragraph("KORUM-OS", styles['ExecTitle']), Paragraph("INTELLIGENCE DOSSIER", styles['ExecSig'])]]

        h_table = Table(header_tab_data, colWidths=[270, 270])
        h_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        story.append(h_table)
        story.append(Spacer(1, 25))

        # 2. --- DOSSIER IDENTIFIER & CONTEXT ---
        story.append(Paragraph(f"{escape(meta.get('title', 'Node_Command').upper())}", styles['ExecTitle']))

        ctx_data = [
            [Paragraph("PREPARED FOR:", styles['ExecLabel']), Paragraph(escape(client_name.upper()), styles['ExecValue'])],
            [Paragraph("MISSION DIRECTIVE:", styles['ExecLabel']), Paragraph(escape(meta.get('workflow', 'STRATEGIC_INTEL').upper()), styles['ExecValue'])],
            [Paragraph("AUTHENTICATION:", styles['ExecLabel']), Paragraph("KORUM-OS DECISION INTELLIGENCE", styles['ExecValue'])]
        ]
        ctx_table = Table(ctx_data, colWidths=[150, 390])
        ctx_table.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 8), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(ctx_table)
        story.append(Spacer(1, 15))

        story.append(Table([[""]], colWidths=[540], rowHeights=[1], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(GOLD))]))
        story.append(Spacer(1, 25))

        # 3. --- STRATEGIC IMPACT SUMMARY (mixed case, bold first sentence) ---
        original_query = meta.get("summary") or "Intel synthesis required."
        story.append(Paragraph("STRATEGIC IMPACT SUMMARY", styles['ExecLabel']))
        story.append(Spacer(1, 10))
        # Split on first sentence boundary — bold the lead finding, regular weight for rest
        _dot = original_query.find('. ')
        if _dot > 0:
            lead_sentence = escape(original_query[:_dot + 1])
            rest_text = escape(original_query[_dot + 2:])
            story.append(Paragraph(f"<b>{lead_sentence}</b> {rest_text}", styles['ExecImpact']))
        else:
            story.append(Paragraph(f"<b>{escape(original_query)}</b>", styles['ExecImpact']))
        story.append(Spacer(1, 30))

        # 4. --- THREE-STAT STRIP (top KPIs as big inline numbers) ---
        key_metrics = structured.get("key_metrics") or []
        if len(key_metrics) >= 2:
            stat_count = min(3, len(key_metrics))
            stat_cells = []
            stat_widths = [540 // stat_count] * stat_count
            for km in key_metrics[:stat_count]:
                val = _as_text(km.get('value', '—'))
                label = _as_text(km.get('metric', '')).upper()
                stat_cells.append(Paragraph(
                    f"<font color='{ACCENT}' size='26'><b>{escape(val)}</b></font><br/>"
                    f"<font color='{TXT_DIM}' size='7'>{escape(label)}</font>",
                    styles['StatBig']))
            stat_strip = Table([stat_cells], colWidths=stat_widths)
            stat_strip.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 12),
                ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ]))
            story.append(stat_strip)
            story.append(Spacer(1, 8))
            # Thin rule under stat strip
            story.append(Table([["", "", ""]], colWidths=[170, 200, 170], rowHeights=[0.5],
                style=[('BACKGROUND', (1,0), (1,0), colors.HexColor(TXT_DIM)),
                       ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                       ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))
            story.append(Spacer(1, 25))

        # 5. --- INTELLIGENCE SECTIONS (Prose Flow w/ Inline Agent Attribution) ---
        section_items = list(sections.items())
        for idx, (sid, content) in enumerate(section_items):
            sec_title = sid.replace("_", " ").upper()

            # Agent attribution: "NODE 04 — ANTHROPIC · Auditor"
            attrib = contrib_map.get(idx)
            if attrib:
                prov_name = _as_text(attrib.get('provider', '')).upper()
                role_name = _as_text(attrib.get('role', ''))
                node_id = f"NODE {idx+1:02d} &mdash; {escape(prov_name)} &middot; {escape(role_name)}"
            else:
                node_id = f"NODE {idx+1:02d}"

            # Agent accent color for this section
            agent_color = AGENT_COLORS.get(prov_name, GOLD) if attrib else GOLD

            # --- Text Processing (Escaping + Dynamic Highlighting) ---
            raw_text = _as_text(content)
            tag_placeholders = {}
            for tag in ["CRITICAL", "ACTION REQUIRED", "VERIFIED", "RISK"]:
                ph = f"___SG_{tag.replace(' ', '_')}___"
                if f"[{tag}]" in raw_text:
                    raw_text = raw_text.replace(f"[{tag}]", ph).replace(f"[/{tag}]", "")
                    tag_placeholders[ph] = f"<font color='{FORENSIC_RED}' size='11'><b>[{tag}]</b></font>" if tag == "CRITICAL" else f"<font color='{GOLD}'><b>[{tag}]</b></font>"

            bold_spans = []
            for m_match in re.finditer(r'\*\*(.*?)\*\*', raw_text):
                bold_spans.append((m_match.group(0), f"___B_{len(bold_spans)}___"))
            for orig, ph in bold_spans: raw_text = raw_text.replace(orig, ph, 1)

            styled = escape(raw_text)
            for ph, st in tag_placeholders.items(): styled = styled.replace(ph, st)
            for orig, ph in bold_spans: styled = styled.replace(ph, f"<b>{escape(orig[2:-2])}</b>")
            styled = styled.replace("\n", "<br/>")

            # --- LAYOUT: Lead section gets accent bar, all others flow as prose ---
            if idx == 0:
                # LEAD ASSESSMENT — accent left bar, full-width, prominent
                lead_content = Paragraph(f"<font color='{GOLD}' size='11'><b>{sec_title}</b></font><br/><font color='{TXT_DIM}' size='7'>{node_id}</font><br/><br/>{styled}", styles['ExecBody'])
                lead_row = Table([["", lead_content]], colWidths=[5, 530])
                lead_row.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (0,0), colors.HexColor(agent_color)),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LEFTPADDING', (1,0), (1,0), 18),
                    ('TOPPADDING', (0,0), (-1,-1), 12),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 18),
                ]))
                story.append(lead_row)
            else:
                # PROSE FLOW — section label + thin rule + flowing content
                story.append(Paragraph(f"<font color='{GOLD}'><b>{sec_title}</b></font> &nbsp;<font color='{TXT_DIM}' size='7'>{node_id}</font>", styles['ExecBody']))
                story.append(Spacer(1, 4))
                # Thin rule under section label (agent-colored)
                rule = Table([[""]], colWidths=[540], rowHeights=[0.5])
                rule.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor(agent_color)),
                    ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))
                story.append(rule)
                story.append(Spacer(1, 6))
                story.append(Paragraph(styled, styles['ExecBody']))

            # --- INLINE PULL QUOTES (from verified_claims matching this provider) ---
            if attrib:
                prov_key = _as_text(attrib.get('provider', '')).lower()
                prov_data = card_results.get(prov_key) or {}
                claims = prov_data.get("verified_claims") or []
                # Show up to 2 pull quotes per section
                for claim in claims[:2]:
                    claim_text = _as_text(claim.get('claim', ''))
                    if not claim_text:
                        continue
                    status = _as_text(claim.get('status', '')).lower()
                    if status == 'verified':
                        pq_border = RACING_GREEN
                        pq_bg = VERIFIED_BG
                        pq_badge = f"<font color='{RACING_GREEN}'><b>VERIFIED</b></font>"
                    elif status in ('challenged', 'unverified'):
                        pq_border = FORENSIC_RED
                        pq_bg = FLAGGED_BG
                        pq_badge = f"<font color='{FORENSIC_RED}'><b>FLAGGED</b></font>"
                    else:
                        pq_border = MUTED_AMBER
                        pq_bg = CONTEXTUAL_BG
                        pq_badge = f"<font color='{MUTED_AMBER}'><b>CONDITIONAL</b></font>"

                    conf_val = claim.get('confidence', '')
                    conf_str = f" &nbsp;&middot;&nbsp; <font size='7' color='{TXT_DIM}'>CONFIDENCE: {escape(_as_text(conf_val))}</font>" if conf_val else ""
                    # Attribution line: — PROVIDER · Role · Phase
                    phase_label = _as_text(attrib.get('phase', ''))
                    attrib_line = f"<br/><font face='Courier' size='7' color='{TXT_DIM}'>&mdash; {escape(prov_name)} &middot; {escape(role_name)} &middot; {escape(phase_label)}</font>"
                    pq_content = Paragraph(
                        f"{pq_badge}{conf_str}<br/>"
                        f"<i>&ldquo;{escape(claim_text)}&rdquo;</i>"
                        f"{attrib_line}",
                        styles['PullQuote'])
                    pq_row = Table([["", pq_content]], colWidths=[4, 520])
                    pq_row.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (0,0), colors.HexColor(pq_border)),
                        ('BACKGROUND', (1,0), (1,0), colors.HexColor(pq_bg)),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LEFTPADDING', (1,0), (1,0), 12),
                        ('TOPPADDING', (0,0), (-1,-1), 8),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                        ('RIGHTPADDING', (1,0), (1,0), 12),
                    ]))
                    story.append(Spacer(1, 6))
                    story.append(pq_row)

            # --- SECTION DIVIDERS (varied rhythm) ---
            if idx < len(section_items) - 1:
                story.append(Spacer(1, 12))
                if idx % 2 == 0:
                    div_row = Table([["", "", ""]], colWidths=[170, 200, 170], rowHeights=[0.5])
                    div_row.setStyle(TableStyle([
                        ('BACKGROUND', (1,0), (1,0), colors.HexColor(TXT_DIM)),
                        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ]))
                    story.append(div_row)
                else:
                    story.append(Paragraph(f"<font color='{TXT_DIM}' size='6'>&bull; &bull; &bull;</font>", ParagraphStyle('DivDots', parent=styles['Normal'], alignment=1, spaceAfter=0)))
                story.append(Spacer(1, 14))

        # 6. --- TRUTH SCORE (computed here, rendered at bottom as anchor bar) ---
        truth_raw = meta.get("composite_truth_score", 0)
        try:
            truth_int = int(float(truth_raw) * 100) if float(truth_raw) <= 1 else int(float(truth_raw))
        except (ValueError, TypeError):
            truth_int = 0
        truth_color = '#4CAF7D' if truth_int > 80 else (GOLD if truth_int > 50 else '#FF3131')

        # --- AGENT TESTIMONY & VERIFICATION ZONE ---
        if card_results:
            story.append(Spacer(1, 10))
            tv_break = Table([["", Paragraph(f"<font color='{ACCENT}' size='8'><b>AGENT TESTIMONY &amp; VERIFICATION</b></font>", styles['ExecBody']), ""]], colWidths=[80, 380, 80], rowHeights=[18])
            tv_break.setStyle(TableStyle([
                ('LINEABOVE', (0,0), (0,0), 0.5, colors.HexColor(TXT_DIM)),
                ('LINEABOVE', (2,0), (2,0), 0.5, colors.HexColor(TXT_DIM)),
                ('ALIGN', (1,0), (1,0), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(tv_break)
            story.append(Spacer(1, 15))

            # Per-provider testimony cards
            for prov_name, prov_data in card_results.items():
                if not isinstance(prov_data, dict):
                    continue
                model_name = _as_text(prov_data.get('model', 'unknown'))
                role = _as_text(prov_data.get('role', 'ANALYST'))
                truth_meter = prov_data.get('truth_meter', {})
                prov_score = 0
                if isinstance(truth_meter, dict):
                    prov_score = truth_meter.get('score', 0)
                    try: prov_score = int(float(prov_score))
                    except (ValueError, TypeError): prov_score = 0

                # Provider badge bar
                score_color = '#4CAF7D' if prov_score > 80 else (MUTED_AMBER if prov_score > 50 else FORENSIC_RED)
                badge_left = Paragraph(
                    f"<font color='{ACCENT}' size='9'><b>{escape(prov_name.upper())}</b></font>"
                    f" &nbsp;<font color='{TXT_DIM}' size='7'>{escape(model_name)} &middot; {escape(role)}</font>",
                    styles['ProviderBadge'])
                badge_right = Paragraph(
                    f"<font color='{score_color}' size='14'><b>{prov_score}</b></font>"
                    f"<font color='{TXT_DIM}' size='7'>/100</font>",
                    ParagraphStyle('BadgeScore', parent=styles['Normal'], alignment=2, fontSize=9, textColor=colors.HexColor(TXT_MAIN)))
                badge_row = Table([[badge_left, badge_right]], colWidths=[400, 135])
                badge_row.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(TXT_DIM)),
                ]))
                story.append(badge_row)

                # Pull quotes from this provider's verified claims
                claims = prov_data.get("verified_claims") or []
                for claim in claims[:4]:
                    claim_text = _as_text(claim.get('claim', ''))
                    if not claim_text:
                        continue
                    status = _as_text(claim.get('status', '')).lower()
                    if status == 'verified':
                        pq_border, pq_bg = RACING_GREEN, VERIFIED_BG
                        badge_txt = f"<font color='{RACING_GREEN}'><b>VERIFIED</b></font>"
                    elif status in ('challenged', 'unverified'):
                        pq_border, pq_bg = FORENSIC_RED, FLAGGED_BG
                        badge_txt = f"<font color='{FORENSIC_RED}'><b>FLAGGED</b></font>"
                    else:
                        pq_border, pq_bg = MUTED_AMBER, CONTEXTUAL_BG
                        badge_txt = f"<font color='{MUTED_AMBER}'><b>CONDITIONAL</b></font>"

                    violations = claim.get('violations') or []
                    viol_str = ""
                    if violations:
                        viol_str = f"<br/><font color='{FORENSIC_RED}' size='7'>FLAG: {escape(', '.join(_as_text(v) for v in violations[:2]))}</font>"

                    pq_content = Paragraph(
                        f"{badge_txt}"
                        f"<br/><i>&ldquo;{escape(claim_text)}&rdquo;</i>"
                        f"{viol_str}",
                        styles['PullQuote'])
                    pq_row = Table([["", pq_content]], colWidths=[4, 531])
                    pq_row.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (0,0), colors.HexColor(pq_border)),
                        ('BACKGROUND', (1,0), (1,0), colors.HexColor(pq_bg)),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LEFTPADDING', (1,0), (1,0), 12),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('RIGHTPADDING', (1,0), (1,0), 12),
                    ]))
                    story.append(pq_row)
                    story.append(Spacer(1, 3))

                story.append(Spacer(1, 14))

            # --- COUNCIL CONSENSUS BAR ---
            if truth_int > 0:
                consensus_summary = _as_text(divergence.get("divergence_summary", "")) or "Multi-model analysis complete. Council has reached operational consensus."
                cons_content = Paragraph(
                    f"<font color='{ACCENT}' size='9'><b>COUNCIL CONSENSUS</b></font> &nbsp;"
                    f"<font color='{truth_color}' size='16'><b>{truth_int}</b></font>"
                    f"<font color='{TXT_DIM}' size='8'>/100 TRUTH SCORE</font><br/><br/>"
                    f"<i>{escape(consensus_summary)}</i>",
                    styles['ConsensusBody'])
                cons_bar = Table([[cons_content]], colWidths=[535])
                cons_bar.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0A0A0A")),
                    ('TOPPADDING', (0,0), (-1,-1), 14),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 14),
                    ('LEFTPADDING', (0,0), (-1,-1), 20),
                    ('RIGHTPADDING', (0,0), (-1,-1), 20),
                    ('ROUNDEDCORNERS', [4, 4, 4, 4]),
                ]))
                story.append(cons_bar)
                story.append(Spacer(1, 25))

        # --- OPERATIONAL DATA ZONE BREAK ---
        risks = structured.get("risks") or []
        has_data = (key_metrics or risks or structured.get("action_items") or structured.get("actions"))
        if has_data:
            story.append(Spacer(1, 15))
            zone_break = Table([["", Paragraph(f"<font color='{ACCENT}' size='8'><b>OPERATIONAL DATA</b></font>", styles['ExecBody']), ""]], colWidths=[80, 380, 80], rowHeights=[18])
            zone_break.setStyle(TableStyle([
                ('LINEABOVE', (0,0), (0,0), 0.5, colors.HexColor(TXT_DIM)),
                ('LINEABOVE', (2,0), (2,0), 0.5, colors.HexColor(TXT_DIM)),
                ('ALIGN', (1,0), (1,0), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(zone_break)
            story.append(Spacer(1, 20))

        # 7. --- KEY METRICS TABLE (remaining metrics after stat strip) ---
        remaining_metrics = key_metrics[3:] if len(key_metrics) > 3 else (key_metrics if len(key_metrics) < 2 else [])
        if remaining_metrics:
            story.append(Paragraph(f"<font color='{GOLD}'><b>KEY INTELLIGENCE METRICS</b></font>", styles['ExecBody']))
            story.append(Spacer(1, 8))
            m_header = [[Paragraph("METRIC", styles['ExecLabel']), Paragraph("VALUE", styles['ExecLabel']), Paragraph("CONTEXT", styles['ExecLabel'])]]
            m_rows = [[Paragraph(escape(_as_text(m.get('metric',''))), styles['ExecBody']),
                        Paragraph(f"<b>{escape(_as_text(m.get('value','')))}</b>", styles['ExecBody']),
                        Paragraph(escape(_as_text(m.get('context',''))), styles['ExecBody'])]
                       for m in remaining_metrics[:12]]
            m_table = Table(m_header + m_rows, colWidths=[160, 120, 260])
            m_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(TXT_DIM)),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor(GOLD)),
            ]))
            story.append(m_table)
            story.append(Spacer(1, 25))

        # 8. --- RISK MATRIX (severity-dependent rendering) ---
        if risks:
            risk_hdr = Table([["", Paragraph(f"<font color='{GOLD}'><b>RISK MATRIX</b></font>", styles['ExecBody'])]], colWidths=[5, 535])
            risk_hdr.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), colors.HexColor(GOLD)), ('LEFTPADDING', (1,0), (1,0), 12), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(risk_hdr)
            story.append(Spacer(1, 8))

            # Split risks by severity: CRITICAL/HIGH → flagged pull quotes, rest → slim table
            high_risks = []
            other_risks = []
            for r in risks[:8]:
                sev = _as_text(r.get('severity', 'MEDIUM')).upper()
                if sev in ('CRITICAL', 'HIGH'):
                    high_risks.append(r)
                else:
                    other_risks.append(r)

            # CRITICAL/HIGH risks as flagged pull quotes
            for r in high_risks:
                risk_text = _as_text(r.get('risk', ''))
                mitigation = _as_text(r.get('mitigation', ''))
                sev = _as_text(r.get('severity', '')).upper()
                pq_content = Paragraph(
                    f"<font color='{FORENSIC_RED}'><b>{escape(sev)}</b></font><br/>"
                    f"<i>&ldquo;{escape(risk_text)}&rdquo;</i><br/>"
                    f"<font size='8' color='{TXT_DIM}'>MITIGATION: {escape(mitigation)}</font>",
                    styles['PullQuote'])
                pq_row = Table([["", pq_content]], colWidths=[4, 531])
                pq_row.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (0,0), colors.HexColor(FORENSIC_RED)),
                    ('BACKGROUND', (1,0), (1,0), colors.HexColor(FLAGGED_BG)),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LEFTPADDING', (1,0), (1,0), 12),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (1,0), (1,0), 12),
                ]))
                story.append(pq_row)
                story.append(Spacer(1, 4))

            # MEDIUM/LOW risks as slim 2-column table (Risk · Mitigation only)
            if other_risks:
                if high_risks:
                    story.append(Spacer(1, 6))
                r_header = [[Paragraph("RISK", styles['ExecLabel']), Paragraph("MITIGATION", styles['ExecLabel'])]]
                r_rows = [[Paragraph(escape(_as_text(r.get('risk',''))), styles['ExecBody']),
                            Paragraph(escape(_as_text(r.get('mitigation',''))), styles['ExecBody'])]
                           for r in other_risks]
                r_table = Table(r_header + r_rows, colWidths=[260, 280])
                r_table.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor(GOLD)),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                ]))
                story.append(r_table)
            story.append(Spacer(1, 25))

        # 9. --- RECOMMENDED ACTIONS (numbered prose, not table) ---
        actions = structured.get("action_items") or structured.get("actions") or []
        if actions:
            story.append(Paragraph(f"<font color='{GOLD}'><b>RECOMMENDED ACTIONS</b></font>", styles['ExecBody']))
            story.append(Spacer(1, 8))
            for ai, a in enumerate(actions[:8]):
                action_text = _as_text(a.get('task', a.get('action', '')))
                pri = _as_text(a.get('priority', '')).upper()
                pri_color = FORENSIC_RED if pri == 'HIGH' else (MUTED_AMBER if pri in ('MED', 'MEDIUM') else ACCENT)
                glyph = _CIRCLED_NUMS[ai] if ai < len(_CIRCLED_NUMS) else f"{ai+1}."
                story.append(Paragraph(
                    f"<font size='12'>{glyph}</font> &nbsp;{escape(action_text)}"
                    f" &nbsp;<font color='{pri_color}' size='8'><b>{escape(pri)}</b></font>",
                    styles['ExecBody']))
                story.append(Spacer(1, 4))
            story.append(Spacer(1, 25))

        # --- COUNCIL INTELLIGENCE ZONE BREAK ---
        if contributors or confidence or divergence:
            story.append(Spacer(1, 10))
            ci_break = Table([["", Paragraph(f"<font color='{ACCENT}' size='8'><b>COUNCIL INTELLIGENCE</b></font>", styles['ExecBody']), ""]], colWidths=[80, 380, 80], rowHeights=[18])
            ci_break.setStyle(TableStyle([
                ('LINEABOVE', (0,0), (0,0), 0.5, colors.HexColor(TXT_DIM)),
                ('LINEABOVE', (2,0), (2,0), 0.5, colors.HexColor(TXT_DIM)),
                ('ALIGN', (1,0), (1,0), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(ci_break)
            story.append(Spacer(1, 20))

        # 10. --- COUNCIL CONTRIBUTORS (slim horizontal strip — Name · Role · Status) ---
        if contributors:
            story.append(Paragraph(f"<font color='{GOLD}'><b>COUNCIL CONTRIBUTORS</b></font>", styles['ExecBody']))
            story.append(Spacer(1, 10))
            # Build slim cells — up to 4 per row
            slim_cells = []
            for c in contributors[:8]:
                prov = _as_text(c.get('provider', '')).upper()
                role = _as_text(c.get('role', ''))
                # Determine status stamp from truth score
                prov_lower = _as_text(c.get('provider', '')).lower()
                prov_cr = card_results.get(prov_lower) or {}
                prov_tm = prov_cr.get('truth_meter', {})
                prov_sc = 0
                if isinstance(prov_tm, dict):
                    try: prov_sc = int(float(prov_tm.get('score', 0)))
                    except (ValueError, TypeError): prov_sc = 0
                elif isinstance(prov_tm, (int, float)):
                    prov_sc = int(prov_tm)
                # Status stamp: ✓ Verified (>80), ◎ Conditional (50-80), ⚑ Flagged (<50)
                if prov_sc > 80:
                    stamp = f"<font color='{RACING_GREEN}'>&#x2713; Verified</font>"
                elif prov_sc > 50:
                    stamp = f"<font color='{MUTED_AMBER}'>&#x25CE; Conditional</font>"
                else:
                    stamp = f"<font color='{FORENSIC_RED}'>&#x2691; Flagged</font>"
                agent_accent = AGENT_COLORS.get(prov, ACCENT)
                cell_content = Paragraph(
                    f"<font color='{ACCENT}' size='9'><b>{escape(prov)}</b></font><br/>"
                    f"<font color='{TXT_DIM}' size='7'>{escape(role)}</font><br/>"
                    f"<font size='7'>{stamp}</font>",
                    styles['ProviderBadge'])
                slim_cells.append((cell_content, agent_accent))
            # Arrange in rows of 4
            col_w = 540 // min(4, len(slim_cells)) if slim_cells else 135
            for row_start in range(0, len(slim_cells), 4):
                row_slice = slim_cells[row_start:row_start + 4]
                row_data = [sc[0] for sc in row_slice]
                # Pad to 4 columns if needed
                while len(row_data) < 4 and len(slim_cells) >= 4:
                    row_data.append("")
                widths = [col_w] * len(row_data)
                strip = Table([row_data], colWidths=widths)
                strip_style = [
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 4),
                ]
                # Left accent border per agent color
                for ci, (_, accent_c) in enumerate(row_slice):
                    strip_style.append(('LINEBEFORE', (ci,0), (ci,0), 2, colors.HexColor(accent_c)))
                strip.setStyle(TableStyle(strip_style))
                story.append(strip)
                story.append(Spacer(1, 4))
            story.append(Spacer(1, 20))

        # 11. --- CONFIDENCE ASSESSMENT (accent-bar callout) ---
        if confidence:
            conf_level = _as_text(confidence.get('overall_confidence', '')).upper()
            conf_color = '#4CAF7D' if 'HIGH' in conf_level else (MUTED_AMBER if 'MODERATE' in conf_level else FORENSIC_RED)
            conf_parts = [f"<font color='{GOLD}' size='10'><b>CONFIDENCE ASSESSMENT</b></font><br/><br/>"]
            conf_parts.append(f"OVERALL CONFIDENCE: <font color='{conf_color}'><b>{escape(conf_level)}</b></font><br/><br/>")
            assumptions = confidence.get('key_assumptions') or []
            if assumptions:
                conf_parts.append(f"<font color='{GOLD}' size='8'><b>KEY ASSUMPTIONS</b></font><br/>")
                for assumption in assumptions[:5]:
                    conf_parts.append(f"&bull; {escape(_as_text(assumption))}<br/>")
                conf_parts.append("<br/>")
            limitations = confidence.get('limitations') or []
            if limitations:
                conf_parts.append(f"<font color='{GOLD}' size='8'><b>LIMITATIONS</b></font><br/>")
                for lim in limitations[:4]:
                    conf_parts.append(f"&bull; {escape(_as_text(lim))}<br/>")
            conf_block = Paragraph("".join(conf_parts), styles['ExecBody'])
            conf_row = Table([["", conf_block]], colWidths=[4, 531])
            conf_row.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,0), colors.HexColor(conf_color)),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (1,0), (1,0), 16),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 14),
            ]))
            story.append(conf_row)
            story.append(Spacer(1, 25))

        # 12. --- DIVERGENCE ANALYSIS ---
        if divergence and (divergence.get("divergence_score") or divergence.get("contested_topics")):
            story.append(Paragraph(f"<font color='{ACCENT}'><b>DIVERGENCE ANALYSIS</b></font>", styles['ExecBody']))
            story.append(Spacer(1, 8))
            div_score = divergence.get("divergence_score", 0)
            con_score = divergence.get("consensus_score", 0)
            try:
                div_score = int(float(div_score))
                con_score = int(float(con_score))
            except (ValueError, TypeError):
                div_score, con_score = 0, 0
            if div_score or con_score:
                con_color = '#4CAF7D' if con_score > 70 else (MUTED_AMBER if con_score > 40 else FORENSIC_RED)
                div_color = FORENSIC_RED if div_score > 60 else (MUTED_AMBER if div_score > 30 else '#4CAF7D')
                stat_data = [[Paragraph(f"<font color='{con_color}' size='18'><b>{con_score}</b></font><br/><font color='{TXT_DIM}' size='7'>CONSENSUS</font>", ParagraphStyle('StatCenter', parent=styles['Normal'], alignment=1, textColor=colors.HexColor(TXT_MAIN))),
                              Paragraph(f"<font color='{div_color}' size='18'><b>{div_score}</b></font><br/><font color='{TXT_DIM}' size='7'>DIVERGENCE</font>", ParagraphStyle('StatCenter2', parent=styles['Normal'], alignment=1, textColor=colors.HexColor(TXT_MAIN)))]]
                stat_tab = Table(stat_data, colWidths=[270, 270])
                stat_tab.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
                story.append(stat_tab)
            div_summary = divergence.get("divergence_summary")
            if div_summary:
                story.append(Paragraph(escape(_as_text(div_summary)), styles['ExecBody']))
                story.append(Spacer(1, 8))
            contested = divergence.get("contested_topics") or []
            if contested:
                story.append(Paragraph(f"<font color='{GOLD}' size='8'><b>CONTESTED TOPICS</b></font>", styles['ExecBody']))
                for topic in contested[:4]:
                    topic_name = topic.get("topic", topic) if isinstance(topic, dict) else _as_text(topic)
                    story.append(Paragraph(f"&bull; <b>{escape(_as_text(topic_name))}</b>", styles['ExecBody']))
            story.append(Spacer(1, 25))

        # 13. --- SUPPLEMENTAL DATA EXHIBITS ---
        artifacts = _report_artifacts(intelligence_object)
        if artifacts:
            story.append(Table([[Paragraph("SUPPLEMENTAL DATA EXHIBITS", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 15))
            for art in artifacts:
                row = [[Paragraph(f"EXHIBIT: {escape(_artifact_label(art).upper())}", styles['ExecLabel']), Paragraph(escape(_as_text(art.get("content", ""))).replace("\n", "<br/>"), styles['ExecBody'])]]
                at_tab = Table(row, colWidths=[160, 380])
                at_tab.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 20)]))
                story.append(at_tab)

        # 14. --- COMPOSITE TRUTH SCORE ANCHOR BAR ---
        if truth_int > 0:
            consensus_text = _as_text(divergence.get("divergence_summary", "")) or "Multi-model analysis complete. Council has reached operational consensus."
            truth_left = Paragraph(f"<i>{escape(consensus_text)}</i>", styles['ConsensusBody'])
            truth_right = Paragraph(
                f"<font color='{truth_color}' size='28'><b>{truth_int}</b></font><br/>"
                f"<font color='{TXT_DIM}' size='8'>TRUTH SCORE / 100</font>",
                ParagraphStyle('TruthRight', parent=styles['Normal'], alignment=2, fontSize=9, textColor=colors.HexColor(TXT_MAIN)))
            truth_bar = Table([[truth_left, truth_right]], colWidths=[380, 155])
            truth_bar.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(INKWELL)),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 16),
                ('BOTTOMPADDING', (0,0), (-1,-1), 16),
                ('LEFTPADDING', (0,0), (0,0), 20),
                ('RIGHTPADDING', (1,0), (1,0), 20),
            ]))
            story.append(Spacer(1, 20))
            story.append(truth_bar)

        # 15. --- SIGN-OFF & AUTHENTICATION ---
        story.append(Spacer(1, 30))
        story.append(Table([[""]], colWidths=[540], rowHeights=[1], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(GOLD))]))
        story.append(Spacer(1, 20))

        signoff_data = [
            [Paragraph("COMPLETED BY:", styles['ExecLabel']), Paragraph("KORUM-OS DECISION INTELLIGENCE ENGINE", styles['ExecValue'])],
            [Paragraph("AUTHORIZATION:", styles['ExecLabel']), Paragraph(f"AUTONOMOUS COUNCIL &mdash; {len(contributors)} CONTRIBUTING AGENTS", styles['ExecValue'])],
            [Paragraph("CLASSIFICATION:", styles['ExecLabel']), Paragraph(f"<font color='{GOLD}'><b>CONFIDENTIAL</b></font> &mdash; PROPRIETARY INTELLIGENCE PRODUCT", styles['ExecValue'])],
            [Paragraph("TIMESTAMP:", styles['ExecLabel']), Paragraph(datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'), styles['ExecValue'])],
        ]
        signoff = Table(signoff_data, colWidths=[150, 390])
        signoff.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(signoff)

        story.append(Spacer(1, 30))
        story.append(Paragraph(f"<font color='{TXT_DIM}'>This document was generated by Korum-OS and contains proprietary analysis. Distribution is restricted to authorized recipients only.</font>", styles['ExecAudit']))

        doc.build(story, onFirstPage=_dark_page_bg, onLaterPages=_dark_page_bg)
        return filepath
class WordExporter:
    """Executive-Grade Word Report — Decision Intelligence Standard."""
    
    @staticmethod
    def _hex_to_rgb(hex_str):
        if hex_str.startswith('#'): hex_str = hex_str[1:]
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        doc = Document()
        
        # --- THE WOW PALETTE ---
        THEMES = {
            'NEON_DESERT': {"accent": "2DD4BF", "gold": "FBBF24"},
            'CARBON_STEEL':{"accent": "D1D5DB", "gold": "BC2F32"},
            'ARCHITECT':   {"accent": "F2F1EF", "gold": "A65E46"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        p_rgb = RGBColor(*WordExporter._hex_to_rgb(t['gold']))
        s_rgb = RGBColor(*WordExporter._hex_to_rgb(t['accent']))

        # Mission context: client name for PREPARED FOR line
        mission_ctx = intelligence_object.get("_mission_context") or {}
        client_name = _as_text(mission_ctx.get("client", "")).strip() or "DECISION COMMANDER ALPHA"

        # 1. --- CONFIDENTIAL BANNER + LOGO ---
        conf_p = doc.add_paragraph()
        conf_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        conf_run = conf_p.add_run("CONFIDENTIAL — PROPRIETARY INTELLIGENCE PRODUCT")
        conf_run.font.size = Pt(7)
        conf_run.font.color.rgb = p_rgb
        conf_run.font.name = 'Courier New'

        # All themes dark — use light logo
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo light.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo.png")

        h_tab = doc.add_table(rows=1, cols=2)
        h_tab.columns[0].width = Inches(3.0)
        h_tab.columns[1].width = Inches(3.0)

        if os.path.exists(logo_path):
            l_cell_p = h_tab.rows[0].cells[0].paragraphs[0]
            l_cell_p.add_run().add_picture(logo_path, width=Inches(1.8))
        else:
            h_tab.rows[0].cells[0].text = "KORUM-OS"

        r_p = h_tab.rows[0].cells[1].paragraphs[0]
        r_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_run = r_p.add_run("INTELLIGENCE DOSSIER")
        r_run.bold = True
        r_run.font.color.rgb = s_rgb
        doc.add_paragraph()

        # 2. --- EXECUTIVE CONTEXT ---
        t_p = doc.add_paragraph()
        t_run = t_p.add_run(meta.get('title', 'COMMAND_NODE').upper())
        t_run.bold = True
        t_run.font.size = Pt(24)
        t_run.font.color.rgb = s_rgb

        ctx_tab = doc.add_table(rows=3, cols=2)
        ctx_tab.columns[0].width = Inches(1.8)
        ctx_tab.columns[1].width = Inches(4.2)

        labels = [("PREPARED FOR:", client_name.upper()),
                  ("MISSION DIRECTIVE:", meta.get('workflow', 'STRATEGIC_INTEL').upper()),
                  ("AUTHENTICATION:", "KORUM-OS DECISION INTELLIGENCE")]

        for i, (lab, val) in enumerate(labels):
            l_cell = ctx_tab.rows[i].cells[0]
            l_p = l_cell.paragraphs[0]
            l_run = l_p.add_run(lab)
            l_run.bold = True
            l_run.font.size = Pt(9)
            l_run.font.color.rgb = p_rgb

            v_cell = ctx_tab.rows[i].cells[1]
            v_p = v_cell.paragraphs[0]
            v_run = v_p.add_run(val)
            v_run.font.size = Pt(10)

        doc.add_paragraph("_" * 90)

        # 3. --- STRATEGIC IMPACT (mixed case, bold first sentence) ---
        sum_p = doc.add_paragraph("STRATEGIC IMPACT SUMMARY")
        sum_p.runs[0].bold = True
        sum_p.runs[0].font.size = Pt(9)
        sum_p.runs[0].font.color.rgb = p_rgb

        impact_text = meta.get("summary") or "Intel synthesis required."
        imp_p = doc.add_paragraph()
        _dot = impact_text.find('. ')
        if _dot > 0:
            lead_run = imp_p.add_run(impact_text[:_dot + 1])
            lead_run.bold = True
            lead_run.font.size = Pt(12)
            rest_run = imp_p.add_run(" " + impact_text[_dot + 2:])
            rest_run.font.size = Pt(12)
        else:
            lead_run = imp_p.add_run(impact_text)
            lead_run.bold = True
            lead_run.font.size = Pt(12)
        doc.add_paragraph()

        # --- Extract reusable data early ---
        card_results = intelligence_object.get("_card_results") or {}
        contributors = intelligence_object.get("council_contributors") or []
        confidence = intelligence_object.get("confidence_and_assumptions") or {}
        divergence = intelligence_object.get("divergence_analysis") or {}
        key_metrics = structured.get("key_metrics") or []
        risks = structured.get("risks") or []

        # Build contributor attribution map: section index → provider info
        contrib_map = {}
        for c in contributors:
            phase_str = _as_text(c.get('phase', ''))
            m_match = re.search(r'(\d+)', phase_str)
            if m_match:
                contrib_map[int(m_match.group(1)) - 1] = c

        # 4. --- THREE-STAT KPI STRIP ---
        if len(key_metrics) >= 2:
            stat_count = min(3, len(key_metrics))
            stat_tab = doc.add_table(rows=2, cols=stat_count)
            stat_tab.autofit = False
            col_w = Inches(6.0 / stat_count)
            for ci in range(stat_count):
                stat_tab.columns[ci].width = col_w
                km = key_metrics[ci]
                val = _as_text(km.get('value', '—'))
                label = _as_text(km.get('metric', '')).upper()
                # Value row
                v_cell = stat_tab.rows[0].cells[ci]
                v_p = v_cell.paragraphs[0]
                v_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                v_run = v_p.add_run(val)
                v_run.bold = True
                v_run.font.size = Pt(20)
                v_run.font.color.rgb = s_rgb
                # Label row
                l_cell = stat_tab.rows[1].cells[ci]
                l_p = l_cell.paragraphs[0]
                l_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                l_run = l_p.add_run(label)
                l_run.font.size = Pt(7)
                l_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
                l_run.bold = True
            doc.add_paragraph()

        # 5. --- INTELLIGENCE SECTIONS (Varied Layout w/ Agent Attribution) ---
        section_items = list(sections.items())
        for idx, (sid, content) in enumerate(section_items):
            sec_title = sid.replace("_", " ").upper()
            clean_text = _clean_tags(content, strip_markdown=True)

            # Agent attribution: "NODE 04 — ANTHROPIC · Auditor"
            attrib = contrib_map.get(idx)
            if attrib:
                prov_name = _as_text(attrib.get('provider', '')).upper()
                role_name = _as_text(attrib.get('role', ''))
                node_label = f"NODE {idx+1:02d} — {prov_name} · {role_name}"
            else:
                node_label = f"NODE {idx+1:02d}"

            # Consistent prose flow — section label + body, no boxes/grids
            hdr_p = doc.add_paragraph()
            hdr_run = hdr_p.add_run(sec_title)
            hdr_run.bold = True
            hdr_run.font.size = Pt(11) if idx == 0 else Pt(10)
            hdr_run.font.color.rgb = p_rgb
            n_run = hdr_p.add_run(f"  {node_label}")
            n_run.font.size = Pt(7)
            n_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            body_p = doc.add_paragraph(clean_text)
            if body_p.runs:
                body_p.runs[0].font.size = Pt(10)

            # Consistent thin divider between sections
            if idx < len(section_items) - 1:
                doc.add_paragraph()

        # 5. --- TRUTH SCORE (computed here, rendered at bottom as anchor bar) ---
        truth_raw = meta.get("composite_truth_score", 0)
        try:
            truth_int = int(float(truth_raw) * 100) if float(truth_raw) <= 1 else int(float(truth_raw))
        except (ValueError, TypeError):
            truth_int = 0

        # 6. --- KEY METRICS TABLE ---
        key_metrics = structured.get("key_metrics") or []
        if key_metrics:
            h_p = doc.add_paragraph("KEY INTELLIGENCE METRICS")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)
            m_tab = doc.add_table(rows=1 + len(key_metrics[:12]), cols=3)
            m_tab.style = 'Table Grid'
            m_tab.autofit = False
            m_tab.columns[0].width = Inches(2.0)
            m_tab.columns[1].width = Inches(1.5)
            m_tab.columns[2].width = Inches(2.5)
            for i, lbl in enumerate(["METRIC", "VALUE", "CONTEXT"]):
                cell = m_tab.rows[0].cells[i]
                cell.text = lbl
                cell.paragraphs[0].runs[0].bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(8)
                cell.paragraphs[0].runs[0].font.color.rgb = p_rgb
            for ri, m in enumerate(key_metrics[:12]):
                m_tab.rows[ri+1].cells[0].text = _as_text(m.get('metric', ''))
                m_tab.rows[ri+1].cells[1].text = _as_text(m.get('value', ''))
                m_tab.rows[ri+1].cells[2].text = _as_text(m.get('context', ''))
            doc.add_paragraph()

        # 7. --- RISK MATRIX (severity-dependent rendering) ---
        risks = structured.get("risks") or []
        if risks:
            h_p = doc.add_paragraph("RISK MATRIX")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)

            high_risks = []
            other_risks = []
            for r in risks[:8]:
                sev = _as_text(r.get('severity', 'MEDIUM')).upper()
                if sev in ('CRITICAL', 'HIGH'):
                    high_risks.append(r)
                else:
                    other_risks.append(r)

            # CRITICAL/HIGH as flagged paragraphs
            for r in high_risks:
                sev = _as_text(r.get('severity', '')).upper()
                rp = doc.add_paragraph()
                sev_run = rp.add_run(f"[{sev}] ")
                sev_run.bold = True
                sev_run.font.size = Pt(9)
                sev_run.font.color.rgb = RGBColor(0x8B, 0x1A, 0x1A)
                risk_run = rp.add_run(_as_text(r.get('risk', '')))
                risk_run.font.size = Pt(10)
                risk_run.italic = True
                mit = _as_text(r.get('mitigation', ''))
                if mit:
                    mit_run = rp.add_run(f"  —  Mitigation: {mit}")
                    mit_run.font.size = Pt(9)
                    mit_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
                rp.paragraph_format.left_indent = Inches(0.2)

            # MEDIUM/LOW as slim 2-column table (Risk · Mitigation only)
            if other_risks:
                r_tab = doc.add_table(rows=1 + len(other_risks), cols=2)
                r_tab.style = 'Table Grid'
                r_tab.autofit = False
                r_tab.columns[0].width = Inches(3.0)
                r_tab.columns[1].width = Inches(3.0)
                for i, lbl in enumerate(["RISK", "MITIGATION"]):
                    cell = r_tab.rows[0].cells[i]
                    cell.text = lbl
                    cell.paragraphs[0].runs[0].bold = True
                    cell.paragraphs[0].runs[0].font.size = Pt(8)
                    cell.paragraphs[0].runs[0].font.color.rgb = p_rgb
                for ri, r in enumerate(other_risks):
                    r_tab.rows[ri+1].cells[0].text = _as_text(r.get('risk', ''))
                    r_tab.rows[ri+1].cells[1].text = _as_text(r.get('mitigation', ''))
            doc.add_paragraph()

        # 8. --- RECOMMENDED ACTIONS (numbered prose, not table) ---
        actions = structured.get("action_items") or structured.get("actions") or []
        if actions:
            h_p = doc.add_paragraph("RECOMMENDED ACTIONS")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)
            for ai, a in enumerate(actions[:8]):
                action_text = _as_text(a.get('task', a.get('action', '')))
                pri = _as_text(a.get('priority', '')).upper()
                glyph = _CIRCLED_NUMS[ai] if ai < len(_CIRCLED_NUMS) else f"{ai+1}."
                ap = doc.add_paragraph()
                g_run = ap.add_run(f"{glyph} ")
                g_run.font.size = Pt(11)
                a_run = ap.add_run(action_text)
                a_run.font.size = Pt(10)
                if pri:
                    pri_run = ap.add_run(f"  ({pri})")
                    pri_run.bold = True
                    pri_run.font.size = Pt(8)
                    if pri == 'HIGH':
                        pri_run.font.color.rgb = RGBColor(0x8B, 0x1A, 0x1A)
                    elif pri in ('MED', 'MEDIUM'):
                        pri_run.font.color.rgb = RGBColor(0xC8, 0x92, 0x2A)
            doc.add_paragraph()

        # 9. --- COUNCIL CONTRIBUTORS (slim horizontal strip — Name · Role · Status) ---
        contributors = intelligence_object.get("council_contributors") or []
        if contributors:
            h_p = doc.add_paragraph("COUNCIL CONTRIBUTORS")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)
            # Slim strip: up to 4 per row
            for row_start in range(0, len(contributors[:8]), 4):
                row_slice = contributors[row_start:row_start + 4]
                c_tab = doc.add_table(rows=1, cols=len(row_slice))
                c_tab.autofit = False
                col_w = Inches(6.0 / len(row_slice))
                for ci, c in enumerate(row_slice):
                    c_tab.columns[ci].width = col_w
                    prov = _as_text(c.get('provider', '')).upper()
                    role = _as_text(c.get('role', ''))
                    # Status stamp from truth score
                    prov_lower = _as_text(c.get('provider', '')).lower()
                    prov_cr = card_results.get(prov_lower) or {}
                    prov_tm = prov_cr.get('truth_meter', {})
                    prov_sc = 0
                    if isinstance(prov_tm, dict):
                        try: prov_sc = int(float(prov_tm.get('score', 0)))
                        except (ValueError, TypeError): prov_sc = 0
                    elif isinstance(prov_tm, (int, float)):
                        prov_sc = int(prov_tm)
                    if prov_sc > 80:
                        stamp = "Verified"
                    elif prov_sc > 50:
                        stamp = "Conditional"
                    else:
                        stamp = "Flagged"
                    cell = c_tab.rows[0].cells[ci]
                    cp = cell.paragraphs[0]
                    prov_run = cp.add_run(prov)
                    prov_run.bold = True
                    prov_run.font.size = Pt(9)
                    prov_run.font.color.rgb = s_rgb
                    cp.add_run("\n")
                    role_run = cp.add_run(f"{role} · {stamp}")
                    role_run.font.size = Pt(7)
                    role_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            doc.add_paragraph()

        # 10. --- CONFIDENCE ASSESSMENT ---
        confidence = intelligence_object.get("confidence_and_assumptions") or {}
        if confidence:
            h_p = doc.add_paragraph("CONFIDENCE ASSESSMENT")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)
            conf_level = _as_text(confidence.get('overall_confidence', '')).upper()
            c_p = doc.add_paragraph()
            c_run = c_p.add_run(f"OVERALL CONFIDENCE: {conf_level}")
            c_run.bold = True
            c_run.font.size = Pt(10)
            assumptions = confidence.get('key_assumptions') or []
            if assumptions:
                a_p = doc.add_paragraph("KEY ASSUMPTIONS:")
                a_p.runs[0].bold = True
                a_p.runs[0].font.size = Pt(9)
                a_p.runs[0].font.color.rgb = p_rgb
                for assumption in assumptions[:5]:
                    doc.add_paragraph(_as_text(assumption), style='List Bullet')
            limitations = confidence.get('limitations') or []
            if limitations:
                l_p = doc.add_paragraph("LIMITATIONS:")
                l_p.runs[0].bold = True
                l_p.runs[0].font.size = Pt(9)
                l_p.runs[0].font.color.rgb = p_rgb
                for lim in limitations[:4]:
                    doc.add_paragraph(_as_text(lim), style='List Bullet')
            doc.add_paragraph()

        # 11. --- COMPOSITE TRUTH SCORE ANCHOR BAR ---
        if truth_int > 0:
            consensus_text = _as_text(divergence.get("divergence_summary", "")) or "Multi-model analysis complete. Council has reached operational consensus."
            ts_tab = doc.add_table(rows=1, cols=2)
            ts_tab.autofit = False
            ts_tab.columns[0].width = Inches(4.2)
            ts_tab.columns[1].width = Inches(1.8)
            # Left: consensus sentence (italic)
            l_cell = ts_tab.rows[0].cells[0]
            l_p = l_cell.paragraphs[0]
            l_run = l_p.add_run(consensus_text)
            l_run.italic = True
            l_run.font.size = Pt(10)
            # Right: large truth score numeral
            r_cell = ts_tab.rows[0].cells[1]
            r_p = r_cell.paragraphs[0]
            r_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            score_run = r_p.add_run(str(truth_int))
            score_run.bold = True
            score_run.font.size = Pt(24)
            score_run.font.color.rgb = s_rgb
            label_run = r_p.add_run("\nTRUTH SCORE / 100")
            label_run.font.size = Pt(7)
            label_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            # Apply Inkwell Blue background via XML shading
            for cell in ts_tab.rows[0].cells:
                shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="273C75"/>')
                cell._tc.get_or_add_tcPr().append(shading)
            doc.add_paragraph()

        # 12. --- SIGN-OFF & AUTHENTICATION ---
        doc.add_paragraph("_" * 90)

        contributors = intelligence_object.get("council_contributors") or []
        signoff_tab = doc.add_table(rows=4, cols=2)
        signoff_tab.columns[0].width = Inches(1.8)
        signoff_tab.columns[1].width = Inches(4.2)

        signoff_labels = [
            ("COMPLETED BY:", "KORUM-OS DECISION INTELLIGENCE ENGINE"),
            ("AUTHORIZATION:", f"AUTONOMOUS COUNCIL — {len(contributors)} CONTRIBUTING AGENTS"),
            ("CLASSIFICATION:", "CONFIDENTIAL — PROPRIETARY INTELLIGENCE PRODUCT"),
            ("TIMESTAMP:", datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')),
        ]
        for i, (lab, val) in enumerate(signoff_labels):
            l_cell = signoff_tab.rows[i].cells[0]
            l_p = l_cell.paragraphs[0]
            l_run = l_p.add_run(lab)
            l_run.bold = True
            l_run.font.size = Pt(9)
            l_run.font.color.rgb = p_rgb
            v_cell = signoff_tab.rows[i].cells[1]
            v_p = v_cell.paragraphs[0]
            v_run = v_p.add_run(val)
            v_run.font.size = Pt(10)

        doc.add_paragraph()
        disc_p = doc.add_paragraph()
        disc_run = disc_p.add_run("This document was generated by Korum-OS and contains proprietary analysis. Distribution is restricted to authorized recipients only.")
        disc_run.font.size = Pt(7)
        disc_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        disc_run.font.name = 'Courier New'

        # Footer
        section = doc.sections[0]
        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        f_run = p.add_run(f"CONFIDENTIAL // Korum-OS Decision Intelligence // {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        f_run.font.name = 'Courier New'
        f_run.font.size = Pt(7)
        f_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        safe_title = _safe_filename_part(meta.get('title', 'Intelligence'))
        filename = f"KORUM-OS_REPORT_{safe_title}_{theme_id}_{_timestamp()}.docx"
        filepath = _output_path(filename, output_dir)
        doc.save(filepath)
        return filepath

class MarkdownExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, _, _, _ = _extract_parts(intelligence_object)
        md = [
            f"# KORUM-OS // {meta.get('title', 'Intelligence Report').upper()}",
            f"**STATUS:** VERIFIED | **TIMESTAMP:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "\n---\n"
        ]
        
        # Primary Directive
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        if directive_list:
            md.append(f"> ### [PRIMARY DIRECTIVE]\n> **{_as_text(directive_list[0]).upper()}**\n")
            md.append("\n---\n")

        for sid, content in sections.items():
            md.append(f"## {sid.replace('_', ' ').upper()}")
            md.append(content)
            md.append("\n---\n")

        # Artifacts
        artifacts = _report_artifacts(intelligence_object)
        if artifacts:
            md.append("## SUPPLEMENTARY EXHIBITS")
            for art in artifacts:
                md.append(f"### EXHIBIT: {_artifact_label(art).upper()}")
                md.append(art.get("content", ""))
                md.append("\n")

        filename = f"KORUM-OS_{_timestamp()}.md"
        filepath = _output_path(filename, output_dir)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(md))
        return filepath

class JSONExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        filename = f"KORUM-OS_INTEL_{_timestamp()}.json"
        filepath = _output_path(filename, output_dir)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(intelligence_object, f, indent=4, ensure_ascii=False)
        return filepath

class CSVExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, _, structured, _, _ = _extract_parts(intelligence_object)
        filename = f"KORUM-OS_DATA_{_timestamp()}.csv"
        filepath = _output_path(filename, output_dir)
        
        # Flatten key metrics and artifacts into CSV
        metrics = structured.get("key_metrics", [])
        artifacts = _report_artifacts(intelligence_object)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["IDENTIFIER", "CATEGORY", "VALUE / CONTENT", "SOURCE"])
            
            for m in metrics:
                writer.writerow([m.get("metric"), "METRIC", m.get("value"), m.get("context")])
            
            for art in artifacts:
                writer.writerow([_artifact_label(art), "ARTIFACT", art.get("preview", art.get("content", ""))[:200], art.get("source")])
                
        return filepath

class TextExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, _, _, _ = _extract_parts(intelligence_object)
        lines = [
            f"KORUM-OS // {meta.get('title', 'INTELLIGENCE BRIEF').upper()}",
            "=" * 60,
            f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"WORKFLOW: {meta.get('workflow', 'RESEARCH')}",
            "-" * 60,
            "\n"
        ]
        
        for sid, content in sections.items():
            lines.append(f"[{sid.replace('_', ' ').upper()}]")
            lines.append(_clean_tags(content, strip_markdown=True))
            lines.append("\n")
            
        filename = f"KORUM-OS_{_timestamp()}.txt"
        filepath = _output_path(filename, output_dir)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        return filepath

class ExcelExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, _, structured, _, _ = _extract_parts(intelligence_object)
        wb = Workbook()
        ws = wb.active
        ws.title = "Intelligence Dashboard"
        
        # Header Styling would go here, but using basic sheet for efficiency
        ws['A1'] = "KORUM-OS INTELLIGENCE LEDGER"
        ws['A2'] = f"Mission: {meta.get('title', 'N/A')}"
        ws['A3'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        ws.append([]) # Spacer
        ws.append(["METRIC", "VALUE", "CONTEXT"])
        for m in structured.get("key_metrics", []):
            ws.append([m.get("metric"), m.get("value"), m.get("context")])
            
        # Artifacts Sheet
        ws2 = wb.create_sheet(title="Exhibits")
        ws2.append(["LABEL", "TYPE", "CONTENT PREVIEW"])
        for art in _report_artifacts(intelligence_object):
            ws2.append([_artifact_label(art), art.get("type"), art.get("preview", "")])

        filename = f"KORUM-OS_LEDGER_{_timestamp()}.xlsx"
        filepath = _output_path(filename, output_dir)
        wb.save(filepath)
        return filepath

class PPTXExporter:
    """Strategy Presentation following Command Alpha layout standards."""
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, _, _ = _extract_parts(intelligence_object)
        prs = PPTXPresentation()
        
        # Title Slide
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = meta.get("title", "INTELLIGENCE BRIEF").upper()
        subtitle.text = f"KORUM-OS COMMAND NODE // {meta.get('workflow', 'RESEARCH')} // {datetime.now().strftime('%Y-%m-%d')}"
        
        # Directive Slide
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        if directive_list:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = "[PRIMARY DIRECTIVE]"
            body = slide.shapes.placeholders[1]
            body.text = _as_text(directive_list[0]).upper()

        # Section Slides
        for sid, content in sections.items():
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = sid.replace("_", " ").upper()
            body = slide.shapes.placeholders[1]
            # Strip tags for PPT cleanup
            body.text = _clean_tags(content, strip_markdown=True)[:500] + ("..." if len(content) > 500 else "")

        # Artifacts Slides
        for art in _report_artifacts(intelligence_object)[:5]: # Limit to 5 for brevity
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = f"EXHIBIT: {_artifact_label(art).upper()}"
            body = slide.shapes.placeholders[1]
            body.text = art.get("content", "")[:600]

        filename = f"KORUM-OS_STRATEGY_{_timestamp()}.pptx"
        filepath = _output_path(filename, output_dir)
        prs.save(filepath)
        return filepath

class ResearchPaperExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        return PDFExporter.generate(intelligence_object, output_dir=output_dir)

class ResearchPaperWordExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        return WordExporter.generate(intelligence_object, output_dir=output_dir)


# --- END OF EXPORTERS ---

