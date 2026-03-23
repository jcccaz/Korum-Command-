import re

def patch_llm_core():
    # 1. Add SerpAPI to llm_core.py
    with open("c:\\Users\\carlo\\Projects\\KorumOS\\llm_core.py", "r", encoding="utf-8") as f:
        core_text = f.read()
        
    if "serpapi-search" not in core_text:
        core_text = core_text.replace(
            '"sonar": {"input": 0.000001, "output": 0.000001},',
            '"sonar": {"input": 0.000001, "output": 0.000001},\n    # Live OSINT Pricing (Flat $0.01 per proxy search)\n    "serpapi-search": {"input": 0.01, "output": 0.0},'
        )
        with open("c:\\Users\\carlo\\Projects\\KorumOS\\llm_core.py", "w", encoding="utf-8") as f:
            f.write(core_text)
        print("Patched llm_core.py")

def patch_app_py():
    with open("c:\\Users\\carlo\\Projects\\KorumOS\\app.py", "r", encoding="utf-8") as f:
        app_text = f.read()

    # 2. Patch get_cost_command_live to include SERPAPI
    if '"SERPAPI": 0.0' not in app_text:
        app_text = app_text.replace(
            '"MISTRAL": 0.0',
            '"MISTRAL": 0.0,\n        "SERPAPI": 0.0'
        )
        print("Patched app.py vendors dictionary")

    # 3. Inject telemetry into fetch_serpapi_data
    if "log_usage_telemetry(\"serpapi-search\"" not in app_text:
        old_serp_block = re.search(r'print\(f"🌐 SerpAPI: Fetching real-time data(.*?)\n\n        return \{"success": True, "results": results, "answer_box": answer_box\}', app_text, re.DOTALL)
        
        if old_serp_block:
            new_block = old_serp_block.group(0).replace(
                'response = requests.get("https://serpapi.com/search", params=params, timeout=15)',
                'import time\n        from llm_core import log_usage_telemetry\n        st = time.time()\n        response = requests.get("https://serpapi.com/search", params=params, timeout=15)\n        lat = int((time.time() - st) * 1000)\n        log_usage_telemetry("serpapi-search", "serpapi", "scout", 1, 0, lat, True)\n'
            ).replace(
                'print(f"❌ SerpAPI Error: {str(e)}")\n        return {"success": False, "error": str(e)}',
                'print(f"❌ SerpAPI Error: {str(e)}")\n        from llm_core import log_usage_telemetry\n        log_usage_telemetry("serpapi-search", "serpapi", "scout", 1, 0, 0, False)\n        return {"success": False, "error": str(e)}'
            )
            app_text = app_text.replace(old_serp_block.group(0), new_block)
            print("Patched app.py fetch_serpapi_data")

    with open("c:\\Users\\carlo\\Projects\\KorumOS\\app.py", "w", encoding="utf-8") as f:
        f.write(app_text)

patch_llm_core()
patch_app_py()
