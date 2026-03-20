# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

import csv
import io
import json
import os
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from xml.sax.saxutils import escape
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- SHARED UTILS ---

def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _safe_filename_part(s):
    if not s: return "UNTITLED"
    return re.sub(r'[^\w\-]', '_', str(s))[:30]

def _output_path(filename, output_dir=None):
    if not output_dir:
        output_dir = os.path.join(os.getcwd(), "exports")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return os.path.join(output_dir, filename)

def _as_text(val):
    if val is None: return ""
    return str(val).strip()

def _extract_parts(o):
    meta = o.get("meta") or {}
    sections = o.get("sections") or {}
    structured = o.get("structured_data") or {}
    interrogations = o.get("interrogations") or []
    verifications = o.get("verifications") or []
    return meta, sections, structured, interrogations, verifications

def _artifact_label(art):
    return _as_text(art.get('title') or art.get('name') or 'ARTIFACT').upper()

def _report_artifacts(o):
    """Filter snippets for inclusion in the report."""
    apps = o.get("docked_snippets") or []
    return [a for a in apps if a.get('includeInReport') is True]

# --- PDF BRANDING CANVAS ---

def _dark_page_bg(canvas, doc):
    """Optional page painting logic (currently simple white for clarity)."""
    canvas.saveState()
    # If we wanted deep dark bg, we'd do it here. 
    # For 'Architect' theme (the user's latest image), we use white bg.
    canvas.restoreState()

# --- EXPORTERS ---

class ExecutiveMemoExporter:
    """Executive Dossier — Dashboard DNA Standard."""
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, _, _ = _extract_parts(intelligence_object)
        
        filename = f"KORUM-OS_DOSSIER_{_safe_filename_part(meta.get('title'))}_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter, 
                                leftMargin=35, rightMargin=35, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        # DNA: Color Palette
        MAIN_BLUE = "#1e3a8a" # The Executive Blue
        TEXT_DIM = "#64748b" # Light Gray
        
        # DNA: Styles - Curated for Executive Scan Patterns
        styles.add(ParagraphStyle('ExecLabel', fontSize=6.5, leading=8, textColor=colors.HexColor(TEXT_DIM), fontName='Helvetica-Bold', letterSpacing=0.5))
        styles.add(ParagraphStyle('ExecSig', fontSize=7, leading=10, textColor=colors.HexColor(TEXT_DIM), alignment=TA_RIGHT, fontName='Helvetica'))
        styles.add(ParagraphStyle('ExecTitle', fontSize=26, leading=30, textColor=colors.HexColor(MAIN_BLUE), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ExecImpact', fontSize=10, leading=14, textColor=colors.HexColor(MAIN_BLUE), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ExecBody', fontSize=8.5, leading=12, textColor=colors.HexColor("#334155"), fontName='Helvetica'))
        styles.add(ParagraphStyle('ExecAudit', fontSize=7, leading=9, textColor=colors.HexColor(TEXT_DIM), fontName='Helvetica'))
        styles.add(ParagraphStyle('StatBig', fontSize=20, leading=24, textColor=colors.HexColor(MAIN_BLUE), fontName='Helvetica-Bold', alignment=TA_CENTER))
        styles.add(ParagraphStyle('StatCaption', fontSize=6.5, leading=8, textColor=colors.HexColor(TEXT_DIM), fontName='Helvetica-Bold', alignment=TA_CENTER, letterSpacing=0.5))
        styles.add(ParagraphStyle('PullQuoteInline', fontSize=8, leading=11, textColor=colors.white, fontName='Helvetica-Oblique'))
        styles.add(ParagraphStyle('Cons', fontSize=9, leading=13, textColor=colors.white, fontName='Helvetica-Oblique'))
        styles.add(ParagraphStyle('ConsScore', fontSize=22, leading=24, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_RIGHT))

        doc._session_id = _as_text(meta.get('session_id') or meta.get('id') or 'KO-INT-9999').upper()
        contributors = intelligence_object.get("council_contributors") or []
        divergence = intelligence_object.get("divergence_analysis") or {}
        mission_ctx = intelligence_object.get("_mission_context") or {}
        client_name = _as_text(mission_ctx.get("client", "")).strip() or "DECISION COMMANDER ALPHA"
        artifacts = _report_artifacts(intelligence_object)
        card_results = intelligence_object.get("_card_results") or {}

        story = []

        # 1. --- STRATEGIC HEADER ---
        workflow_label = _as_text(meta.get('workflow')).upper() or 'STRATEGIC_INTEL'
        doc_title = _as_text(meta.get('title')).upper() or 'COMMAND_NODE'
        
        # Header Metadata (Top Line)
        top_meta = [
            [[Paragraph(f"INTELLIGENCE DOSSIER &middot; CONFIDENTIAL &middot; {workflow_label}", styles['ExecLabel'])], 
             [Paragraph(f"<b>KORUM-OS</b><br/>{client_name}<br/>SESSION {doc._session_id}<br/>COUNCIL: {len(contributors)} AGENTS", styles['ExecSig'])]]
        ]
        top_tab = Table(top_meta, colWidths=[360, 180])
        top_tab.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 12)]))
        story.append(top_tab)
        
        # Title
        story.append(Paragraph(doc_title, styles['ExecTitle']))
        story.append(Spacer(1, 15))
        
        # The Blue Underline (Thick Command Line)
        story.append(Table([[[Paragraph("", styles['ExecBody'])]]], colWidths=[540], rowHeights=[2.5], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(MAIN_BLUE))]))
        story.append(Spacer(1, 30))

        # 2. --- EXECUTIVE SUMMARY & TOP VISUAL ---
        summary_text = meta.get("summary") or "Intel synthesis required."
        summary_p = Paragraph(f"<b>{escape(summary_text)}</b>", styles['ExecImpact'])
        
        top_visual = None
        for art in artifacts:
            if art.get('type') in ('donut', 'pie') or 'REVENUE' in _artifact_label(art):
                top_visual = art
                artifacts.remove(art)
                break
        
        sidebar_content = [""]
        if top_visual:
            sidebar_content = [
                Paragraph(_artifact_label(top_visual), styles['StatCaption']),
                Spacer(1, 5),
                Paragraph(escape(_as_text(top_visual.get('content',''))[:150]).replace("\n","<br/>"), styles['ExecAudit'])
            ]
            
        summary_tab = Table([[[summary_p], sidebar_content]], colWidths=[380, 160])
        summary_tab.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (1,0), (1,0), 20)]))
        story.append(summary_tab)
        story.append(Spacer(1, 30))

        # 3. --- KPI STRIP ---
        key_metrics = structured.get("key_metrics") or []
        if key_metrics:
            stat_cells = []
            for km in key_metrics[:3]:
                val = _as_text(km.get('value', '—'))
                lab = _as_text(km.get('metric', '')).upper()
                stat_cells.append([[Paragraph(val, styles['StatBig'])], [Paragraph(lab, styles['StatCaption'])]])
            
            while len(stat_cells) < 3: stat_cells.append([[""], [""]])
            s_tab_data = [[Table(cell, colWidths=[178], style=[('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]) for cell in stat_cells]]
            s_tab = Table(s_tab_data, colWidths=[180, 180, 180], style=[
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                ('TOPPADDING', (0,0), (-1,-1), 12),
                ('BOTTOMPADDING', (0,0), (-1,-1), 12),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ])
            story.append(s_tab)
            story.append(Spacer(1, 30))

        # 4. --- DNA: INTELLIGENCE NODES (SECTIONS) ---
        section_items = list(sections.items())
        for idx, (sid, content) in enumerate(section_items):
            sec_title = sid.replace("_", " ").upper()
            prov_name = "KORUM"
            if idx < len(contributors):
                prov_name = _as_text(contributors[idx].get('provider', '')).upper()
            
            node_id = f"{sec_title} &middot; NODE {idx+1:02d} &mdash; {prov_name}"
            
            styled_body = escape(_as_text(content)).replace("\n", "<br/>")
            text_p = Paragraph(styled_body, styles['ExecBody'])
            
            # Match sidebar artifact
            local_visual = None
            for art in artifacts:
                label = _artifact_label(art)
                if sec_title in label or prov_name in label:
                    local_visual = art
                    artifacts.remove(art)
                    break
            
            # Try pull-quote if no visual
            local_quote = None
            if not local_visual:
                prov_key = prov_name.lower()
                prov_data = card_results.get(prov_key) or {}
                claims = prov_data.get("verified_claims") or []
                if claims: local_quote = claims[0]
            
            right_col = [""]
            if local_visual:
                right_col = [
                    Paragraph(_artifact_label(local_visual), styles['StatCaption']),
                    Spacer(1, 4),
                    Paragraph(escape(_as_text(local_visual.get('content',''))[:150]).replace("\n","<br/>"), styles['ExecAudit'])
                ]
            elif local_quote:
                q_text = escape(_as_text(local_quote.get('claim','')))
                q_attrib = f"&mdash; {prov_name}"
                right_col = [
                    Table([[[Paragraph("")], [Paragraph(f"<i>&ldquo;{q_text}&rdquo;</i><br/><font size='7' color='#64748b'>{q_attrib}</font>", styles['PullQuoteInline'])]]], colWidths=[4, 146], style=[
                        ('BACKGROUND', (0,0), (0,0), colors.HexColor(MAIN_BLUE)),
                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                        ('RIGHTPADDING', (0,0), (-1,-1), 0),
                        ('LEFTPADDING', (1,0), (1,0), 10),
                    ])
                ]
            
            story.append(Paragraph(node_id, styles['ExecLabel']))
            story.append(Spacer(1, 6))
            story.append(Table([[[Paragraph("", styles['ExecBody'])]]], colWidths=[540], rowHeights=[1], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E2E8F0"))]))
            story.append(Spacer(1, 10))
            
            sec_tab = Table([[[text_p], right_col]], colWidths=[380, 160])
            sec_tab.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (1,0), (1,0), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(sec_tab)
            story.append(Spacer(1, 20))

        # 5. --- CONSENSUS FOOTER ---
        truth_raw = meta.get("composite_truth_score")
        truth_int = int(float(truth_raw if truth_raw is not None else 0.85) * 100)
        consensus_summary = _as_text(divergence.get("divergence_summary", "")) or "Council reached operational consensus."
        cons_data = [
            [[Paragraph("COUNCIL CONSENSUS", styles['ExecLabel'])], [""]],
            [[Paragraph(f"<i>{escape(consensus_summary)}</i>", styles['Cons'])], 
             [Paragraph(f"<b>{truth_int}</b><br/><font size='7'>TRUTH SCORE / 100</font>", styles['ConsScore'])]]
        ]
        cons_tab = Table(cons_data, colWidths=[410, 130])
        cons_tab.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(MAIN_BLUE)),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('LEFTPADDING', (0,0), (-1,-1), 15),
            ('RIGHTPADDING', (0,0), (-1,-1), 15),
            ('SPAN', (0,0), (1,0)),
        ]))
        story.append(cons_tab)

        try:
            doc.build(story, onFirstPage=_dark_page_bg, onLaterPages=_dark_page_bg)
        except Exception as e:
            raise RuntimeError(f"ReportLab Build Error: {str(e)}") from e
            
        return filepath

class WordExporter:
    """Executive-Grade Word Report — Premium Dashboard Standard."""
    @staticmethod
    def _hex_to_rgb(hex_str):
        if hex_str.startswith('#'): hex_str = hex_str[1:]
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _set_cell_background(cell, fill):
        """Helper to set cell shading in python-docx."""
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill}"/>')
        cell._tc.get_or_add_tcPr().append(shading_elm)

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, _, _ = _extract_parts(intelligence_object)
        doc = Document()
        
        # DNA: SHARED THEME
        MAIN_BLUE = "1e3a8a" 
        DIM_GRAY = "64748b"
        s_rgb = RGBColor(*WordExporter._hex_to_rgb(MAIN_BLUE))

        mission_ctx = intelligence_object.get("_mission_context") or {}
        client_name = _as_text(mission_ctx.get("client", "")).strip() or "DECISION COMMANDER ALPHA"
        artifacts = _report_artifacts(intelligence_object)
        card_results = intelligence_object.get("_card_results") or {}
        contributors = intelligence_object.get("council_contributors") or []
        divergence = intelligence_object.get("divergence_analysis") or {}

        # 1. --- PREMIUM HEADER ---
        h_tab = doc.add_table(rows=1, cols=2)
        h_tab.columns[0].width = Inches(3.8)
        h_tab.columns[1].width = Inches(2.2)
        
        l_p = h_tab.rows[0].cells[0].paragraphs[0]
        l_run = l_p.add_run(f"INTELLIGENCE DOSSIER  &middot;  CONFIDENTIAL  &middot;  {_as_text(meta.get('workflow')).upper() or 'STRATEGIC_INTEL'}")
        l_run.font.size = Pt(6.5)
        l_run.font.bold = True
        l_run.font.color.rgb = RGBColor.from_string(DIM_GRAY)
        
        r_p = h_tab.rows[0].cells[1].paragraphs[0]
        r_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_run = r_p.add_run(f"KORUM-OS\n{client_name}\nSESSION {_as_text(meta.get('session_id') or 'KO-INT-9999').upper()}\nCOUNCIL: {len(contributors)} AGENTS")
        r_run.font.size = Pt(7)
        r_run.font.color.rgb = RGBColor.from_string(DIM_GRAY)
        
        # Title
        t_p = doc.add_paragraph()
        t_run = t_p.add_run(_as_text(meta.get('title') or 'COMMAND_NODE').upper())
        t_run.bold = True
        t_run.font.size = Pt(22)
        t_run.font.color.rgb = s_rgb
        
        # Thick Blue Rule (Executive Baseline)
        u_tab = doc.add_table(rows=1, cols=1)
        WordExporter._set_cell_background(u_tab.rows[0].cells[0], MAIN_BLUE)
        u_tab.rows[0].height = Inches(0.05)
        
        doc.add_paragraph() # Spacer

        # 2. --- DASHBOARD SUMMARY ---
        summary_text = meta.get("summary") or "Intel synthesis required."
        sum_tab = doc.add_table(rows=1, cols=2)
        sum_tab.columns[0].width = Inches(4.5)
        sum_tab.columns[1].width = Inches(2.0)
        
        s_cell = sum_tab.rows[0].cells[0]
        s_p = s_cell.paragraphs[0]
        s_run = s_p.add_run(summary_text)
        s_run.bold = True
        s_run.font.size = Pt(11)
        s_run.font.color.rgb = s_rgb
        
        doc.add_paragraph()

        # 3. --- KPI STRIP ---
        key_metrics = structured.get("key_metrics") or []
        if key_metrics:
            kpi_tab = doc.add_table(rows=2, cols=min(3, len(key_metrics)))
            for i, km in enumerate(key_metrics[:3]):
                # Value
                v_p = kpi_tab.rows[0].cells[i].paragraphs[0]
                v_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                v_run = v_p.add_run(_as_text(km.get('value', '')))
                v_run.bold = True
                v_run.font.size = Pt(18)
                v_run.font.color.rgb = s_rgb
                # Metric
                l_p = kpi_tab.rows[1].cells[i].paragraphs[0]
                l_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                l_run = l_p.add_run(_as_text(km.get('metric', '')).upper())
                l_run.font.size = Pt(7)
                l_run.font.color.rgb = RGBColor.from_string(DIM_GRAY)
            doc.add_paragraph()

        # 4. --- INTELLIGENCE NODES ---
        section_items = list(sections.items())
        for idx, (sid, content) in enumerate(section_items):
            sec_title = sid.replace("_", " ").upper()
            prov_name = "KORUM"
            if idx < len(contributors):
                prov_name = _as_text(contributors[idx].get('provider', '')).upper()

            # Node Label
            n_p = doc.add_paragraph()
            n_run = n_p.add_run(f"{sec_title} · NODE {idx+1:02d} — {prov_name}")
            n_run.font.size = Pt(7)
            n_run.font.color.rgb = RGBColor.from_string(DIM_GRAY)
            
            # Sub-table Layout
            n_tab = doc.add_table(rows=1, cols=2)
            n_tab.columns[0].width = Inches(4.5)
            n_tab.columns[1].width = Inches(2.0)
            
            # Left: Main Text
            n_tab.rows[0].cells[0].add_paragraph(_as_text(content))
            
            # Right: Sidebar Shaded
            r_cell = n_tab.rows[0].cells[1]
            WordExporter._set_cell_background(r_cell, "F8FAFC")
            
            # Match artifact
            local_visual = None
            for art in artifacts:
                label = _artifact_label(art)
                if sec_title in label or prov_name in label:
                    local_visual = art
                    artifacts.remove(art)
                    break
            
            if local_visual:
                r_p = r_cell.paragraphs[0]
                r_p.add_run(_artifact_label(local_visual)).bold = True
                r_p.add_run("\n")
                r_p.add_run(_as_text(local_visual.get('content',''))[:150]).font.size = Pt(7)
            else:
                prov_key = prov_name.lower()
                prov_data = card_results.get(prov_key) or {}
                claims = prov_data.get("verified_claims") or []
                if claims:
                    q_p = r_cell.paragraphs[0]
                    q_p.add_run(f"\"{_as_text(claims[0].get('claim',''))}\"").italic = True
                    q_p.add_run(f"\n— {prov_name}").font.size = Pt(7)
            
            doc.add_paragraph()

        # 5. --- CONSENSUS FOOTER ---
        truth_int = int(float(meta.get("composite_truth_score") or 0.85) * 100)
        c_p = doc.add_paragraph()
        c_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c_run = c_p.add_run(f"COUNCIL CONSENSUS: {truth_int}/100 TRUTH SCORE")
        c_run.bold = True
        c_run.font.color.rgb = RGBColor(255, 255, 255)
        
        filename = f"KORUM-OS_DOSSIER_{_safe_filename_part(meta.get('title'))}_{_timestamp()}.docx"
        filepath = _output_path(filename, output_dir)
        doc.save(filepath)
        return filepath

class JSONExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        filename = f"KORUM-OS_DUMP_{_timestamp()}.json"
        filepath = _output_path(filename, output_dir)
        with open(filepath, 'w') as f:
            json.dump(intelligence_object, f, indent=4)
        return filepath

class CSVExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        filename = f"KORUM-OS_EXPORT_{_timestamp()}.csv"
        filepath = _output_path(filename, output_dir)
        meta, sections, _, _, _ = _extract_parts(intelligence_object)
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Value"])
            writer.writerow(["Title", meta.get('title')])
            writer.writerow(["Summary", meta.get('summary')])
            for k, v in sections.items():
                writer.writerow([k, v])
        return filepath

class TextExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, _, _ = _extract_parts(intelligence_object)
        lines = [f"KORUM-OS REPORT: {meta.get('title','').upper()}", "="*40, ""]
        lines.append(f"SUMMARY: {meta.get('summary','')}\n")
        for k, v in sections.items():
            lines.append(f"SECTION: {k.upper()}\n{v}\n")
        filename = f"KORUM-OS_BRIEF_{_timestamp()}.txt"
        filepath = _output_path(filename, output_dir)
        with open(filepath, 'w') as f:
            f.write("\n".join(lines))
        return filepath

class ResearchPaperWordExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        return WordExporter.generate(intelligence_object, output_dir)

# Aliases for unified routing
PDFExporter = ExecutiveMemoExporter
MarkdownExporter = TextExporter # Fallback
PPTXExporter = TextExporter     # Placeholder
ResearchPaperExporter = ExecutiveMemoExporter
ExcelExporter = CSVExporter      # Fallback
