# KorumOS - Decision Governance Stack

**KorumOS** is an Adversarial Decision Governance System for high-stakes intelligence analysis. It achieves **Decision Integrity** by wrapping modular AI providers in a zero-trust governance stack: **the Falcon Protocol** (PII Security), **the Confidence Governor** (Calibrated Fact-Scoring), and **the Audit Trail Ledger** (Immutable Provenance).

## Latest Launch

As of Monday, March 23, 2026, KorumOS includes the live **DRE Engine** workflow for defensible downside analysis.

- **Workflow:** Select `RISK EXPOSURE` in the workflow dropdown.
- **Input:** Provide an industry scenario, decision, or operating posture.
- **Output:** KorumOS runs five phases through the council: Intake, Multi-Model Risk Construction, Red Team Strike, Governor Assessment, and the final **Decision Risk Exposure Report**.
- **Key differentiator:** The numbers are debated before they reach the client. Red Team challenges inflated assumptions, and the Governor forces a defensible range with variance percentages and evidence grades.
- **Rule:** No "reduces risk by X%" claims without showing the math.

## Governance Layers

- **Falcon Protocol**: A 3-pass PII/PHI redaction engine with deterministic entity pseudonymization.
- **Confidence Governor**: A dual-layered scoring model (Fact vs. Decision) that enforces mandatory scoring floors and hard caps for unresolved conflicts.
- **Audit Trail Ledger (ATL)**: A tamper-evident, cryptographic history of every event in the mission lifecycle.
- **Neurol Council (Execution)**: A sequential reasoning chain of five independent AI providers (OpenAI, Anthropic, Google, Perplexity, Mistral).
- **Validated Intelligence Estimate (VIE)**: High-fidelity, truth-scored briefs that replace standard AI "responses" with auditable intelligence artifacts.
- **Decision Risk Exposure (DRE) Engine**: A five-phase council workflow that quantifies undefended decisions in dollar exposure before action is taken.

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

## Technical Specifications

KorumOS is a high-trust intelligence platform. Detailed architectural and protocol documentation is available for enterprise auditors:

- [GOVERNOR.md](file:///c:/Users/carlo/Projects/KorumOS/GOVERNOR.md) — Confidence Governor (theory & calibration)
- [SCORING_LOGIC.md](file:///c:/Users/carlo/Projects/KorumOS/SCORING_LOGIC.md) — Scoring floors, caps, & truth matrix logic
- [FALCON_SPEC.md](file:///c:/Users/carlo/Projects/KorumOS/FALCON_SPEC.md) — Falcon Protocol (3-pass redaction & PII masking)
- [ARCHITECTURE.md](file:///c:/Users/carlo/Projects/KorumOS/ARCHITECTURE.md) — 4-layer system overview
- [EXPORT_SPEC.md](file:///c:/Users/carlo/Projects/KorumOS/EXPORT_SPEC.md) — Report Exporter (Scans & Signals)
- [WORKFLOW_DNA.md](file:///c:/Users/carlo/Projects/KorumOS/WORKFLOW_DNA.md) — Posture & Output Registries
- [API_REFERENCE.md](file:///c:/Users/carlo/Projects/KorumOS/API_REFERENCE.md) — Operational endpoints & auth gates
- [CHART_ENGINE.md](file:///c:/Users/carlo/Projects/KorumOS/CHART_ENGINE.md) — Semantic visualization & SVG renderers
- [INTELLIGENCE_LIFECYCLE.md](file:///c:/Users/carlo[REDACTED]) — End-to-end operational walkthrough
- [PROVENANCE_SPEC.md](file:///c:/Users/carlo/Projects/KorumOS/PROVENANCE_SPEC.md) — Audit Trail Ledger (ATL) logic

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
