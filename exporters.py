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
        return json.dumps(value, ensure_ascii=True)
    return str(value)


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

        doc = Document()
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)

        title = doc.add_heading(meta.get("title", "KORUM Intelligence Report"), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        models = meta.get("models_used", [])
        if not isinstance(models, list):
            models = [str(models)]

        doc.add_paragraph(f"Generated at: {meta.get('generated_at', datetime.now().isoformat())}")
        doc.add_paragraph(f"Composite Truth Score: {meta.get('composite_truth_score', 'N/A')}/100")
        doc.add_paragraph("Models Used: " + ", ".join(models))
        doc.add_page_break()

        doc.add_heading("Executive Summary", level=1)
        doc.add_paragraph(_as_text(meta.get("summary", "")))
        doc.add_paragraph(_as_text(sections.get("executive_summary", "")))

        for section_id, content in sections.items():
            if section_id == "executive_summary":
                continue
            doc.add_heading(section_id.replace("_", " ").title(), level=1)
            doc.add_paragraph(_as_text(content))

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
                row = table.add_row().cells
                row[0].text = _as_text(metric.get("metric", ""))
                row[1].text = _as_text(metric.get("value", ""))
                row[2].text = _as_text(metric.get("context", ""))

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
        meta, sections, _ = _extract_parts(intelligence_object)
        prs = PPTXPresentation()

        title_slide = prs.slides.add_slide(prs.slide_layouts[0])
        title_slide.shapes.title.text = _as_text(meta.get("title", "Intelligence Report"))
        subtitle = title_slide.placeholders[1] if len(title_slide.placeholders) > 1 else None
        if subtitle:
            subtitle.text = f"KORUM-OS | {_as_text(meta.get('generated_at', ''))}"

        for section_id, content in sections.items():
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = section_id.replace("_", " ").title()
            if len(slide.placeholders) > 1:
                tf = slide.placeholders[1].text_frame
                text = _as_text(content)
                tf.text = text[:1000]
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
        filename = f"korum_intelligence_{_timestamp()}.pdf"
        filepath = _output_path(filename, output_dir)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(_as_text(meta.get("title", "KORUM Intelligence Report")), styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Generated at: {_as_text(meta.get('generated_at', datetime.now().isoformat()))}", styles["Normal"]))
        story.append(Paragraph(f"Composite Truth Score: {_as_text(meta.get('composite_truth_score', 'N/A'))}/100", styles["Normal"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        story.append(Paragraph(_as_text(meta.get("summary", "")), styles["BodyText"]))
        story.append(Spacer(1, 12))

        for section_id, content in sections.items():
            story.append(Paragraph(section_id.replace("_", " ").title(), styles["Heading2"]))
            story.append(Paragraph(_as_text(content), styles["BodyText"]))
            story.append(Spacer(1, 10))

        key_metrics = structured.get("key_metrics", [])
        if key_metrics:
            table_data = [["Metric", "Value", "Context"]]
            for metric in key_metrics:
                table_data.append(
                    [
                        _as_text(metric.get("metric", "")),
                        _as_text(metric.get("value", "")),
                        _as_text(metric.get("context", "")),
                    ]
                )
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(Spacer(1, 12))
            story.append(Paragraph("Key Intelligence Metrics", styles["Heading2"]))
            story.append(table)

        doc.build(story)
        return filepath
