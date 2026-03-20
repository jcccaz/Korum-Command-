import tempfile
import unittest
from pathlib import Path

from PyPDF2 import PdfReader

from exporters import ExecutiveMemoExporter


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


if __name__ == "__main__":
    unittest.main()
