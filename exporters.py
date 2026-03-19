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

def _as_text(value):
    if value is None: return ""
    if isinstance(value, (dict, list)): return json.dumps(value, ensure_ascii=False)
    return str(value)

def _sanitize_for_csv(value):
    text = _as_text(value)
    text = re.sub(r'\[\/?(?:DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]', '', text)
    if text and text[0] in ('=', '+', '-', '@'): text = "'" + text
    return text

def _convert_mermaid_to_table(text):
    # (Helper logic for Mermaid integration)
    return text

def _clean_tags(text, strip_markdown=True):
    text = _as_text(text)
    text = re.sub(r'\[\/?(?:DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]', '', text)
    if strip_markdown:
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'#{1,4}\s*', '', text)
    return text.strip()

def _extract_parts(intelligence_object):
    data = intelligence_object or {}
    meta = data.get("meta", {}) or {}
    sections = data.get("sections", {}) or {}
    structured = data.get("structured_data", {}) or {}
    interrogations = data.get("interrogations", [])
    verifications = data.get("verifications", [])
    return meta, sections, structured, interrogations, verifications

def _report_artifacts(intelligence_object):
    snippets = intelligence_object.get("docked_snippets") or []
    selected = [s for s in snippets if s.get("includeInReport")]
    return selected or snippets

def _artifact_label(snippet):
    return _as_text(snippet.get("label", "Artifact")).strip() or "Artifact"

def _dark_page_bg(canvas, doc):
    canvas.saveState()
    # Get current theme background from doc if available, else default
    bg_color = getattr(doc, '_bg_color', "#0D0D0D")
    canvas.setFillColor(colors.HexColor(bg_color))
    canvas.rect(0, 0, 612, 792, fill=True, stroke=False)
    canvas.restoreState()

class PDFExporter:
    """Command-Grade PDF briefing — High high-fidelity Command Alpha standards."""
    
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        mission_ctx = intelligence_object.get("_mission_context") or {}
        
        # --- THE TRINITY: CORPORATE | NEURAL | OPERATOR ---
        THEMES = {
            'ARCHITECT':   {"bg": "#2D3436", "primary": "#A65E46", "secondary": "#636E72", "text": "#F2F1EF"},
            'BIO_NEON':    {"bg": "#0F172A", "primary": "#2DD4BF", "secondary": "#FBBF24", "text": "#94A3B8"},
            'CARBON_STEEL':{"bg": "#1A1A1A", "primary": "#BC2F32", "secondary": "#4B5563", "text": "#D1D5DB"},
        }
        theme_id = meta.get("theme", "BIO_NEON").upper()
        if theme_id not in THEMES:
             if "ARCH" in theme_id: theme_id = "ARCHITECT"
             elif "STEEL" in theme_id: theme_id = "CARBON_STEEL"
             else: theme_id = "BIO_NEON"
        
        t = THEMES[theme_id]
        BG_DARK = t['bg']
        ACCENT_PRIMARY = t['primary']
        ACCENT_SECONDARY = t['secondary']
        TEXT_PRIMARY = t['text']
        TEXT_SECONDARY = t['secondary']
        BORDER = t['secondary']

        filename = f"KORUM-OS_{meta.get('title', 'Intelligence')}_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)
        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=25, bottomMargin=25, leftMargin=40, rightMargin=40)
        doc._bg_color = BG_DARK
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('BrandedTitle', parent=styles['Heading1'], fontSize=28, textColor=colors.HexColor(TEXT_PRIMARY), alignment=1, spaceAfter=20, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('BannerText', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor(TEXT_SECONDARY), alignment=1, fontName='Courier'))
        styles.add(ParagraphStyle('SectionBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor(TEXT_PRIMARY), leading=14))
        styles.add(ParagraphStyle('BrandedHeading1', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor(ACCENT_PRIMARY), spaceBefore=20, fontName='Helvetica-Bold'))

        story = []

        # --- LOGO HEADER ---
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "korum os logo.png")
        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=180, height=45)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 10))

        # --- COMMAND DASHBOARD ---
        workflow = _as_text(meta.get("workflow", "INTEL")).upper()
        agents_cnt = len(meta.get("models_used", []))
        dash_data = [
            [Paragraph(f"<font color='{ACCENT_SECONDARY}'>KORUM-OS // COMMAND NODE</font>", styles['BannerText']),
             Paragraph(f"INTELLIGENCE BRIEF — {workflow}", styles['BannerText'])],
            [Paragraph(f"MISSION: {meta.get('title', 'KORUM_ALPHA').upper()}", styles['BannerText']),
             Paragraph(f"AGENTS: {agents_cnt} ACTIVE", styles['BannerText'])]
        ]
        dash_table = Table(dash_data, colWidths=[250, 250])
        dash_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(BG_DARK)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(dash_table)
        story.append(Spacer(1, 4))

        # --- TACTICAL STATUS BAR ---
        truth_raw = meta.get("composite_truth_score", "0")
        try:
             truth_int = int(float(truth_raw) * 100) if float(truth_raw) <= 1 else int(float(truth_raw))
        except:
             truth_int = 0
             
        stat_data = [[f"CONFIDENCE: {truth_int}/100    |    RISK: HIGH    |    SYSTEM: VERIFIED"]]
        stat_table = Table(stat_data, colWidths=[500])
        stat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#161616")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(TEXT_SECONDARY)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(stat_table)
        story.append(Spacer(1, 30))

        # --- PRIMARY DIRECTIVE (Center Callout) ---
        directive = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        if directive:
            d_data = [[Paragraph(f"<b>[PRIMARY DIRECTIVE]</b><br/><br/><font size='16'>{_as_text(directive[0]).upper()}</font><br/><br/>— ACTION REQUIRED —", styles['BrandedTitle'])]]
            d_table = Table(d_data, colWidths=[500])
            d_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1A1A1A")),
                ('BOX', (0,0), (-1,-1), 2, colors.HexColor(ACCENT_PRIMARY)),
                ('TOPPADDING', (0,0), (-1,-1), 20),
                ('BOTTOMPADDING', (0,0), (-1,-1), 20),
            ]))
            story.append(d_table)
            story.append(Spacer(1, 40))

        # --- SECTIONS ---
        for sid, content in sections.items():
            story.append(Paragraph(sid.replace("_", " ").upper(), styles['BrandedHeading1']))
            story.append(Paragraph(_clean_tags(content), styles['SectionBody']))
            story.append(Spacer(1, 15))

        # --- FOOTER ---
        story.append(Spacer(1, 40))
        footer_data = [[f"KORUM-OS AUTHENTICATED INTEL NODE — {datetime.now().strftime('%Y-%m-%d %H:%M')}"]]
        footer_table = Table(footer_data, colWidths=[512])
        footer_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor(ACCENT_SECONDARY)),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(footer_table)

        doc.build(story, onFirstPage=_dark_page_bg, onLaterPages=_dark_page_bg)
        return filepath

class WordExporter:
    """Branded Word report following Trinity Theme standards."""
    
    @staticmethod
    def _shade_cell(cell, hex_color):
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        doc = Document()
        
        THEMES = {
            'ARCHITECT':   {"bg": "2D3436", "primary": (0xA6, 0x5E, 0x46), "secondary": (0x63, 0x6E, 0x72), "text": "F2F1EF"},
            'BIO_NEON':    {"bg": "0F172A", "primary": (0x2D, 0xD4, 0xBF), "secondary": (0xFB, 0xBF, 0x24), "text": "94A3B8"},
            'CARBON_STEEL':{"bg": "1A1A1A", "primary": (0xBC, 0x2F, 0x32), "secondary": (0x4B, 0x55, 0x63), "text": "D1D5DB"},
        }
        theme_id = meta.get("theme", "BIO_NEON").upper()
        if theme_id not in THEMES: theme_id = "BIO_NEON"
        t = THEMES[theme_id]
        p_rgb = RGBColor(*t['primary'])
        
        # Margins
        sec = doc.sections[0]
        sec.top_margin = Inches(0.8)
        
        # Logo Header
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "korum os logo.png")
        if os.path.exists(logo_path):
            doc.add_picture(logo_path, width=Inches(2.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
        # Title Table (Command Bar)
        title_tab = doc.add_table(rows=1, cols=1)
        title_tab.autofit = True
        cell = title_tab.rows[0].cells[0]
        WordExporter._shade_cell(cell, t['bg'])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(meta.get("title", "INTELLIGENCE BRIEF").upper())
        run.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = p_rgb
        
        doc.add_paragraph() # Spacer
        
        # Primary Directive Block
        directive = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        if directive:
            d_tab = doc.add_table(rows=1, cols=1)
            d_tab.autofit = True
            cell = d_tab.rows[0].cells[0]
            WordExporter._shade_cell(cell, "1A1A1A")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run("PRIMARY DIRECTIVE")
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = p_rgb
            p2 = cell.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run2 = p2.add_run(_as_text(directive[0]).upper())
            run2.bold = True
            run2.font.size = Pt(14)
            run2.font.color.rgb = p_rgb
            doc.add_paragraph()
        
        # Content
        for sid, content in sections.items():
            h = doc.add_heading(sid.replace("_", " ").upper(), level=1)
            p = doc.add_paragraph(_clean_tags(content))
            
        filename = f"KORUM-OS_{_timestamp()}.docx"
        filepath = _output_path(filename, output_dir)
        doc.save(filepath)
        return filepath

class MarkdownExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, _, _, _ = _extract_parts(intelligence_object)
        md = [f"# {meta.get('title', 'Intelligence Report').upper()}", f"## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", "---"]
        for sid, content in sections.items():
            md.append(f"### {sid.replace('_', ' ').upper()}")
            md.append(content)
            md.append("\n---")
        filename = f"KORUM-OS_{_timestamp()}.md"
        filepath = _output_path(filename, output_dir)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(md))
        return filepath

class ResearchPaperExporter:
    @staticmethod
    def generate(o, d=None): return PDFExporter.generate(o, d) # Minimalist fallback for now

class ExcelExporter:
    @staticmethod
    def generate(o, d=None): return ""

class PowerPointExporter:
    @staticmethod
    def generate(o, d=None): return ""
