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


def _normalize_theme(theme_id):
    theme_key = _as_text(theme_id).upper() or "BONE_FIELD"
    return theme_key if theme_key in THEME_COLORS else "BONE_FIELD"


def _safe_paragraph(text, style):
    return Paragraph(escape(_as_text(text)).replace("\n", "<br/>"), style)


def _table_from_rows(headers, rows):
    if not headers or not rows:
        return None
    clean_headers = [_as_text(h) for h in headers]
    clean_rows = [[_as_text(cell) for cell in row] for row in rows if any(_as_text(cell) for cell in row)]
    if not clean_rows:
        return None
    return {"headers": clean_headers, "rows": clean_rows}


def _parse_structured_table_payload(raw_payload):
    try:
        data = json.loads(raw_payload.strip())
    except Exception:
        return None

    headers = []
    rows = []
    if isinstance(data, dict):
        if isinstance(data.get("headers"), list):
            headers = [_as_text(h) for h in data.get("headers", [])]
        if isinstance(data.get("rows"), list):
            rows = data["rows"]
        elif isinstance(data.get("data"), list):
            rows = data["data"]
        elif all(isinstance(v, (str, int, float)) for v in data.values()):
            headers = ["Field", "Value"]
            rows = [[k, v] for k, v in data.items()]
    elif isinstance(data, list):
        rows = data

    if rows and isinstance(rows[0], dict):
        if not headers:
            headers = list(rows[0].keys())
        matrix = [[row.get(h, "") for h in headers] for row in rows]
        return _table_from_rows(headers, matrix)

    if rows and isinstance(rows[0], (list, tuple)):
        if not headers and len(rows) > 1:
            headers = [_as_text(cell) for cell in rows[0]]
            rows = rows[1:]
        elif not headers:
            headers = [f"Column {idx + 1}" for idx in range(len(rows[0]))]
        return _table_from_rows(headers, rows)

    return None


def _parse_markdown_table_block(block):
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) < 2 or not all(line.startswith("|") and line.endswith("|") for line in lines[:2]):
        return None

    separator = re.sub(r"[|\-:\s]", "", lines[1])
    if separator:
        return None

    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines[2:]]
    return _table_from_rows(headers, rows)


def _parse_delimited_table_block(block):
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    delimiter = None
    for candidate in ("\t", ","):
        if all(candidate in line for line in lines[:2]):
            delimiter = candidate
            break
    if not delimiter:
        return None

    parsed = [[cell.strip() for cell in line.split(delimiter)] for line in lines]
    width = len(parsed[0])
    if width < 2 or any(len(row) != width for row in parsed):
        return None
    return _table_from_rows(parsed[0], parsed[1:])


def _parse_key_value_block(lines):
    pairs = []
    for line in lines:
        match = re.match(r"^([^:]{2,120}):\s+(.+)$", line)
        if not match:
            return None
        pairs.append([match.group(1).strip(), match.group(2).strip()])
    if len(pairs) < 2:
        return None
    return _table_from_rows(["Metric", "Value"], pairs)


def _extract_content_blocks(text):
    raw_text = _as_text(text)
    if not raw_text:
        return []

    blocks = []
    last_end = 0
    pattern = re.compile(r"\[STRUCTURED_TABLE\]([\s\S]*?)\[/STRUCTURED_TABLE\]", re.IGNORECASE)
    for match in pattern.finditer(raw_text):
        if match.start() > last_end:
            blocks.extend(_extract_content_blocks(raw_text[last_end:match.start()]))
        table_block = _parse_structured_table_payload(match.group(1))
        if table_block:
            blocks.append({"type": "table", **table_block})
        last_end = match.end()

    if last_end:
        if last_end < len(raw_text):
            blocks.extend(_extract_content_blocks(raw_text[last_end:]))
        return blocks

    for chunk in re.split(r"\n\s*\n", raw_text):
        chunk = chunk.strip()
        if not chunk:
            continue

        markdown_table = _parse_markdown_table_block(chunk)
        if markdown_table:
            blocks.append({"type": "table", **markdown_table})
            continue

        delimited_table = _parse_delimited_table_block(chunk)
        if delimited_table:
            blocks.append({"type": "table", **delimited_table})
            continue

        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if len(lines) >= 3 and ":" not in lines[0]:
            kv_table = _parse_key_value_block(lines[1:])
            if kv_table:
                blocks.append({"type": "heading", "text": lines[0]})
                blocks.append({"type": "table", **kv_table})
                continue

        kv_table = _parse_key_value_block(lines)
        if kv_table:
            blocks.append({"type": "table", **kv_table})
            continue

        blocks.append({"type": "paragraph", "text": chunk})

    return blocks


def _first_table_block(text):
    for block in _extract_content_blocks(text):
        if block.get("type") == "table":
            return block
    return None


def _artifact_matches(label, section_title, provider_name):
    text = _as_text(label).upper()
    return section_title in text or provider_name in text


def _pdf_col_widths(total_width, column_count):
    if column_count <= 1:
        return [total_width]
    if column_count == 2:
        return [total_width * 0.64, total_width * 0.36]
    return [total_width / column_count] * column_count


def _build_pdf_table(block, styles, total_width, palette):
    headers = block.get("headers") or []
    rows = block.get("rows") or []
    if not headers or not rows:
        return None

    table_rows = [
        [Paragraph(f"<b>{escape(_as_text(cell))}</b>", styles["ExecTableHead"]) for cell in headers]
    ]
    table_rows.extend(
        [
            [Paragraph(escape(_as_text(cell)).replace("\n", "<br/>"), styles["ExecTableCell"]) for cell in row]
            for row in rows
        ]
    )
    tbl = Table(table_rows, colWidths=_pdf_col_widths(total_width, len(headers)), repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(palette["shade_alt"])),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(palette["accent_dark"])),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor(palette["line"])),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette["line_strong"])),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(palette["paper"]), colors.HexColor(palette["bg_shade"])]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def _render_pdf_blocks(blocks, styles, total_width, palette):
    flowables = []
    for block in blocks:
        if block["type"] == "paragraph":
            flowables.append(_safe_paragraph(block["text"], styles["ExecBody"]))
            flowables.append(Spacer(1, 8))
        elif block["type"] == "heading":
            flowables.append(_safe_paragraph(block["text"], styles["ExecSectionSubhead"]))
            flowables.append(Spacer(1, 5))
        elif block["type"] == "table":
            table = _build_pdf_table(block, styles, total_width, palette)
            if table:
                flowables.append(table)
                flowables.append(Spacer(1, 10))
    return flowables


def _resolve_session_id(meta, intelligence_object):
    mission_ctx = intelligence_object.get("_mission_context") or {}
    return _as_text(
        meta.get("session_id")
        or meta.get("id")
        or intelligence_object.get("session_id")
        or intelligence_object.get("id")
        or mission_ctx.get("session_id")
        or "KO-INT-9999"
    ).upper()


def _normalize_truth_score(raw_score):
    if raw_score is None or raw_score == "":
        return 85
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return 85
    if score <= 1:
        score *= 100
    return int(round(score))

# --- BRANDING CONFIG ---

IRON_DISPATCH = {
    "accent": "#b44c3d",
    "accent_dark": "#45382d",
    "text": "#332d28",
    "label": "#7e746a",
    "bg_shade": "#efe6dc",
    "shade_alt": "#e0d2c5",
    "paper": "#f8f2ea",
    "line": "#d2c0b2",
    "line_strong": "#b44c3d",
}

DEEP_WATER = {
    "accent": "#16b7c8",
    "accent_dark": "#263d73",
    "text": "#1f2f44",
    "label": "#708399",
    "bg_shade": "#e7edf3",
    "shade_alt": "#d2dce7",
    "paper": "#f4f7fa",
    "line": "#bfd0de",
    "line_strong": "#16b7c8",
}

BONE_FIELD = {
    "accent": "#395e46",
    "accent_dark": "#234333",
    "text": "#2f2b24",
    "label": "#6f675a",
    "bg_shade": "#ede6d8",
    "shade_alt": "#d8d0bf",
    "paper": "#f6f0e3",
    "line": "#cbbfa9",
    "line_strong": "#4c6e57",
}

THEME_COLORS = {
    "IRON_DISPATCH": IRON_DISPATCH,
    "DEEP_WATER": DEEP_WATER,
    "BONE_FIELD": BONE_FIELD,
    "ARCHITECT": IRON_DISPATCH,
    "NEON_DESERT": BONE_FIELD,
    "CARBON_STEEL": DEEP_WATER,
    "STEEL_RUBY": IRON_DISPATCH,
}

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
        
        # DNA: Color Palette - locked to Bone & Field across legacy theme ids
        theme_id = _normalize_theme(meta.get('theme', 'BONE_FIELD'))
        tc = THEME_COLORS[theme_id]
        
        ACCENT_HEX = tc["accent"]
        TEXT_HEX = tc["text"]
        LABEL_HEX = tc["label"]
        SHADE_HEX = tc["bg_shade"]
        
        # DNA: Styles - Curated for Executive Scan Patterns
        styles.add(ParagraphStyle('ExecLabel', fontSize=6.5, leading=8, textColor=colors.HexColor(LABEL_HEX), fontName='Helvetica-Bold', letterSpacing=0.5))
        styles.add(ParagraphStyle('ExecSig', fontSize=7, leading=10, textColor=colors.HexColor(LABEL_HEX), alignment=TA_RIGHT, fontName='Helvetica'))
        styles.add(ParagraphStyle('ExecTitle', fontSize=24, leading=28, textColor=colors.HexColor(tc["accent_dark"]), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ExecImpact', fontSize=11, leading=16, textColor=colors.HexColor(tc["accent_dark"]), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ExecBody', fontSize=8.5, leading=12.5, textColor=colors.HexColor(TEXT_HEX), fontName='Helvetica'))
        styles.add(ParagraphStyle('ExecAudit', fontSize=7, leading=9.5, textColor=colors.HexColor(LABEL_HEX), fontName='Helvetica'))
        styles.add(ParagraphStyle('ExecSectionSubhead', fontSize=8, leading=10, textColor=colors.HexColor(tc["accent_dark"]), fontName='Helvetica-BoldOblique'))
        styles.add(ParagraphStyle('ExecTableHead', fontSize=7, leading=8, textColor=colors.HexColor(tc["accent_dark"]), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('ExecTableCell', fontSize=7.5, leading=9.5, textColor=colors.HexColor(TEXT_HEX), fontName='Helvetica'))
        styles.add(ParagraphStyle('StatBig', fontSize=20, leading=24, textColor=colors.HexColor(tc["accent_dark"]), fontName='Helvetica-Bold', alignment=TA_CENTER))
        styles.add(ParagraphStyle('StatCaption', fontSize=6.5, leading=8, textColor=colors.HexColor(LABEL_HEX), fontName='Helvetica-Bold', alignment=TA_CENTER, letterSpacing=0.5))
        styles.add(ParagraphStyle('PullQuoteInline', fontSize=8, leading=11, textColor=colors.HexColor(TEXT_HEX), fontName='Helvetica-Oblique'))
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
        story.append(Table([[[Paragraph("", styles['ExecBody'])]]], colWidths=[540], rowHeights=[2.5], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(ACCENT_HEX))]))
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
        
        sidebar_content = [
            Paragraph("MISSION SNAPSHOT", styles['StatCaption']),
            Spacer(1, 5),
            Paragraph(
                escape(f"{workflow_label} | {client_name} | SESSION {doc._session_id}").replace(" | ", "<br/>"),
                styles['ExecAudit']
            ),
        ]
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
            value_row = []
            label_row = []
            for km in key_metrics[:3]:
                val = _as_text(km.get('value', '—'))
                lab = _as_text(km.get('metric', '')).upper()
                value_row.append(Paragraph(val, styles['StatBig']))
                label_row.append(Paragraph(lab, styles['StatCaption']))
            
            while len(value_row) < 3:
                value_row.append(Paragraph("", styles['StatBig']))
                label_row.append(Paragraph("", styles['StatCaption']))
            s_tab = Table([value_row, label_row], colWidths=[180, 180, 180], style=[
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(tc["line"])),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor(tc["line"])),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(SHADE_HEX)),
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
            
            left_blocks = _extract_content_blocks(content)

            # Match sidebar artifact
            local_visual = None
            for art in artifacts:
                label = _artifact_label(art)
                if _artifact_matches(label, sec_title, prov_name):
                    local_visual = art
                    artifacts.remove(art)
                    break
            
            # Try pull-quote if no visual
            local_quote = None
            prov_key = prov_name.lower()
            prov_data = card_results.get(prov_key) or {}
            if not local_visual:
                claims = prov_data.get("verified_claims") or []
                if claims:
                    local_quote = claims[0]

            if not any(block.get("type") == "table" for block in left_blocks):
                provider_table = _first_table_block(prov_data.get("response", ""))
                if provider_table:
                    left_blocks.append({"type": "heading", "text": "SOURCE TABLE"})
                    left_blocks.append(provider_table)

            narrative_blocks = [block for block in left_blocks if block.get("type") != "table"]
            table_blocks = [block for block in left_blocks if block.get("type") == "table"]
            left_col = _render_pdf_blocks(narrative_blocks, styles, 340, tc) or [Paragraph("", styles['ExecBody'])]

            right_col = [
                Paragraph("SECTION CONTEXT", styles['StatCaption']),
                Spacer(1, 4),
                Paragraph(f"{prov_name} // {sec_title}", styles['ExecAudit'])
            ]
            if local_visual:
                right_col.extend([
                    Spacer(1, 6),
                    Paragraph(_artifact_label(local_visual), styles['StatCaption']),
                    Spacer(1, 4),
                    Paragraph(escape(_as_text(local_visual.get('content',''))[:220]).replace("\n","<br/>"), styles['ExecAudit'])
                ])
            elif local_quote:
                q_text = escape(_as_text(local_quote.get('claim','')))
                right_col.extend([
                    Spacer(1, 8),
                    Paragraph(f"&ldquo;{q_text}&rdquo;", styles['PullQuoteInline']),
                    Spacer(1, 4),
                    Paragraph(prov_name, styles['ExecAudit'])
                ])

            story.append(Paragraph(node_id, styles['ExecLabel']))
            story.append(Spacer(1, 6))
            story.append(Table([[[Paragraph("", styles['ExecBody'])]]], colWidths=[540], rowHeights=[1], style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(tc["line"]))]))
            story.append(Spacer(1, 10))
            
            sec_tab = Table([[left_col, right_col]], colWidths=[380, 160])
            sec_tab.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (0,0), 0),
                ('LEFTPADDING', (1,0), (1,0), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('BACKGROUND', (1,0), (1,0), colors.HexColor(tc["paper"])),
                ('BOX', (1,0), (1,0), 0.4, colors.HexColor(tc["line"])),
                ('TOPPADDING', (1,0), (1,0), 8),
                ('BOTTOMPADDING', (1,0), (1,0), 8),
            ]))
            story.append(sec_tab)
            for table_block in table_blocks:
                table_flowable = _build_pdf_table(table_block, styles, 540, tc)
                if table_flowable:
                    story.append(table_flowable)
                    story.append(Spacer(1, 10))
            story.append(Spacer(1, 20))

        # 5. --- CONSENSUS FOOTER ---
        truth_raw = meta.get("composite_truth_score")
        truth_int = int(float(truth_raw if truth_raw is not None else 0.85) * 100)
        consensus_summary = _as_text(divergence.get("divergence_summary", "")) or "Council reached operational consensus."
        cons_data = [
            [Paragraph("COUNCIL CONSENSUS", styles['ExecLabel']), Paragraph("", styles['Cons'])],
            [Paragraph(f"<i>{escape(consensus_summary)}</i>", styles['Cons']),
             Paragraph(f"<b>{truth_int}</b><br/><font size='7'>TRUTH SCORE / 100</font>", styles['ConsScore'])]
        ]
        cons_tab = Table(cons_data, colWidths=[410, 130])
        cons_tab.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(tc["accent_dark"])),
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
    def _set_run_style(run, *, size=None, bold=False, italic=False, color=None):
        if size is not None:
            run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic
        if color:
            run.font.color.rgb = RGBColor.from_string(color.lstrip('#'))

    @staticmethod
    def _clear_cell(cell):
        cell.text = ""

    @staticmethod
    def _add_paragraph(container, text="", *, size=9, bold=False, italic=False, color=None, align=None):
        p = container.add_paragraph()
        if align is not None:
            p.alignment = align
        run = p.add_run(_as_text(text))
        WordExporter._set_run_style(run, size=size, bold=bold, italic=italic, color=color)
        return p

    @staticmethod
    def _render_word_table(container, block, theme):
        headers = block.get("headers") or []
        rows = block.get("rows") or []
        if not headers or not rows:
            return None

        table = container.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"

        for idx, header in enumerate(headers):
            cell = table.rows[0].cells[idx]
            WordExporter._set_cell_background(cell, theme["shade_alt"].lstrip('#'))
            p = cell.paragraphs[0]
            run = p.add_run(_as_text(header))
            WordExporter._set_run_style(run, size=8, bold=True, color=theme["accent_dark"])

        for row in rows:
            cells = table.add_row().cells
            for idx, value in enumerate(row):
                p = cells[idx].paragraphs[0]
                run = p.add_run(_as_text(value))
                WordExporter._set_run_style(run, size=8.5, color=theme["text"])

        return table

    @staticmethod
    def _render_word_blocks(container, blocks, theme):
        for block in blocks:
            if block["type"] == "paragraph":
                WordExporter._add_paragraph(container, block["text"], size=9, color=theme["text"])
            elif block["type"] == "heading":
                WordExporter._add_paragraph(container, block["text"], size=8, bold=True, italic=True, color=theme["accent_dark"])
            elif block["type"] == "table":
                WordExporter._render_word_table(container, block, theme)

    @staticmethod
    def _add_spacing(doc, count=1):
        for _ in range(count):
            doc.add_paragraph()

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, _, _ = _extract_parts(intelligence_object)
        doc = Document()
        
        # DNA: SHARED THEME - specialist dynamic resolution
        theme_id = _normalize_theme(meta.get('theme', 'BONE_FIELD'))
        tc = THEME_COLORS[theme_id]
        
        ACCENT_HEX = tc["accent"].lstrip('#')
        DIM_GRAY = tc["label"].lstrip('#')
        s_rgb = RGBColor(*WordExporter._hex_to_rgb(ACCENT_HEX))

        mission_ctx = intelligence_object.get("_mission_context") or {}
        client_name = _as_text(mission_ctx.get("client", "")).strip() or "DECISION COMMANDER ALPHA"
        artifacts = _report_artifacts(intelligence_object)
        card_results = intelligence_object.get("_card_results") or {}
        contributors = intelligence_object.get("council_contributors") or []
        divergence = intelligence_object.get("divergence_analysis") or {}
        session_id = _resolve_session_id(meta, intelligence_object)

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
        r_run = r_p.add_run(f"KORUM-OS\n{client_name}\nSESSION {session_id}\nCOUNCIL: {len(contributors)} AGENTS")
        r_run.font.size = Pt(7)
        r_run.font.color.rgb = RGBColor.from_string(DIM_GRAY)
        
        # Title
        t_p = doc.add_paragraph()
        t_run = t_p.add_run(_as_text(meta.get('title') or 'COMMAND_NODE').upper())
        t_run.bold = True
        t_run.font.size = Pt(22)
        t_run.font.color.rgb = s_rgb
        
        # Thick Rule (Executive Baseline)
        u_tab = doc.add_table(rows=1, cols=1)
        WordExporter._set_cell_background(u_tab.rows[0].cells[0], ACCENT_HEX)
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
        meta_cell = sum_tab.rows[0].cells[1]
        WordExporter._clear_cell(meta_cell)
        WordExporter._set_cell_background(meta_cell, tc["bg_shade"].lstrip('#'))
        WordExporter._add_paragraph(meta_cell, "MISSION SNAPSHOT", size=7, bold=True, color=DIM_GRAY)
        WordExporter._add_paragraph(meta_cell, workflow := (_as_text(meta.get('workflow')).upper() or 'STRATEGIC_INTEL'), size=8, color=ACCENT_HEX)
        WordExporter._add_paragraph(meta_cell, client_name, size=8, color=tc["text"])
        WordExporter._add_paragraph(meta_cell, f"SESSION {session_id}", size=8, color=tc["text"])
        
        WordExporter._add_spacing(doc)

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
            WordExporter._add_spacing(doc)

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

            left_blocks = _extract_content_blocks(content)

            # Match artifact
            local_visual = None
            for art in artifacts:
                label = _artifact_label(art)
                if _artifact_matches(label, sec_title, prov_name):
                    local_visual = art
                    artifacts.remove(art)
                    break

            prov_key = prov_name.lower()
            prov_data = card_results.get(prov_key) or {}
            if not any(block.get("type") == "table" for block in left_blocks):
                provider_table = _first_table_block(prov_data.get("response", ""))
                if provider_table:
                    left_blocks.append({"type": "heading", "text": "SOURCE TABLE"})
                    left_blocks.append(provider_table)

            narrative_blocks = [block for block in left_blocks if block.get("type") != "table"]
            table_blocks = [block for block in left_blocks if block.get("type") == "table"]

            n_tab = doc.add_table(rows=1, cols=2)
            n_tab.columns[0].width = Inches(4.5)
            n_tab.columns[1].width = Inches(2.0)

            left_cell = n_tab.rows[0].cells[0]
            right_cell = n_tab.rows[0].cells[1]
            WordExporter._clear_cell(left_cell)
            WordExporter._clear_cell(right_cell)
            WordExporter._set_cell_background(right_cell, tc["bg_shade"].lstrip('#'))

            WordExporter._render_word_blocks(left_cell, narrative_blocks, tc)

            WordExporter._add_paragraph(right_cell, "SECTION CONTEXT", size=7, bold=True, color=DIM_GRAY)
            WordExporter._add_paragraph(right_cell, f"{prov_name} // {sec_title}", size=8, color=tc["text"])

            if local_visual:
                WordExporter._add_paragraph(right_cell, _artifact_label(local_visual), size=8, bold=True, color=ACCENT_HEX)
                WordExporter._add_paragraph(right_cell, _as_text(local_visual.get('content', ''))[:220], size=7, color=DIM_GRAY)
            else:
                claims = prov_data.get("verified_claims") or []
                if claims:
                    WordExporter._add_paragraph(right_cell, f"\"{_as_text(claims[0].get('claim', ''))}\"", size=8, italic=True, color=tc["text"])
                    WordExporter._add_paragraph(right_cell, prov_name, size=7, color=DIM_GRAY)

            for table_block in table_blocks:
                WordExporter._render_word_table(doc, table_block, tc)

            WordExporter._add_spacing(doc)

        # 5. --- CONSENSUS FOOTER ---
        truth_int = _normalize_truth_score(meta.get("composite_truth_score"))
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
