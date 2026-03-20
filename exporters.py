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
    """Command-Grade PDF briefing — High high-fidelity Command Alpha standards."""
    
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        mission_ctx = intelligence_object.get("_mission_context") or {}
        
        # --- THE TRINITY: CORPORATE | NEURAL | OPERATOR ---
        THEMES = {
            'ARCHITECT':   {"bg": "#F2F1EF", "primary": "#A65E46", "secondary": "#636E72", "text": "#2D3436", "card": "#FFFFFF", "accent": "#A65E46"},
            'NEON_DESERT': {"bg": "#0D1117", "primary": "#FFB020", "secondary": "#2DD4BF", "text": "#D1D5DB", "card": "#161B22", "accent": "#FFB020"},
            'CARBON_STEEL':{"bg": "#0D0D0D", "primary": "#E2E8F0", "secondary": "#94A3B8", "text": "#F1F5F9", "card": "#1A1A1A", "accent": "#64748B"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES:
             if "ARCH" in theme_id: theme_id = "ARCHITECT"
             elif "STEEL" in theme_id: theme_id = "CARBON_STEEL"
             else: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        BG_PAGE = t['bg']
        ACCENT_PRIMARY = t['primary']
        ACCENT_SECONDARY = t['secondary']
        TEXT_PRIMARY = t['text']
        TEXT_SECONDARY = t['secondary']
        CARD_BG = t['card']
        ACCENT_BAR = t['accent']

        # Signal Colors
        SIGNAL_RED = "#FF3131"
        AMBER = "#FFB020"

        safe_title = _safe_filename_part(meta.get('title', 'Intelligence'))
        filename = f"KORUM-OS_{safe_title}_{theme_id}_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)
        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=25, bottomMargin=35, leftMargin=40, rightMargin=40)
        doc._bg_color = BG_PAGE
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('BrandedTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor(TEXT_PRIMARY), alignment=1, spaceAfter=20, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('HUDLabel', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor(ACCENT_SECONDARY), alignment=1, fontName='Courier-Bold'))
        styles.add(ParagraphStyle('HUDValue', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor(TEXT_PRIMARY), alignment=1, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('SectionBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor(TEXT_PRIMARY), leading=14, fontName='Helvetica'))
        styles.add(ParagraphStyle('CardTitle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor(ACCENT_PRIMARY), spaceBefore=0, fontName='Helvetica-Bold', leftIndent=10))
        styles.add(ParagraphStyle('DirectiveTitle', parent=styles['Normal'], fontSize=16, textColor=colors.HexColor(ACCENT_PRIMARY), alignment=1, spaceAfter=5, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('DirectiveText', parent=styles['Normal'], fontSize=13, textColor=colors.HexColor(TEXT_PRIMARY), alignment=1, leading=17, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ArtifactTitle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor(ACCENT_SECONDARY), fontName='Courier-Bold'))

        story = []

        # --- LOGO & HUD HEADER ---
        logo_filename = "main korum os logo light.png" if theme_id != "ARCHITECT" else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo.png")

        header_table_data = []
        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=160, height=40)
            header_table_data.append([img])
        
        h_table = Table(header_table_data or [["KORUM-OS INTEL"]], colWidths=[532])
        h_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        story.append(h_table)
        story.append(Spacer(1, 10))

        # --- COMMAND HUD (Tactical HUD) ---
        workflow = _as_text(meta.get("workflow", "INTEL")).upper()
        truth_raw = meta.get("composite_truth_score", "0")
        try:
             truth_int = int(float(truth_raw) * 100) if float(truth_raw) <= 1 else int(float(truth_raw))
        except:
             truth_int = 0
             
        hud_data = [
            [Paragraph("MISSION IDENTIFIER", styles['HUDLabel']), Paragraph("WORKFLOW CONTEXT", styles['HUDLabel']), Paragraph("TRUTH SCORE", styles['HUDLabel'])],
            [Paragraph(escape(meta.get('title', 'KORUM_ALPHA').upper()), styles['HUDValue']), 
             Paragraph(escape(workflow), styles['HUDValue']), 
             Paragraph(f"{truth_int}%", styles['HUDValue'])]
        ]
        hud_table = Table(hud_data, colWidths=[177, 177, 177])
        hud_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(CARD_BG)),
            ('BOTTOMPADDING', (0,0), (-1,0), 0),
            ('TOPPADDING', (0,1), (-1,1), 2),
            ('BOTTOMPADDING', (0,1), (-1,1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor(ACCENT_SECONDARY)),
        ]))
        story.append(hud_table)

        # Visual Truth Bar
        bar_width = 532
        filled_width = (truth_int / 100.0) * bar_width
        truth_bar_data = [[""]]
        truth_bar = Table(truth_bar_data, colWidths=[filled_width, bar_width - filled_width] if filled_width > 0 else [0.1, bar_width])
        truth_bar.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), colors.HexColor(ACCENT_BAR)),
            ('BACKGROUND', (1,0), (1,0), colors.HexColor("#333333")),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(truth_bar)
        story.append(Spacer(1, 30))

        # --- [PRIMARY DIRECTIVE] BANNER ---
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        directive = directive_list[0] if directive_list else (meta.get("summary") or "ANALYSIS IN PROGRESS")
        
        d_data = [
            [Paragraph(f"<b>[PRIMARY DIRECTIVE]</b>", styles['DirectiveTitle'])],
            [Paragraph(escape(_as_text(directive).upper()), styles['DirectiveText'])],
            [Paragraph(f"STATUS: LOGIC VERIFIED // ACTION REQUIRED", styles['HUDLabel'])]
        ]
        d_table = Table(d_data, colWidths=[510])
        d_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(CARD_BG)),
            ('BOX', (0,0), (-1,-1), 2, colors.HexColor(ACCENT_PRIMARY)),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('LEFTPADDING', (0,0), (-1,-1), 15),
            ('RIGHTPADDING', (0,0), (-1,-1), 15),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(d_table)
        story.append(Spacer(1, 40))

        # --- SECTIONS (INTEL CARDS) ---
        for sid, content in sections.items():
            section_title = sid.replace("_", " ").upper()
            
            # Prepare Content with Signal Highlighting
            raw_text = _as_text(content)
            tag_placeholders = {}
            critical_ph = "___SIGNAL_CRITICAL___"
            raw_text = raw_text.replace("[CRITICAL]", critical_ph)
            signal_tags = ["ACTION REQUIRED", "VERIFIED", "RISK", "WARNING", "DECISION CANDIDATE"]
            for tag in signal_tags:
                ph = f"___SIGNAL_{tag.replace(' ', '_')}___"
                raw_text = raw_text.replace(f"[{tag}]", ph)
                raw_text = raw_text.replace(f"[/{tag}]", "")
                tag_placeholders[ph] = f"<font color='{AMBER}'><b>[{tag}]</b></font>"

            bold_spans = []
            for m in re.finditer(r'\*\*(.*?)\*\*', raw_text):
                bold_spans.append((m.group(0), f"___BOLD_{len(bold_spans)}___"))
            for orig, ph in bold_spans: raw_text = raw_text.replace(orig, ph, 1)

            styled_content = escape(raw_text)
            styled_content = styled_content.replace(critical_ph, f"<font color='{SIGNAL_RED}'><b>[CRITICAL]</b></font>")
            for ph, styled_tag in tag_placeholders.items(): styled_content = styled_content.replace(ph, styled_tag)
            for original, placeholder in bold_spans:
                bold_text = escape(original[2:-2])
                styled_content = styled_content.replace(placeholder, f"<b>{bold_text}</b>")
            styled_content = styled_content.replace("\n", "<br/>")

            # Build the Card
            card_data = [
                [Paragraph(section_title, styles['CardTitle'])],
                [Paragraph(styled_content, styles['SectionBody'])]
            ]
            
            card_table = Table(card_data, colWidths=[520])
            card_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(CARD_BG)),
                ('TOPPADDING', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 5),
                ('BOTTOMPADDING', (0,1), (-1,1), 15),
                ('LEFTPADDING', (0,0), (-1,-1), 15),
                ('RIGHTPADDING', (0,0), (-1,-1), 15),
                ('LINEBEFORE', (0,0), (0,1), 4, colors.HexColor(ACCENT_BAR)), # Accent Bar
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#333333")),
            ]))
            
            story.append(card_table)
            story.append(Spacer(1, 20))

        # --- EXHIBITS ---
        artifacts = _report_artifacts(intelligence_object)
        if artifacts:
            story.append(Spacer(1, 20))
            story.append(Paragraph("SUPPLEMENTAL EXHIBITS // MISSION DATA", styles['CardTitle']))
            for art in artifacts:
                title = _artifact_label(art).upper()
                art_content = escape(_as_text(art.get("content", ""))).replace("\n", "<br/>")
                
                ex_data = [[Paragraph(f"EXHIBIT: {title}", styles['ArtifactTitle'])],
                           [Paragraph(art_content, styles['SectionBody'])]]
                ex_table = Table(ex_data, colWidths=[520])
                ex_table.setStyle(TableStyle([
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('GRID', (0,0), (-1,0), 0.5, colors.HexColor(ACCENT_SECONDARY)),
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A1A1A") if theme_id != "ARCHITECT" else colors.HexColor("#EAEAEA")),
                ]))
                story.append(ex_table)
                story.append(Spacer(1, 15))

        # --- FOOTER ---
        footer_text = f"KOS // {datetime.now().strftime('%Y-%m-%d %H:%M')} // AUTHENTICATED INTEL NODE // PROP-RESTRICTIVE"
        footer_table = Table([[Paragraph(footer_text, styles['HUDLabel'])]], colWidths=[532])
        footer_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        story.append(Spacer(1, 40))
        story.append(footer_table)

        doc.build(story, onFirstPage=_dark_page_bg, onLaterPages=_dark_page_bg)
        return filepath

class WordExporter:
    """Premium Word report with themed headers and high-contrast logic."""
    
    @staticmethod
    def _shade_cell(cell, hex_color):
        if hex_color.startswith('#'): hex_color = hex_color[1:]
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        doc = Document()
        
        THEMES = {
            'ARCHITECT':   {"bg": "F2F1EF", "primary": (0xA6, 0x5E, 0x46), "secondary": (0x63, 0x6E, 0x72), "text": "2D3436"},
            'NEON_DESERT': {"bg": "0D1117", "primary": (0xFF, 0xB0, 0x20), "secondary": (0x2D, 0xD4, 0xBF), "text": "D1D5DB"},
            'CARBON_STEEL':{"bg": "0D0D0D", "primary": (0xD1, 0xD5, 0xDB), "secondary": (0x4B, 0x55, 0x63), "text": "E2E8F0"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES:
             if "ARCH" in theme_id: theme_id = "ARCHITECT"
             elif "STEEL" in theme_id: theme_id = "CARBON_STEEL"
             else: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        p_rgb = RGBColor(*t['primary'])
        s_rgb = RGBColor(*t['secondary'])
        
        # Header: Logo
        logo_filename = "main korum os logo light.png" if theme_id != "ARCHITECT" else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        if os.path.exists(logo_path):
            doc.add_picture(logo_path, width=Inches(2.2))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()

        # Premium Directive Banner
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        directive = directive_list[0] if directive_list else (meta.get("summary") or "INTEL ANALYSIS")
        
        d_tab = doc.add_table(rows=1, cols=1)
        d_tab.style = 'Table Grid'
        cell = d_tab.rows[0].cells[0]
        WordExporter._shade_cell(cell, "050505")
        
        # [PRIMARY DIRECTIVE] Label
        p1 = cell.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = p1.add_run("[PRIMARY DIRECTIVE]")
        run1.bold = True
        run1.font.color.rgb = p_rgb
        
        # Directive Content
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run2 = p2.add_run(_as_text(directive).upper())
        run2.bold = True
        run2.font.size = Pt(14)
        run2.font.color.rgb = p_rgb
        
        doc.add_paragraph()
        
        # Content Sections as "Cards"
        for sid, content in sections.items():
            s_tab = doc.add_table(rows=2, cols=1)
            s_tab.style = 'Table Grid'
            # Header Row
            h_cell = s_tab.rows[0].cells[0]
            WordExporter._shade_cell(h_cell, "1A1A1A")
            h_p = h_cell.paragraphs[0]
            h_run = h_p.add_run(sid.replace("_", " ").upper())
            h_run.bold = True
            h_run.font.color.rgb = p_rgb
            
            # Body Row
            b_cell = s_tab.rows[1].cells[0]
            b_p = b_cell.paragraphs[0]
            # Strip tags for clean word output
            clean_text = _clean_tags(content, strip_markdown=True)
            b_p.add_run(clean_text)
            
            doc.add_paragraph()

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

