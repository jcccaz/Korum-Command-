import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from exporters import PDFExporter

# Mock intelligence object
intel = {
    "meta": {
        "title": "Test Dossier",
        "workflow": "STRATEGIC_SURVEY",
        "summary": "This is a test summary for the new PDF exporter. It should be bold and look premium.",
        "composite_truth_score": 0.85,
        "theme": "ARCHITECT"
    },
    "sections": {
        "Executive_Assessment": "This is the primary assessment. It should have a blue accent bar on the left.",
        "Market_Analysis": "Market sentiment is positive. There should be a pull quote below this."
    },
    "structured_data": {
        "key_metrics": [
            {"metric": "Revenue Growth", "value": "+24%", "context": "YoY"},
            {"metric": "Churn Rate", "value": "1.2%", "context": "MoM"},
            {"metric": "DAU", "value": "450k", "context": "Daily"}
        ]
    },
    "council_contributors": [
        {"provider": "openai", "role": "Lead Strategist", "phase": "Phase I"},
        {"provider": "anthropic", "role": "Auditor", "phase": "Phase II"}
    ],
    "_card_results": {
        "openai": {
            "model": "gpt-4o",
            "role": "Lead Strategist",
            "verified_claims": [
                {"claim": "Revenue jumped 24% in Q1.", "status": "verified", "confidence": "0.98"}
            ]
        },
        "anthropic": {
            "model": "claude-3-5-sonnet",
            "role": "Auditor",
            "verified_claims": [
                {"claim": "Profit margins are thinning.", "status": "challenged", "confidence": "0.65"}
            ]
        }
    },
    "divergence_analysis": {
        "divergence_summary": "Council consensus reached on top-line growth, divergence on margin sustainability."
    },
    "docked_snippets": [
        {"title": "Revenue Chart", "type": "donut", "content": "Chart showing 24% growth", "includeInReport": True}
    ]
}

try:
    print("Running PDF Export Test...")
    output_path = PDFExporter.generate(intel, output_dir="exports")
    print(f"PDF successfully generated at: {output_path}")
except Exception as e:
    print(f"PDF Generation Failed: {e}")
    import traceback
    traceback.print_exc()
