
import os
import json
from engine_v2 import classify_query_v2
from dotenv import load_dotenv

load_dotenv()

query = "What are the current prices for Nvidia RTX 5090?"
active_personas = {
    "openai": "Strategist",
    "anthropic": "Architect",
    "google": "Critic",
    "perplexity": "Scout",
    "mistral": "Analyst"
}

print(f"Testing Planner with query: {query}")
plan = classify_query_v2(query, active_personas)
print("Plan executionOrder:", plan.get('executionOrder'))
print("Plan JSON:", json.dumps(plan, indent=2))
