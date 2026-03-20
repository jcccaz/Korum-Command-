
import sys
import os
import json
from datetime import datetime
from exporters import PDFExporter, WordExporter

# Mock Intelligence Object matching KorumOS structure
intel = {
    "metadata": {
        "title": "Operation Warm Stone",
        "summary": "Full infiltration of the network perimeter successful. Strategic pivot to phase 02 recommended for long-term target persistence.",
        "workflow": "Perimeter_Audit_01",
        "theme": "NEON_DESERT"
    },
    "sections": {
        "tactical_analysis": "The network perimeter [VERIFIED] remains stable. However, a [CRITICAL] risk was detected in the outbound firewall. **Priority recommendation:** seal breach immediately.",
        "strategic_pivot": "Move to phase 02. This involves [ACTION REQUIRED] internal node auditing. All results are verified by the Falcon protocol."
    },
    "intelligence_tags": {
        "decisions": ["PROCEED TO PHASE 02 WITHOUT DELAY"]
    },
    "artifacts": [
        {"label": "Network Topology", "content": "NODE_A -> NODE_B -> NODE_C\nAll nodes operating at 98% efficiency."}
    ]
}

print("--- Testing PDF Exporter ---")
try:
    path = PDFExporter.generate(intel, output_dir="exports")
    print(f"✅ PDF Success: {path}")
except Exception as e:
    import traceback
    print("❌ PDF CRASHED:")
    print(traceback.format_exc())

print("\n--- Testing Word Exporter ---")
try:
    path = WordExporter.generate(intel, output_dir="exports")
    print(f"✅ Word Success: {path}")
except Exception as e:
    import traceback
    print("❌ Word CRASHED:")
    print(traceback.format_exc())
