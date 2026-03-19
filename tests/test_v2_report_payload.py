import json
import os
import sys
import unittest
from unittest.mock import patch


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as korum_app


class TestV2ReportPayload(unittest.TestCase):

    @patch('app.execute_council_v2')
    def test_async_pipeline_preserves_report_recall_fields(self, mock_execute_council_v2):
        job_id = "job-report-payload"
        korum_app._council_jobs.pop(job_id, None)

        mock_execute_council_v2.return_value = {
            "consensus": "Council reached a clear recommendation.",
            "classification": {"outputType": "report"},
            "divergence": {"divergence_score": 12, "divergence_summary": "Minor variance only."},
            "synthesis": {
                "meta": {
                    "summary": "Executive synthesis summary.",
                    "final_document": "Final document body."
                }
            },
            "metrics": {"run_cost": 0.031, "latency_ms": 4200},
            "results": {
                "openai": {
                    "success": True,
                    "role": "Strategic Core",
                    "model": "gpt-4o",
                    "response": "Provider body text that must remain available for report recall.",
                    "truth_meter": 82,
                    "contribution_score": 91,
                    "citations": ["https://example.com/a", "https://example.com/b"],
                    "verified_claims": [
                        {"claim": "Claim A", "status": "VERIFIED", "score": 97, "type": "metric"}
                    ],
                    "usage": {"cost": 0.0091, "latency": 12340, "input": 100, "output": 200}
                }
            }
        }

        korum_app._run_council_job(
            job_id=job_id,
            query="Test query",
            personas={"openai": "strategist"},
            workflow="RESEARCH",
            active_models=["openai"],
            user_id=None,
            hacker_mode=False,
            use_falcon=False,
            falcon_level="STANDARD",
            falcon_meta=None,
            _falcon_placeholder_map={},
            _ghost_map_summary={},
            _residual_report={},
            _vault_doc_ids_used=[]
        )

        status, result_raw = korum_app._job_get(job_id)
        self.assertEqual(status["status"], "complete")
        self.assertIsNotNone(result_raw)

        result = json.loads(result_raw)
        pipeline_result = result["pipeline_result"]
        provider = pipeline_result["results"]["openai"]

        self.assertEqual(pipeline_result["consensus"], "Council reached a clear recommendation.")
        self.assertEqual(pipeline_result["classification"]["outputType"], "report")
        self.assertEqual(pipeline_result["divergence"]["divergence_score"], 12)
        self.assertEqual(provider["role"], "Strategic Core")
        self.assertEqual(provider["response"], "Provider body text that must remain available for report recall.")
        self.assertEqual(provider["citations"], ["https://example.com/a", "https://example.com/b"])
        self.assertEqual(provider["cost"], 0.0091)
        self.assertEqual(provider["time"], 12.34)


if __name__ == '__main__':
    unittest.main()
