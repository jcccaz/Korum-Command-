import sys
import os
import json
from datetime import datetime

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from exporters import WordExporter, PDFExporter, PPTXExporter, ExcelExporter

# Mock Intelligence Object
intel_obj = {
    "mission_metadata": {
        "title": "Operation Emerald: Strategic Verification",
        "generated_at": datetime.now().isoformat(),
        "composite_truth_score": 94,
        "theme": "EMERALD", # NEW THEME TEST
        "models_used": ["Google Gemini Pro", "Anthropic Claude 3.5"]
    },
    "synthesis_results": {
        "executive_summary": "This is a **High-Priority** Emerald brief.\n\n### Key Findings\n- **Metric 1**: Verified via source node A.\n- **Metric 2**: High-confidence correlation.\n\nThis report has been **themed** for Jade/Green visibility.",
        "detailed_analysis": "#### Analysis Cluster A\nThe adversarial audit (Interrogation) was successful.\n\n- Bullet A: Correct\n- Bullet B: Validated"
    },
    "intelligence_interrogations": [
        {
            "attacker": "Red Team",
            "attacker_model": "GPT-4o",
            "defender": "Green Team",
            "defender_model": "Claude 3.5",
            "attacker_response": "Why is the **Emerald** theme better?",
            "defender_response": "It provides **superior eye-comfort** and distinct branding.",
            "verdict": "VERIFIED"
        }
    ],
    "intelligence_verifications": [
        {
            "claim": "Strategic Emerald is the best theme",
            "verification": "Source node verified **Jade/Green** is superior for visibility.",
            "verdict": "CONFIRMED"
        }
    ],
    "structured_data": {
        "key_metrics": [
            {"metric": "Verification Speed", "value": "98 ms", "context": "Benchmark A"},
            {"metric": "Theme Distinctness", "value": "High", "context": "User Audit"}
        ],
        "risks": [
            {"risk": "Theme Fatigue", "severity": "LOW", "mitigation": "Rotate colors"}
        ]
    }
}

output_dir = "exports/test_emerald"
os.makedirs(output_dir, exist_ok=True)

print("\n[KORUM-OS] Generating Emerald Theme Test Suite...")

try:
    docx_path = WordExporter.generate(intel_obj, output_dir=output_dir)
    print(f"OK DOCX Exported: {docx_path}")
    
    pdf_path = PDFExporter.generate(intel_obj, output_dir=output_dir)
    print(f"OK PDF Exported: {pdf_path}")
    
    pptx_path = PPTXExporter.generate(intel_obj, output_dir=output_dir)
    print(f"OK PPTX Exported: {pptx_path}")
    
    xlsx_path = ExcelExporter.generate(intel_obj, output_dir=output_dir)
    print(f"OK XLSX Exported: {xlsx_path}")
    
    print("\n[SUCCESS] Test Complete. All files now reside in " + os.path.abspath(output_dir))
except Exception as e:
    import traceback
    print(f"ERROR during generation: {e}")
    traceback.print_exc()
