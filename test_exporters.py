import sys
import os
import json
from datetime import datetime

# Mock the environment
sys.path.append(os.getcwd())

from exporters import PDFExporter, WordExporter

dummy_intel = {
    "meta": {
        "title": "Debug Mission",
        "workflow": "Research",
        "composite_truth_score": "0.85",
        "theme": "NEON_DESERT",
        "models_used": ["GPT-4", "Claude-3"]
    },
    "sections": {
        "Executive_Summary": "This is a **bold** finding with a [CRITICAL] tag and <xml> special chars.",
        "Strategic_Analysis": "More findings [ACTION REQUIRED] here."
    },
    "intelligence_tags": {
        "decisions": ["Execute the plan immediately."]
    },
    "docked_snippets": [
        {"title": "Evidence A", "content": "Raw data here.", "includeInReport": True}
    ]
}

print("--- Testing PDF Exporter ---")
try:
    path = PDFExporter.generate(dummy_intel, output_dir="exports")
    print(f"✅ PDF Success: {path}")
except Exception as e:
    import traceback
    print("❌ PDF CRASHED:")
    traceback.print_exc()

print("\n--- Testing Word Exporter ---")
try:
    path = WordExporter.generate(dummy_intel, output_dir="exports")
    print(f"✅ Word Success: {path}")
except Exception as e:
    import traceback
    print("❌ Word CRASHED:")
    traceback.print_exc()
