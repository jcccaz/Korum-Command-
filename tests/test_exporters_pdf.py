import tempfile
import unittest
import sys
import os
from pathlib import Path

from PyPDF2 import PdfReader
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Preformatted

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from exporters import ExecutiveMemoExporter, _build_pdf_red_team_alert


class ExecutiveMemoExporterTests(unittest.TestCase):
    def test_pdf_export_renders_section_tables(self):
        intelligence_object = {
            "meta": {
                "title": "Bozo Inc Financial Viability",
                "summary": "Revenue remains healthy but cash flow controls need work.",
                "workflow": "FINANCE",
                "theme": "BONE_FIELD",
                "composite_truth_score": 0.85,
                "session_id": "KO-INT-0094",
            },
            "sections": {
                "unit_economics_modeling": (
                    "Base Case Analysis\n"
                    "Monthly Recurring Revenue (MRR): $37,500\n"
                    "Monthly COGS: $15,000\n"
                    "Monthly Operating Burn: $10,000\n"
                    "Monthly Net Cash Generation: $12,500"
                ),
                "sensitivity_table": "Scenario review is below.",
            },
            "structured_data": {
                "key_metrics": [
                    {"metric": "Total Revenue", "value": "$20K"},
                    {"metric": "Net Profit", "value": "$8K"},
                    {"metric": "LTV / CAC", "value": "12.35x"},
                ]
            },
            "council_contributors": [
                {"provider": "openai"},
                {"provider": "perplexity"},
            ],
            "_card_results": {
                "openai": {
                    "verified_claims": [{"claim": "Revenue extraction confirmed across all three streams."}],
                    "response": "No table here.",
                },
                "perplexity": {
                    "verified_claims": [{"claim": "Sensitivity ranges confirmed across modeled scenarios."}],
                    "response": (
                        "| Scenario | Revenue | Net Income |\n"
                        "|---|---:|---:|\n"
                        "| Base | $450,000 | $150,000 |\n"
                        "| Down 10% | $405,000 | $105,000 |\n"
                        "| Up 25% | $562,500 | $262,500 |"
                    ),
                },
            },
            "divergence_analysis": {
                "divergence_summary": "Revenue is verified. Cash controls require remediation."
            },
            "_mission_context": {"client": "BOZO Inc"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(ExecutiveMemoExporter.generate(intelligence_object, output_dir=tmpdir))

            self.assertTrue(pdf_path.exists())

            reader = PdfReader(str(pdf_path))
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

            self.assertIn("Monthly Recurring Revenue (MRR)", extracted)
            self.assertIn("$37,500", extracted)
            self.assertIn("Scenario", extracted)
            self.assertIn("Down 10%", extracted)

    def test_red_team_alert_uses_wrapping_paragraph_for_attack_path(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('ExecBody', fontSize=8.5, leading=12.5))
        styles.add(ParagraphStyle('RedTeamAlertHeader', parent=styles['Heading2'], textColor=colors.HexColor('#C00000'), fontSize=18, leading=22))
        styles.add(ParagraphStyle('RedTeamMetadataBlock', parent=styles['BodyText'], backColor=colors.HexColor('#EEEEEE'), leading=14))
        styles.add(ParagraphStyle('AlertSubcap', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=10))
        styles.add(ParagraphStyle('RedTeamAttackPath', parent=styles['ExecBody'], fontName='Courier', fontSize=8, leading=11, leftIndent=15, rightIndent=4))

        raw_text = """
        {
          "weakest_assumption": "Upgrading hardware will directly improve customer-perceived speeds.",
          "execution_risks": [
            "A long attack path can describe routing inefficiencies, congestion spillover, telemetry blind spots, staged rollout conflicts, and post-cutover incompatibilities that remain unresolved if diagnostics are skipped before the $2 million upgrade is approved."
          ],
          "reversal_trigger": "If complaints remain flat after capex, reverse the strategy.",
          "confidence_attack": "Confidence is inflated because core claims are not empirically verified.",
          "unsupported_claims": [
            "Upgrading equipment will reduce complaints by at least 40%."
          ],
          "missing_evidence": [
            "Latency, packet loss, and jitter baselines by affected market."
          ],
          "red_team_status": "FAIL"
        }
        """

        flowables = _build_pdf_red_team_alert(raw_text, styles, 540)

        self.assertEqual(len(flowables), 4)
        alert_box = flowables[2]
        inner_flowables = alert_box._cellvalues[0][0]

        self.assertTrue(any(isinstance(item, Paragraph) and "ATTACK PATH:" in item.text for item in inner_flowables))
        self.assertTrue(any(isinstance(item, Paragraph) and "routing inefficiencies" in item.text for item in inner_flowables))
        self.assertFalse(any(isinstance(item, Preformatted) for item in inner_flowables))


if __name__ == "__main__":
    unittest.main()
