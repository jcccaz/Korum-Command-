import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from exporters import WordExporter

# Same intel as before
intel = {
    "meta": {
        "title": "Test Dossier Word",
        "workflow": "STRATEGIC_SURVEY",
        "summary": "Elite summary for Word output. DNA parity enabled.",
        "composite_truth_score": 0.85,
        "theme": "ARCHITECT"
    },
    "sections": {
        "Executive_Assessment": "This should be on the left, sidebar on the right.",
        "Market_Analysis": "Prose goes here. Pull quote sidebar enabled."
    },
    "structured_data": {
        "key_metrics": [
            {"metric": "Revenue", "value": "20k"},
            {"metric": "Profit", "value": "8k"}
        ]
    },
    "council_contributors": [
        {"provider": "openai", "role": "Lead Strategist", "phase": "Phase I"},
        {"provider": "anthropic", "role": "Auditor", "phase": "Phase II"}
    ],
    "_card_results": {
        "openai": {"model": "gpt-4o", "role": "Lead Strategist", "verified_claims": [{"claim": "Revenue 20k", "status": "verified"}]},
        "anthropic": {"model": "claude-3-5", "role": "Auditor", "verified_claims": [{"claim": "Profit 8k", "status": "verified"}]}
    },
    "divergence_analysis": {"divergence_summary": "High consensus."},
    "docked_snippets": [{"title": "Chart", "type": "donut", "content": "Chart content", "includeInReport": True}]
}

try:
    print("Running Word Export Test...")
    output_path = WordExporter.generate(intel, output_dir="exports")
    print(f"Word successfully generated at: {output_path}")
except Exception as e:
    print(f"Word Generation Failed: {e}")
    import traceback
    traceback.print_exc()
