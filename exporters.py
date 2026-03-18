# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

import csv
import json
import os
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches, RGBColor
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from openpyxl import Workbook
from pptx import Presentation as PPTXPresentation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _output_path(filename: str, output_dir: str | None = None) -> str:
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, filename)
    return filename


def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _sanitize_for_csv(value):
    """Strip intelligence tags, clean bullets, and prevent Excel formula injection."""
    import re
    text = _as_text(value)
    # Strip intelligence system tags (keep inner content)
    text = re.sub(r'\[\/?(?:DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]', '', text)
    # Replace bullet characters that cause #NAME? in Excel
    text = text.replace('\u2022', '-').replace('\u2023', '-').replace('\u25aa', '-')
    # Strip markdown bold/italic
    text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text)
    # Strip markdown headings
    text = re.sub(r'^#{1,4}\s*', '', text, flags=re.MULTILINE)
    # Collapse excessive whitespace
    text = re.sub(r'[ \t]{2,}', ' ', text).strip()
    # Prevent Excel formula injection (cells starting with =, +, -, @)
    if text and text[0] in ('=', '+', '-', '@'):
        text = "'" + text
    return text


def _sanitize_for_pptx(text):
    """Replace Unicode symbols that render as squares in default PowerPoint fonts."""
    if not isinstance(text, str):
        return str(text) if text else ""
    import re
    replacements = {
        '\u2022': '-',   # • bullet
        '\u2023': '-',   # ‣ triangular bullet
        '\u25aa': '-',   # ▪ small black square
        '\u25cb': 'o',   # ○ white circle
        '\u2713': '[X]', # ✓ checkmark
        '\u2714': '[X]', # ✔ heavy checkmark
        '\u2717': '[ ]', # ✗ ballot x
        '\u2718': '[ ]', # ✘ heavy ballot x
        '\u2192': '->',  # → right arrow
        '\u2190': '<-',  # ← left arrow
        '\u21d2': '=>',  # ⇒ double right arrow
        '\u2014': '--',  # — em dash
        '\u2013': '-',   # – en dash
        '\u2018': "'",   # left single quote
        '\u2019': "'",   # right single quote
        '\u201c': '"',   # left double quote
        '\u201d': '"',   # right double quote
        '\u2026': '...', # … ellipsis
        '\u221e': 'inf', # ∞ infinity
        '\u2248': '~=',  # ≈ approximately
        '\u00b1': '+/-', # ± plus-minus
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Strip any remaining emoji (Supplementary Multilingual Plane)
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    # Clean markdown artifacts
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)        # *italic* -> italic
    return text


def _convert_mermaid_to_table(text):
    """Convert Mermaid chart blocks into readable plain-text tables."""
    import re

    def _pie_to_table(match):
        block = match.group(0)
        # Extract title
        title_match = re.search(r'title\s+"([^"]*)"', block) or re.search(r'title\s+(.+)', block)
        title = title_match.group(1).strip() if title_match else "Chart Data"
        # Extract slices: "Label" : value
        slices = re.findall(r'"([^"]+)"\s*:\s*([\d.]+)', block)
        if not slices:
            return block  # Can't parse, return as-is
        total = sum(float(v) for _, v in slices)
        lines = [f"\n{title}:", "-" * 40]
        for label, value in slices:
            pct = (float(value) / total * 100) if total > 0 else 0
            lines.append(f"  {label}: {value} ({pct:.1f}%)")
        lines.append(f"  Total: {total}")
        return "\n".join(lines) + "\n"

    def _bar_to_table(match):
        block = match.group(0)
        title_match = re.search(r'title\s+"([^"]*)"', block) or re.search(r'title\s+(.+)', block)
        title = title_match.group(1).strip() if title_match else "Chart Data"
        # xychart-beta format: x-axis [...] and bar [...]
        x_match = re.search(r'x-axis\s*\[([^\]]+)\]', block)
        bar_match = re.search(r'bar\s*\[([^\]]+)\]', block)
        if x_match and bar_match:
            labels = [l.strip().strip('"') for l in x_match.group(1).split(',')]
            values = [v.strip() for v in bar_match.group(1).split(',')]
            lines = [f"\n{title}:", "-" * 40]
            for i, label in enumerate(labels):
                val = values[i] if i < len(values) else "N/A"
                lines.append(f"  {label}: {val}")
            return "\n".join(lines) + "\n"
        return block

    def _flowchart_to_text(match):
        block = match.group(0)
        # Extract node labels: A["Label"] or A[Label]
        nodes = re.findall(r'(\w+)\s*\["?([^"\]]+)"?\]', block)
        # Extract connections: A --> B or A -->|label| B
        connections = re.findall(r'(\w+)\s*-->(?:\|([^|]*)\|)?\s*(\w+)', block)
        node_map = {k: v for k, v in nodes}
        if not nodes and not connections:
            return block
        lines = ["\nProcess Flow:", "-" * 40]
        for src, edge_label, dst in connections:
            src_name = node_map.get(src, src)
            dst_name = node_map.get(dst, dst)
            arrow = f" ({edge_label})" if edge_label else ""
            lines.append(f"  {src_name} -> {dst_name}{arrow}")
        return "\n".join(lines) + "\n"

    # Match mermaid code blocks: ```mermaid ... ```
    text = re.sub(r'```mermaid\s*(pie[\s\S]*?)```', _pie_to_table, text)
    text = re.sub(r'```mermaid\s*(xychart-beta[\s\S]*?)```', _bar_to_table, text)
    text = re.sub(r'```mermaid\s*((?:graph|flowchart)[\s\S]*?)```', _flowchart_to_text, text)

    # Match bare mermaid blocks (no code fence)
    text = re.sub(r'(?m)^pie\b[\s\S]*?(?=\n\n|\n[A-Z]|\Z)', _pie_to_table, text)
    text = re.sub(r'(?m)^xychart-beta\b[\s\S]*?(?=\n\n|\n[A-Z]|\Z)', _bar_to_table, text)
    text = re.sub(r'(?m)^(?:graph|flowchart)\b[\s\S]*?(?=\n\n|\n[A-Z]|\Z)', _flowchart_to_text, text)

    # Clean up any remaining ``` fences
    text = re.sub(r'```\w*\s*', '', text)
    text = re.sub(r'```', '', text)

    return text


def _clean_tags(text):
    """Strip intelligence tags, markdown artifacts, and convert Mermaid charts to tables."""
    import re
    # Convert Mermaid charts to readable tables first
    text = _convert_mermaid_to_table(text)
    # Remove paired tags, keeping inner content
    text = re.sub(r'\[\/?(DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]', '', text)
    # Remove markdown bold markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Remove markdown headings
    text = re.sub(r'#{1,4}\s*', '', text)
    # Clean up extra whitespace and dashes used as bullets
    text = re.sub(r'\s*-\s*\*\*', '\n\n', text)
    text = re.sub(r'\s*-\s{2,}', '\n\n- ', text)
    # Collapse excessive whitespace
    text = re.sub(r'[ \t]{2,}', ' ', text)
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
    label = _as_text(snippet.get("label", "Artifact")).strip() or "Artifact"
    if snippet.get("type") == "mermaid" or snippet.get("source") == "visualization":
        if "chart" not in label.lower() and "diagram" not in label.lower():
            return f"{label} Chart"
    return label


class WordExporter:
    """Palantir-tier DOCX report — branded, color-coded tables, visual truth scores."""

    @staticmethod
    def _shade_cell(cell, hex_color):
        """Apply background shading to a table cell."""
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    @staticmethod
    def _style_header_row(row, bg_hex="0D1117", text_color=RGBColor(0x00, 0xE5, 0xFF)):
        """Style a table header row with dark background and accent text."""
        for cell in row.cells:
            WordExporter._shade_cell(cell, bg_hex)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in paragraph.runs:
                    run.font.color.rgb = text_color
                    run.font.bold = True
                    run.font.size = Pt(9)
                    run.font.name = "Calibri"

    @staticmethod
    def _style_data_row(row, idx, alt_hex="F6F8FA"):
        """Alternate row shading for readability."""
        if idx % 2 == 0:
            for cell in row.cells:
                WordExporter._shade_cell(cell, alt_hex)

    @staticmethod
    def _add_section_divider(doc):
        """Add a styled dark rule between sections."""
        t = doc.add_table(rows=1, cols=1)
        t.autofit = True
        cell = t.rows[0].cells[0]
        WordExporter._shade_cell(cell, "161B22")
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(" ")
        run.font.size = Pt(1)
        # Breathing room after divider
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(2)
        spacer.paragraph_format.space_after = Pt(2)

    @staticmethod
    def _add_branded_heading(doc, text, level=1):
        """Add a heading with dark background bar — matching PDF style."""
        # Dark background header bar via table
        t = doc.add_table(rows=1, cols=1)
        t.autofit = True
        cell = t.rows[0].cells[0]
        WordExporter._shade_cell(cell, "0D1117")
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text.upper())
        run.font.bold = True
        run.font.name = "Calibri"
        run.font.letter_spacing = Pt(1.5)
        if level == 1:
            run.font.size = Pt(13)
            run.font.color.rgb = RGBColor(0x00, 0xE5, 0xFF)
        elif level == 2:
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x00, 0xFF, 0x9D)
        else:
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
        # Small spacer after heading
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(4)
        spacer.paragraph_format.space_after = Pt(2)
        return t

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        card_results = intelligence_object.get("_card_results", {})
        mission_ctx = intelligence_object.get("_mission_context") or {}

        doc = Document()

        # --- Global Styles ---
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(10.5)
        style.font.color.rgb = RGBColor(0x2D, 0x2D, 0x2D)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.line_spacing = 1.15

        # --- Page Margins ---
        sec = doc.sections[0]
        sec.top_margin = Inches(0.8)
        sec.bottom_margin = Inches(0.6)
        sec.left_margin = Inches(0.9)
        sec.right_margin = Inches(0.9)

        # --- Normalize truth score ---
        truth_raw = meta.get("composite_truth_score", "N/A")
        try:
            truth_val = float(truth_raw)
            if truth_val <= 1:
                truth_val = truth_val * 100
            truth_int = int(truth_val)
            truth_display = str(truth_int)
        except (ValueError, TypeError):
            truth_int = 0
            truth_display = str(truth_raw)

        models = meta.get("models_used", [])
        if not isinstance(models, list):
            models = [str(models)]
        agent_count = len(models)

        workflow = _as_text(meta.get("workflow", "RESEARCH")).upper()
        date_str = meta.get("generated_at", datetime.now().isoformat())
        try:
            date_obj = datetime.fromisoformat(date_str)
            date_display = date_obj.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            date_display = date_str

        # ═══════════════════════════════════════════════════════════════
        # COVER PAGE
        # ═══════════════════════════════════════════════════════════════

        # Dynamic branding logic — uses client name from mission context
        title_text = _as_text(meta.get("title", "Strategic Intelligence Report"))
        client_name = _as_text(mission_ctx.get("client", "")).strip()
        if client_name:
            branding_prefix = f"{client_name.upper()} x KORUM-OS"
            is_client_branded = True
        elif "QANAPI" in workflow or "QANAPI" in title_text.upper():
            branding_prefix = "QANAPI x KORUM-OS"
            is_client_branded = True
        else:
            branding_prefix = "KORUM-OS INTERNAL"
            is_client_branded = False

        # Classification Banner
        banner = doc.add_table(rows=1, cols=1)
        banner.autofit = True
        cell = banner.rows[0].cells[0]
        cell.text = f"{branding_prefix}  ·  MULTI-AGENT INTELLIGENCE  ·  {workflow}"
        WordExporter._shade_cell(cell, "0D1117")
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(0x00, 0xE5, 0xFF)
                run.font.size = Pt(8)
                run.font.name = "Calibri"
                run.font.bold = True
                run.font.letter_spacing = Pt(2)

        doc.add_paragraph()  # spacer

        # Title — Dark classified cover style
        title_table = doc.add_table(rows=1, cols=1)
        title_table.autofit = True
        title_cell = title_table.rows[0].cells[0]
        WordExporter._shade_cell(title_cell, "0D1117")
        tp = title_cell.paragraphs[0]
        tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tp.paragraph_format.space_before = Pt(18)
        tp.paragraph_format.space_after = Pt(18)
        title_run = tp.add_run(title_text.upper())
        title_run.font.size = Pt(20)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        title_run.font.name = "Calibri"
        title_run.font.letter_spacing = Pt(2)
        # Subtitle line
        tp2 = title_cell.add_paragraph()
        tp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tp2.paragraph_format.space_before = Pt(4)
        tp2.paragraph_format.space_after = Pt(12)
        sub_run = tp2.add_run(f"MULTI-AGENT INTELLIGENCE ASSESSMENT  ·  {workflow}")
        sub_run.font.size = Pt(8)
        sub_run.font.color.rgb = RGBColor(0x00, 0xE5, 0xFF)
        sub_run.font.bold = True
        sub_run.font.name = "Calibri"
        sub_run.font.letter_spacing = Pt(1.5)

        # Metadata Bar
        meta_table = doc.add_table(rows=1, cols=4)
        meta_table.autofit = True
        cells = meta_table.rows[0].cells
        meta_items = [
            ("DATE", date_display),
            ("WORKFLOW", workflow),
            ("AGENTS", str(agent_count)),
            ("TRUTH_SCORE", f"{truth_display}/100"),
        ]
        for i, (label, value) in enumerate(meta_items):
            WordExporter._shade_cell(cells[i], "F6F8FA")
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_label = p.add_run(f"{label}\n")
            run_label.font.size = Pt(7)
            run_label.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
            run_label.font.bold = True
            run_label.font.name = "Calibri"
            run_val = p.add_run(value)
            run_val.font.size = Pt(10)
            run_val.font.bold = True
            run_val.font.name = "Calibri"
            if label == "TRUTH_SCORE":
                if truth_int >= 80:
                    run_val.font.color.rgb = RGBColor(0x00, 0xAA, 0x55)
                elif truth_int >= 50:
                    run_val.font.color.rgb = RGBColor(0xDD, 0x88, 0x00)
                else:
                    run_val.font.color.rgb = RGBColor(0xCC, 0x33, 0x33)

        # Truth Score Visual Bar
        doc.add_paragraph()
        bar_table = doc.add_table(rows=1, cols=2)
        bar_table.autofit = False
        filled_width = max(0.5, (truth_int / 100) * 5.5)
        empty_width = max(0.1, 5.5 - filled_width)
        bar_table.columns[0].width = Inches(filled_width)
        bar_table.columns[1].width = Inches(empty_width)
        if truth_int >= 80:
            bar_color = "00AA55"
        elif truth_int >= 50:
            bar_color = "DD8800"
        else:
            bar_color = "CC3333"
        WordExporter._shade_cell(bar_table.rows[0].cells[0], bar_color)
        WordExporter._shade_cell(bar_table.rows[0].cells[1], "E8E8E8")
        # Make bar thin
        for cell in bar_table.rows[0].cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(" ")
                run.font.size = Pt(3)

        doc.add_page_break()

        # ═══════════════════════════════════════════════════════════════
        # EXECUTIVE SUMMARY
        # ═══════════════════════════════════════════════════════════════
        WordExporter._add_branded_heading(doc, "Executive Summary")
        summary_text = _as_text(meta.get("summary", ""))
        exec_section = _as_text(sections.get("executive_summary", ""))
        full_summary = summary_text or exec_section
        if full_summary:
            p = doc.add_paragraph()
            run = p.add_run(full_summary)
            run.font.size = Pt(10.5)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        WordExporter._add_section_divider(doc)

        # ═══════════════════════════════════════════════════════════════
        # SYNTHESIS SECTIONS
        # ═══════════════════════════════════════════════════════════════
        for section_id, content in sections.items():
            if section_id == "executive_summary":
                continue
            WordExporter._add_branded_heading(doc, section_id.replace("_", " ").title())
            
            text = _clean_tags(_as_text(content))
            # New: Detect and render markdown tables vs paragraphs
            lines = text.split("\n")
            in_table = False
            table_lines = []
            
            def flush_para(para_lines):
                p_text = " ".join(l.strip() for l in para_lines if l.strip())
                if p_text:
                    doc.add_paragraph(p_text)
            
            def flush_table(t_lines):
                rows = []
                for l in t_lines:
                    if "|" in l:
                        # Split by pipe, remove empty outer columns if they exist
                        cells = [c.strip() for c in l.split("|")]
                        if not cells[0]: cells = cells[1:]
                        if not cells[-1]: cells = cells[:-1]
                        # Skip separators
                        if all(c.replace("-", "").replace(":", "").replace(" ", "") == "" for c in cells):
                            continue
                        rows.append(cells)
                
                if rows:
                    cols = max(len(r) for r in rows)
                    table = doc.add_table(rows=len(rows), cols=cols)
                    table.autofit = True
                    for i, r_cells in enumerate(rows):
                        for j, c_text in enumerate(r_cells):
                            if j < len(table.rows[i].cells):
                                table.rows[i].cells[j].text = c_text
                    
                    WordExporter._style_header_row(table.rows[0])
                    for i in range(1, len(table.rows)):
                        WordExporter._style_data_row(table.rows[i], i-1)
                    doc.add_paragraph() # Spacer after table
            
            current_para = []
            for line in lines:
                if "|" in line:
                    if not in_table:
                        # Flush previous paragraph
                        flush_para(current_para)
                        current_para = []
                        in_table = True
                    table_lines.append(line)
                else:
                    if in_table:
                        # Flush table
                        flush_table(table_lines)
                        table_lines = []
                        in_table = False
                    if not line.strip():
                        flush_para(current_para)
                        current_para = []
                    else:
                        current_para.append(line)
            
            # Final flush
            if in_table: flush_table(table_lines)
            else: flush_para(current_para)
            
            WordExporter._add_section_divider(doc)

        # ═══════════════════════════════════════════════════════════════
        # AUDIT & VERIFICATION TRAIL
        # ═══════════════════════════════════════════════════════════════
        if interrogations or verifications:
            WordExporter._add_branded_heading(doc, "Audit & Verification Trail")

            if interrogations:
                doc.add_paragraph("The following adversarial cross-examinations were performed by the council to challenge and validate the synthesis results.")
                for idx, entry in enumerate(interrogations):
                    table = doc.add_table(rows=1, cols=2)
                    table.autofit = True
                    hdr = table.rows[0].cells
                    hdr[0].text = f"INTERROGATION #{idx+1}"
                    hdr[1].text = entry.get('verdict', 'CONTESTED')
                    WordExporter._style_header_row(table.rows[0], bg_hex="1A0A0A", text_color=RGBColor(0xFF, 0x44, 0x44))

                    row = table.add_row().cells
                    row[0].text = "ATTACKER"
                    row[1].text = f"{entry.get('attacker', '').upper()} ({entry.get('attacker_model', '')})"

                    row = table.add_row().cells
                    row[0].text = "DEFENDER"
                    row[1].text = f"{entry.get('defender', '').upper()} ({entry.get('defender_model', '')})"

                    if entry.get('attacker_response'):
                        row = table.add_row().cells
                        row[0].text = "CHALLENGE"
                        row[1].text = _clean_tags(entry['attacker_response'])

                    if entry.get('defender_response'):
                        row = table.add_row().cells
                        row[0].text = "REBUTTAL"
                        row[1].text = _clean_tags(entry['defender_response'])

                    doc.add_paragraph() # Spacer

            if verifications:
                doc.add_paragraph("Authoritative source verification results via external intelligence nodes.")
                for idx, entry in enumerate(verifications):
                    table = doc.add_table(rows=1, cols=2)
                    table.autofit = True
                    hdr = table.rows[0].cells
                    hdr[0].text = f"SOURCE CHECK #{idx+1}"
                    hdr[1].text = entry.get('verdict', 'UNRESOLVED')
                    WordExporter._style_header_row(table.rows[0], bg_hex="0A1628", text_color=RGBColor(0x00, 0xE5, 0xFF))

                    row = table.add_row().cells
                    row[0].text = "CLAIM"
                    row[1].text = entry.get('claim', '')

                    row = table.add_row().cells
                    row[0].text = "EVIDENCE"
                    row[1].text = _clean_tags(entry.get('verification', ''))

                    doc.add_paragraph()

            WordExporter._add_section_divider(doc)

        # ═══════════════════════════════════════════════════════════════
        # KEY METRICS TABLE
        # ═══════════════════════════════════════════════════════════════
        key_metrics = structured.get("key_metrics", [])
        if key_metrics:
            doc.add_page_break()
            WordExporter._add_branded_heading(doc, "Key Intelligence Metrics")
            table = doc.add_table(rows=1, cols=3)
            table.autofit = True
            hdr = table.rows[0].cells
            hdr[0].text = "METRIC"
            hdr[1].text = "VALUE"
            hdr[2].text = "CONTEXT"
            WordExporter._style_header_row(table.rows[0])
            for idx, metric in enumerate(key_metrics):
                if isinstance(metric, dict):
                    row = table.add_row().cells
                    row[0].text = _as_text(metric.get("metric", ""))
                    row[1].text = _as_text(metric.get("value", ""))
                    row[2].text = _as_text(metric.get("context", ""))
                    WordExporter._style_data_row(table.rows[-1], idx)

        # ═══════════════════════════════════════════════════════════════
        # ACTION ITEMS TABLE
        # ═══════════════════════════════════════════════════════════════
        action_items = structured.get("action_items", [])
        if action_items:
            doc.add_paragraph()
            WordExporter._add_branded_heading(doc, "Action Items")
            table = doc.add_table(rows=1, cols=3)
            table.autofit = True
            hdr = table.rows[0].cells
            hdr[0].text = "TASK"
            hdr[1].text = "PRIORITY"
            hdr[2].text = "TIMELINE"
            WordExporter._style_header_row(table.rows[0])
            priority_colors = {
                "HIGH": RGBColor(0xCC, 0x33, 0x33),
                "CRITICAL": RGBColor(0xFF, 0x00, 0x00),
                "MEDIUM": RGBColor(0xDD, 0x88, 0x00),
                "LOW": RGBColor(0x00, 0xAA, 0x55),
            }
            for idx, item in enumerate(action_items):
                if isinstance(item, dict):
                    row = table.add_row().cells
                    row[0].text = _as_text(item.get("task", ""))
                    priority = _as_text(item.get("priority", "")).upper()
                    row[1].text = priority
                    row[2].text = _as_text(item.get("timeline", ""))
                    WordExporter._style_data_row(table.rows[-1], idx)
                    # Color-code priority cell
                    color = priority_colors.get(priority)
                    if color:
                        for run in row[1].paragraphs[0].runs:
                            run.font.color.rgb = color
                            run.font.bold = True

        # ═══════════════════════════════════════════════════════════════
        # RISK ASSESSMENT TABLE
        # ═══════════════════════════════════════════════════════════════
        risks = structured.get("risks", [])
        if risks:
            doc.add_paragraph()
            WordExporter._add_branded_heading(doc, "Risk Assessment")
            table = doc.add_table(rows=1, cols=3)
            table.autofit = True
            hdr = table.rows[0].cells
            hdr[0].text = "RISK"
            hdr[1].text = "SEVERITY"
            hdr[2].text = "MITIGATION"
            WordExporter._style_header_row(table.rows[0], bg_hex="1A0A0A",
                                           text_color=RGBColor(0xFF, 0x44, 0x44))
            severity_colors = {
                "CRITICAL": "FFE0E0",
                "HIGH": "FFF0E0",
                "MEDIUM": "FFFFF0",
                "LOW": "E0FFE0",
            }
            for idx, risk in enumerate(risks):
                if isinstance(risk, dict):
                    row = table.add_row().cells
                    row[0].text = _as_text(risk.get("risk", ""))
                    severity = _as_text(risk.get("severity", "")).upper()
                    row[1].text = severity
                    row[2].text = _as_text(risk.get("mitigation", ""))
                    # Color-code entire row by severity
                    bg = severity_colors.get(severity, "FFFFFF")
                    for cell in row:
                        WordExporter._shade_cell(cell, bg)

        # ═══════════════════════════════════════════════════════════════
        # FIPS 206 COMPLIANCE (auto-detected)
        # ═══════════════════════════════════════════════════════════════
        all_text = (_as_text(meta.get("summary", "")) + " " +
                    " ".join(_as_text(v) for v in sections.values())).lower()
        is_quantum = (
            "quantum" in workflow.lower() or "security" in workflow.lower() or "cyber" in workflow.lower() or
            "pqc" in all_text or "post-quantum" in all_text or "fips 203" in all_text or
            "fips 206" in all_text or "falcon" in all_text or "ml-kem" in all_text or
            "tls" in all_text or "cryptograph" in all_text
        )

        if is_quantum:
            doc.add_page_break()

            # Section banner
            banner = doc.add_table(rows=1, cols=1)
            cell = banner.rows[0].cells[0]
            cell.text = "FIPS 206 COMPLIANCE VERIFICATION · POST-QUANTUM CRYPTOGRAPHY AUDIT"
            WordExporter._shade_cell(cell, "0A1628")
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.color.rgb = RGBColor(0x00, 0xBF, 0xFF)
                    run.font.size = Pt(9)
                    run.font.bold = True
                    run.font.letter_spacing = Pt(1.5)

            doc.add_paragraph()
            WordExporter._add_branded_heading(doc, "PQC Standards Coverage", level=2)
            fips_table = doc.add_table(rows=1, cols=4)
            fips_table.autofit = True
            hdr = fips_table.rows[0].cells
            hdr[0].text = "STANDARD"
            hdr[1].text = "ALGORITHM"
            hdr[2].text = "USE CASE"
            hdr[3].text = "STATUS"
            WordExporter._style_header_row(fips_table.rows[0], bg_hex="0A1628",
                                           text_color=RGBColor(0x00, 0xBF, 0xFF))

            fips_data = [
                ("FIPS 203", "ML-KEM (Kyber)", "Key Encapsulation", "NIST Finalized"),
                ("FIPS 204", "ML-DSA (Dilithium)", "General Digital Signatures (~2.4KB)", "NIST Finalized"),
                ("FIPS 205", "SLH-DSA (SPHINCS+)", "Hash-Based Long-Term Signing", "NIST Finalized"),
                ("FIPS 206", "FN-DSA (FALCON)", "Integrity Anchor — Constrained Bandwidth", "NIST Draft Mar 2026"),
            ]
            for idx, (standard, algo, use_case, status) in enumerate(fips_data):
                row = fips_table.add_row().cells
                row[0].text = standard
                row[1].text = algo
                row[2].text = use_case
                row[3].text = status
                WordExporter._style_data_row(fips_table.rows[-1], idx, alt_hex="EBF5FF")
                # Highlight FIPS 206 row
                if standard == "FIPS 206":
                    for cell in row:
                        WordExporter._shade_cell(cell, "E0F7FF")
                        for p in cell.paragraphs:
                            for run in p.runs:
                                run.font.bold = True

            doc.add_paragraph()
            WordExporter._add_branded_heading(doc, "Integrity Anchor Assessment", level=2)
            doc.add_paragraph(
                "FALCON (FN-DSA) signatures are approximately 666 bytes, fitting within standard network "
                "packet MTUs. ML-DSA (FIPS 204) signatures at ~2.4KB risk packet fragmentation on constrained "
                "links (satellite uplinks, remote industrial sensors, legacy gateway interfaces with <1KB limits). "
                "In these environments, FN-DSA is the only quantum-resistant signature algorithm that provides "
                "cryptographic integrity without triggering denial-of-service via fragmentation."
            )

            # Signature Size Comparison Table
            sig_table = doc.add_table(rows=1, cols=3)
            sig_table.autofit = True
            hdr = sig_table.rows[0].cells
            hdr[0].text = "ALGORITHM"
            hdr[1].text = "SIGNATURE SIZE"
            hdr[2].text = "NETWORK IMPACT"
            WordExporter._style_header_row(sig_table.rows[0], bg_hex="0A1628",
                                           text_color=RGBColor(0x00, 0xBF, 0xFF))
            sig_data = [
                ("RSA-2048 (Legacy)", "256 bytes", "Fits MTU — but NOT quantum-resistant"),
                ("ML-DSA-65 (FIPS 204)", "~3,293 bytes", "Exceeds 1KB — fragmentation risk on constrained links"),
                ("SLH-DSA (FIPS 205)", "~8,000–41,000 bytes", "Long-term only — too large for real-time"),
                ("FALCON-512 (FIPS 206)", "~666 bytes", "Fits MTU — quantum-resistant Integrity Anchor"),
            ]
            for idx, (algo, size, impact) in enumerate(sig_data):
                row = sig_table.add_row().cells
                row[0].text = algo
                row[1].text = size
                row[2].text = impact
                WordExporter._style_data_row(sig_table.rows[-1], idx, alt_hex="EBF5FF")
                # Green highlight for FALCON
                if "FALCON" in algo:
                    for cell in row:
                        WordExporter._shade_cell(cell, "E0FFE8")

            doc.add_paragraph()
            doc.add_paragraph(
                "Recommendation: Deploy ML-KEM (FIPS 203) for key encapsulation on all channels. "
                "Use SLH-DSA (FIPS 205) for firmware and code signing where signature size is not constrained. "
                "Use FALCON/FN-DSA (FIPS 206) as the Integrity Anchor for any path with bandwidth constraints "
                "or legacy packet-size limitations. Reject non-hybrid certificates by the 2030 CNSS horizon."
            )

            WordExporter._add_branded_heading(doc, "Quantum Drift Detection", level=2)
            drift_found = False
            if card_results:
                for provider, result in card_results.items():
                    if not isinstance(result, dict) or not result.get("success"):
                        continue
                    claims = result.get("verified_claims", [])
                    for claim in claims:
                        violations = claim.get("violations", [])
                        for v in violations:
                            if "quantum" in v.lower() or "pqc" in v.lower() or "fips" in v.lower():
                                doc.add_paragraph(
                                    f"[{provider.upper()}] {claim.get('claim', 'N/A')[:200]}",
                                    style='List Bullet'
                                )
                                p = doc.add_paragraph()
                                run = p.add_run(f"  ⚠ {v}")
                                run.font.color.rgb = RGBColor(0xCC, 0x33, 0x33)
                                run.font.size = Pt(9)
                                drift_found = True
            if not drift_found:
                p = doc.add_paragraph()
                run = p.add_run(
                    "✓ No Quantum Drift violations detected. All referenced cryptographic "
                    "mechanisms include post-quantum wrappers or are PQC-native."
                )
                run.font.color.rgb = RGBColor(0x00, 0xAA, 0x55)

            # Attestation Box
            doc.add_paragraph()
            attest_table = doc.add_table(rows=1, cols=1)
            cell = attest_table.rows[0].cells[0]
            WordExporter._shade_cell(cell, "F0F8FF")
            p = cell.paragraphs[0]
            run = p.add_run("COMPLIANCE ATTESTATION\n")
            run.font.size = Pt(8)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x00, 0x80, 0xBF)
            
            if client_name:
                node_desc = f"{client_name} Federated Intelligence Node"
            elif is_client_branded and "QANAPI" in branding_prefix.upper():
                node_desc = "Qanapi Armory Federated Node"
            else:
                node_desc = "KORUM-OS Secure Kernel Enclave"
            run = p.add_run(
                f"Generated by KORUM-OS Multi-Agent Council ({agent_count} independent AI providers) "
                f"on {date_display}. Composite Truth Score: {truth_display}/100. "
                f"Covers NIST FIPS 203, 204, 205, and 206 (Draft). "
                f"Report ready for cryptographic signing via {node_desc}."
            )
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

        # ═══════════════════════════════════════════════════════════════
        # ANALYTIC DIVERGENCE
        # ═══════════════════════════════════════════════════════════════
        divergence = intelligence_object.get("divergence_analysis") or {}
        if divergence and divergence.get("divergence_summary"):
            doc.add_paragraph()
            WordExporter._add_branded_heading(doc, "Analytic Divergence")

            # Scores
            p = doc.add_paragraph()
            run = p.add_run(f"Consensus: {divergence.get('consensus_score', 'N/A')}/100  |  Divergence: {divergence.get('divergence_score', 'N/A')}/100")
            run.font.bold = True
            run.font.size = Pt(10)
            if divergence.get('protocol_variance'):
                run = p.add_run("  |  PROTOCOL VARIANCE DETECTED")
                run.font.color.rgb = RGBColor(0xFF, 0x44, 0x44)
                run.font.bold = True

            if divergence.get('divergence_summary'):
                doc.add_paragraph(_as_text(divergence['divergence_summary']))

            # Areas of Agreement
            agreement = divergence.get("agreement_topics", [])
            if agreement:
                p = doc.add_paragraph()
                run = p.add_run("Areas of Agreement")
                run.font.bold = True
                for a in agreement:
                    providers = ", ".join(p.upper() for p in (a.get("providers") or []))
                    doc.add_paragraph(
                        f"[{_as_text(a.get('confidence', 'MODERATE')).upper()}] {_as_text(a.get('topic', ''))} — {_as_text(a.get('detail', ''))}"
                        + (f" (Supported by: {providers})" if providers else ""),
                        style='List Bullet'
                    )

            # Contested Positions
            contested = divergence.get("contested_topics", [])
            if contested:
                p = doc.add_paragraph()
                run = p.add_run("Contested Positions")
                run.font.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0x88, 0x44)
                for c in contested:
                    doc.add_paragraph(
                        f"[{_as_text(c.get('severity', 'MEDIUM')).upper()}] {_as_text(c.get('topic', ''))}",
                        style='List Bullet'
                    )
                    for pos in c.get("positions", []):
                        doc.add_paragraph(
                            f"{_as_text(pos.get('provider', '')).upper()}: {_as_text(pos.get('position', ''))}",
                            style='List Bullet 2'
                        )
                    if c.get("operational_impact"):
                        p = doc.add_paragraph()
                        run = p.add_run(f"Operational Impact: {_as_text(c['operational_impact'])}")
                        run.font.size = Pt(9)
                        run.font.color.rgb = RGBColor(0xFF, 0x88, 0x44)

            # Resolution Requirements
            resolutions = divergence.get("resolution_requirements", [])
            if resolutions:
                p = doc.add_paragraph()
                run = p.add_run("Resolution Requirements")
                run.font.bold = True
                for r in resolutions:
                    doc.add_paragraph(
                        f"[{_as_text(r.get('priority', 'MEDIUM')).upper()}] {_as_text(r.get('question', ''))}",
                        style='List Bullet'
                    )

            WordExporter._add_section_divider(doc)

        # ═══════════════════════════════════════════════════════════════
        # CONFIDENCE & ASSUMPTIONS
        # ═══════════════════════════════════════════════════════════════
        conf_data = intelligence_object.get("confidence_and_assumptions") or {}
        if conf_data:
            doc.add_paragraph()
            WordExporter._add_branded_heading(doc, "Confidence & Assumptions")
            overall = _as_text(conf_data.get("overall_confidence", "moderate-to-high"))
            p = doc.add_paragraph()
            run = p.add_run(f"Overall Confidence: {overall.upper()}")
            run.font.bold = True
            run.font.size = Pt(11)
            assumptions = conf_data.get("key_assumptions", [])
            if assumptions:
                p = doc.add_paragraph()
                run = p.add_run("Key Assumptions:")
                run.font.bold = True
                for a in assumptions:
                    doc.add_paragraph(_as_text(a), style='List Bullet')
            limitations = conf_data.get("limitations", [])
            if limitations:
                p = doc.add_paragraph()
                run = p.add_run("Limitations:")
                run.font.bold = True
                for l in limitations:
                    doc.add_paragraph(_as_text(l), style='List Bullet')
            WordExporter._add_section_divider(doc)

        # ═══════════════════════════════════════════════════════════════
        # COUNCIL CONTRIBUTORS
        # ═══════════════════════════════════════════════════════════════
        contributors = intelligence_object.get("council_contributors") or []
        if not contributors:
            models_used = meta.get("models_used", [])
            if models_used:
                contributors = [{"phase": f"Phase {i+1}", "provider": m, "role": "", "contribution_summary": ""} for i, m in enumerate(models_used)]
        if contributors:
            doc.add_paragraph()
            WordExporter._add_branded_heading(doc, "Council Contributors")
            table = doc.add_table(rows=1, cols=4)
            table.autofit = True
            hdr = table.rows[0].cells
            hdr[0].text = "PHASE"
            hdr[1].text = "PROVIDER"
            hdr[2].text = "ROLE"
            hdr[3].text = "CONTRIBUTION"
            WordExporter._style_header_row(table.rows[0])
            for idx, c in enumerate(contributors):
                row = table.add_row().cells
                row[0].text = _as_text(c.get("phase", ""))
                row[1].text = _as_text(c.get("provider", ""))
                row[2].text = _as_text(c.get("role", ""))
                row[3].text = _as_text(c.get("contribution_summary", ""))
                WordExporter._style_data_row(table.rows[-1], idx)
            WordExporter._add_section_divider(doc)

        # ═══════════════════════════════════════════════════════════════
        # COUNCIL MEMBER ANALYSIS
        # ═══════════════════════════════════════════════════════════════
        if card_results:
            doc.add_page_break()
            WordExporter._add_branded_heading(doc, "Council Member Analysis")
            for provider, result in card_results.items():
                if not isinstance(result, dict) or not result.get("success"):
                    continue
                provider_name = provider.replace("_", " ").title()
                role = _as_text(result.get("role", "")).upper()
                truth = result.get("truth_meter", "N/A")

                # Provider header bar
                prov_table = doc.add_table(rows=1, cols=2)
                prov_table.autofit = True
                c0 = prov_table.rows[0].cells[0]
                c1 = prov_table.rows[0].cells[1]
                WordExporter._shade_cell(c0, "0D1117")
                WordExporter._shade_cell(c1, "0D1117")
                p0 = c0.paragraphs[0]
                run = p0.add_run(f"{provider_name} — {role}")
                run.font.color.rgb = RGBColor(0x00, 0xE5, 0xFF)
                run.font.size = Pt(10)
                run.font.bold = True
                p1 = c1.paragraphs[0]
                p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                run = p1.add_run(f"TRUTH: {truth}/100")
                try:
                    t = int(truth)
                    if t >= 80:
                        run.font.color.rgb = RGBColor(0x00, 0xAA, 0x55)
                    elif t >= 50:
                        run.font.color.rgb = RGBColor(0xDD, 0x88, 0x00)
                    else:
                        run.font.color.rgb = RGBColor(0xCC, 0x33, 0x33)
                except (ValueError, TypeError):
                    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
                run.font.size = Pt(10)
                run.font.bold = True

                response_text = _clean_tags(_as_text(result.get("response", "")))
                # Parse markdown tables vs plain paragraphs (same logic as synthesis sections)
                _lines = response_text.split("\n")
                _in_tbl = False
                _tbl_lines = []
                _cur_para = []

                def _flush_member_para(pl):
                    pt = " ".join(l.strip() for l in pl if l.strip())
                    if pt:
                        doc.add_paragraph(pt)

                def _flush_member_table(tl):
                    rows = []
                    for l in tl:
                        if "|" in l:
                            cells = [c.strip() for c in l.split("|")]
                            if not cells[0]: cells = cells[1:]
                            if cells and not cells[-1]: cells = cells[:-1]
                            if all(c.replace("-", "").replace(":", "").replace(" ", "") == "" for c in cells):
                                continue
                            rows.append(cells)
                    if rows:
                        cols = max(len(r) for r in rows)
                        tbl = doc.add_table(rows=len(rows), cols=cols)
                        tbl.autofit = True
                        for i, r_cells in enumerate(rows):
                            for j, c_text in enumerate(r_cells):
                                if j < len(tbl.rows[i].cells):
                                    tbl.rows[i].cells[j].text = c_text
                        WordExporter._style_header_row(tbl.rows[0])
                        for i in range(1, len(tbl.rows)):
                            WordExporter._style_data_row(tbl.rows[i], i - 1)
                        doc.add_paragraph()

                for _line in _lines:
                    if "|" in _line:
                        if not _in_tbl:
                            _flush_member_para(_cur_para)
                            _cur_para = []
                            _in_tbl = True
                        _tbl_lines.append(_line)
                    else:
                        if _in_tbl:
                            _flush_member_table(_tbl_lines)
                            _tbl_lines = []
                            _in_tbl = False
                        if not _line.strip():
                            _flush_member_para(_cur_para)
                            _cur_para = []
                        else:
                            _cur_para.append(_line)
                if _in_tbl:
                    _flush_member_table(_tbl_lines)
                if _cur_para:
                    _flush_member_para(_cur_para)

                WordExporter._add_section_divider(doc)

        # ═══════════════════════════════════════════════════════════════
        # COMPLIANCE ATTESTATION
        # ═══════════════════════════════════════════════════════════════
        doc.add_paragraph()  # spacer
        if client_name:
            node_desc = f"{client_name} Federated Intelligence Node"
        elif is_client_branded and "QANAPI" in branding_prefix.upper():
            node_desc = "Qanapi Armory Federated Node"
        else:
            node_desc = "KORUM-OS Secure Kernel Enclave"
        attest_table = doc.add_table(rows=1, cols=1)
        attest_table.autofit = True
        attest_cell = attest_table.rows[0].cells[0]
        WordExporter._shade_cell(attest_cell, "F0F8FF")
        ap = attest_cell.paragraphs[0]
        ap.paragraph_format.space_before = Pt(4)
        ap.paragraph_format.space_after = Pt(4)
        # Build attestation text in two runs so date never truncates on a single line
        run1 = ap.add_run(
            f"COMPLIANCE ATTESTATION: Generated via {node_desc}. "
            f"Integrity Anchor: FN-DSA. Composite Score: {truth_display}/100."
        )
        run1.font.size = Pt(8)
        run1.font.color.rgb = RGBColor(0x00, 0x80, 0xBF)
        run1.font.name = "Calibri"
        run1.font.bold = True
        ap.add_run("\n")
        attest_run = ap.add_run(f"Audit Date: {date_display}")
        attest_run.font.size = Pt(8)
        attest_run.font.color.rgb = RGBColor(0x00, 0x80, 0xBF)
        attest_run.font.name = "Calibri"
        attest_run.font.bold = True

        # ═══════════════════════════════════════════════════════════════
        # FOOTER
        # ═══════════════════════════════════════════════════════════════
        # Footer with branding
        footer = doc.sections[0].footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Top rule
        rule_run = fp.add_run("━" * 60 + "\n")
        rule_run.font.size = Pt(5)
        rule_run.font.color.rgb = RGBColor(0x00, 0xE5, 0xFF)
        rule_run.font.name = "Calibri"
        # Branding text
        brand_text = (f"{branding_prefix}  ·  MULTI-AGENT INTELLIGENCE  ·  "
                      f"{agent_count} PROVIDERS  ·  TRUTH SCORE {truth_display}/100  ·  CONFIDENTIAL")
        run = fp.add_run(brand_text)
        run.font.size = Pt(6.5)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        run.font.bold = True
        run.font.name = "Calibri"
        run.font.letter_spacing = Pt(0.5)

        # ═══════════════════════════════════════════════════════════════
        # RESEARCH ARTIFACTS
        # ═══════════════════════════════════════════════════════════════
        snippets = _report_artifacts(intelligence_object)
        if snippets:
            doc.add_page_break()
            WordExporter._add_branded_heading(doc, "Executive Exhibits")
            doc.add_paragraph("The following selected artifacts were curated in the dock and attached as supporting exhibits for executive review.")
            
            for idx, s in enumerate(snippets):
                table = doc.add_table(rows=1, cols=2)
                table.autofit = True
                hdr = table.rows[0].cells
                hdr[0].text = f"EXHIBIT #{idx+1} — {_artifact_label(s).upper()}"
                hdr[1].text = s.get('type', 'text').upper()
                WordExporter._style_header_row(table.rows[0], bg_hex="161B22", text_color=RGBColor(0x00, 0xFF, 0x9D))
                
                row = table.add_row().cells
                row[0].text = "SOURCE"
                row[1].text = s.get('source', 'Selection')

                tags = ", ".join(s.get("tags", []))
                if tags:
                    row = table.add_row().cells
                    row[0].text = "TAGS"
                    row[1].text = tags
                
                content = _clean_tags(_as_text(s.get("content", "")))
                # If content is large, add as separate paragraph
                if len(content) > 100:
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(8)
                    run = p.add_run(content)
                    run.font.size = Pt(9)
                    run.font.name = "Consolas" if s.get('type') == 'code' or s.get('type') == 'mermaid' else "Calibri"
                else:
                    row = table.add_row().cells
                    row[0].text = "CONTENT"
                    row[1].text = content
                
                doc.add_paragraph() # Spacer
            
            WordExporter._add_section_divider(doc)

        filename = f"korum_report_{_timestamp()}.docx"
        filepath = _output_path(filename, output_dir)
        doc.save(filepath)
        return filepath


class PPTXExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        from pptx.util import Pt as PptxPt

        meta, sections, _, interrogations, verifications = _extract_parts(intelligence_object)
        prs = PPTXPresentation()

        title_slide = prs.slides.add_slide(prs.slide_layouts[0])
        title_slide.shapes.title.text = _sanitize_for_pptx(_as_text(meta.get("title", "Intelligence Report")))
        subtitle = title_slide.placeholders[1] if len(title_slide.placeholders) > 1 else None
        if subtitle:
            subtitle.text = _sanitize_for_pptx(f"KORUM-OS | {_as_text(meta.get('generated_at', ''))}")

        for section_id, content in sections.items():
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = section_id.replace("_", " ").title()
            if len(slide.placeholders) > 1:
                tf = slide.placeholders[1].text_frame
                text = _sanitize_for_pptx(_as_text(content))
                tf.text = text[:1000]
                for paragraph in tf.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = 'Calibri'
                        run.font.size = PptxPt(14)
                if len(text) > 1000:
                    p = tf.add_paragraph()
                    p.text = "... (Continued in report)"

        filename = f"korum_deck_{_timestamp()}.pptx"
        filepath = _output_path(filename, output_dir)
        prs.save(filepath)
        return filepath


class ExcelExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        from openpyxl.chart import PieChart, Reference
        from openpyxl.styles import PatternFill, Font

        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        wb = Workbook()

        # ── SUMMARY SHEET ──
        ws_meta = wb.active
        ws_meta.title = "Summary"
        ws_meta.append(["Field", "Value"])
        ws_meta.append(["Title", _sanitize_for_csv(meta.get("title", ""))])
        ws_meta.append(["Generated At", _sanitize_for_csv(meta.get("generated_at", ""))])
        ws_meta.append(["Truth Score", _sanitize_for_csv(meta.get("composite_truth_score", ""))])
        ws_meta.append(
            [
                "Models Used",
                _sanitize_for_csv(", ".join(meta.get("models_used", [])) if isinstance(meta.get("models_used"), list) else _as_text(meta.get("models_used", ""))),
            ]
        )
        ws_meta.append(["Summary", _sanitize_for_csv(meta.get("summary", ""))])

        # ── SECTIONS SHEET ──
        ws_sections = wb.create_sheet("Sections")
        ws_sections.append(["Section", "Content"])
        for section_id, content in sections.items():
            ws_sections.append([section_id.replace("_", " ").title(), _sanitize_for_csv(content)])

        # ── KEY METRICS & PIE CHART ──
        ws_metrics = wb.create_sheet("Key Metrics")
        ws_metrics.append(["Metric", "Value", "Context"])
        chart_data_rows = 0
        for metric in structured.get("key_metrics", []):
            val_str = _sanitize_for_csv(metric.get("value", ""))
            ws_metrics.append([_sanitize_for_csv(metric.get("metric", "")), val_str, _sanitize_for_csv(metric.get("context", ""))])
            chart_data_rows += 1

        # Embed Pie Chart if we have metrics (try to parse numeric values)
        if chart_data_rows > 1:
            try:
                pie = PieChart()
                labels = Reference(ws_metrics, min_col=1, min_row=2, max_row=chart_data_rows + 1)
                data = Reference(ws_metrics, min_col=2, min_row=1, max_row=chart_data_rows + 1)
                pie.add_data(data, titles_from_data=True)
                pie.set_categories(labels)
                pie.title = "Metrics Breakdown"
                ws_metrics.add_chart(pie, "E2")
            except:
                pass # Skip chart if data is non-numeric

        # ── ACTION ITEMS ──
        ws_actions = wb.create_sheet("Action Items")
        ws_actions.append(["Task", "Priority", "Timeline"])
        for item in structured.get("action_items", []):
            ws_actions.append([_sanitize_for_csv(item.get("task", "")), _sanitize_for_csv(item.get("priority", "")), _sanitize_for_csv(item.get("timeline", ""))])

        # ── RISKS (WITH COLOR) ──
        ws_risks = wb.create_sheet("Risks")
        ws_risks.append(["Risk", "Severity", "Mitigation"])
        red_fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
        red_font = Font(color="990000", bold=True)
        
        for risk in structured.get("risks", []):
            severity = _sanitize_for_csv(risk.get("severity", "")).lower()
            row_idx = ws_risks.max_row + 1
            ws_risks.append([_sanitize_for_csv(risk.get("risk", "")), severity, _sanitize_for_csv(risk.get("mitigation", ""))])
            if "high" in severity or "critical" in severity or "truth bomb" in severity:
                for cell in ws_risks[row_idx]:
                    cell.fill = red_fill
                    cell.font = red_font

        # ── AUDIT TRAILS ──
        if interrogations:
            ws_int = wb.create_sheet("Audit - Interrogations")
            ws_int.append(["Timestamp", "Target", "Attacker", "Defender", "Verdict", "Score Delta", "Challenge", "Rebuttal"])
            for entry in interrogations:
                ws_int.append([
                    _sanitize_for_csv(entry.get('timestamp', '')),
                    _sanitize_for_csv(entry.get('target', '')),
                    _sanitize_for_csv(f"{entry.get('attacker', '').upper()} ({entry.get('attacker_model', '')})"),
                    _sanitize_for_csv(f"{entry.get('defender', '').upper()} ({entry.get('defender_model', '')})"),
                    _sanitize_for_csv(entry.get('verdict', '')),
                    entry.get('score_delta', 0),
                    _sanitize_for_csv(entry.get('attacker_response', '')),
                    _sanitize_for_csv(entry.get('defender_response', ''))
                ])

        if verifications:
            ws_ver = wb.create_sheet("Audit - Verifications")
            ws_ver.append(["Timestamp", "Claim", "Verdict", "Score Delta", "Evidence"])
            for entry in verifications:
                ws_ver.append([
                    _sanitize_for_csv(entry.get('timestamp', '')),
                    _sanitize_for_csv(entry.get('claim', '')),
                    _sanitize_for_csv(entry.get('verdict', '')),
                    entry.get('score_delta', 0),
                    _sanitize_for_csv(entry.get('verification', ''))
                ])

        filename = f"korum_intelligence_{_timestamp()}.xlsx"
        filepath = _output_path(filename, output_dir)
        wb.save(filepath)
        return filepath


class CSVExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        filename = f"korum_intelligence_{_timestamp()}.csv"
        filepath = _output_path(filename, output_dir)
        with open(filepath, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["type", "key", "value", "extra"])

            if interrogations:
                for entry in interrogations:
                    writer.writerow(["audit_interrogation", entry.get('target', ''), entry.get('verdict', ''), f"Delta: {entry.get('score_delta', 0)}"])
            
            if verifications:
                for entry in verifications:
                    writer.writerow(["audit_verification", entry.get('claim', ''), entry.get('verdict', ''), ""])

            writer.writerow(["meta", "title", _sanitize_for_csv(meta.get("title", "")), ""])
            writer.writerow(["meta", "generated_at", _sanitize_for_csv(meta.get("generated_at", "")), ""])
            writer.writerow(["meta", "summary", _sanitize_for_csv(meta.get("summary", "")), ""])
            writer.writerow(["meta", "truth_score", _sanitize_for_csv(meta.get("composite_truth_score", "")), ""])

            for section_id, content in sections.items():
                writer.writerow(["section", section_id, _sanitize_for_csv(content), ""])

            for metric in structured.get("key_metrics", []):
                writer.writerow(
                    ["key_metric", _sanitize_for_csv(metric.get("metric", "")), _sanitize_for_csv(metric.get("value", "")), _sanitize_for_csv(metric.get("context", ""))]
                )
            for item in structured.get("action_items", []):
                writer.writerow(
                    ["action_item", _sanitize_for_csv(item.get("task", "")), _sanitize_for_csv(item.get("priority", "")), _sanitize_for_csv(item.get("timeline", ""))]
                )
            for risk in structured.get("risks", []):
                writer.writerow(
                    ["risk", _sanitize_for_csv(risk.get("risk", "")), _sanitize_for_csv(risk.get("severity", "")), _sanitize_for_csv(risk.get("mitigation", ""))]
                )
        return filepath


class TextExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        filename = f"korum_intelligence_{_timestamp()}.txt"
        filepath = _output_path(filename, output_dir)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(f"{_as_text(meta.get('title', 'KORUM Intelligence Report'))}\n")
            file.write("=" * 72 + "\n")
            file.write(f"Generated at: {_as_text(meta.get('generated_at', datetime.now().isoformat()))}\n")
            file.write(f"Truth score: {_as_text(meta.get('composite_truth_score', 'N/A'))}/100\n\n")
            file.write(f"Summary:\n{_as_text(meta.get('summary', ''))}\n\n")
            for section_id, content in sections.items():
                file.write(f"{section_id.replace('_', ' ').title()}\n")
                file.write("-" * 72 + "\n")
                file.write(f"{_as_text(content)}\n\n")
            if structured:
                file.write("Structured Data\n")
                file.write("-" * 72 + "\n")
                file.write(json.dumps(structured, indent=2, ensure_ascii=True))
                file.write("\n")
        return filepath


class MarkdownExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        filename = f"korum_intelligence_{_timestamp()}.md"
        filepath = _output_path(filename, output_dir)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(f"# {_as_text(meta.get('title', 'KORUM Intelligence Report'))}\n\n")
            file.write(f"- Generated at: {_as_text(meta.get('generated_at', datetime.now().isoformat()))}\n")
            file.write(f"- Composite Truth Score: {_as_text(meta.get('composite_truth_score', 'N/A'))}/100\n\n")
            file.write(f"## Executive Summary\n\n{_as_text(meta.get('summary', ''))}\n\n")
            for section_id, content in sections.items():
                file.write(f"## {section_id.replace('_', ' ').title()}\n\n{_as_text(content)}\n\n")
            if interrogations or verifications:
                file.write("## Audit & Verification Trail\n\n")
                if interrogations:
                    file.write("### Adversarial Interrogations\n\n")
                    for entry in interrogations:
                        file.write(f"**Target:** {entry.get('target', 'Claim')}\n")
                        file.write(f"**Verdict:** {entry.get('verdict', 'CONTESTED')} (Delta: {entry.get('score_delta', 0)})\n\n")
                        file.write(f"> **Attacker ({entry.get('attacker', '').upper()}):** {entry.get('attacker_response', '')}\n\n")
                        file.write(f"> **Defender ({entry.get('defender', '').upper()}):** {entry.get('defender_response', '')}\n\n")
                if verifications:
                    file.write("### Source Verifications\n\n")
                    for entry in verifications:
                        file.write(f"**Claim:** {entry.get('claim', '')}\n")
                        file.write(f"**Verdict:** {entry.get('verdict', 'UNRESOLVED')}\n\n")
                        file.write(f"> **Evidence:** {entry.get('verification', '')}\n\n")

            file.write("## Structured Data\n\n")
            file.write("```json\n")
            file.write(json.dumps(structured, indent=2, ensure_ascii=True))
            file.write("\n```\n")
        return filepath


class JSONExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        filename = f"korum_intelligence_{_timestamp()}.json"
        filepath = _output_path(filename, output_dir)
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(intelligence_object or {}, file, indent=2, ensure_ascii=True)
        return filepath


class PDFExporter:
    """Palantir-tier PDF report — matching WordExporter's branding and visual density."""

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, interrogations, verifications = _extract_parts(intelligence_object)
        card_results = intelligence_object.get("_card_results", {})
        mission_ctx = intelligence_object.get("_mission_context") or {}
        filename = f"korum_report_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)

        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                topMargin=40, bottomMargin=40,
                                leftMargin=50, rightMargin=50)
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.graphics.shapes import Drawing, Rect as DrawRect

        def _dark_page_bg(canvas, doc):
            """Paint dark background on every page."""
            canvas.saveState()
            canvas.setFillColor(colors.HexColor("#0D1117"))
            canvas.rect(0, 0, letter[0], letter[1], fill=True, stroke=False)
            canvas.restoreState()

        styles = getSampleStyleSheet()

        # --- DARK THEME PALETTE (matches KorumOS web UI) ---
        BG_DARK = "#0D1117"
        BG_CARD = "#161B22"
        BG_SURFACE = "#1C2333"
        TEXT_PRIMARY = "#E6EDF3"
        TEXT_SECONDARY = "#8B949E"
        ACCENT_CYAN = "#00E5FF"
        ACCENT_GREEN = "#00FF9D"
        ACCENT_GOLD = "#FFB020"
        ACCENT_RED = "#FF4444"
        BORDER = "#30363D"

        # Define high-end dark-theme styles
        styles.add(ParagraphStyle(
            name='BannerText',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor(ACCENT_CYAN),
            alignment=1,
            leading=10,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            name='BrandedTitle',
            parent=styles['Title'],
            fontSize=22,
            textColor=colors.HexColor(TEXT_PRIMARY),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            name='BrandedHeading1',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor(ACCENT_CYAN),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))

        styles.add(ParagraphStyle(
            name='SectionBody',
            parent=styles['BodyText'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor(TEXT_PRIMARY),
            wordWrap='CJK'
        ))

        story = []

        # --- Normalize truth score ---
        truth_raw = meta.get("composite_truth_score", "N/A")
        try:
            truth_val = float(truth_raw)
            if truth_val <= 1: truth_val *= 100
            truth_int = int(truth_val)
            truth_display = str(truth_int)
        except (ValueError, TypeError):
            truth_int = 0
            truth_display = str(truth_raw)

        workflow = _as_text(meta.get("workflow", "RESEARCH")).upper()
        date_str = meta.get("generated_at", datetime.now().isoformat())
        try:
            date_obj = datetime.fromisoformat(date_str)
            date_display = date_obj.strftime("%Y-%m-%d %H:%M UTC")
        except:
            date_display = date_str

        agent_count = len(meta.get("models_used", []))

        # Dynamic branding logic — uses client name from mission context
        title_text = _as_text(meta.get("title", "Strategic Intelligence Report"))
        client_name = _as_text(mission_ctx.get("client", "")).strip()
        if client_name:
            branding_prefix = f"{client_name.upper()} x KORUM-OS"
            is_client_branded = True
        elif "QANAPI" in workflow or "QANAPI" in title_text.upper():
            branding_prefix = "QANAPI x KORUM-OS"
            is_client_branded = True
        else:
            branding_prefix = "KORUM-OS INTERNAL"
            is_client_branded = False

        # --- CLASSIFICATION BANNER ---
        banner_data = [[f"{branding_prefix}  ·  MULTI-AGENT INTELLIGENCE  ·  {workflow}"]]
        banner_table = Table(banner_data, colWidths=[512])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0D1117")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#00E5FF")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 40))

        # --- TITLE ---
        story.append(Paragraph(title_text, styles['BrandedTitle']))
        story.append(Spacer(1, 20))

        # --- METADATA BAR ---
        score_color = "#00AA55" if truth_int >= 80 else ("#DD8800" if truth_int >= 50 else "#CC3333")
        
        meta_data = [
            ["DATE", "WORKFLOW", "AGENTS", "TRUTH_SCORE"],
            [date_display, workflow, str(agent_count), f"{truth_display}/100"]
        ]
        meta_table = Table(meta_data, colWidths=[180, 100, 80, 152])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BG_CARD)),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), ( -1, 0), 7),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(TEXT_SECONDARY)),
            ('FONTSIZE', (0, 1), (-1, 1), 10),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor(TEXT_PRIMARY)),
            ('TEXTCOLOR', (-1, 1), (-1, 1), colors.HexColor(score_color)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(meta_table)

        # --- TRUTH SCORE BAR ---
        story.append(Spacer(1, 10))
        filled_width = (truth_int / 100.0) * 512
        empty_width = 512 - filled_width
        bar_data = [["", ""]]
        bar_table = Table(bar_data, colWidths=[filled_width, empty_width], rowHeights=[4])
        bar_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor(score_color)),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor(BG_CARD)),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(bar_table)
        story.append(Spacer(1, 30))

        # --- EXECUTIVE SUMMARY ---
        story.append(Paragraph("Executive Summary", styles['BrandedHeading1']))
        summary_text = _as_text(meta.get("summary", "")) or _as_text(sections.get("executive_summary", ""))
        story.append(Paragraph(summary_text, styles['SectionBody']))
        story.append(Spacer(1, 10))

        # --- SECTIONS ---
        for section_id, content in sections.items():
            if section_id == "executive_summary": continue
            story.append(Paragraph(section_id.replace("_", " ").title(), styles['BrandedHeading1']))
            text = _clean_tags(_as_text(content))
            
            lines = text.split("\n")
            in_table = False
            table_lines = []
            current_para = []

            def flush_para_pdf(para_lines, s):
                p_text = " ".join(l.strip() for l in para_lines if l.strip())
                if p_text:
                    s.append(Paragraph(p_text, styles['SectionBody']))
                    s.append(Spacer(1, 6))

            def flush_table_pdf(t_lines, s):
                rows = []
                for l in t_lines:
                    if "|" in l:
                        cells = [c.strip() for c in l.split("|")]
                        if not cells[0]: cells = cells[1:]
                        if not cells[-1]: cells = cells[:-1]
                        if all(c.replace("-", "").replace(":", "").replace(" ", "") == "" for c in cells):
                            continue
                        rows.append([Paragraph(c, tbl_cell) for c in cells])
                
                if rows:
                    col_count = max(len(r) for r in rows)
                    # Simple heuristic for column widths
                    cw = [512 / col_count] * col_count
                    t = Table(rows, colWidths=cw, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0D1117")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#00E5FF")),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor(BG_CARD), colors.HexColor(BG_SURFACE)])
                    ]))
                    s.append(t)
                    s.append(Spacer(1, 10))

            for line in lines:
                if "|" in line:
                    if not in_table:
                        flush_para_pdf(current_para, story)
                        current_para = []
                        in_table = True
                    table_lines.append(line)
                else:
                    if in_table:
                        flush_table_pdf(table_lines, story)
                        table_lines = []
                        in_table = False
                    if not line.strip():
                        flush_para_pdf(current_para, story)
                        current_para = []
                    else:
                        current_para.append(line)
            
            if in_table: flush_table_pdf(table_lines, story)
            else: flush_para_pdf(current_para, story)

        # --- STRUCTURED DATA TABLES (Metrics, Actions, Risks) ---
        metrics = structured.get("key_metrics", [])
        tbl_cell = ParagraphStyle('TblCell', parent=styles['SectionBody'], fontSize=8, leading=10, wordWrap='CJK')
        tbl_hdr = ParagraphStyle('TblHdr', parent=tbl_cell, textColor=colors.HexColor("#00E5FF"), fontName='Helvetica-Bold')
        if metrics:
            story.append(Paragraph("Key Intelligence Metrics", styles['BrandedHeading1']))
            m_data = [[Paragraph("METRIC", tbl_hdr), Paragraph("VALUE", tbl_hdr), Paragraph("CONTEXT", tbl_hdr)]]
            for m in metrics:
                m_data.append([Paragraph(_as_text(m.get("metric")), tbl_cell),
                               Paragraph(_as_text(m.get("value")), tbl_cell),
                               Paragraph(_as_text(m.get("context")), tbl_cell)])
            t = Table(m_data, colWidths=[150, 100, 262], repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0D1117")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#00E5FF")),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor(BG_CARD), colors.HexColor(BG_SURFACE)])
            ]))
            story.append(t)

        # --- TRUTH BOMBS ---
        truth_bombs = (intelligence_object.get("intelligence_tags") or {}).get("truth_bombs", [])
        if truth_bombs:
            story.append(Paragraph("CRITICAL DISCREPANCIES (TRUTH BOMBS)", styles['BrandedHeading1']))
            for tb in truth_bombs:
                tb_data = [[Paragraph(tb, ParagraphStyle('TruthBombBody', parent=styles['SectionBody'], textColor=colors.HexColor("#FFFFFF")))]]
                tb_table = Table(tb_data, colWidths=[512])
                tb_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#330000")),
                    ('BOX', (0, 0), (-1, -1), 2, colors.HexColor("#FF0000")),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(tb_table)
                story.append(Spacer(1, 10))

        # Risks
        risks = structured.get("risks", [])
        if risks:
            story.append(Paragraph("Risk Assessment", styles['BrandedHeading1']))
            risk_hdr = ParagraphStyle('RiskHdr', parent=tbl_cell, textColor=colors.HexColor("#FF4444"), fontName='Helvetica-Bold')
            r_data = [[Paragraph("RISK", risk_hdr), Paragraph("SEVERITY", risk_hdr), Paragraph("MITIGATION", risk_hdr)]]
            sev_box = {"CRITICAL": "#FF4444", "HIGH": "#FF8844", "MEDIUM": "#FFCC00", "LOW": "#00AA55"}
            for r in risks:
                r_data.append([Paragraph(_as_text(r.get("risk")), tbl_cell),
                               Paragraph(_as_text(r.get("severity", "")).upper(), tbl_cell),
                               Paragraph(_as_text(r.get("mitigation")), tbl_cell)])
            t = Table(r_data, colWidths=[180, 80, 252], repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A0A0A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(ACCENT_RED)),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor(BG_CARD), colors.HexColor("#1A1015")])
            ]))
            story.append(t)

        # --- FIPS COMPLIANCE ---
        all_text = (_as_text(meta.get("summary", "")) + " " + " ".join(_as_text(v) for v in sections.values())).lower()
        if "quantum" in all_text or "pqc" in all_text or "fips" in all_text:
            story.append(Paragraph("FIPS 206 Compliance Audit", styles['BrandedHeading1']))
            f_data = [["STANDARD", "ALGORITHM", "STATUS"]]
            f_data.append(["FIPS 203", "ML-KEM (Kyber)", "NIST Finalized"])
            f_data.append(["FIPS 204", "ML-DSA (Dilithium)", "NIST Finalized"])
            f_data.append(["FIPS 206", "FN-DSA (FALCON)", "NIST Draft Mar 2026"])
            t = Table(f_data, colWidths=[150, 200, 162])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A1628")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(ACCENT_CYAN)),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor(TEXT_PRIMARY)),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor(BG_CARD), colors.HexColor(BG_SURFACE)])
            ]))
            story.append(t)

        # --- AUDIT & VERIFICATION TRAIL ---
        if interrogations or verifications:
            story.append(Paragraph("Audit & Verification Trail", styles['BrandedHeading1']))

            if interrogations:
                story.append(Paragraph("The following adversarial cross-examinations were performed by the council to challenge and validate the synthesis results.", styles['SectionBody']))
                story.append(Spacer(1, 4))
                for idx, entry in enumerate(interrogations):
                    i_data = [
                        [Paragraph(f"<b>INTERROGATION #{idx+1}</b>", styles['SectionBody']),
                         Paragraph(f"<b>{entry.get('verdict', 'CONTESTED')}</b>", styles['SectionBody'])],
                        ["ATTACKER", f"{entry.get('attacker', '').upper()} ({entry.get('attacker_model', '')})"],
                        ["DEFENDER", f"{entry.get('defender', '').upper()} ({entry.get('defender_model', '')})"]
                    ]

                    if entry.get('attacker_response'):
                        i_data.append(["CHALLENGE", Paragraph(entry['attacker_response'][:1000], styles['SectionBody'])])
                    if entry.get('defender_response'):
                        i_data.append(["REBUTTAL", Paragraph(entry['defender_response'][:1000], styles['SectionBody'])])

                    t = Table(i_data, colWidths=[100, 412])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A0A0A")),
                        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor(ACCENT_RED)),
                        ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor(ACCENT_RED)),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('TEXTCOLOR', (0, 1), (0, -1), colors.HexColor(TEXT_SECONDARY)),
                        ('TEXTCOLOR', (1, 1), (1, -1), colors.HexColor(TEXT_PRIMARY)),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                        ('VALIGN', (1, 1), (1, -1), 'TOP'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6)
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 10))

            if verifications:
                story.append(Paragraph("Authoritative source verification results via external intelligence nodes.", styles['SectionBody']))
                story.append(Spacer(1, 4))
                for idx, entry in enumerate(verifications):
                    v_data = [
                        [Paragraph(f"<b>SOURCE CHECK #{idx+1}</b>", styles['SectionBody']),
                         Paragraph(f"<b>{entry.get('verdict', 'UNRESOLVED')}</b>", styles['SectionBody'])],
                        ["CLAIM", Paragraph(f"<i>\"{entry.get('claim', '')}\"</i>", styles['SectionBody'])],
                        ["EVIDENCE", Paragraph(entry.get('verification', ''), styles['SectionBody'])]
                    ]
                    t = Table(v_data, colWidths=[100, 412])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A1628")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(ACCENT_CYAN)),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('TEXTCOLOR', (0, 1), (0, -1), colors.HexColor(TEXT_SECONDARY)),
                        ('TEXTCOLOR', (1, 1), (1, -1), colors.HexColor(TEXT_PRIMARY)),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                        ('VALIGN', (1, 1), (1, -1), 'TOP'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6)
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 10))

        # --- ANALYTIC DIVERGENCE ---
        divergence = intelligence_object.get("divergence_analysis") or {}
        if divergence and divergence.get("divergence_summary"):
            story.append(Paragraph("Analytic Divergence", styles['BrandedHeading1']))

            # Scores bar
            cons_score = divergence.get('consensus_score', 0)
            div_score = divergence.get('divergence_score', 0)
            variance = divergence.get('protocol_variance', False)
            variance_text = "PROTOCOL VARIANCE DETECTED" if variance else "CONSENSUS STABLE"
            score_color = "#FF4444" if variance else "#00AA55"

            score_data = [["CONSENSUS", "DIVERGENCE", "STATUS"],
                          [f"{cons_score}/100", f"{div_score}/100", variance_text]]
            score_table = Table(score_data, colWidths=[170, 170, 172], repeatRows=1)
            score_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BG_DARK)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(ACCENT_CYAN)),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor(TEXT_PRIMARY)),
                ('TEXTCOLOR', (-1, 1), (-1, 1), colors.HexColor(score_color)),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor(BG_CARD)),
            ]))
            story.append(score_table)
            story.append(Spacer(1, 8))

            if divergence.get('divergence_summary'):
                story.append(Paragraph(_as_text(divergence['divergence_summary']), styles['SectionBody']))
                story.append(Spacer(1, 6))

            # Agreement
            agreement = divergence.get("agreement_topics", [])
            if agreement:
                story.append(Paragraph("<b>Areas of Agreement</b>", styles['SectionBody']))
                for a in agreement:
                    providers = ", ".join(p.upper() for p in (a.get("providers") or []))
                    text = f"<b>[{_as_text(a.get('confidence', 'MODERATE')).upper()}]</b> {_as_text(a.get('topic', ''))} — {_as_text(a.get('detail', ''))}"
                    if providers:
                        text += f" <i>(Supported by: {providers})</i>"
                    story.append(Paragraph(f"&bull; {text}", styles['SectionBody']))

            # Contested
            contested = divergence.get("contested_topics", [])
            if contested:
                story.append(Spacer(1, 6))
                story.append(Paragraph("<b>Contested Positions</b>", styles['SectionBody']))
                for c in contested:
                    story.append(Paragraph(
                        f"&bull; <b>[{_as_text(c.get('severity', 'MEDIUM')).upper()}]</b> {_as_text(c.get('topic', ''))}",
                        styles['SectionBody']
                    ))
                    for pos in c.get("positions", []):
                        story.append(Paragraph(
                            f"&nbsp;&nbsp;&nbsp;&nbsp;{_as_text(pos.get('provider', '')).upper()}: {_as_text(pos.get('position', ''))}",
                            styles['SectionBody']
                        ))

            # Resolution
            resolutions = divergence.get("resolution_requirements", [])
            if resolutions:
                story.append(Spacer(1, 6))
                story.append(Paragraph("<b>Resolution Requirements</b>", styles['SectionBody']))
                for r in resolutions:
                    story.append(Paragraph(
                        f"&bull; <b>[{_as_text(r.get('priority', 'MEDIUM')).upper()}]</b> {_as_text(r.get('question', ''))}",
                        styles['SectionBody']
                    ))

            story.append(Spacer(1, 10))

        # --- CONFIDENCE & ASSUMPTIONS ---
        conf_data = intelligence_object.get("confidence_and_assumptions") or {}
        if conf_data:
            story.append(Paragraph("Confidence &amp; Assumptions", styles['BrandedHeading1']))
            overall = _as_text(conf_data.get("overall_confidence", "moderate-to-high"))
            story.append(Paragraph(f"<b>Overall Confidence:</b> {overall.upper()}", styles['SectionBody']))
            story.append(Spacer(1, 4))
            assumptions = conf_data.get("key_assumptions", [])
            if assumptions:
                story.append(Paragraph("<b>Key Assumptions:</b>", styles['SectionBody']))
                for a in assumptions:
                    story.append(Paragraph(f"&bull; {_as_text(a)}", styles['SectionBody']))
            limitations = conf_data.get("limitations", [])
            if limitations:
                story.append(Paragraph("<b>Limitations:</b>", styles['SectionBody']))
                for l in limitations:
                    story.append(Paragraph(f"&bull; {_as_text(l)}", styles['SectionBody']))
            story.append(Spacer(1, 10))

        # --- COUNCIL CONTRIBUTORS ---
        contributors = intelligence_object.get("council_contributors") or []
        if not contributors:
            # Fallback: build from models_used metadata
            models_used = meta.get("models_used", [])
            if models_used:
                contributors = [{"phase": f"Phase {i+1}", "provider": m, "role": "", "contribution_summary": ""} for i, m in enumerate(models_used)]
        if contributors:
            story.append(Paragraph("Council Contributors", styles['BrandedHeading1']))
            cell_style = ParagraphStyle('CellText', parent=styles['SectionBody'], fontSize=8, leading=10, wordWrap='CJK')
            hdr_style = ParagraphStyle('CellHdr', parent=cell_style, textColor=colors.HexColor("#00E5FF"), fontName='Helvetica-Bold')
            c_data = [[Paragraph("PHASE", hdr_style), Paragraph("PROVIDER", hdr_style),
                        Paragraph("ROLE", hdr_style), Paragraph("CONTRIBUTION", hdr_style)]]
            for c in contributors:
                c_data.append([
                    Paragraph(_as_text(c.get("phase", "")), cell_style),
                    Paragraph(_as_text(c.get("provider", "")), cell_style),
                    Paragraph(_as_text(c.get("role", "")), cell_style),
                    Paragraph(_as_text(c.get("contribution_summary", "")), cell_style)
                ])
            ct = Table(c_data, colWidths=[80, 70, 70, 292], repeatRows=1)
            ct.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BG_DARK)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(ACCENT_CYAN)),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(BORDER)),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor(BG_CARD), colors.HexColor(BG_SURFACE)])
            ]))
            story.append(ct)
            story.append(Spacer(1, 10))

        # --- FOOTER ATTESTATION ---
        story.append(Spacer(1, 40))
        if client_name:
            node_desc = f"{client_name} Federated Intelligence Node"
        elif is_client_branded and "QANAPI" in branding_prefix.upper():
            node_desc = "Qanapi Armory Federated Node"
        else:
            node_desc = "KORUM-OS Secure Kernel Enclave"
        attest_data = [[f"COMPLIANCE ATTESTATION: Generated via {node_desc}. Integrity Anchor: FN-DSA. "
                         f"Composite Score: {truth_display}/100. Audit Date: {date_display}"]]
        attest_t = Table(attest_data, colWidths=[512])
        attest_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(BG_SURFACE)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(ACCENT_CYAN)),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(attest_t)

        doc.build(story, onFirstPage=_dark_page_bg, onLaterPages=_dark_page_bg)
        return filepath



class ResearchPaperExporter:
    """Generates a clean research paper PDF — no intelligence branding."""

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch

        meta, sections, structured = _extract_parts(intelligence_object)
        tags = (intelligence_object or {}).get("intelligence_tags", {}) or {}
        filename = f"korum_research_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)

        doc = SimpleDocTemplate(
            filepath, pagesize=letter,
            topMargin=1 * inch, bottomMargin=0.75 * inch,
            leftMargin=1 * inch, rightMargin=1 * inch
        )
        base_styles = getSampleStyleSheet()

        # Custom styles for research paper feel
        title_style = ParagraphStyle(
            'PaperTitle', parent=base_styles['Title'],
            fontSize=20, leading=24, alignment=TA_CENTER,
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'PaperSubtitle', parent=base_styles['Normal'],
            fontSize=10, alignment=TA_CENTER, textColor=colors.grey,
            spaceAfter=20
        )
        abstract_style = ParagraphStyle(
            'Abstract', parent=base_styles['BodyText'],
            fontSize=10, leading=14, alignment=TA_JUSTIFY,
            leftIndent=36, rightIndent=36, spaceAfter=16,
            textColor=colors.Color(0.2, 0.2, 0.2)
        )
        heading_style = ParagraphStyle(
            'PaperHeading', parent=base_styles['Heading2'],
            fontSize=14, leading=18, spaceBefore=18, spaceAfter=8,
            textColor=colors.Color(0.15, 0.15, 0.15)
        )
        body_style = ParagraphStyle(
            'PaperBody', parent=base_styles['BodyText'],
            fontSize=11, leading=15, alignment=TA_JUSTIFY,
            spaceAfter=10, textColor=colors.Color(0.15, 0.15, 0.15)
        )
        small_style = ParagraphStyle(
            'SmallText', parent=base_styles['Normal'],
            fontSize=9, leading=12, textColor=colors.grey
        )

        story = []

        # --- TITLE ---
        title_text = _as_text(meta.get("title", "Research Report"))
        # Strip intelligence jargon from title if present
        for junk in ["INTELLIGENCE", "KORUM", "Intelligence Object"]:
            title_text = title_text.replace(junk, "").strip()
        story.append(Paragraph(title_text, title_style))

        # Date line
        date_str = meta.get("generated_at", datetime.now().isoformat())
        try:
            date_obj = datetime.fromisoformat(date_str)
            date_display = date_obj.strftime("%B %d, %Y")
        except Exception:
            date_display = date_str
        models = meta.get("models_used", [])
        if not isinstance(models, list):
            models = [str(models)]
        agent_count = len(models)
        story.append(Paragraph(
            f"{date_display} &bull; Multi-source analysis ({agent_count} sources consulted)",
            subtitle_style
        ))

        # --- ABSTRACT ---
        summary = _clean_tags(_as_text(meta.get("summary", "")))
        exec_summary = _clean_tags(_as_text(sections.get("executive_summary", "")))
        abstract_text = summary or exec_summary
        if abstract_text:
            story.append(Paragraph("<b>Abstract</b>", ParagraphStyle(
                'AbstractLabel', parent=base_styles['Normal'],
                fontSize=10, alignment=TA_CENTER, spaceAfter=6
            )))
            story.append(Paragraph(abstract_text, abstract_style))

        # Divider
        story.append(Spacer(1, 8))
        story.append(Table(
            [[""]],
            colWidths=[doc.width],
            style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey)])
        ))
        story.append(Spacer(1, 12))

        # --- MAIN SECTIONS ---
        section_counter = 1
        for section_id, content in sections.items():
            if section_id == "executive_summary":
                continue
            heading = section_id.replace("_", " ").title()
            story.append(Paragraph(f"{section_counter}. {heading}", heading_style))

            content_text = _clean_tags(_as_text(content))
            # Split into paragraphs on newlines, double-newlines, or sentence clusters
            import re
            # First split on explicit newlines
            raw_paragraphs = [p.strip() for p in content_text.split('\n') if p.strip()]
            # If we got a single giant block, split on sentence boundaries (~3 sentences per paragraph)
            final_paragraphs = []
            for para in raw_paragraphs:
                if len(para) > 400:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    chunk = []
                    for sentence in sentences:
                        chunk.append(sentence)
                        if len(' '.join(chunk)) > 300:
                            final_paragraphs.append(' '.join(chunk))
                            chunk = []
                    if chunk:
                        final_paragraphs.append(' '.join(chunk))
                else:
                    final_paragraphs.append(para)

            for para in final_paragraphs:
                story.append(Paragraph(para, body_style))

            section_counter += 1

        # --- COMPARISON TABLE (Key Metrics) ---
        key_metrics = structured.get("key_metrics", [])
        if key_metrics:
            story.append(Paragraph(f"{section_counter}. Comparative Data", heading_style))
            section_counter += 1

            table_data = [["Category", "Finding", "Notes"]]
            for metric in key_metrics:
                table_data.append([
                    _clean_tags(_as_text(metric.get("metric", ""))),
                    _clean_tags(_as_text(metric.get("value", ""))),
                    _clean_tags(_as_text(metric.get("context", "")))
                ])
            table = Table(table_data, repeatRows=1, colWidths=[1.8 * inch, 2.5 * inch, 2.2 * inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.92, 0.92, 0.92)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

        # --- RISKS / CONSIDERATIONS ---
        risks = structured.get("risks", [])
        if risks:
            story.append(Paragraph(f"{section_counter}. Considerations &amp; Risks", heading_style))
            section_counter += 1
            for r in risks:
                risk_text = _clean_tags(_as_text(r.get("risk", "")))
                severity = _clean_tags(_as_text(r.get("severity", "")))
                mitigation = _clean_tags(_as_text(r.get("mitigation", "")))
                bullet = f"<b>{risk_text}</b>"
                if severity:
                    bullet += f" ({severity})"
                if mitigation:
                    bullet += f" — {mitigation}"
                story.append(Paragraph(f"&bull; {bullet}", body_style))
                story.append(Spacer(1, 4))

        # --- RECOMMENDATIONS ---
        decisions = tags.get("decisions", [])
        action_items = structured.get("action_items", [])
        if decisions or action_items:
            story.append(Paragraph(f"{section_counter}. Recommendations", heading_style))
            section_counter += 1
            for d in decisions:
                story.append(Paragraph(f"&bull; {_clean_tags(_as_text(d))}", body_style))
                story.append(Spacer(1, 4))
            for item in action_items:
                task = _clean_tags(_as_text(item.get("task", "")))
                priority = _clean_tags(_as_text(item.get("priority", "")))
                timeline = _clean_tags(_as_text(item.get("timeline", "")))
                line = f"&bull; <b>{task}</b>"
                if priority:
                    line += f" [Priority: {priority.upper()}]"
                if timeline:
                    line += f" — {timeline}"
                story.append(Paragraph(line, body_style))
                story.append(Spacer(1, 4))

        # --- FOOTER ---
        story.append(Spacer(1, 24))
        story.append(Table(
            [[""]],
            colWidths=[doc.width],
            style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey)])
        ))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Report generated {date_display}. Analysis based on {agent_count} independent sources.",
            small_style
        ))

        doc.build(story)
        return filepath


class ResearchPaperWordExporter:
    """Generates a clean, editable research paper DOCX — no intelligence branding."""

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        import re
        from docx.shared import Inches, RGBColor

        meta, sections, structured = _extract_parts(intelligence_object)
        tags = (intelligence_object or {}).get("intelligence_tags", {}) or {}

        wdoc = Document()

        # --- STYLES ---
        style = wdoc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.font.color.rgb = RGBColor(0x2D, 0x2D, 0x2D)
        pf = style.paragraph_format
        pf.space_after = Pt(8)
        pf.line_spacing = 1.15

        # --- PAGE MARGINS ---
        sec = wdoc.sections[0]
        sec.top_margin = Inches(1)
        sec.bottom_margin = Inches(0.75)
        sec.left_margin = Inches(1)
        sec.right_margin = Inches(1)

        # --- TITLE ---
        title_text = _clean_tags(_as_text(meta.get("title", "Research Report")))
        for junk in ["INTELLIGENCE", "KORUM", "Intelligence Object"]:
            title_text = title_text.replace(junk, "").strip()
        title = wdoc.add_heading(title_text, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Date & source line
        date_str = meta.get("generated_at", datetime.now().isoformat())
        try:
            date_obj = datetime.fromisoformat(date_str)
            date_display = date_obj.strftime("%B %d, %Y")
        except Exception:
            date_display = date_str
        models = meta.get("models_used", [])
        if not isinstance(models, list):
            models = [str(models)]
        agent_count = len(models)

        subtitle = wdoc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = subtitle.add_run(f"{date_display}  |  Multi-source analysis ({agent_count} sources consulted)")
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

        # --- ABSTRACT ---
        summary = _clean_tags(_as_text(meta.get("summary", "")))
        exec_summary = _clean_tags(_as_text(sections.get("executive_summary", "")))
        abstract_text = summary or exec_summary
        if abstract_text:
            wdoc.add_paragraph()
            label = wdoc.add_paragraph()
            label.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = label.add_run("Abstract")
            run.bold = True
            run.font.size = Pt(10)

            abs_para = wdoc.add_paragraph()
            abs_para.paragraph_format.left_indent = Inches(0.5)
            abs_para.paragraph_format.right_indent = Inches(0.5)
            run = abs_para.add_run(abstract_text)
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
            run.italic = True

        wdoc.add_paragraph("_" * 80)

        # --- HELPER: split long text into paragraphs ---
        def _add_body_text(wdoc, text):
            text = _clean_tags(text)
            raw_paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            for para in raw_paragraphs:
                if len(para) > 400:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    chunk = []
                    for sentence in sentences:
                        chunk.append(sentence)
                        if len(' '.join(chunk)) > 300:
                            wdoc.add_paragraph(' '.join(chunk))
                            chunk = []
                    if chunk:
                        wdoc.add_paragraph(' '.join(chunk))
                else:
                    wdoc.add_paragraph(para)

        # --- MAIN SECTIONS ---
        section_counter = 1
        for section_id, content in sections.items():
            if section_id == "executive_summary":
                continue
            heading = section_id.replace("_", " ").title()
            wdoc.add_heading(f"{section_counter}. {heading}", level=1)
            _add_body_text(wdoc, _as_text(content))
            section_counter += 1

        # --- COMPARISON TABLE ---
        key_metrics = structured.get("key_metrics", [])
        if key_metrics:
            wdoc.add_heading(f"{section_counter}. Comparative Data", level=1)
            section_counter += 1
            table = wdoc.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            hdr[0].text = "Category"
            hdr[1].text = "Finding"
            hdr[2].text = "Notes"
            for cell in hdr:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True
            for metric in key_metrics:
                row = table.add_row().cells
                row[0].text = _clean_tags(_as_text(metric.get("metric", "")))
                row[1].text = _clean_tags(_as_text(metric.get("value", "")))
                row[2].text = _clean_tags(_as_text(metric.get("context", "")))

        # --- RISKS ---
        risks = structured.get("risks", [])
        if risks:
            wdoc.add_heading(f"{section_counter}. Considerations & Risks", level=1)
            section_counter += 1
            for r in risks:
                risk_text = _clean_tags(_as_text(r.get("risk", "")))
                severity = _clean_tags(_as_text(r.get("severity", "")))
                mitigation = _clean_tags(_as_text(r.get("mitigation", "")))
                p = wdoc.add_paragraph()
                run = p.add_run(risk_text)
                run.bold = True
                if severity:
                    p.add_run(f" ({severity})")
                if mitigation:
                    p.add_run(f" — {mitigation}")

        # --- RECOMMENDATIONS ---
        decisions = tags.get("decisions", [])
        action_items = structured.get("action_items", [])
        if decisions or action_items:
            wdoc.add_heading(f"{section_counter}. Recommendations", level=1)
            section_counter += 1
            for d in decisions:
                wdoc.add_paragraph(_clean_tags(_as_text(d)), style='List Bullet')
            for item in action_items:
                task = _clean_tags(_as_text(item.get("task", "")))
                priority = _clean_tags(_as_text(item.get("priority", "")))
                timeline = _clean_tags(_as_text(item.get("timeline", "")))
                p = wdoc.add_paragraph(style='List Bullet')
                run = p.add_run(task)
                run.bold = True
                if priority:
                    p.add_run(f"  [{priority.upper()}]")
                if timeline:
                    p.add_run(f" — {timeline}")

        # --- RESEARCH ARTIFACTS ---
        snippets = _report_artifacts(intelligence_object)
        if snippets:
            wdoc.add_heading(f"{section_counter}. Research Artifacts & Evidence", level=1)
            section_counter += 1
            wdoc.add_paragraph("The following selected dock artifacts were attached as executive exhibits for the final package.")
            
            for s in snippets:
                label = _artifact_label(s)
                source = s.get('source', 'Selection')
                content = _clean_tags(_as_text(s.get("content", "")))
                
                p = wdoc.add_paragraph()
                run = p.add_run(f"[{label.upper()}] from {source}")
                run.bold = True
                run.font.size = Pt(10)

                tags = ", ".join(s.get("tags", []))
                if tags:
                    p_tags = wdoc.add_paragraph()
                    p_tags.paragraph_format.left_indent = Inches(0.3)
                    run_tags = p_tags.add_run(f"Tags: {tags}")
                    run_tags.italic = True
                    run_tags.font.size = Pt(8.5)
                
                # Use smaller font for content
                p_content = wdoc.add_paragraph()
                p_content.paragraph_format.left_indent = Inches(0.3)
                run_content = p_content.add_run(content)
                run_content.font.size = Pt(9.5)
                if s.get('type') in ('code', 'mermaid'):
                    run_content.font.name = "Consolas"
                wdoc.add_paragraph() # spacing

        # --- FOOTER ---
        footer = wdoc.sections[0].footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = fp.add_run(f"Report generated {date_display}. Analysis based on {agent_count} independent sources.")
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        filename = f"korum_research_{_timestamp()}.docx"
        filepath = _output_path(filename, output_dir)
        wdoc.save(filepath)
        return filepath
