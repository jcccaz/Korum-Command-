# CONFIDENTIAL - TRADE SECRET
# Proprietary KorumOS source code. Access is limited to authorized personnel
# and collaborators operating under written confidentiality obligations.

import base64
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
    label = _as_text(art.get('title') or art.get('name') or '').strip()
    raw_content = _as_text(art.get('content', '')).lstrip()
    if raw_content.startswith('<svg'):
        return 'CHART'
    if not label:
        art_type = _as_text(art.get('type') or '').upper()
        if art_type in ('VISUALIZATION', 'MERMAID', 'CHART', 'SVG'):
            label = 'CHART'
        elif art_type in ('CSV', 'TABLE', 'DATA'):
            label = 'DATA TABLE'
        else:
            # Only use recognized types — suppress stray labels like CODE, TEXT, etc.
            label = ''
    return label.upper()


def _is_raw_svg_artifact(art):
    return _as_text((art or {}).get('content', '')).lstrip().startswith('<svg')

def _report_artifacts(o):
    """Filter snippets for inclusion in the report."""
    apps = o.get("docked_snippets") or []
    return [a for a in apps if a.get('includeInReport') is True]


def _normalize_theme(theme_id):
    theme_key = _as_text(theme_id).upper() or "BONE_FIELD"
    return theme_key if theme_key in THEME_COLORS else "BONE_FIELD"


def _safe_paragraph(text, style):
    return Paragraph(escape(_as_text(text)).replace("\n", "<br/>"), style)


def _artifact_unavailable_note(styles):
    return Paragraph("Chart artifact unavailable for export capture.", styles['ExecAudit'])


def _closing_stamp_parts(session_id):
    timestamp = datetime.now().strftime("%B %d, %Y %I:%M %p")
    return (
        "Produced by KorumOS Decision Intelligence",
        "Proprietary \u00b7 Confidential",
        f"SESSION {session_id} \u00b7 {timestamp}",
    )


def _clean_cell_text(text):
    t = _as_text(text)
    t = re.sub(r"\[/?METRIC_ANCHOR\]", "", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", t)
    return t.strip()


def _table_from_rows(headers, rows):
    if not headers or not rows:
        return None
    clean_headers = [_clean_cell_text(h) for h in headers]
    clean_rows = [[_clean_cell_text(cell) for cell in row] for row in rows if any(_as_text(cell) for cell in row)]
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

    # Pre-pass: extract full evidence blocks (SOURCE VERIFICATION / INTERROGATION)
    # These span multiple paragraphs — capture from header to next header or end
    _EV_BLOCK = re.compile(
        r"((?:SOURCE VERIFICATION|VERIFICATION|INTERROGATION)\s*\[[^\]]+\][\s\S]*?)(?=(?:SOURCE VERIFICATION|VERIFICATION|INTERROGATION)\s*\[|$)",
        re.IGNORECASE
    )
    ev_regions = []
    for ev_match in _EV_BLOCK.finditer(raw_text):
        ev_text = ev_match.group(1).strip()
        if len(ev_text) > 30:  # skip trivially short matches
            ev_regions.append((ev_match.start(), ev_match.end(), ev_text))

    # If we found evidence blocks, extract them and process remaining text separately
    if ev_regions:
        cursor = 0
        for start, end, ev_text in ev_regions:
            if start > cursor:
                # Process non-evidence text before this block
                blocks.extend(_extract_content_blocks(raw_text[cursor:start]))
            blocks.append(_parse_evidence_block(ev_text))
            cursor = end
        if cursor < len(raw_text):
            blocks.extend(_extract_content_blocks(raw_text[cursor:]))
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


def _parse_evidence_block(text):
    """Parse a SOURCE VERIFICATION / INTERROGATION block into structured fields."""
    lines = text.split("\n")

    # Extract header status
    header_match = re.match(
        r"(SOURCE VERIFICATION|VERIFICATION|INTERROGATION)\s*\[([^\]]+)\]",
        lines[0].strip(), re.IGNORECASE
    )
    status = header_match.group(2).strip().upper() if header_match else "UNKNOWN"
    label = header_match.group(1).strip().upper() if header_match else "VERIFICATION"

    claim = ""
    verdict = ""
    evidence_points = []
    sources = []
    challenges = []
    current_section = "body"  # body, evidence, sources

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        clean_text = stripped.replace("**", "").replace("*", "").strip()
        clean_lower = clean_text.lower()

        # Claim line
        if stripped.lower().startswith("claim:"):
            claim_text = stripped[6:].strip().strip('"').strip("'")
            claim = claim_text
            continue

        # Verdict line: **ACCURATE.** or **INACCURATE.**
        if (
            stripped.startswith("**")
            and stripped.endswith("**")
            and len(stripped) < 40
            and ":" not in clean_text
            and re.match(
                r"^(ACCURATE|INACCURATE|PARTIALLY ACCURATE|MIXED|CONDITIONAL|FLAGGED|UNCERTAIN)\.?$",
                clean_text,
                re.IGNORECASE,
            )
        ):
            verdict = clean_text.rstrip(".")
            continue

        # Section markers — must look like a header line ("Sources:", "Authoritative references:")
        source_header = re.match(r"^sources?\s*:\s*(.*)", clean_lower)
        if "authoritative reference" in clean_lower or source_header:
            current_section = "sources"
            # If there's inline content after "Source: <value>", capture it
            if source_header:
                inline_val = clean_text[source_header.start(1):].strip()
                if inline_val:
                    sources.append(inline_val)
            continue
        if "challenged by" in clean_lower or "challenge:" in clean_lower:
            challenge_text = clean_text.lstrip("⚑").strip()
            challenges.append(challenge_text)
            continue

        # Bullet points
        if stripped.startswith("- "):
            clean = stripped[2:].strip().replace("**", "")
            if current_section == "sources":
                sources.append(clean)
            else:
                evidence_points.append(clean)
                current_section = "evidence"
            continue

        # Continuation text
        if current_section == "sources":
            sources.append(clean_text)
        elif current_section == "evidence":
            evidence_points.append(clean_text)

    return {
        "type": "evidence",
        "status": status,
        "label": label,
        "claim": claim,
        "verdict": verdict,
        "evidence_points": evidence_points,
        "sources": sources,
        "challenges": challenges,
        "text": text,  # raw fallback
    }


def _first_table_block(text):
    for block in _extract_content_blocks(text):
        if block.get("type") == "table":
            return block
    return None


def _decode_image_data(data_url, max_width=500, max_height=300):
    """Decode a base64 data URL into a ReportLab Image flowable."""
    try:
        if not data_url or not data_url.startswith('data:image/'):
            return None
        header, encoded = data_url.split(',', 1)
        img_bytes = base64.b64decode(encoded)
        buf = io.BytesIO(img_bytes)
        img = Image(buf)
        # Scale to fit within max bounds while preserving aspect ratio
        w, h = img.drawWidth, img.drawHeight
        if w > max_width:
            scale = max_width / w
            w, h = w * scale, h * scale
        if h > max_height:
            scale = max_height / h
            w, h = w * scale, h * scale
        img.drawWidth = w
        img.drawHeight = h
        return img
    except Exception:
        return None


def _decode_image_bytes(data_url, max_width_inches=4.5, max_height_inches=3.5):
    """Decode a base64 data URL into (BytesIO, width_inches, height_inches) for Word embedding.
    Scales to fit within max bounds while preserving aspect ratio."""
    try:
        if not data_url or not data_url.startswith('data:image/'):
            return None, None, None
        _, encoded = data_url.split(',', 1)
        img_bytes = base64.b64decode(encoded)

        # Read PNG dimensions from header (bytes 16-23 for width/height)
        w_px, h_px = 800, 400  # fallback
        if len(img_bytes) > 24 and img_bytes[:4] == b'\x89PNG':
            import struct
            w_px = struct.unpack('>I', img_bytes[16:20])[0]
            h_px = struct.unpack('>I', img_bytes[20:24])[0]

        # Convert to inches at 96 DPI and scale to fit
        w_in = w_px / 96.0
        h_in = h_px / 96.0
        if w_in > max_width_inches:
            scale = max_width_inches / w_in
            w_in, h_in = w_in * scale, h_in * scale
        if h_in > max_height_inches:
            scale = max_height_inches / h_in
            w_in, h_in = w_in * scale, h_in * scale

        return io.BytesIO(img_bytes), w_in, h_in
    except Exception:
        return None, None, None


def _artifact_matches(art, section_title, provider_name):
    """Check if an artifact belongs next to a given node by matching content keywords."""
    label = _artifact_label(art).upper()
    content = _as_text(art.get('content', '')).upper()[:500]
    sec = section_title.upper()
    prov = provider_name.upper()
    # Match if artifact label/content mentions the provider or section topic
    return (prov and prov != 'KORUM' and (prov in label or prov in content)) or \
           (sec and len(sec) > 3 and (sec in label or sec in content))


def _assign_artifacts_to_nodes(artifacts, section_items, contributors):
    """Map each artifact to its FIRST matching node. Each artifact renders exactly once."""
    assigned = {i: [] for i in range(len(section_items))}
    assigned[-1] = []  # unmatched bucket
    claimed = set()  # track artifact indices already assigned
    for i, (sid, _content) in enumerate(section_items):
        sec_title = sid.replace("_", " ").upper()
        prov_name = "KORUM"
        if i < len(contributors):
            prov_name = _as_text(contributors[i].get('provider', '')).upper()
        for ai, a in enumerate(artifacts):
            if ai not in claimed and _artifact_matches(a, sec_title, prov_name):
                assigned[i].append(a)
                claimed.add(ai)
    # Unmatched artifacts go to the last node
    for ai, a in enumerate(artifacts):
        if ai not in claimed:
            last_idx = len(section_items) - 1 if section_items else -1
            assigned[last_idx].append(a)
    return assigned


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


def _pull_quote_color(status):
    status_lower = _as_text(status).lower()
    if status_lower in ("flagged", "challenged"):
        return SEM_RED, "#FDF2F2"
    if status_lower == "verified":
        return SEM_GREEN, "#F2F8F4"
    return SEM_BLUE, "#F0F3FA"


def _build_pull_quote(claim_text, status, provider, role, session_id, styles):
    border_color, bg_color = _pull_quote_color(status)
    quote_style = ParagraphStyle(
        'PQ', parent=styles['ExecBody'], fontSize=8, leading=11,
        fontName='Helvetica-Oblique', textColor=colors.HexColor("#2f2b24"),
    )
    attr_style = ParagraphStyle(
        'PQAttr', parent=styles['ExecAudit'], fontSize=6.5,
        fontName='Courier', textColor=colors.HexColor(SEM_MUTED),
    )
    role_part = f" \u00b7 {role}" if role else ""
    content = [
        Paragraph(f"&ldquo;{escape(_as_text(claim_text))}&rdquo;", quote_style),
        Spacer(1, 4),
        Paragraph(f"\u2014 {provider}{role_part} \u00b7 {session_id}", attr_style),
    ]
    tbl = Table([[content]], colWidths=[520])
    tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_color)),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINEBEFORE', (0,0), (0,-1), 3, colors.HexColor(border_color)),
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
        elif block["type"] == "evidence":
            ev_flowables = _build_pdf_evidence_block(block, styles, total_width, palette)
            flowables.extend(ev_flowables)
    return flowables


def _build_pdf_evidence_block(block, styles, total_width, palette):
    """KORUM-style evidence block: claim strip + status + evidence + provenance."""
    block_label = _as_text(block.get("label") or "SOURCE VERIFICATION").upper()
    status = block.get("status", "").upper()
    claim = block.get("claim", "")
    evidence_points = block.get("evidence_points", [])
    sources = block.get("sources", [])
    challenges = block.get("challenges", [])

    if status in ("INACCURATE", "FLAGGED", "CHALLENGED"):
        border_color = colors.HexColor("#A45A52")
        status_symbol = "\u2717"
        status_label = "FLAGGED"
        bg_color = colors.HexColor("#FDF6F5")
    elif status in ("ACCURATE", "VERIFIED"):
        border_color = colors.HexColor("#5B7F5E")
        status_symbol = "\u2713"
        status_label = "VERIFIED"
        bg_color = colors.HexColor("#F4F8F5")
    else:
        border_color = colors.HexColor("#4A6A7A")
        status_symbol = "\u25ce"
        status_label = "CONDITIONAL"
        bg_color = colors.HexColor("#F0F3FA")

    flowables = [Spacer(1, 6)]

    # ── 1. CLAIM STRIP (left-bordered) ───────────────────────────────
    if claim:
        claim_parts = [
            Paragraph(f"<b><i>{escape(claim)}</i></b>", styles["ExecBody"]),
            Spacer(1, 3),
            Paragraph(f"\u2014 {status_label} CLAIM", styles["ExecAudit"]),
        ]
        claim_tab = Table([[claim_parts]], colWidths=[total_width - 30])
        claim_tab.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBEFORE', (0, 0), (0, -1), 3, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        flowables.append(claim_tab)
        flowables.append(Spacer(1, 6))

    # ── 2. STATUS STRIP ──────────────────────────────────────────────
    status_text = f"{block_label}   {status_symbol} {status_label}"
    status_tab = Table([[Paragraph(f"<b>{escape(status_text)}</b>", styles["ExecAudit"])]], colWidths=[total_width - 30])
    status_tab.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    flowables.append(status_tab)
    flowables.append(Spacer(1, 6))

    # ── 3. CHALLENGES ────────────────────────────────────────────────
    for challenge in challenges[:2]:
        ch_parts = [Paragraph(f"<i>{escape(challenge)}</i>", styles["ExecAudit"])]
        ch_tab = Table([[ch_parts]], colWidths=[total_width - 30])
        ch_tab.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBEFORE', (0, 0), (0, -1), 2, colors.HexColor("#A45A52")),
        ]))
        flowables.append(ch_tab)
        flowables.append(Spacer(1, 4))

    # ── 4. WHY THIS HOLDS ────────────────────────────────────────────
    if evidence_points:
        flowables.append(Paragraph(f"<b>WHY THIS HOLDS:</b>", styles["ExecAudit"]))
        flowables.append(Spacer(1, 3))
        for point in evidence_points[:5]:
            flowables.append(Paragraph(f"\u2022 {escape(point)}", styles["ExecBody"]))
            flowables.append(Spacer(1, 2))
        flowables.append(Spacer(1, 4))

    # ── 5. PROVENANCE ────────────────────────────────────────────────
    if sources:
        source_summary = " \u00b7 ".join(s[:60] for s in sources[:3])
        challenge_status = "PASSED" if status in ("ACCURATE", "VERIFIED") else "FAILED" if status in ("INACCURATE", "FLAGGED") else "PENDING"
        prov_parts = [
            Paragraph(f"SOURCE: {escape(source_summary)}", styles["ExecAudit"]),
            Spacer(1, 2),
            Paragraph(f"<b>STATUS: {status_symbol} {status_label}   CHALLENGE: {challenge_status}</b>", styles["ExecAudit"]),
        ]
        prov_tab = Table([[prov_parts]], colWidths=[total_width - 30])
        prov_tab.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        flowables.append(prov_tab)

    flowables.append(Spacer(1, 12))
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

# Fixed semantic colors — DO NOT vary by theme
SEM_BLUE = "#273C75"      # Structural — headers, borders, consensus bar
SEM_GREEN = "#1B4332"     # Verified findings
SEM_RED = "#8B1A1A"       # Flagged/audit findings
SEM_AMBER = "#C8922A"     # Conditional
SEM_MUTED = "#888888"     # Attribution lines
SEM_RULE = "#D8D4CC"      # Thin divider rules

# Agent accent colors — left border per contributor
AGENT_COLORS = {
    "OPENAI": "#273C75",
    "ANTHROPIC": "#8B3A00",
    "GOOGLE": "#2A5C1A",
    "PERPLEXITY": "#4A2A8A",
    "MISTRAL": "#1A4A5C",
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

        # Chart Standard: assign artifacts to their source nodes for inline placement
        section_items_pre = list((sections or {}).items())
        node_artifacts = _assign_artifacts_to_nodes(artifacts, section_items_pre, contributors)

        story = []

        # 1. --- STRATEGIC HEADER ---
        workflow_label = _as_text(meta.get('workflow')).upper() or 'STRATEGIC_INTEL'
        doc_title = _as_text(meta.get('title')) or 'Command Node'
        
        # Header Metadata (Top Line)
        top_meta = [
            [[Paragraph(f"INTELLIGENCE DOSSIER \u00b7 CONFIDENTIAL \u00b7 {workflow_label}", styles['ExecLabel'])], 
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

        # 2. --- EXECUTIVE SUMMARY ---
        summary_text = meta.get("summary") or "Intel synthesis required."
        summary_p = Paragraph(f"<b>{escape(summary_text)}</b>", styles['ExecImpact'])

        top_visual = None
        if artifacts:
            top_visual = artifacts.pop(0)

        if top_visual:
            chart_img = _decode_image_data(top_visual.get('imageData'), max_width=200, max_height=180)
            if chart_img:
                visual_col = [
                    Paragraph(_artifact_label(top_visual), styles['StatCaption']),
                    Spacer(1, 5),
                    chart_img,
                ]
            else:
                fallback_note = _artifact_unavailable_note(styles) if _is_raw_svg_artifact(top_visual) else Paragraph(escape(_as_text(top_visual.get('content',''))[:150]).replace("\n","<br/>"), styles['ExecAudit'])
                visual_col = [
                    Paragraph(_artifact_label(top_visual), styles['StatCaption']),
                    Spacer(1, 5),
                    fallback_note
                ]
            summary_tab = Table([[[summary_p], visual_col]], colWidths=[324, 216])
            summary_tab.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (1,0), (1,0), 15),
            ]))
            story.append(summary_tab)
        else:
            story.append(summary_p)
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
                ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor(SEM_RULE)),
                ('LINEBELOW', (0,-1), (-1,-1), 0.5, colors.HexColor(SEM_RULE)),
                ('TOPPADDING', (0,0), (-1,-1), 12),
                ('BOTTOMPADDING', (0,0), (-1,-1), 12),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ])
            story.append(s_tab)
            story.append(Spacer(1, 30))

        # 4. --- INTELLIGENCE NODES (FULL-WIDTH PROSE) ---
        seen_claims = set()  # Deduplicate claims across nodes
        section_items = list(sections.items())
        for idx, (sid, content) in enumerate(section_items):
            sec_title = sid.replace("_", " ").upper()
            prov_name = "KORUM"
            prov_role = ""
            if idx < len(contributors):
                prov_name = _as_text(contributors[idx].get('provider', '')).upper()
                prov_role = _as_text(contributors[idx].get('role', ''))

            role_suffix = f" &middot; {escape(prov_role)}" if prov_role else ""
            node_id = f"{sec_title} &middot; NODE {idx+1:02d} &mdash; {prov_name}{role_suffix}"

            content_blocks = _extract_content_blocks(content)

            prov_key = prov_name.lower()
            prov_data = card_results.get(prov_key) or {}

            if not any(block.get("type") == "table" for block in content_blocks):
                provider_table = _first_table_block(prov_data.get("response", ""))
                if provider_table:
                    content_blocks.append(provider_table)

            # Node label + thin rule (always full-width)
            story.append(Paragraph(node_id, styles['ExecLabel']))
            story.append(Spacer(1, 6))
            story.append(Table([[""]],  colWidths=[540], rowHeights=[1],
                style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor(SEM_RULE))]))
            story.append(Spacer(1, 10))

            # Collect chart images for this node (only those with imageData)
            node_arts = node_artifacts.get(idx, [])
            float_charts = []
            remaining_arts = []
            for art in node_arts:
                chart_img = _decode_image_data(art.get('imageData'), max_width=200, max_height=220)
                if chart_img:
                    float_charts.append((art, chart_img))
                else:
                    remaining_arts.append(art)

            # PDF reliability mode: render node prose full-width, then charts immediately after.
            # ReportLab cannot split tall table cells across pages; side-by-side float tables can
            # hard-fail export on long nodes. Stacking preserves proximity without breaking export.
            story.extend(_render_pdf_blocks(content_blocks, styles, 540, tc))
            if float_charts:
                for art, chart_img in float_charts:
                    art_label = _artifact_label(art)
                    if art_label:
                        story.append(Paragraph(art_label, styles['StatCaption']))
                        story.append(Spacer(1, 4))
                    story.append(chart_img)
                    story.append(Spacer(1, 8))

            # Inline pull quotes from verified claims (skip trivial/duplicate)
            claims = prov_data.get("verified_claims") or []
            for claim in claims[:2]:
                claim_text = _as_text(claim.get('claim', ''))
                if not claim_text or len(claim_text) < 25:
                    continue
                claim_key = claim_text.strip().lower()
                if claim_key in seen_claims:
                    continue
                seen_claims.add(claim_key)
                claim_status = _as_text(claim.get('status', 'strategic'))
                pq = _build_pull_quote(claim_text, claim_status, prov_name, prov_role, doc._session_id, styles)
                story.append(pq)
                story.append(Spacer(1, 8))

            # Remaining artifacts without imageData — render below as text (skip empty)
            for art in remaining_arts:
                if _is_raw_svg_artifact(art):
                    art_label = _artifact_label(art)
                    if art_label:
                        story.append(Paragraph(art_label, styles['ExecSectionSubhead']))
                        story.append(Spacer(1, 4))
                    story.append(_artifact_unavailable_note(styles))
                    story.append(Spacer(1, 10))
                    continue
                art_content = _as_text(art.get('content', '')).strip()
                if not art_content:
                    continue  # skip artifacts with no content and no image — bare labels
                art_label = _artifact_label(art)
                if art_label:
                    story.append(Paragraph(art_label, styles['ExecSectionSubhead']))
                    story.append(Spacer(1, 4))
                art_blocks = _extract_content_blocks(art_content)
                story.extend(_render_pdf_blocks(art_blocks, styles, 540, tc))
                story.append(Spacer(1, 10))

            story.append(Spacer(1, 16))

        # 5. --- COUNCIL CONTRIBUTORS STRIP ---
        if contributors:
            story.append(Paragraph("COUNCIL CONTRIBUTORS", styles['ExecLabel']))
            story.append(Spacer(1, 6))
            contrib_cells = []
            for contrib in contributors[:5]:
                c_prov = _as_text(contrib.get('provider', '')).upper()
                c_role = _as_text(contrib.get('role', ''))
                c_data = card_results.get(c_prov.lower()) or {}
                c_claims = c_data.get("verified_claims") or []
                if any(_as_text(cl.get('status','')).lower() in ('flagged','challenged') for cl in c_claims):
                    stamp, stamp_color = "\u2691 Flagged", SEM_RED
                elif any(_as_text(cl.get('status','')).lower() == 'verified' for cl in c_claims):
                    stamp, stamp_color = "\u2713 Verified", SEM_GREEN
                else:
                    stamp, stamp_color = "\u25ce Conditional", SEM_AMBER
                cell_content = [
                    Paragraph(f"<b>{escape(c_prov)}</b>", styles['ExecAudit']),
                    Paragraph(escape(c_role), styles['ExecAudit']),
                    Paragraph(f"<font color='{stamp_color}'>{stamp}</font>", styles['ExecAudit']),
                ]
                contrib_cells.append(cell_content)
            col_w = 540 / len(contrib_cells)
            contrib_tab = Table([contrib_cells], colWidths=[col_w] * len(contrib_cells))
            agent_style_cmds = [
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
            ]
            for ci, contrib in enumerate(contributors[:5]):
                agent_color = AGENT_COLORS.get(_as_text(contrib.get('provider','')).upper(), SEM_BLUE)
                agent_style_cmds.append(('LINEBEFORE', (ci,0), (ci,-1), 2.5, colors.HexColor(agent_color)))
            contrib_tab.setStyle(TableStyle(agent_style_cmds))
            story.append(contrib_tab)
            story.append(Spacer(1, 20))

        # 6. --- CONSENSUS FOOTER ---
        truth_int = _normalize_truth_score(meta.get("composite_truth_score"))
        consensus_summary = _as_text(divergence.get("divergence_summary", "")) or "Council reached operational consensus."
        cons_data = [
            [Paragraph("COUNCIL CONSENSUS", styles['ExecLabel']), Paragraph("", styles['Cons'])],
            [Paragraph(f"<i>{escape(consensus_summary)}</i>", styles['Cons']),
             Paragraph(f"<b>{truth_int}</b><br/><font size='7'>TRUTH SCORE / 100</font>", styles['ConsScore'])]
        ]
        cons_tab = Table(cons_data, colWidths=[410, 130])
        cons_tab.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(SEM_BLUE)),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 15),
            ('RIGHTPADDING', (0,0), (-1,-1), 15),
            ('SPAN', (0,0), (1,0)),
        ]))
        story.append(cons_tab)
        story.append(Spacer(1, 10))

        closer_head, closer_legal, closer_meta = _closing_stamp_parts(doc._session_id)
        closer_left = [
            Paragraph(closer_head, styles['ExecLabel']),
            Spacer(1, 2),
            Paragraph(closer_legal, styles['ExecAudit']),
        ]
        closer_right = [
            Paragraph(closer_meta, styles['ExecSig']),
            Spacer(1, 2),
            Paragraph("EXPORT STATUS \u00b7 DECISION ARTIFACT", styles['ExecSig']),
        ]
        closer_tab = Table([[closer_left, closer_right]], colWidths=[340, 200])
        closer_tab.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (-1,0), 0.6, colors.HexColor(SEM_RULE)),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (0,0), (0,-1), 0),
            ('RIGHTPADDING', (0,0), (0,-1), 6),
            ('LEFTPADDING', (1,0), (1,-1), 6),
            ('RIGHTPADDING', (1,0), (1,-1), 0),
        ]))
        story.append(closer_tab)

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
            elif block["type"] == "evidence":
                WordExporter._render_evidence_block(container, block, theme)

    @staticmethod
    def _render_evidence_block(container, block, theme):
        """KORUM-style evidence block: claim strip + status + evidence + provenance."""
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls

        block_label = _as_text(block.get("label") or "SOURCE VERIFICATION").upper()
        status = block.get("status", "").upper()
        claim = block.get("claim", "")
        evidence_points = block.get("evidence_points", [])
        sources = block.get("sources", [])
        challenges = block.get("challenges", [])

        # Status-based colors
        if status in ("INACCURATE", "FLAGGED", "CHALLENGED"):
            border_color = "A45A52"
            status_symbol = "\u2717"  # ✗
            status_label = "FLAGGED"
            bg_hex = "FDF6F5"
        elif status in ("ACCURATE", "VERIFIED"):
            border_color = "5B7F5E"
            status_symbol = "\u2713"  # ✓
            status_label = "VERIFIED"
            bg_hex = "F4F8F5"
        else:
            border_color = "4A6A7A"
            status_symbol = "\u25ce"  # ◎
            status_label = "CONDITIONAL"
            bg_hex = "F0F3FA"

        # Fallback for table cells — simplified rendering
        if not hasattr(container, 'add_table'):
            if claim:
                p = WordExporter._add_paragraph(container, claim, size=8, italic=True, color=theme["text"])
                if p:
                    p.paragraph_format.left_indent = Inches(0.3)
            return

        # ── 1. CLAIM STRIP (left-bordered, prominent) ────────────────────
        if claim:
            claim_tab = container.add_table(rows=1, cols=1)
            claim_cell = claim_tab.rows[0].cells[0]
            tc_pr = claim_cell._tc.get_or_add_tcPr()
            borders = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'<w:left w:val="single" w:sz="18" w:space="0" w:color="{border_color}"/>'
                f'<w:top w:val="none" w:sz="0" w:space="0"/>'
                f'<w:bottom w:val="none" w:sz="0" w:space="0"/>'
                f'<w:right w:val="none" w:sz="0" w:space="0"/>'
                f'</w:tcBorders>'
            )
            tc_pr.append(borders)
            WordExporter._add_paragraph(claim_cell, claim, size=9, bold=True, italic=True, color=theme["text"])
            WordExporter._add_paragraph(claim_cell, f"\u2014 {status_label} CLAIM", size=7, color=border_color)

        # ── 2. STATUS STRIP ──────────────────────────────────────────────
        status_tab = container.add_table(rows=1, cols=1)
        status_cell = status_tab.rows[0].cells[0]
        WordExporter._set_cell_background(status_cell, bg_hex)
        status_text = f"{block_label}   {status_symbol} {status_label}"
        WordExporter._add_paragraph(status_cell, status_text, size=7, bold=True, color=border_color)

        # ── 3. CHALLENGES (if any) ───────────────────────────────────────
        for challenge in challenges[:2]:
            ch_tab = container.add_table(rows=1, cols=1)
            ch_cell = ch_tab.rows[0].cells[0]
            tc_pr = ch_cell._tc.get_or_add_tcPr()
            borders = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'<w:left w:val="single" w:sz="8" w:space="0" w:color="A45A52"/>'
                f'<w:top w:val="none" w:sz="0" w:space="0"/>'
                f'<w:bottom w:val="none" w:sz="0" w:space="0"/>'
                f'<w:right w:val="none" w:sz="0" w:space="0"/>'
                f'</w:tcBorders>'
            )
            tc_pr.append(borders)
            WordExporter._add_paragraph(ch_cell, challenge, size=8, italic=True, color="A45A52")

        # ── 4. WHY THIS HOLDS (evidence points) ─────────────────────────
        if evidence_points:
            WordExporter._add_paragraph(container, "WHY THIS HOLDS:", size=7, bold=True, color=border_color)
            for point in evidence_points[:5]:
                WordExporter._add_paragraph(container, f"\u2022 {point}", size=8, color=theme["text"])

        # ── 5. PROVENANCE (compact sources) ──────────────────────────────
        if sources:
            source_summary = " \u00b7 ".join(s[:60] for s in sources[:3])
            prov_tab = container.add_table(rows=1, cols=1)
            prov_cell = prov_tab.rows[0].cells[0]
            WordExporter._set_cell_background(prov_cell, bg_hex)
            WordExporter._add_paragraph(prov_cell, f"SOURCE: {source_summary}", size=6.5, color=SEM_MUTED)
            challenge_status = "PASSED" if status in ("ACCURATE", "VERIFIED") else "FAILED" if status in ("INACCURATE", "FLAGGED") else "PENDING"
            WordExporter._add_paragraph(prov_cell, f"STATUS: {status_symbol} {status_label}   CHALLENGE: {challenge_status}", size=6.5, bold=True, color=border_color)

    @staticmethod
    def _add_spacing(doc, count=1):
        for _ in range(count):
            doc.add_paragraph()

    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured, _, _ = _extract_parts(intelligence_object)
        doc = Document()
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls
        
        # DNA: SHARED THEME - specialist dynamic resolution
        theme_id = _normalize_theme(meta.get('theme', 'BONE_FIELD'))
        tc = THEME_COLORS[theme_id]
        
        ACCENT_HEX = tc["accent"].lstrip('#')
        DIM_GRAY = tc["label"].lstrip('#')
        s_rgb = RGBColor(*WordExporter._hex_to_rgb(ACCENT_HEX))

        mission_ctx = intelligence_object.get("_mission_context") or {}
        client_name = _as_text(mission_ctx.get("client", "")).strip() or "DECISION COMMANDER ALPHA"
        card_results = intelligence_object.get("_card_results") or {}
        contributors = intelligence_object.get("council_contributors") or []
        divergence = intelligence_object.get("divergence_analysis") or {}
        artifacts = _report_artifacts(intelligence_object)
        session_id = _resolve_session_id(meta, intelligence_object)

        # Chart Standard: assign artifacts to their source nodes for inline placement
        section_items_pre = list((sections or {}).items())
        node_artifacts = _assign_artifacts_to_nodes(artifacts, section_items_pre, contributors)

        # 1. --- PREMIUM HEADER ---
        h_tab = doc.add_table(rows=1, cols=2)
        h_tab.columns[0].width = Inches(3.8)
        h_tab.columns[1].width = Inches(2.2)
        
        l_p = h_tab.rows[0].cells[0].paragraphs[0]
        l_run = l_p.add_run(f"INTELLIGENCE DOSSIER  \u00b7  CONFIDENTIAL  \u00b7  {_as_text(meta.get('workflow')).upper() or 'STRATEGIC_INTEL'}")
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
        t_run = t_p.add_run(_as_text(meta.get('title') or 'Command Node'))
        t_run.bold = True
        t_run.font.size = Pt(22)
        t_run.font.color.rgb = s_rgb
        
        # Thick Rule (Executive Baseline) — exact height, no cell expansion
        from docx.enum.table import WD_ROW_HEIGHT_RULE
        u_tab = doc.add_table(rows=1, cols=1)
        WordExporter._set_cell_background(u_tab.rows[0].cells[0], ACCENT_HEX)
        # Shrink default paragraph to prevent cell height expansion
        u_p = u_tab.rows[0].cells[0].paragraphs[0]
        u_p.paragraph_format.space_before = Pt(0)
        u_p.paragraph_format.space_after = Pt(0)
        u_p.paragraph_format.line_spacing = Pt(1)
        u_run = u_p.add_run("")
        u_run.font.size = Pt(1)
        u_tab.rows[0].height = Inches(0.04)
        u_tab.rows[0].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        
        doc.add_paragraph() # Spacer

        # 2. --- EXECUTIVE SUMMARY ---
        summary_text = meta.get("summary") or "Intel synthesis required."
        s_p = doc.add_paragraph()
        s_run = s_p.add_run(summary_text)
        s_run.bold = True
        s_run.font.size = Pt(11)
        s_run.font.color.rgb = s_rgb

        WordExporter._add_spacing(doc)

        # 3. --- KPI STRIP (thin rules, no box) ---
        key_metrics = structured.get("key_metrics") or []
        if key_metrics:
            kpi_tab = doc.add_table(rows=2, cols=min(3, len(key_metrics)))
            kpi_tab.style = "Table Grid"
            for i, km in enumerate(key_metrics[:3]):
                v_p = kpi_tab.rows[0].cells[i].paragraphs[0]
                v_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                v_run = v_p.add_run(_as_text(km.get('value', '')))
                v_run.bold = True
                v_run.font.size = Pt(18)
                v_run.font.color.rgb = s_rgb
                l_p = kpi_tab.rows[1].cells[i].paragraphs[0]
                l_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                l_run = l_p.add_run(_as_text(km.get('metric', '')).upper())
                l_run.font.size = Pt(7)
                l_run.font.color.rgb = RGBColor.from_string(DIM_GRAY)
            WordExporter._add_spacing(doc)

        # 4. --- INTELLIGENCE NODES (full-width prose) ---
        seen_claims = set()  # Deduplicate claims across nodes
        section_items = list(sections.items())
        for idx, (sid, content) in enumerate(section_items):
            sec_title = sid.replace("_", " ").upper()
            prov_name = "KORUM"
            prov_role = ""
            if idx < len(contributors):
                prov_name = _as_text(contributors[idx].get('provider', '')).upper()
                prov_role = _as_text(contributors[idx].get('role', ''))

            role_suffix = f" \u00b7 {prov_role}" if prov_role else ""
            n_p = doc.add_paragraph()
            n_run = n_p.add_run(f"{sec_title} \u00b7 NODE {idx+1:02d} \u2014 {prov_name}{role_suffix}")
            n_run.font.size = Pt(7)
            n_run.font.color.rgb = RGBColor.from_string(DIM_GRAY)

            content_blocks = _extract_content_blocks(content)
            prov_key = prov_name.lower()
            prov_data = card_results.get(prov_key) or {}

            if not any(block.get("type") == "table" for block in content_blocks):
                provider_table = _first_table_block(prov_data.get("response", ""))
                if provider_table:
                    content_blocks.append(provider_table)

            # Collect chart images for this node
            node_arts = node_artifacts.get(idx, [])
            float_charts = []
            remaining_arts = []
            for art in node_arts:
                img_stream, img_w, img_h = _decode_image_bytes(art.get('imageData'), max_width_inches=2.4, max_height_inches=2.5)
                if img_stream:
                    float_charts.append((art, img_stream, img_w, img_h))
                else:
                    remaining_arts.append(art)

            if float_charts:
                # FLOAT MODE: 60/40 side-by-side — prose left, chart right
                float_tab = doc.add_table(rows=1, cols=2)
                float_tab.columns[0].width = Inches(3.6)
                float_tab.columns[1].width = Inches(2.4)
                left_cell = float_tab.rows[0].cells[0]
                right_cell = float_tab.rows[0].cells[1]

                # Left: prose content
                WordExporter._render_word_blocks(left_cell, content_blocks, tc)

                # Right: chart image(s) with labels
                for art, img_stream, img_w, img_h in float_charts:
                    art_label = _artifact_label(art)
                    if art_label:
                        WordExporter._add_paragraph(right_cell, art_label, size=7, bold=True, italic=True, color=tc["accent_dark"])
                    pic_kwargs = {}
                    if img_w:
                        pic_kwargs['width'] = Inches(img_w)
                    if img_h:
                        pic_kwargs['height'] = Inches(img_h)
                    if not pic_kwargs:
                        pic_kwargs['width'] = Inches(2.2)
                    p = right_cell.add_paragraph()
                    r = p.add_run()
                    r.add_picture(img_stream, **pic_kwargs)
            else:
                # No chart — full-width prose
                WordExporter._render_word_blocks(doc, content_blocks, tc)

            # Inline pull quotes (skip trivial/duplicate)
            claims = prov_data.get("verified_claims") or []
            for claim in claims[:2]:
                claim_text = _as_text(claim.get('claim', ''))
                if not claim_text or len(claim_text) < 25:
                    continue
                claim_key = claim_text.strip().lower()
                if claim_key in seen_claims:
                    continue
                seen_claims.add(claim_key)
                claim_status = _as_text(claim.get('status', 'strategic')).lower()
                if claim_status in ('flagged', 'challenged'):
                    border_hex, bg_hex = SEM_RED, "FDF2F2"
                elif claim_status == 'verified':
                    border_hex, bg_hex = SEM_GREEN, "F2F8F4"
                else:
                    border_hex, bg_hex = SEM_BLUE, "F0F3FA"
                pq_tab = doc.add_table(rows=1, cols=1)
                pq_cell = pq_tab.rows[0].cells[0]
                WordExporter._set_cell_background(pq_cell, bg_hex)
                WordExporter._add_paragraph(pq_cell, f"\u201c{claim_text}\u201d", size=8, italic=True, color=tc["text"])
                role_part = f" \u00b7 {prov_role}" if prov_role else ""
                WordExporter._add_paragraph(pq_cell, f"\u2014 {prov_name}{role_part} \u00b7 {session_id}", size=6.5, color=SEM_MUTED)

            # Remaining text-only artifacts — render below full-width (skip empty)
            for art in remaining_arts:
                if _is_raw_svg_artifact(art):
                    art_label = _artifact_label(art)
                    if art_label:
                        WordExporter._add_paragraph(doc, art_label, size=8, bold=True, italic=True, color=tc["accent_dark"])
                    WordExporter._add_paragraph(doc, "Chart artifact unavailable for export capture.", size=8, italic=True, color=DIM_GRAY)
                    continue
                art_content = _as_text(art.get('content', '')).strip()
                if not art_content:
                    continue  # skip artifacts with no content and no image — bare labels
                art_label = _artifact_label(art)
                if art_label:
                    WordExporter._add_paragraph(doc, art_label, size=8, bold=True, italic=True, color=tc["accent_dark"])
                art_blocks = _extract_content_blocks(art_content)
                WordExporter._render_word_blocks(doc, art_blocks, tc)

            WordExporter._add_spacing(doc)

        # 5. --- COUNCIL CONTRIBUTORS STRIP ---
        if contributors:
            WordExporter._add_paragraph(doc, "COUNCIL CONTRIBUTORS", size=7, bold=True, color=DIM_GRAY)
            c_tab = doc.add_table(rows=1, cols=min(5, len(contributors)))
            for ci, contrib in enumerate(contributors[:5]):
                c_prov = _as_text(contrib.get('provider', '')).upper()
                c_role = _as_text(contrib.get('role', ''))
                c_data = card_results.get(c_prov.lower()) or {}
                c_claims = c_data.get("verified_claims") or []
                if any(_as_text(cl.get('status','')).lower() in ('flagged','challenged') for cl in c_claims):
                    stamp = "\u2691 Flagged"
                elif any(_as_text(cl.get('status','')).lower() == 'verified' for cl in c_claims):
                    stamp = "\u2713 Verified"
                else:
                    stamp = "\u25ce Conditional"
                cell = c_tab.rows[0].cells[ci]
                WordExporter._add_paragraph(cell, c_prov, size=7, bold=True, color=tc["text"])
                WordExporter._add_paragraph(cell, c_role, size=7, color=DIM_GRAY)
                WordExporter._add_paragraph(cell, stamp, size=7, color=tc["text"])
            WordExporter._add_spacing(doc)

        # 6. --- CONSENSUS FOOTER ---
        truth_int = _normalize_truth_score(meta.get("composite_truth_score"))
        consensus_summary = _as_text(divergence.get("divergence_summary", "")) or "Council reached operational consensus."
        cons_tab = doc.add_table(rows=1, cols=2)
        cons_tab.columns[0].width = Inches(4.5)
        cons_tab.columns[1].width = Inches(2.0)
        left_cell = cons_tab.rows[0].cells[0]
        right_cell = cons_tab.rows[0].cells[1]
        WordExporter._set_cell_background(left_cell, SEM_BLUE.lstrip('#'))
        WordExporter._set_cell_background(right_cell, SEM_BLUE.lstrip('#'))
        WordExporter._add_paragraph(left_cell, "COUNCIL CONSENSUS", size=7, bold=True, color="FFFFFF")
        WordExporter._add_paragraph(left_cell, consensus_summary, size=8, italic=True, color="FFFFFF")
        WordExporter._add_paragraph(right_cell, f"{truth_int}", size=19, bold=True, color="FFFFFF", align=WD_ALIGN_PARAGRAPH.RIGHT)
        WordExporter._add_paragraph(right_cell, "TRUTH SCORE / 100", size=7, bold=True, color="FFFFFF", align=WD_ALIGN_PARAGRAPH.RIGHT)

        closer_head, closer_legal, closer_meta = _closing_stamp_parts(session_id)
        WordExporter._add_spacing(doc)
        closer_tab = doc.add_table(rows=1, cols=2)
        closer_tab.columns[0].width = Inches(4.6)
        closer_tab.columns[1].width = Inches(1.9)
        for cell in closer_tab.rows[0].cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            top_border = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'<w:top w:val="single" w:sz="8" w:space="0" w:color="{tc["line"].lstrip("#")}"/>'
                f'</w:tcBorders>'
            )
            tc_pr.append(top_border)
        WordExporter._add_paragraph(closer_tab.rows[0].cells[0], closer_head, size=7, bold=True, color=DIM_GRAY)
        WordExporter._add_paragraph(closer_tab.rows[0].cells[0], closer_legal, size=7, color=DIM_GRAY)
        WordExporter._add_paragraph(closer_tab.rows[0].cells[1], closer_meta, size=6.5, color=DIM_GRAY, align=WD_ALIGN_PARAGRAPH.RIGHT)
        WordExporter._add_paragraph(closer_tab.rows[0].cells[1], "EXPORT STATUS \u00b7 DECISION ARTIFACT", size=6.5, bold=True, color=tc["accent_dark"], align=WD_ALIGN_PARAGRAPH.RIGHT)
        
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
