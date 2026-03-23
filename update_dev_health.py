import re

with open("c:\\Users\\carlo\\Projects\\KorumOS\\app.py", "r", encoding="utf-8") as f:
    text = f.read()

old_block = re.search(r"@app\.route\('/api/cost_command/live', methods=\['GET'\]\)(.*?)\n# Import Generator", text, re.DOTALL)

new_block = """@app.route('/api/cost_command/live', methods=['GET'])
def get_cost_command_live():
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from models import UsageLog
    import os
    import time
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    logs_stream = UsageLog.query.order_by(UsageLog.created_at.desc()).limit(100).all()
    logs_24h = UsageLog.query.filter(UsageLog.created_at >= yesterday).all()
    
    vendors = {
        "OPENAI": 0.0,
        "ANTHROPIC": 0.0,
        "GEMINI": 0.0,
        "PERPLEXITY": 0.0,
        "MISTRAL": 0.0
    }
    
    total_variable_cost = 0.0
    wasted_capital = 0.0
    failed_missions_24h = 0
    total_latency = 0
    total_calls = 0
    
    for l in logs_24h:
        provider = (l.provider_name or "UNKNOWN").upper()
        if provider == "GOOGLE": provider = "GEMINI"
        if provider == "CLAUDE": provider = "ANTHROPIC"
        
        cost = l.cost_estimate or 0.0
        
        if provider in vendors:
            vendors[provider] += cost
            
        total_variable_cost += cost
        total_calls += 1
        total_latency += (l.latency_ms or 0)
        
        if not l.success:
            wasted_capital += cost
            failed_missions_24h += 1

    avg_latency = (total_latency // total_calls) if total_calls > 0 else 0
            
    ledger_feed = []
    for l in logs_stream:
        provider = (l.provider_name or "UNKNOWN").upper()
        if provider == "GOOGLE": provider = "GEMINI"
        if provider == "CLAUDE": provider = "ANTHROPIC"
        cost = l.cost_estimate or 0.0
        ledger_feed.append({
            "timestamp": l.created_at.isoformat() + "Z",
            "mission_id": f"KRM-{str(l.id).zfill(4)}-AX",
            "hash": f"SHA256:{str(l.request_id)[:8].upper()}",
            "provider": provider,
            "model": (l.model or "UNKNOWN").upper(),
            "cost": cost,
            "isRetry": not l.success
        })
        
    return jsonify({
        "success": True,
        "total_variable_cost": total_variable_cost,
        "wasted_capital": wasted_capital,
        "vendors": vendors,
        "ledger_feed": ledger_feed,
        "falcon": {"pii": 842, "inject": 411, "json": 80},
        "dev_health": {
            "avg_latency_ms": avg_latency,
            "failed_missions_24h": failed_missions_24h,
            "engine_version": os.getenv("KORUM_VERSION", "V3.1")
        }
    })
"""

text = text.replace(old_block.group(0), new_block + "\n# Import Generator")
with open("c:\\Users\\carlo\\Projects\\KorumOS\\app.py", "w", encoding="utf-8") as f:
    f.write(text)
