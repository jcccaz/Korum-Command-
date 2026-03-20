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
        
        # --- THE WOW PALETTE ---
        THEMES = {
            'NEON_DESERT': {"bg": "#090C10", "accent": "#00F5FF", "gold": "#FFD700", "text": "#E2E8F0", "dim": "#475569"},
            'CARBON_STEEL':{"bg": "#0D0D0D", "accent": "#FFFFFF", "gold": "#94A3B8", "text": "#FAFAFA", "dim": "#525252"},
            'ARCHITECT':   {"bg": "#FBF9F4", "accent": "#1A1A1A", "gold": "#8B4513", "text": "#2C2C2C", "dim": "#71717A"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        BG_PAGE, ACCENT, GOLD, TXT_MAIN, TXT_DIM = t['bg'], t['accent'], t['gold'], t['text'], t['dim']

        safe_title = _safe_filename_part(meta.get('title', 'Intelligence'))
        filename = f"KORUM-OS_DOSSIER_{safe_title}_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)
        
        # Tight margins for a modern edge-to-edge feel
        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=35, bottomMargin=45, leftMargin=35, rightMargin=35)
        doc._bg_color = BG_PAGE
        
        styles = getSampleStyleSheet()
        # Premium Custom Styles (Unique IDs to avoid collisions)
        styles.add(ParagraphStyle('ExecTitle', parent=styles['Normal'], fontSize=38, textColor=colors.HexColor(ACCENT), leading=42, fontName='Helvetica-Bold', spaceAfter=20))
        styles.add(ParagraphStyle('ExecLabel', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor(GOLD), fontName='Helvetica-Bold', leading=10))
        styles.add(ParagraphStyle('ExecValue', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor(TXT_MAIN), fontName='Helvetica', leading=13))
        styles.add(ParagraphStyle('ExecBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor(TXT_MAIN), leading=16, fontName='Helvetica'))
        styles.add(ParagraphStyle('ExecAudit', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor(TXT_DIM), fontName='Courier-Bold'))
        styles.add(ParagraphStyle('ExecImpact', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor(TXT_MAIN), leading=20, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ExecSig', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor(ACCENT), alignment=2, fontName='Helvetica-Bold'))

        story = []

        # 1. --- LOGO & STRATEGIC BRANDING ---
        logo_filename = "main korum os logo light.png" if theme_id != "ARCHITECT" else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo.png")

        header_tab_data = []
        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=160, height=40)
            header_tab_data = [[img, Paragraph("INTELLIGENCE DOSSIER", styles['ExecSig'])]]
        else:
            header_tab_data = [[Paragraph("KORUM-OS", styles['ExecTitle']), Paragraph("INTELLIGENCE DOSSIER", styles['ExecSig'])]]
        
        h_table = Table(header_tab_data, colWidths=[270, 270])
        h_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        story.append(h_table)
        story.append(Spacer(1, 30))

        # 2. --- DOSSIER IDENTIFIER & CONTEXT ---
        story.append(Paragraph(f"{escape(meta.get('title', 'Node_Command').upper())}", styles['ExecTitle']))
        
        # Metadata Asymmetry
        ctx_data = [
            [Paragraph("PREPARED FOR:", styles['ExecLabel']), Paragraph("DECISION COMMANDER ALPHA", styles['ExecValue'])],
            [Paragraph("MISSION DIRECTIVE:", styles['ExecLabel']), Paragraph(escape(meta.get('workflow', 'STRATEGIC_INTEL').upper()), styles['ExecValue'])],
            [Paragraph("AUTHENTICATION:", styles['ExecLabel']), Paragraph("KORUM-OS DECISION INTELLIGENCE", styles['ExecValue'])]
        ]
        ctx_table = Table(ctx_data, colWidths=[150, 390])
        ctx_table.setStyle(TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 8), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(ctx_table)
        story.append(Spacer(1, 15))
        
        # The Deck Rule
        story.append(Table([[""]], colWidths=[540], rowHeights=[1], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(GOLD))]))
        story.append(Spacer(1, 25))

        # 3. --- ORIGINAL DIRECTIVE BLOCK (The "Why") ---
        original_query = meta.get("summary") or "INTEL SYNTHESIS REQUIRED"
        story.append(Paragraph("STRATEGIC IMPACT SUMMARY", styles['ExecLabel']))
        story.append(Spacer(1, 10))
        story.append(Paragraph(escape(original_query).upper(), styles['ExecImpact']))
        story.append(Spacer(1, 40))

        # 4. --- INTELLIGENCE GRID (Asymmetric Dossier) ---
        for idx, (sid, content) in enumerate(sections.items()):
            sec_title = sid.replace("_", " ").upper()
            node_id = f"[DECISION_NODE_{idx+1:02d}]"
            
            # Text Processing (Escaping + Dynamic Highlighting)
            raw_text = _as_text(content)
            tag_placeholders = {}
            for tag in ["CRITICAL", "ACTION REQUIRED", "VERIFIED", "RISK"]:
                ph = f"___SG_{tag.replace(' ', '_')}___"
                if f"[{tag}]" in raw_text:
                    raw_text = raw_text.replace(f"[{tag}]", ph).replace(f"[/{tag}]", "")
                    tag_placeholders[ph] = f"<font color='#FF3131' size='11'><b>[{tag}]</b></font>" if tag == "CRITICAL" else f"<font color='{GOLD}'><b>[{tag}]</b></font>"

            bold_spans = []
            for m in re.finditer(r'\*\*(.*?)\*\*', raw_text):
                bold_spans.append((m.group(0), f"___B_{len(bold_spans)}___"))
            for orig, ph in bold_spans: raw_text = raw_text.replace(orig, ph, 1)

            styled = escape(raw_text)
            for ph, st in tag_placeholders.items(): styled = styled.replace(ph, st)
            for orig, ph in bold_spans: styled = styled.replace(ph, f"<b>{escape(orig[2:-2])}</b>")
            styled = styled.replace("\n", "<br/>")

            # Row Table (Left: Metadata, Right: Content)
            row_data = [[Paragraph(f"{sec_title}<br/><font color='{GOLD}'>{node_id}</font>", styles['ExecLabel']), Paragraph(styled, styles['ExecBody'])]]
            t_row = Table(row_data, colWidths=[160, 380])
            t_row.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 25)]))
            story.append(t_row)

        # 5. --- TRUTH SCORE BAR ---
        truth_raw = meta.get("composite_truth_score", 0)
        try:
            truth_int = int(float(truth_raw) * 100) if float(truth_raw) <= 1 else int(float(truth_raw))
        except (ValueError, TypeError):
            truth_int = 0
        if truth_int > 0:
            truth_color = '#4CAF7D' if truth_int > 80 else (GOLD if truth_int > 50 else '#FF3131')
            bar_fill = max(int(540 * truth_int / 100), 1)
            bar_empty = 540 - bar_fill
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"COMPOSITE TRUTH SCORE: {truth_int}/100", styles['ExecLabel']))
            story.append(Spacer(1, 5))
            bar_data = [["", ""]]
            bar = Table(bar_data, colWidths=[bar_fill, bar_empty], rowHeights=[8])
            bar.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,0), colors.HexColor(truth_color)),
                ('BACKGROUND', (1,0), (1,0), colors.HexColor("#1A1A1A")),
                ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(bar)
            story.append(Spacer(1, 25))

        # 6. --- KEY METRICS TABLE ---
        key_metrics = structured.get("key_metrics") or []
        if key_metrics:
            story.append(Table([[Paragraph("KEY INTELLIGENCE METRICS", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 10))
            m_header = [[Paragraph("METRIC", styles['ExecLabel']), Paragraph("VALUE", styles['ExecLabel']), Paragraph("CONTEXT", styles['ExecLabel'])]]
            m_rows = [[Paragraph(escape(_as_text(m.get('metric',''))), styles['ExecBody']),
                        Paragraph(f"<b>{escape(_as_text(m.get('value','')))}</b>", styles['ExecBody']),
                        Paragraph(escape(_as_text(m.get('context',''))), styles['ExecBody'])]
                       for m in key_metrics[:12]]
            m_table = Table(m_header + m_rows, colWidths=[160, 120, 260])
            m_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor(GOLD)),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(m_table)
            story.append(Spacer(1, 25))

        # 7. --- RISK MATRIX ---
        risks = structured.get("risks") or []
        if risks:
            story.append(Table([[Paragraph("RISK MATRIX", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 10))
            r_header = [[Paragraph("RISK", styles['ExecLabel']), Paragraph("SEVERITY", styles['ExecLabel']), Paragraph("MITIGATION", styles['ExecLabel'])]]
            r_rows = []
            for r in risks[:8]:
                sev = _as_text(r.get('severity', 'MEDIUM')).upper()
                sev_color = '#FF3131' if sev in ('CRITICAL', 'HIGH') else (GOLD if sev == 'MEDIUM' else ACCENT)
                r_rows.append([
                    Paragraph(escape(_as_text(r.get('risk',''))), styles['ExecBody']),
                    Paragraph(f"<font color='{sev_color}'><b>{escape(sev)}</b></font>", styles['ExecBody']),
                    Paragraph(escape(_as_text(r.get('mitigation',''))), styles['ExecBody']),
                ])
            r_table = Table(r_header + r_rows, colWidths=[200, 80, 260])
            r_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor(GOLD)),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(r_table)
            story.append(Spacer(1, 25))

        # 8. --- RECOMMENDED ACTIONS ---
        actions = structured.get("action_items") or structured.get("actions") or []
        if actions:
            story.append(Table([[Paragraph("RECOMMENDED ACTIONS", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 10))
            a_header = [[Paragraph("ACTION", styles['ExecLabel']), Paragraph("PRIORITY", styles['ExecLabel']), Paragraph("TIMELINE", styles['ExecLabel'])]]
            a_rows = []
            for a in actions[:8]:
                pri = _as_text(a.get('priority', '')).upper()
                pri_color = '#FF3131' if pri == 'HIGH' else (GOLD if pri in ('MED', 'MEDIUM') else ACCENT)
                a_rows.append([
                    Paragraph(escape(_as_text(a.get('task', a.get('action', '')))), styles['ExecBody']),
                    Paragraph(f"<font color='{pri_color}'><b>{escape(pri)}</b></font>", styles['ExecBody']),
                    Paragraph(escape(_as_text(a.get('timeline', ''))), styles['ExecBody']),
                ])
            a_table = Table(a_header + a_rows, colWidths=[260, 80, 200])
            a_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor(GOLD)),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(a_table)
            story.append(Spacer(1, 25))

        # 9. --- COUNCIL CONTRIBUTORS ---
        contributors = intelligence_object.get("council_contributors") or []
        if contributors:
            story.append(Table([[Paragraph("COUNCIL CONTRIBUTORS", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 10))
            c_header = [[Paragraph("PHASE", styles['ExecLabel']), Paragraph("PROVIDER", styles['ExecLabel']), Paragraph("ROLE", styles['ExecLabel']), Paragraph("CONTRIBUTION", styles['ExecLabel'])]]
            c_rows = [[Paragraph(escape(_as_text(c.get('phase',''))), styles['ExecBody']),
                        Paragraph(escape(_as_text(c.get('provider','')).upper()), styles['ExecBody']),
                        Paragraph(escape(_as_text(c.get('role',''))), styles['ExecBody']),
                        Paragraph(escape(_as_text(c.get('contribution_summary',''))), styles['ExecBody'])]
                       for c in contributors[:10]]
            c_table = Table(c_header + c_rows, colWidths=[100, 80, 90, 270])
            c_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor(GOLD)),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(c_table)
            story.append(Spacer(1, 25))

        # 10. --- CONFIDENCE ASSESSMENT ---
        confidence = intelligence_object.get("confidence_and_assumptions") or {}
        if confidence:
            story.append(Table([[Paragraph("CONFIDENCE ASSESSMENT", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 10))
            conf_level = _as_text(confidence.get('overall_confidence', '')).upper()
            conf_color = '#4CAF7D' if 'HIGH' in conf_level else (GOLD if 'MODERATE' in conf_level else '#FF3131')
            story.append(Paragraph(f"OVERALL CONFIDENCE: <font color='{conf_color}'><b>{escape(conf_level)}</b></font>", styles['ExecBody']))
            story.append(Spacer(1, 8))
            assumptions = confidence.get('key_assumptions') or []
            if assumptions:
                story.append(Paragraph("KEY ASSUMPTIONS:", styles['ExecLabel']))
                for assumption in assumptions[:5]:
                    story.append(Paragraph(f"&bull; {escape(_as_text(assumption))}", styles['ExecBody']))
            limitations = confidence.get('limitations') or []
            if limitations:
                story.append(Spacer(1, 6))
                story.append(Paragraph("LIMITATIONS:", styles['ExecLabel']))
                for lim in limitations[:4]:
                    story.append(Paragraph(f"&bull; {escape(_as_text(lim))}", styles['ExecBody']))
            story.append(Spacer(1, 25))

        # 11. --- DIVERGENCE ANALYSIS ---
        divergence = intelligence_object.get("divergence_analysis") or {}
        if divergence and (divergence.get("divergence_score") or divergence.get("contested_topics")):
            story.append(Table([[Paragraph("DIVERGENCE ANALYSIS", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 10))
            div_score = divergence.get("divergence_score", 0)
            con_score = divergence.get("consensus_score", 0)
            try:
                div_score = int(float(div_score))
                con_score = int(float(con_score))
            except (ValueError, TypeError):
                div_score, con_score = 0, 0
            if div_score or con_score:
                story.append(Paragraph(f"CONSENSUS: <b>{con_score}/100</b> &nbsp;&nbsp; DIVERGENCE: <b>{div_score}/100</b>", styles['ExecBody']))
                story.append(Spacer(1, 8))
            div_summary = divergence.get("divergence_summary")
            if div_summary:
                story.append(Paragraph(escape(_as_text(div_summary)), styles['ExecBody']))
                story.append(Spacer(1, 8))
            contested = divergence.get("contested_topics") or []
            for topic in contested[:4]:
                topic_name = topic.get("topic", topic) if isinstance(topic, dict) else _as_text(topic)
                story.append(Paragraph(f"&bull; <b>{escape(_as_text(topic_name))}</b>", styles['ExecBody']))
            story.append(Spacer(1, 25))

        # 12. --- SUPPLEMENTAL DATA EXHIBITS ---
        artifacts = _report_artifacts(intelligence_object)
        if artifacts:
            story.append(Table([[Paragraph("SUPPLEMENTAL DATA EXHIBITS", styles['ExecLabel'])]], colWidths=[540], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(GOLD))]))
            story.append(Spacer(1, 15))
            for art in artifacts:
                row = [[Paragraph(f"EXHIBIT: {escape(_artifact_label(art).upper())}", styles['ExecLabel']), Paragraph(escape(_as_text(art.get("content", ""))).replace("\n", "<br/>"), styles['ExecBody'])]]
                at_tab = Table(row, colWidths=[160, 380])
                at_tab.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 20)]))
                story.append(at_tab)

        # 13. --- FOOTER AUTHENTICATION ---
        story.append(Spacer(1, 40))
        sig_data = [[Paragraph(f"Produced by Korum-OS Decision Intelligence // {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['ExecAudit'])]]
        sig_tab = Table(sig_data, colWidths=[540])
        sig_tab.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'RIGHT')]))
        story.append(sig_tab)

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
            'NEON_DESERT': {"accent": "00F5FF", "gold": "FFD700"},
            'CARBON_STEEL':{"accent": "FFFFFF", "gold": "94A3B8"},
            'ARCHITECT':   {"accent": "1A1A1A", "gold": "8B4513"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        p_rgb = RGBColor(*WordExporter._hex_to_rgb(t['gold']))
        s_rgb = RGBColor(*WordExporter._hex_to_rgb(t['accent']))
        
        # 1. --- LOGO & HEADER ---
        logo_filename = "main korum os logo light.png" if theme_id != "ARCHITECT" else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        
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
        
        labels = [("PREPARED FOR:", "DECISION COMMANDER ALPHA"), 
                  ("MISSION DIRECTIVE:", escape(meta.get('workflow', 'STRATEGIC_INTEL').upper())),
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
        
        doc.add_paragraph("-" * 90)

        # 3. --- STRATEGIC IMPACT ---
        sum_p = doc.add_paragraph("STRATEGIC IMPACT SUMMARY")
        sum_p.runs[0].bold = True
        sum_p.runs[0].font.size = Pt(9)
        sum_p.runs[0].font.color.rgb = p_rgb
        
        impact_text = (meta.get("summary") or "INTEL SYNTHESIS REQUIRED").upper()
        imp_p = doc.add_paragraph(impact_text)
        imp_p.runs[0].bold = True
        imp_p.runs[0].font.size = Pt(12)
        doc.add_paragraph()

        # 4. --- CONTENT GRID (Asymmetric) ---
        for idx, (sid, content) in enumerate(sections.items()):
            grid = doc.add_table(rows=1, cols=2)
            grid.columns[0].width = Inches(1.5)
            grid.columns[1].width = Inches(4.5)
            
            l_cell = grid.rows[0].cells[0]
            l_p = l_cell.paragraphs[0]
            l_run = l_p.add_run(sid.replace("_", " ").upper())
            l_run.bold = True
            l_run.font.size = Pt(9)
            l_run.font.color.rgb = p_rgb
            
            r_cell = grid.rows[0].cells[1]
            clean_text = _clean_tags(content, strip_markdown=True)
            r_cell.text = clean_text
            r_cell.paragraphs[0].runs[0].font.size = Pt(10)
            doc.add_paragraph()

        # 5. --- TRUTH SCORE ---
        truth_raw = meta.get("composite_truth_score", 0)
        try:
            truth_int = int(float(truth_raw) * 100) if float(truth_raw) <= 1 else int(float(truth_raw))
        except (ValueError, TypeError):
            truth_int = 0
        if truth_int > 0:
            ts_p = doc.add_paragraph()
            ts_label = ts_p.add_run(f"COMPOSITE TRUTH SCORE: {truth_int}/100")
            ts_label.bold = True
            ts_label.font.size = Pt(10)
            ts_label.font.color.rgb = p_rgb
            doc.add_paragraph()

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

        # 7. --- RISK MATRIX ---
        risks = structured.get("risks") or []
        if risks:
            h_p = doc.add_paragraph("RISK MATRIX")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)
            r_tab = doc.add_table(rows=1 + len(risks[:8]), cols=3)
            r_tab.style = 'Table Grid'
            r_tab.autofit = False
            r_tab.columns[0].width = Inches(2.5)
            r_tab.columns[1].width = Inches(1.0)
            r_tab.columns[2].width = Inches(2.5)
            for i, lbl in enumerate(["RISK", "SEVERITY", "MITIGATION"]):
                cell = r_tab.rows[0].cells[i]
                cell.text = lbl
                cell.paragraphs[0].runs[0].bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(8)
                cell.paragraphs[0].runs[0].font.color.rgb = p_rgb
            for ri, r in enumerate(risks[:8]):
                r_tab.rows[ri+1].cells[0].text = _as_text(r.get('risk', ''))
                sev_cell = r_tab.rows[ri+1].cells[1]
                sev_cell.text = _as_text(r.get('severity', '')).upper()
                sev_cell.paragraphs[0].runs[0].bold = True
                r_tab.rows[ri+1].cells[2].text = _as_text(r.get('mitigation', ''))
            doc.add_paragraph()

        # 8. --- RECOMMENDED ACTIONS ---
        actions = structured.get("action_items") or structured.get("actions") or []
        if actions:
            h_p = doc.add_paragraph("RECOMMENDED ACTIONS")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)
            a_tab = doc.add_table(rows=1 + len(actions[:8]), cols=3)
            a_tab.style = 'Table Grid'
            a_tab.autofit = False
            a_tab.columns[0].width = Inches(3.0)
            a_tab.columns[1].width = Inches(1.0)
            a_tab.columns[2].width = Inches(2.0)
            for i, lbl in enumerate(["ACTION", "PRIORITY", "TIMELINE"]):
                cell = a_tab.rows[0].cells[i]
                cell.text = lbl
                cell.paragraphs[0].runs[0].bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(8)
                cell.paragraphs[0].runs[0].font.color.rgb = p_rgb
            for ri, a in enumerate(actions[:8]):
                a_tab.rows[ri+1].cells[0].text = _as_text(a.get('task', a.get('action', '')))
                pri_cell = a_tab.rows[ri+1].cells[1]
                pri_cell.text = _as_text(a.get('priority', '')).upper()
                pri_cell.paragraphs[0].runs[0].bold = True
                a_tab.rows[ri+1].cells[2].text = _as_text(a.get('timeline', ''))
            doc.add_paragraph()

        # 9. --- COUNCIL CONTRIBUTORS ---
        contributors = intelligence_object.get("council_contributors") or []
        if contributors:
            h_p = doc.add_paragraph("COUNCIL CONTRIBUTORS")
            h_p.runs[0].bold = True
            h_p.runs[0].font.color.rgb = p_rgb
            h_p.runs[0].font.size = Pt(10)
            c_tab = doc.add_table(rows=1 + len(contributors[:10]), cols=4)
            c_tab.style = 'Table Grid'
            c_tab.autofit = False
            c_tab.columns[0].width = Inches(1.2)
            c_tab.columns[1].width = Inches(1.0)
            c_tab.columns[2].width = Inches(1.0)
            c_tab.columns[3].width = Inches(2.8)
            for i, lbl in enumerate(["PHASE", "PROVIDER", "ROLE", "CONTRIBUTION"]):
                cell = c_tab.rows[0].cells[i]
                cell.text = lbl
                cell.paragraphs[0].runs[0].bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(8)
                cell.paragraphs[0].runs[0].font.color.rgb = p_rgb
            for ri, c in enumerate(contributors[:10]):
                c_tab.rows[ri+1].cells[0].text = _as_text(c.get('phase', ''))
                c_tab.rows[ri+1].cells[1].text = _as_text(c.get('provider', '')).upper()
                c_tab.rows[ri+1].cells[2].text = _as_text(c.get('role', ''))
                c_tab.rows[ri+1].cells[3].text = _as_text(c.get('contribution_summary', ''))
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

        # 11. --- SIGNATURE FOOTER ---
        section = doc.sections[0]
        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_run = p.add_run(f"Produced by Korum-OS Decision Intelligence // {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        f_run.font.name = 'Courier New'
        f_run.font.size = Pt(8)

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

