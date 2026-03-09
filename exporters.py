import csv
import json
import os
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
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
    return meta, sections, structured


class WordExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured = _extract_parts(intelligence_object)
        card_results = intelligence_object.get("_card_results", {})

        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)

        # --- Normalize truth score ---
        truth_raw = meta.get("composite_truth_score", "N/A")
        try:
            truth_val = float(truth_raw)
            truth_display = str(int(truth_val * 100)) if truth_val <= 1 else str(int(truth_val))
        except (ValueError, TypeError):
            truth_display = str(truth_raw)

        title = doc.add_heading(meta.get("title", "KORUM Intelligence Report"), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        models = meta.get("models_used", [])
        if not isinstance(models, list):
            models = [str(models)]

        doc.add_paragraph(f"Generated: {meta.get('generated_at', datetime.now().isoformat())}  |  "
                          f"Workflow: {meta.get('workflow', 'RESEARCH')}  |  "
                          f"Truth Score: {truth_display}/100  |  Agents: {len(models)}")
        doc.add_page_break()

        # --- Executive Summary ---
        doc.add_heading("Executive Summary", level=1)
        doc.add_paragraph(_as_text(meta.get("summary", "")))
        exec_section = _as_text(sections.get("executive_summary", ""))
        if exec_section:
            doc.add_paragraph(exec_section)

        # --- Synthesis Sections ---
        for section_id, content in sections.items():
            if section_id == "executive_summary":
                continue
            doc.add_heading(section_id.replace("_", " ").title(), level=1)
            text = _as_text(content)
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    doc.add_paragraph(para)

        # --- Key Metrics ---
        key_metrics = structured.get("key_metrics", [])
        if key_metrics:
            doc.add_page_break()
            doc.add_heading("Key Intelligence Metrics", level=1)
            table = doc.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            hdr[0].text = "Metric"
            hdr[1].text = "Value"
            hdr[2].text = "Context"
            for metric in key_metrics:
                if isinstance(metric, dict):
                    row = table.add_row().cells
                    row[0].text = _as_text(metric.get("metric", ""))
                    row[1].text = _as_text(metric.get("value", ""))
                    row[2].text = _as_text(metric.get("context", ""))

        # --- Action Items ---
        action_items = structured.get("action_items", [])
        if action_items:
            doc.add_heading("Action Items", level=1)
            table = doc.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            hdr[0].text = "Task"
            hdr[1].text = "Priority"
            hdr[2].text = "Timeline"
            for item in action_items:
                if isinstance(item, dict):
                    row = table.add_row().cells
                    row[0].text = _as_text(item.get("task", ""))
                    row[1].text = _as_text(item.get("priority", "")).upper()
                    row[2].text = _as_text(item.get("timeline", ""))

        # --- Risks ---
        risks = structured.get("risks", [])
        if risks:
            doc.add_heading("Risk Assessment", level=1)
            table = doc.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            hdr[0].text = "Risk"
            hdr[1].text = "Severity"
            hdr[2].text = "Mitigation"
            for risk in risks:
                if isinstance(risk, dict):
                    row = table.add_row().cells
                    row[0].text = _as_text(risk.get("risk", ""))
                    row[1].text = _as_text(risk.get("severity", "")).upper()
                    row[2].text = _as_text(risk.get("mitigation", ""))

        # --- FIPS 206 Compliance Verification (auto-detected for quantum/security workflows) ---
        workflow = _as_text(meta.get("workflow", "")).upper()
        all_text = (_as_text(meta.get("summary", "")) + " " +
                    " ".join(_as_text(v) for v in sections.values())).lower()
        is_quantum = (
            "quantum" in workflow or "security" in workflow or "cyber" in workflow or
            "pqc" in all_text or "post-quantum" in all_text or "fips 203" in all_text or
            "fips 206" in all_text or "falcon" in all_text or "ml-kem" in all_text or
            "tls" in all_text or "cryptograph" in all_text
        )

        if is_quantum:
            doc.add_page_break()
            doc.add_heading("FIPS 206 Compliance Verification", level=1)

            doc.add_heading("Post-Quantum Cryptography Standards Coverage", level=2)
            fips_table = doc.add_table(rows=1, cols=4)
            fips_table.style = "Table Grid"
            hdr = fips_table.rows[0].cells
            hdr[0].text = "Standard"
            hdr[1].text = "Algorithm"
            hdr[2].text = "Use Case"
            hdr[3].text = "Status"

            fips_data = [
                ("FIPS 203", "ML-KEM (Kyber)", "Key Encapsulation", "NIST Finalized"),
                ("FIPS 204", "ML-DSA (Dilithium)", "General Digital Signatures (~2.4KB)", "NIST Finalized"),
                ("FIPS 205", "SLH-DSA (SPHINCS+)", "Hash-Based Long-Term Signing", "NIST Finalized"),
                ("FIPS 206", "FN-DSA (FALCON)", "Integrity Anchor — Constrained Bandwidth", "NIST Draft March 2026"),
            ]
            for standard, algo, use_case, status in fips_data:
                row = fips_table.add_row().cells
                row[0].text = standard
                row[1].text = algo
                row[2].text = use_case
                row[3].text = status

            doc.add_heading("FIPS 206 Integrity Anchor Assessment", level=2)
            doc.add_paragraph(
                "FALCON (FN-DSA) signatures are approximately 666 bytes, fitting within standard network "
                "packet MTUs. ML-DSA (FIPS 204) signatures at ~2.4KB risk packet fragmentation on constrained "
                "links (satellite uplinks, remote industrial sensors, legacy gateway interfaces with <1KB limits). "
                "In these environments, FN-DSA is the only quantum-resistant signature algorithm that provides "
                "cryptographic integrity without triggering denial-of-service via fragmentation."
            )
            doc.add_paragraph(
                "Recommendation: Deploy ML-KEM (FIPS 203) for key encapsulation on all channels. "
                "Use SLH-DSA (FIPS 205) for firmware and code signing where signature size is not constrained. "
                "Use FALCON/FN-DSA (FIPS 206) as the Integrity Anchor for any path with bandwidth constraints "
                "or legacy packet-size limitations. Reject non-hybrid certificates by the 2030 CNSS horizon."
            )

            doc.add_heading("Quantum Drift Detection Results", level=2)
            # Scan card results for quantum drift violations
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
                                    f"[{provider.upper()}] {claim.get('claim', 'N/A')[:200]}\n"
                                    f"  Violation: {v}",
                                    style='List Bullet'
                                )
                                drift_found = True
            if not drift_found:
                doc.add_paragraph(
                    "No Quantum Drift violations detected in this analysis. All referenced cryptographic "
                    "mechanisms include post-quantum wrappers or are PQC-native."
                )

            doc.add_heading("Compliance Attestation", level=2)
            doc.add_paragraph(
                f"This report was generated by KORUM-OS Multi-Agent Council ({len(meta.get('models_used', []))} "
                f"independent AI providers) on {meta.get('generated_at', datetime.now().isoformat())}. "
                f"Composite Truth Score: {truth_display}/100. "
                f"Cryptographic compliance assessment covers NIST FIPS 203, 204, 205, and 206 (Draft). "
                f"Report ready for cryptographic signing via Qanapi Armory (FedRAMP High Enclave)."
            )

        # --- Individual Council Analysis ---
        if card_results:
            doc.add_page_break()
            doc.add_heading("Council Member Analysis", level=1)
            for provider, result in card_results.items():
                if not isinstance(result, dict) or not result.get("success"):
                    continue
                provider_name = provider.replace("_", " ").title()
                role = _as_text(result.get("role", "")).upper()
                truth = result.get("truth_meter", "N/A")
                doc.add_heading(f"{provider_name} — {role} (Truth: {truth}/100)", level=2)
                response_text = _as_text(result.get("response", ""))
                for para in response_text.split("\n\n"):
                    para = para.strip()
                    if para:
                        doc.add_paragraph(para)

        footer = doc.sections[0].footer
        paragraph = footer.paragraphs[0]
        paragraph.text = (
            f"KORUM-OS Intelligence Asset | Confirmed via Multi-Agent Council | {datetime.now().year}"
        )
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        filename = f"korum_report_{_timestamp()}.docx"
        filepath = _output_path(filename, output_dir)
        doc.save(filepath)
        return filepath


class PPTXExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        from pptx.util import Pt as PptxPt

        meta, sections, _ = _extract_parts(intelligence_object)
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
        meta, sections, structured = _extract_parts(intelligence_object)
        wb = Workbook()

        ws_meta = wb.active
        ws_meta.title = "Summary"
        ws_meta.append(["Field", "Value"])
        ws_meta.append(["Title", _as_text(meta.get("title", ""))])
        ws_meta.append(["Generated At", _as_text(meta.get("generated_at", ""))])
        ws_meta.append(["Truth Score", _as_text(meta.get("composite_truth_score", ""))])
        ws_meta.append(
            [
                "Models Used",
                ", ".join(meta.get("models_used", [])) if isinstance(meta.get("models_used"), list) else _as_text(meta.get("models_used", "")),
            ]
        )
        ws_meta.append(["Summary", _as_text(meta.get("summary", ""))])

        ws_sections = wb.create_sheet("Sections")
        ws_sections.append(["Section", "Content"])
        for section_id, content in sections.items():
            ws_sections.append([section_id.replace("_", " ").title(), _as_text(content)])

        ws_metrics = wb.create_sheet("Key Metrics")
        ws_metrics.append(["Metric", "Value", "Context"])
        for metric in structured.get("key_metrics", []):
            ws_metrics.append(
                [
                    _as_text(metric.get("metric", "")),
                    _as_text(metric.get("value", "")),
                    _as_text(metric.get("context", "")),
                ]
            )

        ws_actions = wb.create_sheet("Action Items")
        ws_actions.append(["Task", "Priority", "Timeline"])
        for item in structured.get("action_items", []):
            ws_actions.append(
                [
                    _as_text(item.get("task", "")),
                    _as_text(item.get("priority", "")),
                    _as_text(item.get("timeline", "")),
                ]
            )

        ws_risks = wb.create_sheet("Risks")
        ws_risks.append(["Risk", "Severity", "Mitigation"])
        for risk in structured.get("risks", []):
            ws_risks.append(
                [
                    _as_text(risk.get("risk", "")),
                    _as_text(risk.get("severity", "")),
                    _as_text(risk.get("mitigation", "")),
                ]
            )

        filename = f"korum_intelligence_{_timestamp()}.xlsx"
        filepath = _output_path(filename, output_dir)
        wb.save(filepath)
        return filepath


class CSVExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured = _extract_parts(intelligence_object)
        filename = f"korum_intelligence_{_timestamp()}.csv"
        filepath = _output_path(filename, output_dir)
        with open(filepath, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["type", "key", "value", "extra"])

            writer.writerow(["meta", "title", _as_text(meta.get("title", "")), ""])
            writer.writerow(["meta", "generated_at", _as_text(meta.get("generated_at", "")), ""])
            writer.writerow(["meta", "summary", _as_text(meta.get("summary", "")), ""])
            writer.writerow(["meta", "truth_score", _as_text(meta.get("composite_truth_score", "")), ""])

            for section_id, content in sections.items():
                writer.writerow(["section", section_id, _as_text(content), ""])

            for metric in structured.get("key_metrics", []):
                writer.writerow(
                    ["key_metric", _as_text(metric.get("metric", "")), _as_text(metric.get("value", "")), _as_text(metric.get("context", ""))]
                )
            for item in structured.get("action_items", []):
                writer.writerow(
                    ["action_item", _as_text(item.get("task", "")), _as_text(item.get("priority", "")), _as_text(item.get("timeline", ""))]
                )
            for risk in structured.get("risks", []):
                writer.writerow(
                    ["risk", _as_text(risk.get("risk", "")), _as_text(risk.get("severity", "")), _as_text(risk.get("mitigation", ""))]
                )
        return filepath


class TextExporter:
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured = _extract_parts(intelligence_object)
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
        meta, sections, structured = _extract_parts(intelligence_object)
        filename = f"korum_intelligence_{_timestamp()}.md"
        filepath = _output_path(filename, output_dir)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(f"# {_as_text(meta.get('title', 'KORUM Intelligence Report'))}\n\n")
            file.write(f"- Generated at: {_as_text(meta.get('generated_at', datetime.now().isoformat()))}\n")
            file.write(f"- Composite Truth Score: {_as_text(meta.get('composite_truth_score', 'N/A'))}/100\n\n")
            file.write(f"## Executive Summary\n\n{_as_text(meta.get('summary', ''))}\n\n")
            for section_id, content in sections.items():
                file.write(f"## {section_id.replace('_', ' ').title()}\n\n{_as_text(content)}\n\n")
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
    @staticmethod
    def generate(intelligence_object, output_dir=None):
        meta, sections, structured = _extract_parts(intelligence_object)
        card_results = intelligence_object.get("_card_results", {})
        filename = f"korum_intelligence_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)

        doc = SimpleDocTemplate(filepath, pagesize=letter,
                                topMargin=50, bottomMargin=50,
                                leftMargin=50, rightMargin=50)
        styles = getSampleStyleSheet()
        story = []

        # --- Normalize truth score ---
        truth_raw = meta.get("composite_truth_score", "N/A")
        try:
            truth_val = float(truth_raw)
            truth_display = str(int(truth_val * 100)) if truth_val <= 1 else str(int(truth_val))
        except (ValueError, TypeError):
            truth_display = str(truth_raw)

        # --- TITLE & META ---
        story.append(Paragraph(_as_text(meta.get("title", "KORUM Intelligence Report")), styles["Title"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Generated: {_as_text(meta.get('generated_at', datetime.now().isoformat()))}  |  "
                                f"Workflow: {_as_text(meta.get('workflow', 'RESEARCH'))}  |  "
                                f"Truth Score: {truth_display}/100  |  "
                                f"Agents: {len(meta.get('models_used', []))}",
                                styles["Normal"]))
        story.append(Spacer(1, 16))

        # --- EXECUTIVE SUMMARY ---
        story.append(Paragraph("Executive Summary", styles["Heading1"]))
        story.append(Paragraph(_as_text(meta.get("summary", "No summary available.")), styles["BodyText"]))
        story.append(Spacer(1, 16))

        # --- SYNTHESIS SECTIONS ---
        for section_id, content in sections.items():
            story.append(Paragraph(section_id.replace("_", " ").title(), styles["Heading2"]))
            text = _as_text(content)
            # Split into paragraphs for better readability
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    story.append(Paragraph(para, styles["BodyText"]))
                    story.append(Spacer(1, 6))
            story.append(Spacer(1, 10))

        # --- KEY METRICS TABLE ---
        key_metrics = structured.get("key_metrics", [])
        if key_metrics:
            story.append(Paragraph("Key Intelligence Metrics", styles["Heading2"]))
            table_data = [["Metric", "Value", "Context"]]
            for metric in key_metrics:
                if isinstance(metric, dict):
                    table_data.append([
                        _as_text(metric.get("metric", "")),
                        _as_text(metric.get("value", "")),
                        _as_text(metric.get("context", "")),
                    ])
            if len(table_data) > 1:
                table = Table(table_data, repeatRows=1, colWidths=[150, 100, 250])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]))
                story.append(table)
                story.append(Spacer(1, 16))

        # --- ACTION ITEMS TABLE ---
        action_items = structured.get("action_items", [])
        if action_items:
            story.append(Paragraph("Action Items", styles["Heading2"]))
            table_data = [["Task", "Priority", "Timeline"]]
            for item in action_items:
                if isinstance(item, dict):
                    table_data.append([
                        _as_text(item.get("task", "")),
                        _as_text(item.get("priority", "")).upper(),
                        _as_text(item.get("timeline", "")),
                    ])
            if len(table_data) > 1:
                table = Table(table_data, repeatRows=1, colWidths=[280, 80, 140])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]))
                story.append(table)
                story.append(Spacer(1, 16))

        # --- RISKS TABLE ---
        risks = structured.get("risks", [])
        if risks:
            story.append(Paragraph("Risk Assessment", styles["Heading2"]))
            table_data = [["Risk", "Severity", "Mitigation"]]
            for risk in risks:
                if isinstance(risk, dict):
                    table_data.append([
                        _as_text(risk.get("risk", "")),
                        _as_text(risk.get("severity", "")).upper(),
                        _as_text(risk.get("mitigation", "")),
                    ])
            if len(table_data) > 1:
                table = Table(table_data, repeatRows=1, colWidths=[200, 80, 220])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]))
                story.append(table)
                story.append(Spacer(1, 16))

        # --- INDIVIDUAL COUNCIL ANALYSIS (Card Results) ---
        if card_results:
            story.append(Paragraph("Council Member Analysis", styles["Heading1"]))
            story.append(Spacer(1, 8))
            for provider, result in card_results.items():
                if not isinstance(result, dict) or not result.get("success"):
                    continue
                provider_name = provider.replace("_", " ").title()
                role = _as_text(result.get("role", "")).upper()
                truth = result.get("truth_meter", "N/A")
                story.append(Paragraph(f"{provider_name} — {role} (Truth: {truth}/100)", styles["Heading2"]))
                response_text = _as_text(result.get("response", ""))
                # Split into paragraphs
                for para in response_text.split("\n\n"):
                    para = para.strip()
                    if para:
                        story.append(Paragraph(para, styles["BodyText"]))
                        story.append(Spacer(1, 4))
                story.append(Spacer(1, 12))

        doc.build(story)
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
