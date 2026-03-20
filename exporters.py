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

def _safe_filename_part(value, fallback="Intelligence"):
    text = _as_text(value).strip()
    if not text:
        text = fallback
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', '_', text)
    text = re.sub(r'\s+', ' ', text).strip().rstrip('. ')
    return text[:120] or fallback

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
            'NEON_DESERT': {"bg": "#0D1117", "primary": "#FFB020", "secondary": "#2DD4BF", "text": "#D1D5DB"},
            'CARBON_STEEL':{"bg": "#0D0D0D", "primary": "#A5A5A5", "secondary": "#4B5563", "text": "#E2E8F0"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES:
             if "ARCH" in theme_id: theme_id = "ARCHITECT"
             elif "STEEL" in theme_id: theme_id = "CARBON_STEEL"
             else: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        BG_DARK = t['bg']
        ACCENT_PRIMARY = t['primary']
        ACCENT_SECONDARY = t['secondary']
        TEXT_PRIMARY = t['text']
        TEXT_SECONDARY = t['secondary']
        BORDER = t['secondary']

        # Signal Red (Reserved for Critical)
        SIGNAL_RED = "#FF3131"
        AMBER = "#FFB020"

        safe_title = _safe_filename_part(meta.get('title', 'Intelligence'))
        filename = f"KORUM-OS_{safe_title}_{theme_id}_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)
        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=25, bottomMargin=25, leftMargin=40, rightMargin=40)
        doc._bg_color = BG_DARK
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('BrandedTitle', parent=styles['Heading1'], fontSize=28, textColor=colors.HexColor(TEXT_PRIMARY), alignment=1, spaceAfter=20, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('BannerText', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor(TEXT_SECONDARY), alignment=1, fontName='Courier'))
        styles.add(ParagraphStyle('SectionBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor(TEXT_PRIMARY), leading=14))
        styles.add(ParagraphStyle('BrandedHeading1', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor(ACCENT_PRIMARY), spaceBefore=20, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('DirectiveTitle', parent=styles['Normal'], fontSize=18, textColor=colors.HexColor(ACCENT_PRIMARY), alignment=1, spaceAfter=5, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('DirectiveText', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor(TEXT_PRIMARY), alignment=1, leading=18, fontName='Helvetica-Bold'))

        story = []

        # --- LOGO HEADER (Adaptive Branding) ---
        is_dark_bg = True # Default for Neon/Steel
        if theme_id == "ARCHITECT": is_dark_bg = False
        
        logo_filename = "main korum os logo light.png" if is_dark_bg else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        # Fallback to main version if specific ones are missing
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo.png")

        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=200, height=50) # Increased size for higher impact
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 15))

        # --- COMMAND DASHBOARD ---
        workflow = _as_text(meta.get("workflow", "INTEL")).upper()
        agents_cnt = len(meta.get("models_used", []))
        dash_data = [
            [Paragraph(f"<font color='{ACCENT_SECONDARY}'>KORUM-OS // COMMAND NODE // ALPHA-MODE ACTIVE</font>", styles['BannerText']),
             Paragraph(f"INTELLIGENCE BRIEF — {workflow}", styles['BannerText'])],
            [Paragraph(f"MISSION: {meta.get('title', 'KORUM_ALPHA').upper()}", styles['BannerText']),
             Paragraph(f"AGENTS: {agents_cnt} ACTIVE NODE(S)", styles['BannerText'])]
        ]
        dash_table = Table(dash_data, colWidths=[266, 266])
        dash_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(BG_DARK)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))

        story.append(dash_table)
        story.append(Spacer(1, 10))

        # --- TACTICAL STATUS BAR ---
        truth_raw = meta.get("composite_truth_score", "0")
        try:
             truth_int = int(float(truth_raw) * 100) if float(truth_raw) <= 1 else int(float(truth_raw))
        except:
             truth_int = 0
             
        stat_data = [[f"CONFIDENCE: {truth_int}/100    |    STATUS: VERIFIED    |    SYSTEM: SECURE"]]
        stat_table = Table(stat_data, colWidths=[532])
        stat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#1A1A1A")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(ACCENT_SECONDARY) if truth_int > 80 else colors.HexColor(AMBER)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Courier-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
        ]))
        story.append(stat_table)
        story.append(Spacer(1, 40))

        # --- [PRIMARY DIRECTIVE] - DIRECTIVE-FIRST APPROACH ---
        # Fetch directly from intelligence_tags or fallback to synthesis summary
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        directive = directive_list[0] if directive_list else (meta.get("summary") or "INTEL ANALYSIS IN PROGRESS")
        
        d_data = [
            [Paragraph(f"<b>[PRIMARY DIRECTIVE]</b>", styles['DirectiveTitle'])],
            [Paragraph(f"{_as_text(directive).upper()}", styles['DirectiveText'])],
            [Paragraph(f"— ACTION REQUIRED —", styles['BannerText'])]
        ]
        d_table = Table(d_data, colWidths=[532])
        d_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#080808")),
            ('BOX', (0,0), (-1,-1), 2, colors.HexColor(ACCENT_PRIMARY)),
            ('TOPPADDING', (0,0), (0,0), 15),
            ('BOTTOMPADDING', (2,2), (2,2), 15),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(d_table)
        story.append(Spacer(1, 50))

        # --- SECTIONS (Executive Intel) ---
        for sid, content in sections.items():
            section_title = sid.replace("_", " ").upper()
            story.append(Paragraph(section_title, styles['BrandedHeading1']))
            
            # Implementation of Signal Tag Highlighting in PDFs
            # Convert [CRITICAL] to red, others to amber
            styled_content = _as_text(content)
            styled_content = styled_content.replace("[CRITICAL]", f"<font color='{SIGNAL_RED}'><b>[CRITICAL]</b></font>")
            tags = ["ACTION REQUIRED", "VERIFIED", "RISK", "WARNING", "DECISION CANDIDATE", "METRIC ANCHOR", "TRUTH BOMB"]
            for tag in tags:
                styled_content = styled_content.replace(f"[{tag}]", f"<font color='{AMBER}'><b>[{tag}]</b></font>")
                styled_content = styled_content.replace(f"[/{tag}]", "") # Cleanup
            
            # Basic markdown conversions for PDF bolding
            styled_content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', styled_content)
            styled_content = styled_content.replace("\n", "<br/>")

            story.append(Paragraph(styled_content, styles['SectionBody']))
            story.append(Spacer(1, 20))

        # --- EXHIBITS: DOCKED ARTIFACTS ---
        artifacts = _report_artifacts(intelligence_object)
        if artifacts:
            story.append(Spacer(1, 30))
            story.append(Paragraph("SUPPLEMENTAL INTELLIGENCE EXHIBITS", styles['BrandedHeading1']))
            for art in artifacts:
                title = _artifact_label(art).upper()
                story.append(Paragraph(f"EXHIBIT: {title}", styles['SectionBody']))
                art_content = _as_text(art.get("content", ""))
                # Handle basic table rendering in PDF for artifacts
                if "|" in art_content and "-" in art_content:
                    # Markdown table approximation
                    rows = [r.strip() for r in art_content.split("\n") if r.strip()]
                    table_data = []
                    for row in rows:
                        if "|" in row:
                            cols_data = [Paragraph(c.strip(), styles['SectionBody']) for c in row.split("|") if c.strip()]
                            if cols_data:
                                table_data.append(cols_data)
                    
                    if table_data:
                        t_obj = Table(table_data)
                        t_obj.setStyle(TableStyle([
                            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A1A1A")),
                        ]))
                        story.append(t_obj)
                        story.append(Spacer(1, 15))
                else:
                    story.append(Paragraph(art_content.replace("\n", "<br/>"), styles['SectionBody']))
                    story.append(Spacer(1, 15))

        # --- FOOTER ---
        story.append(Spacer(1, 40))
        footer_data = [[f"KORUM-OS AUTHENTICATED INTEL NODE — {datetime.now().strftime('%Y-%m-%d %H:%M')} — PROP-RESTRICTIVE ACCESS"]]
        footer_table = Table(footer_data, colWidths=[512])
        footer_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor(ACCENT_SECONDARY)),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Courier'),
        ]))
        story.append(footer_table)

        doc.build(story, onFirstPage=_dark_page_bg, onLaterPages=_dark_page_bg)
        return filepath

class WordExporter:
    """Branded Word report following High-Fidelity Command Alpha identity."""
    
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
            'ARCHITECT':   {"bg": "2D3436", "primary": (0xA6, 0x5E, 0x46), "secondary": (0x63, 0x6E, 0x72), "text": "F2F1EF"},
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
        
        # Margins & Section Setup
        sec = doc.sections[0]
        sec.top_margin = Inches(0.5)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)
        
        # Header: Logo (Adaptive)
        is_dark_bg = theme_id != "ARCHITECT"
        logo_filename = "main korum os logo light.png" if is_dark_bg else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "main korum os logo.png")

        if os.path.exists(logo_path):
            doc.add_picture(logo_path, width=Inches(2.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()
            
        # Command Registry Table
        cmd_tab = doc.add_table(rows=2, cols=2)
        cmd_tab.style = 'Table Grid'
        cmd_tab.autofit = True
        
        for r in range(2):
            for c in range(2):
                WordExporter._shade_cell(cmd_tab.rows[r].cells[c], t['bg'])

        def _p_style(cell, text, bold=False, color=None, size=8):
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(text)
            run.font.name = 'Courier New'
            run.font.size = Pt(size)
            if bold: run.bold = True
            if color: run.font.color.rgb = color
            return run

        _p_style(cmd_tab.rows[0].cells[0], "KORUM-OS // COMMAND NODE // ALPHA", color=s_rgb)
        _p_style(cmd_tab.rows[0].cells[1], f"MISSION: {meta.get('title', 'KORUM_ALPHA').upper()}", color=s_rgb)
        _p_style(cmd_tab.rows[1].cells[0], f"WORKFLOW: {meta.get('workflow', 'INTEL').upper()}", color=s_rgb)
        _p_style(cmd_tab.rows[1].cells[1], f"SYSTEM STATUS: SECURE", color=s_rgb)
        
        doc.add_paragraph() # Spacer
        
        # Primary Directive Block
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        directive = directive_list[0] if directive_list else (meta.get("summary") or "INTEL ANALYSIS IN PROGRESS")
        
        d_tab = doc.add_table(rows=1, cols=1)
        cell = d_tab.rows[0].cells[0]
        WordExporter._shade_cell(cell, "0D0D0D")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("[PRIMARY DIRECTIVE]")
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = p_rgb
        
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run2 = p2.add_run(_as_text(directive).upper())
        run2.bold = True
        run2.font.size = Pt(14)
        run2.font.color.rgb = p_rgb
        
        p3 = cell.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run3 = p3.add_run("— ACTION REQUIRED —")
        run3.font.size = Pt(8)
        run3.font.color.rgb = s_rgb
        
        doc.add_paragraph()
        
        # Content Sections
        for sid, content in sections.items():
            h = doc.add_heading(sid.replace("_", " ").upper(), level=1)
            # Find and style run for Signal Tags
            text_block = _clean_tags(content, strip_markdown=False)
            p = doc.add_paragraph()
            
            # Simple splitter to highlight tags
            parts = re.split(r'(\[.*?\])', text_block)
            for part in parts:
                run = p.add_run(part)
                if part == "[CRITICAL]":
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0x31, 0x31)
                elif part.startswith("[") and part.endswith("]"):
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xB0, 0x20)
                
            doc.add_paragraph()

        # Exhibits
        artifacts = _report_artifacts(intelligence_object)
        if artifacts:
            doc.add_heading("SUPPLEMENTARY EXHIBITS", level=1)
            for art in artifacts:
                label = _artifact_label(art).upper()
                p = doc.add_paragraph()
                run = p.add_run(f"EXHIBIT: {label}")
                run.bold = True
                doc.add_paragraph(art.get("content", ""))
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
    def generate(o, d=None): return PDFExporter.generate(o, d)

class ResearchPaperWordExporter:
    @staticmethod
    def generate(o, d=None): return WordExporter.generate(o, d)

# --- INTERNAL HELPERS ---

def _extract_parts(o):
    """Deep extraction helper for Korum intelligence objects."""
    if not o: return {}, {}, {}, [], []
    meta = o.get("meta", {})
    sections = o.get("sections", {})
    # Handle both new 'cards' and old 'results' keys
    structured = o.get("structured", {})
    interrogations = o.get("interrogations", [])
    verifications = o.get("verifications", [])
    return meta, sections, structured, interrogations, verifications

def _report_artifacts(o):
    """Extracts docked artifacts or snippets for exhibit rendering."""
    # Check 'docked_snippets' first (passed from JS ResearchDock)
    snippets = o.get("docked_snippets")
    if snippets: return snippets
    # Fallback to research_results or data_lake
    return o.get("research_results", [])

def _artifact_label(art):
    """Returns a clean display name for an artifact."""
    return art.get("title") or art.get("label") or art.get("filename") or "UNNAMED EXHIBIT"

def _clean_tags(text, strip_markdown=False):
    """Strips Korum logic tags and optionally markdown for clean exports."""
    if not text: return ""
    # Strip KOS directive tags
    text = re.sub(r'\[\/?(?:DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]', '', text)
    if strip_markdown:
        # Simple markdown stripper
        text = re.sub(r'#+\s', '', text)
        text = re.sub(r'\*\*', '', text)
        text = re.sub(r'__', '', text)
        text = re.sub(r'`', '', text)
    return text

def _convert_mermaid_to_table(text):
    """Placeholder for eventual Mermaid-to-Grid rendering."""
    # For now, just return clean text
    return text
