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
    """Professional Intelligence Dossier — 30-Year Veteran Standard — Strat-Asymmetric Layout."""
    
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        
        # --- COMMAND PALETTE ---
        THEMES = {
            'NEON_DESERT': {"bg": "#0D1117", "accent": "#2DD4BF", "gold": "#FFB020", "text": "#D1D5DB", "dim": "#636E72"},
            'CARBON_STEEL':{"bg": "#0D0D0D", "accent": "#E2E8F0", "gold": "#94A3B8", "text": "#F1F5F9", "dim": "#4B5563"},
            'ARCHITECT':   {"bg": "#F2F1EF", "accent": "#A65E46", "gold": "#636E72", "text": "#2D3436", "dim": "#636E72"},
        }
        theme_id = meta.get("theme", "NEON_DESERT").upper()
        if theme_id not in THEMES: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        BG_PAGE, ACC_TEAL, ACC_GOLD, TXT_MAIN, TXT_DIM = t['bg'], t['accent'], t['gold'], t['text'], t['dim']

        safe_title = _safe_filename_part(meta.get('title', 'Intelligence'))
        filename = f"KORUM-OS_DOSSIER_{safe_title}_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=25, rightMargin=25)
        doc._bg_color = BG_PAGE
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('DossierTitle', parent=styles['Normal'], fontSize=34, textColor=colors.HexColor(ACC_TEAL), leading=38, fontName='Helvetica-Bold', spaceAfter=10))
        styles.add(ParagraphStyle('TacticalLabel', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor(TXT_MAIN), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('NodeID', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor(ACC_GOLD), fontName='Courier-Bold'))
        styles.add(ParagraphStyle('DossierBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor(TXT_MAIN), leading=14, fontName='Helvetica'))
        styles.add(ParagraphStyle('DirectiveTitle', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor(ACC_GOLD), alignment=1, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('DirectiveText', parent=styles['Normal'], fontSize=16, textColor=colors.HexColor(TXT_MAIN), leading=20, alignment=1, fontName='Helvetica-Bold'))

        story = []

        # 1. --- LOGO & PRIMARY TITLE (Asymmetric Start) ---
        logo_filename = "main korum os logo light.png" if theme_id != "ARCHITECT" else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=150, height=38)
            img.hAlign = 'LEFT'
            story.append(img)
            story.append(Spacer(1, 25))

        story.append(Paragraph(f"KORUM-OS -<br/>{escape(meta.get('title', 'Intelligence Briefing').upper())}", styles['DossierTitle']))
        
        # Gold Separator Line
        line = Table([[""]], colWidths=[562], rowHeights=[2], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(ACC_GOLD))])
        story.append(line)
        story.append(Spacer(1, 30))

        # 2. --- [PRIMARY DIRECTIVE] (Full-Width Tactical Break) ---
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        if directive_list:
            directive = _as_text(directive_list[0]).upper()
            d_box_data = [
                [Paragraph("[PRIMARY DIRECTIVE]", styles['DirectiveTitle'])],
                [Paragraph(f"{escape(directive)}", styles['DirectiveText'])]
            ]
            d_box = Table(d_box_data, colWidths=[520])
            d_box.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#080808")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor(ACC_GOLD)),
                ('TOPPADDING', (0,0), (-1,-1), 20),
                ('BOTTOMPADDING', (0,0), (-1,-1), 20),
            ]))
            story.append(d_box)
            story.append(Spacer(1, 40))

        # 3. --- INTELLIGENCE GRID (2-Column Asymmetric) ---
        # 140pt Left Margin for labels/node-ids
        for idx, (sid, content) in enumerate(sections.items()):
            section_title = sid.replace("_", " ").upper()
            node_id = f"KOS-NODE-{100 + idx:03d}"
            
            # High-Fidelity Content Processing
            raw_text = _as_text(content)
            tag_placeholders = {}
            critical_ph = "___SIGNAL_CRITICAL___"
            raw_text = raw_text.replace("[CRITICAL]", critical_ph)
            signal_tags = ["ACTION REQUIRED", "VERIFIED", "RISK", "WARNING", "DECISION CANDIDATE"]
            for tag in signal_tags:
                ph = f"___SIGNAL_{tag.replace(' ', '_')}___"
                raw_text = raw_text.replace(f"[{tag}]", ph)
                raw_text = raw_text.replace(f"[/{tag}]", "")
                tag_placeholders[ph] = f"<font color='{ACC_GOLD}'><b>[{tag}]</b></font>"

            bold_spans = []
            for m in re.finditer(r'\*\*(.*?)\*\*', raw_text):
                bold_spans.append((m.group(0), f"___BOLD_{len(bold_spans)}___"))
            for orig, ph in bold_spans: raw_text = raw_text.replace(orig, ph, 1)

            styled_content = escape(raw_text)
            styled_content = styled_content.replace(critical_ph, f"<font color='#FF3131'><b>[CRITICAL]</b></font>")
            for ph, st in tag_placeholders.items(): styled_content = styled_content.replace(ph, st)
            for orig, ph in bold_spans:
                styled_content = styled_content.replace(ph, f"<b>{escape(orig[2:-2])}</b>")
            styled_content = styled_content.replace("\n", "<br/>")

            # Asymmetric Row
            row_data = [
                [Paragraph(section_title, styles['TacticalLabel']), Paragraph(node_id, styles['NodeID'])],
                Paragraph(styled_content, styles['DossierBody'])
            ]
            t_row = Table([row_data], colWidths=[140, 412])
            t_row.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), idx == len(sections)-1 and 20 or 30),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(t_row)

        # 4. --- SUPPLEMENTAL EXHIBITS (Full-Width Breakouts) ---
        artifacts = _report_artifacts(intelligence_object)
        if artifacts:
            story.append(Spacer(1, 20))
            story.append(Table([[Paragraph("SUPPLEMENTAL TECHNICAL EXHIBITS", styles['TacticalLabel'])]], colWidths=[552], style=[('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor(ACC_GOLD))]))
            story.append(Spacer(1, 15))
            
            for art in artifacts:
                title = _artifact_label(art).upper()
                content = escape(_as_text(art.get("content", ""))).replace("\n", "<br/>")
                
                # Hybrid Grid-Breakout
                # Small label on left, LARGE content on Right (using almost full width)
                ex_row = [
                    [Paragraph(f"EXHIBIT: {title}", styles['NodeID']), Paragraph("MISSION_DATA", styles['NodeID'])],
                    Paragraph(content, styles['DossierBody'])
                ]
                ex_grid = Table([ex_row], colWidths=[110, 442])
                ex_grid.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 20),
                ]))
                story.append(ex_grid)

        # 5. --- FOOTER HUD ---
        story.append(Spacer(1, 40))
        footer_text = f"KORUM-OS AUTH-ALPHA // {datetime.now().strftime('%Y-%m-%d %H:%M')} // SECURE ACCESS ONLY // PAGE 01"
        footer = Table([[Paragraph(footer_text, styles['NodeID'])]], colWidths=[562])
        footer.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'RIGHT'), ('LINEABOVE', (0,0), (-1,-1), 0.5, colors.HexColor(ACC_GOLD))]))
        story.append(footer)

        doc.build(story, onFirstPage=_dark_page_bg, onLaterPages=_dark_page_bg)
        return filepath

class WordExporter:
    """Professional Asymmetric Word Report — High-Fidelity Intelligence Standard."""
    
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
        if theme_id not in THEMES: theme_id = "NEON_DESERT"
        
        t = THEMES[theme_id]
        p_rgb, s_rgb = RGBColor(*t['primary']), RGBColor(*t['secondary'])
        
        # Header: Logo
        logo_filename = "main korum os logo light.png" if theme_id != "ARCHITECT" else "main korum os logo dark.png"
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", logo_filename)
        if os.path.exists(logo_path):
            doc.add_picture(logo_path, width=Inches(2.0))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.LEFT
            doc.add_paragraph()

        # Title Section
        t_p = doc.add_paragraph()
        t_run = t_p.add_run(f"KORUM-OS // {meta.get('title', 'Intelligence Briefing').upper()}")
        t_run.bold = True
        t_run.font.size = Pt(22)
        t_run.font.color.rgb = s_rgb
        doc.add_paragraph()

        # Primary Directive Block (Tactical Break)
        directive_list = (intelligence_object.get("intelligence_tags") or {}).get("decisions", [])
        if directive_list:
            directive = _as_text(directive_list[0]).upper()
            doc.add_paragraph("-" * 80)
            d_p = doc.add_paragraph("[PRIMARY DIRECTIVE]")
            d_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            d_p.runs[0].bold = True
            d_p.runs[0].font.color.rgb = p_rgb
            
            d_main = doc.add_paragraph(escape(directive))
            d_main.alignment = WD_ALIGN_PARAGRAPH.CENTER
            d_run = d_main.runs[0]
            d_run.bold = True
            d_run.font.size = Pt(14)
            d_run.font.color.rgb = p_rgb
            doc.add_paragraph("-" * 80)
            doc.add_paragraph()

        # Content Sections (Asymmetric Grid)
        for idx, (sid, content) in enumerate(sections.items()):
            node_id = f"KOS-NODE-{100 + idx:03d}"
            # Create a 2-column invisible table
            tab = doc.add_table(rows=1, cols=2)
            tab.autofit = False
            tab.columns[0].width = Inches(1.5)
            tab.columns[1].width = Inches(4.5)
            
            # Left Metadata Cell
            l_cell = tab.rows[0].cells[0]
            lp = l_cell.paragraphs[0]
            l_run = lp.add_run(sid.replace("_", " ").upper())
            l_run.bold = True
            l_run.font.size = Pt(9)
            
            lp2 = l_cell.add_paragraph()
            id_run = lp2.add_run(node_id)
            id_run.font.name = 'Courier New'
            id_run.font.size = Pt(7)
            id_run.font.color.rgb = p_rgb
            
            # Right Content Cell
            r_cell = tab.rows[0].cells[1]
            rp = r_cell.paragraphs[0]
            # Strip tags but keep some basic bolding
            clean_text = _clean_tags(content, strip_markdown=False)
            rp.add_run(clean_text)
            
            doc.add_paragraph()

        # Footer Audit
        section = doc.sections[0]
        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_run = p.add_run(f"KORUM-OS AUTH-ALPHA // {datetime.now().strftime('%Y-%M-%d %H:%M')} // SECURE")
        f_run.font.name = 'Courier New'
        f_run.font.size = Pt(7)

        safe_title = _safe_filename_part(meta.get('title', 'Intelligence'))
        filename = f"KORUM-OS_REPORT_{safe_title}_{theme_id}_{_timestamp()}.docx"
        filepath = _output_path(filename, output_dir)
        doc.save(filepath)
        return filepath

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

