# KorumOS — Onboarding Manual

### Version 1.0 | March 2026

---

## Welcome to KorumOS

KorumOS is a multi-AI intelligence platform. Instead of asking one AI a question, you convene a council of five — each with a different specialty — and get a cross-verified intelligence brief. This manual walks you through everything on the screen, what it does, and how to use it.

---

## Table of Contents

1. [Logging In](#1-logging-in)
2. [The Dashboard — What You're Looking At](#2-the-dashboard)
3. [Choosing a Workflow](#3-choosing-a-workflow)
4. [The Five AI Cards](#4-the-five-ai-cards)
5. [Cycling Personas](#5-cycling-personas)
6. [Writing a Query](#6-writing-a-query)
7. [Smart Routing](#7-smart-routing)
8. [Prompt Enhancement](#8-prompt-enhancement)
9. [Reading the Results](#9-reading-the-results)
10. [Intelligence Tags — What the Colors Mean](#10-intelligence-tags)
11. [Truth Scoring](#11-truth-scoring)
12. [The Synthesis (Yellow Highlight)](#12-the-synthesis)
13. [Red Team Mode](#13-red-team-mode)
14. [Global Comms (Sentinel)](#14-global-comms)
15. [Follow-Up Questions](#15-follow-up-questions)
16. [Research Dock](#16-research-dock)
17. [File Upload](#17-file-upload)
18. [Exporting Your Intelligence](#18-exporting-your-intelligence)
19. [Report Library](#19-report-library)
20. [Workflow Quick Reference](#20-workflow-quick-reference)
21. [Persona Quick Reference](#21-persona-quick-reference)
22. [Persona Playbook — Who to Call and When](#22-persona-playbook)
23. [Keyboard & Tips](#23-keyboard-and-tips)

---

## 1. Logging In

Navigate to **KorumOS.com**. You'll see the login screen.

- **First time?** Click **Register** to create an account.
- **Returning?** Enter your username and password, click **Login**.
- Sessions persist until you close the browser or log out.

---

## 2. The Dashboard

Once logged in, you see the KorumOS dashboard. Here's the layout:

```
┌─────────────────────────────────────────────────────────┐
│  TOP NAV BAR — Workflow buttons (14 presets)             │
├───────────────────────────┬─────────────────────────────┤
│                           │                             │
│   LEFT COLUMN             │   RIGHT COLUMN              │
│   • 5 AI Provider Cards   │   • Global Comms (Sentinel) │
│   • Query Input Bar       │   • Research Dock            │
│   • Results Display       │   • Telemetry Log           │
│                           │                             │
├───────────────────────────┴─────────────────────────────┤
│  BOTTOM — Export Bar (Documents, Decks, Social)          │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Choosing a Workflow

The **top navigation bar** has 14 workflow presets. Click one to configure all five AI cards automatically.

### General Workflows
| Workflow | Best For |
|----------|----------|
| **System Core** | General-purpose questions, default config |
| **War Room** | Crisis situations, threat analysis, strategy |
| **Deep Research** | Academic research, deep-dive analysis |
| **Creative Council** | Content creation, marketing, brainstorming |
| **Code Audit** | Code review, security, architecture |

### Domain-Specific Workflows
| Workflow | Best For |
|----------|----------|
| **Legal Review** | Contracts, regulations, compliance |
| **Medical Council** | Clinical questions, health policy |
| **Finance Desk** | Investment, tax, portfolio analysis |
| **Science Panel** | Physics, chemistry, biology research |
| **Startup Launch** | Business plans, MVPs, go-to-market |
| **Tech Council** | Infrastructure, cloud, AI/ML, networking |

### Defense & Intelligence Workflows
| Workflow | Best For |
|----------|----------|
| **Defense Council** | Military ops, UAS/drone, force projection |
| **Cyber Command** | Cybersecurity, encryption, zero trust, incident response |
| **Quantum Security** | Post-quantum cryptography readiness, Zero Trust, FedRAMP/CMMC compliance |
| **Intel Brief** | OSINT, geopolitical risk, threat assessment |

**On mobile:** The nav collapses into a hamburger menu (three lines) at the top-right.

---

## 4. The Five AI Cards

Each card represents one AI provider on the council:

| Card | Provider | Strengths |
|------|----------|-----------|
| **Card 1** | OpenAI (GPT-4o) | Strong general analysis, strategic thinking |
| **Card 2** | Anthropic (Claude) | Nuanced reasoning, safety-conscious, thorough |
| **Card 3** | Google (Gemini) | Fast, good with data, real-time knowledge |
| **Card 4** | Perplexity (Sonar) | Live web search, citations, current events |
| **Card 5** | Mistral | European perspective, multilingual, technical |

A sixth **Local** fallback exists if all cloud providers fail (requires LM Studio running locally).

**How the V2 Engine works:** The AIs execute **sequentially, not in parallel**. Card 1 goes first. Card 2 sees Card 1's response and builds on it. Card 3 sees both. And so on. This means each successive response is deeper and more refined.

---

## 5. Cycling Personas

Each card shows a **role label** (e.g., STRATEGIST, HACKER, DEFENSE_OPS). You can change any card's persona:

1. **Click the role label** on any card.
2. It cycles to the next available persona for that provider.
3. Keep clicking to find the one you want.

There are **62 personas** total. Each provider has 15-20 available. Some examples:

- STRATEGIST, ANALYST, ARCHITECT, VISIONARY
- HACKER, NETWORK, CYBER_OPS, DEFENSE_OPS
- CRYPTOGRAPHER, ZERO_TRUST, SIGINT, COUNTERINTEL
- CFO, HEDGE_FUND, TAX, AUDITOR
- JURIST, MEDICAL, PHYSICIST, CHEMIST

When you select a workflow preset, it auto-assigns the best persona to each card. You can then override any individual card by cycling.

---

## 6. Writing a Query

The **query input bar** is below the AI cards.

1. Type your question in plain language.
2. Click **Execute** (or press Enter).
3. Watch each card light up sequentially as the council deliberates.

**Tips for better queries:**
- Be specific: "Assess counter-UAS capabilities against Iranian drone swarms in the Gulf region" beats "tell me about drones"
- State what you need: analysis, comparison, recommendation, risk assessment
- Include context: industry, region, timeframe, constraints

---

## 7. Smart Routing

KorumOS analyzes your query and **suggests the best workflow** automatically.

- Type your query and a suggestion appears: *"Detected: Defense Council"*
- Click to accept, or ignore it and use your current workflow.
- Keywords trigger routing (e.g., "drone" → Defense Council, "ransomware" → Cyber Command, "encryption" → Cyber Command, "patent" → Legal Review)

---

## 8. Prompt Enhancement

Before your query hits the council, the **Prompt Enhancement Engine** upgrades it:

- Rough input: *"tell me about drones in china"*
- Enhanced version: *"Assess Chinese drone capabilities including military UAS platforms, autonomous systems, swarm technology, and counter-UAS vulnerabilities. Analyze implications for Pacific theater operations and U.S. defense posture."*

This happens automatically. You get the enhanced version — your original intent, sharpened for intelligence-grade output.

---

## 9. Reading the Results

After execution, each card displays its response. You'll see:

- **Individual card responses** — Each AI's analysis from its assigned persona perspective
- **Colored intelligence tags** — Highlighted text with tactical labels (see below)
- **Truth scores** — Confidence ratings on key claims
- **Synthesis panel** — The unified intelligence brief combining all five perspectives

---

## 10. Intelligence Tags

Colored highlights in the output mark different types of intelligence:

| Tag | Color | Meaning | Example |
|-----|-------|---------|---------|
| **RISK VECTOR** | Red | Threats, vulnerabilities, dangers | "Reliance on GNSS makes swarms vulnerable to spoofing" |
| **DECISION CANDIDATE** | Blue | Actionable recommendations | "Deploy directed energy weapons for swarm countermeasures" |
| **KEY METRIC** | Purple | Important numbers/statistics | "40-60% parts commonality across drone platforms" |
| **TRUTH BOMB** | Green | Verified high-confidence facts | "CMMC Level 2 required for all DOD contractors by 2026" |

These tags help you scan a long brief quickly and find the critical intelligence.

---

## 11. Truth Scoring

Every major claim gets a truth score based on cross-provider verification:

| Score Range | Label | Meaning |
|-------------|-------|---------|
| **90-100** | CONFIRMED | Multiple AIs independently agree, high confidence |
| **70-89** | SUPPORTED | Majority agreement, likely accurate |
| **50-69** | UNVERIFIED | Mixed signals, needs further investigation |
| **Below 50** | CONTESTED | AIs disagree, treat with caution |

The accountability pass runs after all five AIs respond, checking each claim against the others.

---

## 12. The Synthesis (Yellow Highlight)

The **yellow highlighted section** at the bottom of results is the **Synthesis** — the unified intelligence brief.

- It's generated by analyzing all five AI responses together.
- It resolves contradictions, weighs evidence, and produces a single coherent assessment.
- This is not just a summary — it's a **new analysis** built from five perspectives.
- Think of it as the "final word" from the council.

---

## 13. Red Team Mode

Red Team activates an **adversarial analysis layer**. When enabled:

- The council still runs normally.
- But an additional pass runs that **attacks your own assumptions**.
- It finds weaknesses in the council's recommendations.
- It identifies what an adversary would exploit.

**How to activate:** Toggle the Red Team switch before executing your query.

**Best for:** Defense scenarios, security assessments, strategy stress-testing, competitive analysis.

---

## 14. Global Comms (Sentinel)

The **right column** contains Global Comms — a fast chat interface powered by Gemini Flash (with GPT-4o fallback).

**The Sentinel** is your tactical aide:
- Quick facts, definitions, calculations
- Fast follow-up questions about council results
- Casual queries that don't need a full council deliberation

Just type in the chat box and hit Enter or click the send arrow.

---

## 15. Follow-Up Questions

Sentinel has **conversation memory** — it remembers the last 6 exchanges in your session.

This means you can have a conversation:
1. *"What are the main counter-UAS technologies?"*
2. *"Which one is most effective against swarms?"*
3. *"Cost comparison of those two?"*

Each follow-up builds on what came before. Memory resets when you refresh the page.

**Pro tip:** Use the council for the big analysis, then use Sentinel follow-ups to drill into specific points. This is your way around the council's autopilot — you steer the conversation manually.

---

## 16. Research Dock

Switch from **Chat** to **Dock** tab in the right column to access the Research Dock.

The dock stores **snippets** extracted from council responses:
- Tables, code blocks, data points, charts
- Each snippet is color-coded by type (blue = table, purple = code, green = data, yellow = chart)
- Hover to see action buttons: copy, expand, delete
- Add tags to organize snippets
- Use **Summarize** to get an AI summary of all docked snippets

---

## 17. File Upload

Upload files for the council to analyze:

**Supported formats:**
- **Images** (PNG, JPG, GIF) — analyzed via vision APIs
- **PDF** documents — text extracted and analyzed
- **Word** (.docx) — full text extraction
- **Excel** (.xlsx) — data extraction and analysis

Click the upload button, select your file, and it becomes part of the query context. The council can reference the file contents in their analysis.

---

## 18. Exporting Your Intelligence

After a council run, the **Export Bar** at the bottom offers three categories:

### Export Report (Documents)
| Format | Description |
|--------|-------------|
| Research Paper (.docx) | Full academic-style paper |
| Research Paper (PDF) | Same, in PDF |
| Board Brief (PDF) | Condensed executive brief |
| Executive Memo (.docx) | Short decision memo |
| Intelligence Workbook (.xlsx) | Structured data in spreadsheet |
| Flat Data (.csv) | Raw data export |
| Raw Intelligence (.json) | Complete JSON payload |
| Markdown Brief (.md) | Markdown format |
| Text Report (.txt) | Plain text |

### Create Deck (Presentations)
| Format | Description |
|--------|-------------|
| PowerPoint (.pptx) | Opens interactive slide editor, then generates .pptx |
| Google Slides Draft | Downloads a text draft for pasting into Google Slides |
| Reveal.js | Markdown draft for Reveal.js presentations |

### Share to Social
| Platform | Description |
|----------|-------------|
| LinkedIn Post | Formatted for LinkedIn |
| X / Twitter Thread | Thread format with character limits |
| Threads | Meta Threads format |
| Reddit Post | Reddit-formatted post |
| Medium Article | Long-form article format |

Social exports copy formatted text to your clipboard for pasting.

---

## 19. Report Library

Your council runs are automatically saved. Access them from the **Report Library**:

- Click any saved report to reload it.
- Click the **X** button to delete a saved report.
- Reports persist across sessions (tied to your account).

---

## 20. Workflow Quick Reference

| Workflow | Card 1 (OpenAI) | Card 2 (Anthropic) | Card 3 (Google) | Card 4 (Perplexity) | Card 5 (Mistral) |
|----------|-----------------|-------------------|-----------------|--------------------|--------------------|
| System Core | Visionary | Architect | Critic | Researcher | Analyst |
| War Room | Strategist | Containment | Takeover | Scout | Analyst |
| Deep Research | Analyst | Researcher | Historian | Scout | Validator |
| Creative Council | Writer | Innovator | Marketing | Social | Creative |
| Code Audit | Architect | Integrity | Hacker | Optimizer | Coding |
| Legal Review | Jurist | Compliance | Critic | Scout | Negotiator |
| Medical Council | Medical | Bioethicist | Researcher | Scout | Analyst |
| Finance Desk | CFO | Auditor | Hedge Fund | Scout | Tax |
| Science Panel | Physicist | Biologist | Chemist | Scout | Professor |
| Startup Launch | BizStrat | Product | Marketing | Scout | CFO |
| Tech Council | AI Architect | Network | Telecom | Scout | Hacker |
| Defense Council | Defense Ops | Cyber Ops | Intel Analyst | Scout | Hacker |
| Cyber Command | Cyber Ops | Counterintel | SIGINT | Intel Analyst | Hacker |
| Quantum Security | Zero Trust | Cryptographer | Compliance | AI Architect | Hacker |
| Intel Brief | Intel Analyst | Counterintel | Defense Ops | Scout | SIGINT |

---

## 21. Persona Quick Reference

### Defense & Intelligence (8 personas)
| Persona | Specialty |
|---------|-----------|
| DEFENSE_OPS | UAS/drone warfare, counter-UAS, ISR, autonomous systems, force projection |
| CYBER_OPS | Offensive/defensive cyber, incident response, NIST/CMMC, red team/blue team |
| INTEL_ANALYST | OSINT, SIGINT, HUMINT, geopolitical risk, threat intelligence |
| DEFENSE_ACQ | DOD contracting, FedRAMP, SBIR/STTR, ITAR/EAR, government proposals |
| SIGINT | Electronic warfare, communications intelligence, spectrum analysis, RF systems |
| COUNTERINTEL | Insider threat, adversary tactics, OPSEC, security protocols |
| CRYPTOGRAPHER | AES/RSA, PKI, post-quantum crypto, TLS/SSL, zero-knowledge proofs |
| ZERO_TRUST | NIST 800-207, DOD ZTRA, micro-segmentation, SASE/SSE, least-privilege |

### Strategy & Analysis (8 personas)
| Persona | Specialty |
|---------|-----------|
| STRATEGIST | Competitive analysis, risk assessment, long-range planning |
| ANALYST | Quantitative analysis, pattern recognition, evidence-based decisions |
| ARCHITECT | Systems design, technical leadership, complex integration |
| CONTAINMENT | Crisis management, risk containment, blast radius mitigation |
| INTEGRITY | Compliance, quality assurance, standards enforcement |
| TAKEOVER | Competitive disruption, market domination, acquisition analysis |
| CRITIC | Stress-testing ideas, finding weaknesses, challenging assumptions |
| OPTIMIZER | Bottleneck identification, process streamlining, efficiency |

### Research & Innovation (5 personas)
| Persona | Specialty |
|---------|-----------|
| RESEARCHER | Academic synthesis, literature gaps, evidence-based analysis |
| INNOVATOR | Novel solutions, emerging opportunities, unconventional approaches |
| VISIONARY | Technology trends, paradigm shifts, transformative possibilities |
| SCOUT | OSINT reconnaissance, source verification, information synthesis |
| VALIDATOR | Fact-checking, data integrity, logical consistency |

### Business & Finance (8 personas)
| Persona | Specialty |
|---------|-----------|
| CFO | Financial modeling, capital allocation, corporate finance |
| BIZSTRAT | Market analysis, competitive positioning, go-to-market |
| PRODUCT | Product strategy, user research, roadmap planning |
| HEDGE_FUND | Alternative investments, derivatives, market microstructure |
| TAX | Corporate taxation, international tax law, tax-efficient structuring |
| NEGOTIATOR | Deal structuring, conflict resolution, strategic concessions |
| AUDITOR | Financial controls, fraud detection, operational risk |
| SALES | Enterprise sales, pipeline management, revenue optimization |

### Legal & Compliance (2 personas)
| Persona | Specialty |
|---------|-----------|
| JURIST | Regulatory compliance, contract law, IP, legal risk |
| COMPLIANCE | Industry regulations, policy frameworks, governance |

### Science & Medical (5 personas)
| Persona | Specialty |
|---------|-----------|
| PHYSICIST | Applied physics, materials science, sensor systems |
| CHEMIST | Chemical analysis, materials science, pharmaceuticals |
| BIOLOGIST | Molecular biology, genetics, biotechnology |
| MEDICAL | Clinical evidence, healthcare policy, biomedical science |
| BIOETHICIST | Moral implications of scientific and medical decisions |

### Technology (5 personas)
| Persona | Specialty |
|---------|-----------|
| AI_ARCHITECT | ML systems, neural networks, autonomous systems, AI at scale |
| NETWORK | Zero-trust architecture, network segmentation, intrusion detection |
| TELECOM | 5G, satellite comms, secure communications, signal processing |
| CODING | Code architecture, debugging, performance, multi-language |
| WEB_DESIGNER | Responsive design, accessibility, UX, frontend architecture |

### Content & Communication (5 personas)
| Persona | Specialty |
|---------|-----------|
| WRITER | Clear, compelling, audience-appropriate content |
| CREATIVE | Storytelling, brand narrative, visual thinking |
| MARKETING | Brand positioning, growth marketing, campaign optimization |
| SOCIAL | Platform algorithms, content virality, community building |
| HISTORIAN | Historical analysis, contextual patterns, lessons from precedent |

### Academic (2 personas)
| Persona | Specialty |
|---------|-----------|
| PROFESSOR | Scholarly analysis with pedagogical clarity |
| ECONOMIST | Macroeconomic analysis, market dynamics, policy impact |

---

## 22. Persona Playbook — Who to Call and When

This is the practical guide: **what situation are you in, and which personas should be on the council?**

### Scenario: "I'm evaluating a defense contract opportunity"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | DEFENSE_ACQ | Knows DOD procurement, SBIR/STTR, contract structures |
| Anthropic | COMPLIANCE | Catches regulatory gaps, ITAR/EAR issues |
| Google | CFO | Models the financials, cost-benefit analysis |
| Perplexity | SCOUT | Pulls live data on the contracting agency, recent awards |
| Mistral | NEGOTIATOR | Deal structuring, pricing strategy, concession planning |

### Scenario: "We've been hit with ransomware"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | CYBER_OPS | Incident response playbook, containment steps |
| Anthropic | COUNTERINTEL | Who's behind it, attribution, adversary TTPs |
| Google | SIGINT | Network forensics, communications analysis |
| Perplexity | INTEL_ANALYST | Live threat intel, IOCs, recent campaign data |
| Mistral | HACKER | Thinks like the attacker, finds the attack vector |

**Enable Red Team** for this one — it'll stress-test your response plan.

### Scenario: "Design a zero trust architecture for our network"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | ZERO_TRUST | NIST 800-207, DOD ZTRA, policy architecture |
| Anthropic | NETWORK | Micro-segmentation, infrastructure implementation |
| Google | CRYPTOGRAPHER | Encryption layers, PKI, key management |
| Perplexity | SCOUT | Latest zero trust vendor solutions, case studies |
| Mistral | HACKER | Finds holes in the proposed architecture |

### Scenario: "Assess our current RSA-2048 cryptographic posture against a 'Harvest Now, Decrypt Later' quantum attack."
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | ZERO_TRUST | Enforces zero trust access controls around current data stores |
| Anthropic | CRYPTOGRAPHER | Analyzes quantum vulnerabilities in RSA/ECC |
| Google | COMPLIANCE | Maps exposure to FedRAMP, CMMC, and NIST PQC standards |
| Perplexity | AI_ARCHITECT | Models the timeline of quantum computing threats |
| Mistral | HACKER | Attacks the deployment strategy of new encryption protocols |

### Scenario: "Assess a competitor's market position"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | STRATEGIST | Competitive frameworks, strategic positioning |
| Anthropic | RESEARCHER | Deep-dive on their patents, products, financials |
| Google | TAKEOVER | Aggressive disruption angles, vulnerabilities |
| Perplexity | SCOUT | Live data — recent news, funding rounds, hires |
| Mistral | ANALYST | Data-driven comparison, metrics, trends |

### Scenario: "Prepare an investor pitch for our startup"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | BIZSTRAT | Go-to-market strategy, competitive positioning |
| Anthropic | PRODUCT | Product-market fit, roadmap, user research |
| Google | MARKETING | Growth strategy, audience, messaging |
| Perplexity | SCOUT | Market size data, comparable valuations |
| Mistral | CFO | Financial projections, unit economics, burn rate |

### Scenario: "Evaluate a new drug treatment for regulatory submission"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | MEDICAL | Clinical evidence, efficacy analysis |
| Anthropic | BIOETHICIST | Ethical implications, patient safety |
| Google | CHEMIST | Compound analysis, mechanism of action |
| Perplexity | SCOUT | Latest clinical trial results, FDA guidance |
| Mistral | ANALYST | Statistical analysis of trial data |

### Scenario: "I need to encrypt communications for a classified project"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | CRYPTOGRAPHER | Encryption protocol selection, post-quantum readiness |
| Anthropic | ZERO_TRUST | Identity-centric security, access controls |
| Google | SIGINT | What adversaries can intercept, signal analysis |
| Perplexity | SCOUT | Latest NSA/CISA guidance, approved crypto libraries |
| Mistral | NETWORK | Implementation, key distribution, infrastructure |

### Scenario: "Write a comprehensive research paper on autonomous drones"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | DEFENSE_OPS | UAS platforms, swarm tech, counter-UAS |
| Anthropic | RESEARCHER | Academic rigor, literature synthesis, citations |
| Google | HISTORIAN | Evolution of drone warfare, precedents |
| Perplexity | SCOUT | Latest developments, live sources |
| Mistral | PROFESSOR | Scholarly structure, pedagogical clarity |

### Scenario: "Audit our financial controls before an acquisition"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | CFO | Corporate finance, deal structure, valuation |
| Anthropic | AUDITOR | Financial controls, fraud detection, risk flags |
| Google | HEDGE_FUND | Market-side view, comparable transactions |
| Perplexity | SCOUT | Target company data, recent filings |
| Mistral | TAX | Tax implications, international structuring |

### Scenario: "Develop a counter-intelligence security program"
| Card | Persona | Why |
|------|---------|-----|
| OpenAI | INTEL_ANALYST | Threat landscape, adversary capabilities |
| Anthropic | COUNTERINTEL | Insider threat programs, OPSEC protocols |
| Google | CYBER_OPS | Digital security, monitoring, detection |
| Perplexity | SCOUT | Recent espionage cases, current threats |
| Mistral | ZERO_TRUST | Access controls, continuous verification |

### The Golden Rule

**If you're not sure which personas to pick, just use the workflow preset.** The presets are tuned for the most common scenarios. Then use Sentinel follow-ups to steer the analysis wherever you need it.

---

## 23. Keyboard & Tips

### Tips for Power Users

- **Cycle personas before executing** — customize the council for your specific question
- **Use Red Team for anything with stakes** — it catches blind spots the council misses
- **Export early, export often** — save to DOCX or PDF before starting a new query
- **Follow up in Sentinel** — don't re-run the whole council just to clarify one point
- **Upload files for context** — the council analyzes images, PDFs, spreadsheets alongside your query
- **Check truth scores** — CONFIRMED (90+) claims are cross-verified; UNVERIFIED (50-69) need more digging
- **The synthesis is not a summary** — it's a new analysis. Read it as the council's final verdict.

### Common Workflows

**"I need a quick fact"**
→ Use Global Comms (Sentinel). No need for the full council.

**"I need deep analysis on a complex topic"**
→ Pick the right workflow preset, write a specific query, enable Red Team, execute.

**"I got results but want to dig into one area"**
→ Use Sentinel follow-ups. Ask 2-3 follow-up questions to drill down.

**"I need to present this to my team"**
→ Click Export Report → Research Paper (.docx) or Board Brief (PDF). For slides, use Create Deck → PowerPoint.

**"I need to share a quick take on social"**
→ Click Share to Social → pick your platform → paste from clipboard.

---

*KorumOS — Five minds. One intelligence.*
