
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
                "keyPoints": ["Market is growing at 40% annually.", "Layer 2 solutions are critical."],
                "numericData": [{"metric": "Market Growth", "value": 40, "unit": "%"}],
                "actionItems": [],
                "risks": []
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
        self.assertIn('keyPoints', result)
        self.assertIn('numericData', result)
        
        # Check that conversational fluff is gone (based on our mock's clean output)
        # Note: In a real integration test, this validates the LLM's adherence to the prompt.
        # Here, it validating our JSON parsing logic works.
        self.assertEqual(result['numericData'][0]['value'], 40)
        self.assertEqual(result['numericData'][0]['unit'], '%')
        
        # Verify no fluff in the extracted points
        for point in result['keyPoints']:
            self.assertNotIn("As I mentioned", point)
            self.assertNotIn("Great point", point)


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
            # We verify that OpenAI (Step 2) was called with a prompt containing Perplexity's output
            args, _ = mock_gpt.call_args
            prompt_sent_to_openai = args[0]
            self.assertIn("PREVIOUS COUNCIL OUTPUT", prompt_sent_to_openai)
            self.assertIn("Perplexity: Found trend X", prompt_sent_to_openai)
            
            print("\n[TEST] Verified that Step 2 (OpenAI) received Context from Step 1 (Perplexity).")

if __name__ == '__main__':
    unittest.main()
