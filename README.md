# KorumOS - Decision Intelligence Interface

**KorumOS** is a neural council interface for autonomous AI decision-making, featuring multi-model orchestration and real-time visualization.

## Features

- **Multi-AI Council**: Orchestrates GPT-4o, Claude 3.5, Gemini 2.0, and Perplexity
- **Adaptive Workflows**: War Room, Deep Research, Creative Council, Code Audit, System Core
- **Falcon Protocol**: Dual-layered PII governance (Shadow Redaction & Veil Re-hydration)
- **V2 Reasoning Pipeline**: Full sequential execution (Deconstruction -> Architecture -> Stress Test -> Synthesis)
- **AI Accountability System**: Real-time Truth Meter, claim highlighting, and suspect statement detection
- **Selective Interrogation**: Targeted "Direct Command Link" interrogation via unified Global Comms
- **Excel-Ready Export**: Optimized CSV copying and Research Dock data collection
- **Orbital Visualization**: Stabilized gyroscopic nodes with real-time neural handshake telemetry

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
GOOGLE_API_KEY=your_key
PERPLEXITY_API_KEY=your_key
DATABASE_URL=postgresql://user:password@host:port/dbname
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.0-flash
PERPLEXITY_MODEL=sonar-pro
PERPLEXITY_ENABLED=true
PERPLEXITY_MAX_INPUT_CHARS=12000
PERPLEXITY_MAX_TOKENS=700
PERPLEXITY_MAX_REQUEST_COST_USD=0.30
PERPLEXITY_DAILY_BUDGET_USD=5.00
PERPLEXITY_REQUEST_FEE_USD=0.00
ALERT_BUDGET_AMBER_PCT=0.70
ALERT_BUDGET_RED_PCT=0.95
```

3. Run the application:
```bash
python app.py
```

4. Open browser to `http://localhost:5000`

## Project Structure

```
KorumOS/
├── index.html          # Main interface
├── js/
│   └── korum.js       # Frontend logic
├── css/               # Stylesheets
├── app.py             # Flask backend
├── requirements.txt   # Python dependencies
└── docs/              # Documentation
```

## License

KorumOS Enterprise — Commercial Licensing Available.

All rights reserved. This software, including its source code, architecture, and associated documentation, is proprietary and confidential. No part of this system may be reproduced, distributed, or transmitted in any form without prior written permission from the copyright holder.

Contact: info@korumos.com
