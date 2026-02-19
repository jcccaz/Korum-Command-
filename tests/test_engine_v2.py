
import unittest
import sys
import os

# Adapt path to import engine_v2
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_v2 import synthesize_results, CouncilContext

# Mock LLM Call to avoid real API usage during test
# In a real scenario, we'd use unittest.mock
from unittest.mock import patch

class TestSynthesizer(unittest.TestCase):

    @patch('engine_v2.call_openai_gpt4')
    def test_synthesizer_extraction(self, mock_gpt):
        # 1. Setup Mock Response from GPT-4 (The Synthesizer)
        # We simulate what GPT-4 *should* return given the prompt instructions
        mock_gpt.return_value = {
            "success": True,
            "response": """
            ```json
            {
                "meta": {
                    "title": "Market Trends Analysis",
                    "generated_at": "2023-10-27T10:00:00",
                    "summary": "Market is growing at 40% annually.",
                    "composite_truth_score": 0.85,
                    "models_used": ["claude"],
                    "workflow": "RESEARCH"
                },
                "sections": {
                    "key_findings": "Market is growing at 40% annually. Layer 2 solutions are critical."
                },
                "structured_data": {
                    "key_metrics": [{"metric": "Market Growth", "value": "40%"}],
                    "action_items": [],
                    "risks": []
                },
                "intelligence_tags": {
                    "decisions": [],
                    "risks": [],
                    "metrics": ["40%"]
                }
            }
            ```
            """
        }

        # 2. Setup Input Context
        context = CouncilContext("Analyze market trends", {"intent": "analysis"})
        context.add_entry("claude", "analyst", "As I mentioned, the market is growing at 40%. Great point about Layer 2, specifically Optimism!")

        # 3. Execution
        result = synthesize_results(context)

        # 4. Assertions
        # Check that keys exist
        self.assertIn('meta', result)
        self.assertIn('sections', result)
        self.assertIn('intelligence_tags', result)
        
        # Check that conversational fluff is gone (based on our mock's clean output)
        self.assertEqual(result['meta']['title'], "Market Trends Analysis")
        self.assertEqual(result['structured_data']['key_metrics'][0]['value'], '40%')
        
        # Verify no fluff in the extracted sections
        for section, content in result['sections'].items():
            self.assertNotIn("As I mentioned", content)
            self.assertNotIn("Great point", content)


    @patch('engine_v2.call_perplexity')
    @patch('engine_v2.call_openai_gpt4')
    @patch('engine_v2.call_anthropic_claude')
    @patch('engine_v2.call_google_gemini')
    @patch('engine_v2.synthesize_results') # Mock synthesis to isolate flow test
    def test_council_flow_context_passing(self, mock_synth, mock_gemini, mock_claude, mock_gpt, mock_pplx):
        # 1. Setup Mock Responses
        mock_pplx.return_value = {"success": True, "response": "Perplexity: Found trend X.", "model": "sonar"}
        mock_gpt.return_value = {"success": True, "response": "OpenAI based on Perplexity: Use trend X strategically.", "model": "gpt-4o"}
        mock_claude.return_value = {"success": True, "response": "Anthropic: Building on OpenAI strategy...", "model": "claude-3-5"}
        mock_gemini.return_value = {"success": True, "response": "Google: Risks found in Anthropic plan.", "model": "gemini-2.0"}
        
        mock_synth.return_value = {"keyPoints": []}

        # 2. Setup Input
        from engine_v2 import execute_council_v2
        query = "Launch crypto token for Gen Z"
        personas = {"perplexity": "scout", "openai": "strategist", "anthropic": "architect", "google": "critic"}
        
        # 3. Execute
        # Note: classifier is internal to execute_council_v2, we should mock it too or rely on default fallback
        # Ideally, we mock `classify_query_v2` to return a fixed order.
        with patch('engine_v2.classify_query_v2') as mock_planner:
            mock_planner.return_value = {
                "executionOrder": ["perplexity-scout", "openai-strategist", "anthropic-architect", "google-critic"],
                "outputType": "report"
            }
            
            result = execute_council_v2(query, personas)
            
            # 4. Analyze Results
            # Check Order
            self.assertIn('perplexity', result['results'])
            self.assertIn('openai', result['results'])
            
            # Check Context Passing (Indirectly via prompt construction)
            # We look for the call that was NOT for claim identification
            orchestration_prompts = [call[0][0] for call in mock_gpt.call_args_list if "## PROFESSIONAL INTELLIGENCE BRIEF" in call[0][0]]
            
            self.assertTrue(len(orchestration_prompts) > 0)
            prompt_sent_to_openai = orchestration_prompts[0]
            self.assertIn("PREVIOUS CONTRIBUTIONS", prompt_sent_to_openai)
            self.assertIn("Perplexity: Found trend X", prompt_sent_to_openai)
            
            print("\n[TEST] Verified that Step 2 (OpenAI) received Context from Step 1 (Perplexity).")

if __name__ == '__main__':
    unittest.main()
