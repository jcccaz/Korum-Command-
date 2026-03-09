# KorumOS: Multi-Source AI Intelligence Platform

### Technical White Paper v1.0
### March 2026

---

## Executive Summary

KorumOS is a multi-source artificial intelligence platform that convenes a council of five independent AI providers to analyze queries, cross-verify claims, and produce structured intelligence briefs. Unlike single-model AI tools, KorumOS operates as a configurable intelligence desk — each provider is assigned a specialized persona, queries are executed sequentially so each AI builds on the previous one's analysis, and every claim is truth-scored through cross-provider verification.

The platform supports 14 workflow presets (including Defense Council, Cyber Command, and Intel Brief), 60+ expert personas, 10 export formats, real-time data enrichment, red team adversarial analysis, and enterprise-grade authentication with audit logging.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [The Council: Five AI Providers](#2-the-council-five-ai-providers)
3. [The V2 Engine: Sequential Execution](#3-the-v2-engine-sequential-execution)
4. [Intelligence Tagging System](#4-intelligence-tagging-system)
5. [Truth Scoring & Accountability Pass](#5-truth-scoring--accountability-pass)
6. [Workflow Presets](#6-workflow-presets)
7. [Persona System](#7-persona-system)
8. [Red Team / Interrogation Mode](#8-red-team--interrogation-mode)
9. [Sentinel: Quick-Strike Intelligence](#9-sentinel-quick-strike-intelligence)
10. [Live Data Enrichment (SERP)](#10-live-data-enrichment-serp)
11. [Prompt Enhancement Engine](#11-prompt-enhancement-engine)
12. [File Upload & Vision APIs](#12-file-upload--vision-apis)
13. [Research Dock](#13-research-dock)
14. [Export Suite](#14-export-suite)
15. [Security & Authentication](#15-security--authentication)
16. [Defense & Intelligence Use Cases](#16-defense--intelligence-use-cases)
17. [FedRAMP Readiness](#17-fedramp-readiness)

---

## 1. Architecture Overview

KorumOS is built on a Flask backend with a vanilla JavaScript frontend. It runs on Railway (US East Virginia) with PostgreSQL for persistent data.

**Core Architecture:**

```
USER QUERY
    │
    ▼
┌─────────────────────────────┐
│   WORKFLOW ENGINE            │
│   (Selects preset, assigns   │
│    personas, sets tone/goal) │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   V2 SEQUENTIAL ENGINE       │
│                              │
│   Phase 1: Classification    │
│   Phase 2: Sequential Exec   │
│   Phase 3: Accountability    │
│   Phase 4: Synthesis         │
└──────────────┬──────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
 ┌──────┐ ┌──────┐ ┌──────┐
 │OpenAI│ │Claude│ │Gemini│
 │GPT-4o│ │Sonnet│ │Flash │
 └──────┘ └──────┘ └──────┘
    │          │          │
    ▼          ▼          ▼
 ┌──────┐ ┌──────┐ ┌──────┐
 │Perpl.│ │Mistr.│ │Local │
 │Sonar │ │Small │ │(LM   │
 │      │ │      │ │Studio│
 └──────┘ └──────┘ └──────┘
               │
               ▼
┌─────────────────────────────┐
│   TRUTH SCORING              │
│   Cross-provider claim       │
│   verification (0-100)       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   SYNTHESIS & EXPORT         │
│   Structured brief with      │
│   tagged intelligence        │
└─────────────────────────────┘
```

**Key Design Principles:**
- **No single point of failure.** If any provider goes down, the others continue. Fallback chains ensure continuity.
- **Sequential, not parallel.** Each AI sees what came before, producing progressively deeper analysis.
- **Modular personas.** Any role can be assigned to any provider with one click.
- **Everything is auditable.** Every query, response, cost, and auth event is logged.

---

## 2. The Council: Five AI Providers

KorumOS maintains a permanent council of five cloud AI providers, plus a local fallback:

| Provider | Default Model | Strengths | Role in Council |
|----------|--------------|-----------|-----------------|
| **OpenAI** | GPT-4o | Broad knowledge, strong reasoning | Primary analyst |
| **Anthropic** | Claude Sonnet 4 | Nuanced analysis, safety-aware | Deep researcher |
| **Google** | Gemini 2.0 Flash | Speed, current knowledge | Fast integrator |
| **Perplexity** | Sonar | Live web search with citations | Real-time intelligence |
| **Mistral** | Mistral Small | European perspective, cost-efficient | Validator/alternative view |
| **Local** | LM Studio | Air-gapped, no data leaves network | Emergency fallback |

**Why five providers matter:**
- Single-AI tools give you one perspective. KorumOS gives you five independent analyses.
- Disagreements between providers are surfaced, not hidden — this is how real intelligence analysis works.
- Provider-specific strengths are leveraged: Perplexity for live citations, Anthropic for nuanced risk assessment, Google for speed.

**Fallback Chain:**
If a provider fails, KorumOS automatically falls back:
1. Primary provider (e.g., OpenAI)
2. Mistral Cloud (Level 1 fallback)
3. Local LLM via LM Studio (Level 2 fallback — fully air-gapped)

---

## 3. The V2 Engine: Sequential Execution

The V2 engine is KorumOS's core execution pipeline. Unlike tools that fire all AI calls in parallel, V2 runs them **sequentially** — each provider sees the previous provider's response and builds on it.

### Phase 1: Classification

The engine analyzes the incoming query to determine:
- **Domain**: business, marketing, software, operations, research, strategy
- **Intent**: plan, build, analyze, optimize, critique, research, launch
- **Complexity**: simple, moderate, complex
- **Output type**: presentation, technical spec, marketing plan, report, strategic framework

This classification determines the execution order and the tone/structure of the final output.

### Phase 2: Sequential Execution

Each AI runs in order, with context from all previous responses:

```
AI #1 (e.g., OpenAI/strategist)
  → Produces initial analysis
    → AI #2 (e.g., Anthropic/researcher) sees AI #1's output
      → Adds deeper research, challenges assumptions
        → AI #3 (e.g., Google/critic) sees AI #1 + #2
          → Stress-tests the analysis
            → AI #4 (e.g., Perplexity/scout) sees all prior
              → Adds live-sourced data with citations
                → AI #5 (e.g., Mistral/validator) sees everything
                  → Final integration and validation
```

The final AI in the chain acts as **Integrator** — it synthesizes all prior analyses into a cohesive report.

### Phase 3: Accountability Pass (Truth Scoring)

After all five AIs have responded, the engine extracts specific, testable claims from each response and cross-references them against the other four. Details in Section 5.

### Phase 4: Synthesis

The raw discussion is converted into a structured intelligence object containing:
- Executive summary
- Key metrics
- Action items
- Risk assessments
- Intelligence tags (decisions, risks, metrics, verified facts)

---

## 4. Intelligence Tagging System

Every AI in the council is instructed to mark high-value intelligence with structured tags. These tags are embedded in the natural response and extracted by the backend for structured analysis.

### Tag Types

| Tag | Color | Purpose | Example |
|-----|-------|---------|---------|
| **RISK VECTOR** | Red | Identified threats, vulnerabilities, dangers | "Reliance on GNSS makes swarms vulnerable to spoofing" |
| **DECISION CANDIDATE** | Blue | Actionable recommendations worth acting on | "Deploy directed energy weapons for swarm countermeasures" |
| **KEY METRIC** | Purple | Important numbers, statistics, measurements | "40-60% parts commonality across drone platforms" |
| **VERIFIED FACT** | Green | Claims cross-checked across multiple providers | "WZ-8 operates at supersonic speeds above 100,000 ft" |

### How It Works

1. The system prompt instructs each AI to wrap important findings in tags
2. Tags don't disrupt the narrative — they're inline markers
3. The backend extracts tagged content using regex parsing
4. Extracted intelligence is categorized into decisions, risks, metrics, and facts
5. All tagged content is preserved in exports (PDF, DOCX, PPTX, etc.)

### Why This Matters

In traditional analysis, a human analyst manually highlights key findings in a brief. KorumOS automates this — every response is pre-marked with the most important intelligence, ready for executive consumption.

---

## 5. Truth Scoring & Accountability Pass

The Truth Scoring system is KorumOS's signature feature. It provides a quantitative measure of how much the council agrees on each claim.

### How Claims Are Scored

1. **Claim Extraction**: The engine parses each AI's response for:
   - Numerical metrics ("40% growth", "$2.3 billion budget")
   - Absolute statements ("This is the primary threat")
   - Named entities (organizations, systems, people)
   - Causal links ("X causes Y", "A leads to B")

2. **Cross-Provider Verification**: Each claim is checked against all other providers:
   - Does OpenAI's claim appear in Anthropic's response?
   - Does Google confirm or contradict Perplexity's finding?
   - How many providers independently reached the same conclusion?

3. **Scoring**:

| Status | Score Range | Meaning |
|--------|-----------|---------|
| **CONFIRMED** | 90-100 | 2+ providers independently agree |
| **SUPPORTED** | 70-89 | 1 provider corroborates |
| **UNVERIFIED** | 50-69 | No other provider confirms or denies |

4. **Composite Truth Score**: The average of all claim scores produces a single 0-100 truth meter for the entire response.

### What the Yellow Highlight Means

In the UI, the **yellow highlighted text** is the **Consensus Synthesis** — the final summary that reconciles what all five providers said. It includes:
- Points of agreement (what the council aligns on)
- Points of divergence (where providers disagreed)
- The composite truth score
- Confidence-weighted recommendations

### Why This Matters for Defense

In intelligence analysis, single-source reporting is unreliable. Multi-source corroboration is the gold standard. KorumOS applies this principle to AI — every claim is cross-checked, every disagreement is surfaced, and nothing is taken at face value.

---

## 6. Workflow Presets

KorumOS ships with 14 pre-configured workflow presets. Each preset assigns specific personas to each provider and sets the tone, goal, risk bias, and output structure.

### General Workflows

| Preset | OpenAI | Anthropic | Google | Perplexity | Mistral | Use Case |
|--------|--------|-----------|--------|------------|---------|----------|
| **War Room** | Strategist | Containment | Takeover | Scout | Analyst | Crisis response, threat containment |
| **Deep Research** | Analyst | Researcher | Historian | Scout | Validator | Academic analysis, evidence-based exploration |
| **Creative Council** | Writer | Innovator | Marketing | Social | Creative | Campaigns, content strategy, brand |
| **Code Audit** | Architect | Integrity | Hacker | Optimizer | Coding | Security review, code quality |
| **System Core** | Visionary | Architect | Critic | Researcher | Analyst | General-purpose analysis |

### Domain-Specific Workflows

| Preset | Focus | Key Personas |
|--------|-------|-------------|
| **Legal Review** | Regulatory compliance, contract risk | Jurist, Compliance, Negotiator |
| **Medical Council** | Clinical evidence, healthcare policy | Medical, Bioethicist, Researcher |
| **Finance Desk** | Investment analysis, risk management | CFO, Auditor, Hedge Fund, Tax |
| **Science Panel** | Research methodology, experimental design | Physicist, Biologist, Chemist, Professor |
| **Startup Launch** | Go-to-market, MVP strategy | BizStrat, Product, Marketing, CFO |
| **Tech Council** | Infrastructure, architecture decisions | AI Architect, Network, Telecom, Hacker |

### Defense & Intelligence Workflows

| Preset | Color | OpenAI | Anthropic | Google | Perplexity | Mistral |
|--------|-------|--------|-----------|--------|------------|---------|
| **Defense Council** | Army Green | Defense Ops | Cyber Ops | Intel Analyst | Scout | Hacker |
| **Cyber Command** | Threat Red | Cyber Ops | Counterintel | SIGINT | Intel Analyst | Hacker |
| **Intel Brief** | Amber Gold | Intel Analyst | Counterintel | Defense Ops | Scout | SIGINT |

### Workflow DNA

Each workflow carries a DNA profile that shapes the entire output:

```
WAR ROOM:
  Posture: Tactical Commander
  Goal: Immediate tactical action and crisis containment
  Tone: Aggressive, direct, zero-fluff
  Risk Bias: Conservative
  Time Horizon: 0-72 hours

RESEARCH:
  Posture: Objective Scientist
  Goal: Deep understanding and evidence-based exploration
  Tone: Neutral, academic, comprehensive
  Risk Bias: Balanced
  Time Horizon: Long-term strategic

FINANCE:
  Posture: CFO/Auditor
  Goal: Economic viability and downside protection
  Tone: Analytical, precise, detached
  Risk Bias: Downside-aware
  Time Horizon: Scenario-based
```

### Smart Routing

KorumOS automatically suggests the best workflow based on query keywords:
- "drone", "military", "DOD" → Defense Council
- "ransomware", "exploit", "CVE" → Cyber Command
- "OSINT", "intelligence", "surveillance" → Intel Brief
- "revenue", "investment", "ROI" → Finance Desk

---

## 7. Persona System

KorumOS has 60+ expert personas, each with a rich system-prompt description that shapes how the AI responds. Personas are assigned per-provider and can be swapped in real time by clicking the provider card.

### How Personas Work

When you assign a persona (e.g., "cyber_ops") to a provider (e.g., Anthropic), the system prompt becomes:

> "You are **a senior cyber operations specialist with expertise in offensive and defensive cybersecurity, incident response, NIST/CMMC frameworks, threat hunting, vulnerability assessment, red team/blue team operations, and DOD cyber warfare doctrine**. Provide expert, concise, high-impact analysis."

This is not a generic "You are a cybersecurity expert." It's a detailed, domain-specific instruction that shapes the AI's entire response.

### Defense & Intelligence Personas

| Key | Description |
|-----|-------------|
| **defense_ops** | UAS/drone warfare, counter-UAS, ISR, autonomous systems, military logistics, force projection, DOD operational planning |
| **cyber_ops** | Offensive/defensive cyber, incident response, NIST/CMMC, threat hunting, red/blue team, DOD cyber doctrine |
| **intel_analyst** | OSINT, SIGINT, HUMINT, geopolitical risk, threat intelligence, pattern analysis, national security |
| **defense_acq** | DOD contracting, FedRAMP, SBIR/STTR, ITAR/EAR, security clearances, government proposals |
| **sigint** | Signals intelligence, electronic warfare, spectrum analysis, encryption/decryption, RF systems |
| **counterintel** | Threat detection, insider threat programs, OPSEC, adversary tactics, security protocols |

### Other Notable Personas

| Category | Personas |
|----------|----------|
| **Strategy** | Strategist, Analyst, Architect, Visionary, Containment |
| **Finance** | CFO, Hedge Fund, Tax, Auditor, Economist |
| **Legal** | Jurist, Compliance, Negotiator |
| **Science** | Physicist, Biologist, Chemist, Professor |
| **Tech** | AI Architect, Network, Telecom, Hacker, Web Designer, Coding |
| **Business** | BizStrat, Product, Marketing, Sales, Social |
| **Medical** | Medical, Bioethicist |
| **Creative** | Writer, Innovator, Creative |
| **Analysis** | Critic, Researcher, Validator, Optimizer, Historian, Scout |

### Modular Design

- Any persona can be assigned to any provider
- Personas are swapped with one click during a live session
- New personas are added by adding one line to the role expansion map
- Workflow presets automatically assign optimal persona combinations

---

## 8. Red Team / Interrogation Mode

Red Team mode adds an adversarial analysis layer to every council query.

### How It Works

1. **Toggle On**: Click the Red Team button in the UI
2. **Normal Execution**: The five-provider council runs as usual
3. **Red Team Pass**: After the council finishes, an additional AI call runs with the "HACKER" persona
4. **Adversarial Prompt**: The Red Team AI receives the original query AND the council's output, with the instruction: *"RED TEAM THIS. Find the fatal flaw."*
5. **Output**: The Red Team response is displayed separately, highlighting vulnerabilities, blind spots, and attack vectors that the council missed

### Why This Matters

Every analysis has blind spots. Red Team mode ensures that the council's recommendations are stress-tested before you act on them. In defense contexts, this maps directly to adversarial threat simulation — the same principle used in DOD red team exercises.

---

## 9. Sentinel: Quick-Strike Intelligence

Sentinel is KorumOS's fast-response system for simple queries that don't need the full council.

### When to Use It
- Quick facts, definitions, weather, math
- Simple lookups that don't require five AI perspectives
- Time-sensitive questions where speed matters

### How It Works
- Uses Google Gemini 2.0 Flash for maximum speed
- Instruction: "Be extremely concise, direct, and factual. Do not lecture."
- Falls back to OpenAI GPT-4o if Gemini is unavailable
- For complex queries, Sentinel suggests: "Convene the Council"

### Sentinel vs. Council

| Feature | Sentinel | Council |
|---------|----------|---------|
| Speed | ~2 seconds | ~15-30 seconds |
| Providers | 1 (Gemini) | 5 (all) |
| Truth Scoring | No | Yes |
| Best for | Quick facts | Deep analysis |

---

## 10. Live Data Enrichment (SERP)

When Live Data mode is activated, KorumOS queries Google's Search API before running the council, injecting real-time information into every AI's context.

### What Gets Injected
- **Direct answers** from Google's knowledge panels
- **Product prices** and ratings (for commerce queries)
- **News articles** with dates (for current events)
- **Web results** with snippets and links

### How It Works

1. User toggles Live Data on
2. Query is sent to SerpAPI (Google Search)
3. Results are formatted and prepended to the query
4. All five AIs receive the real-time context
5. AIs are instructed: "Cite specific prices, dates, or sources when relevant"
6. Raw search data is included in the response for transparency

### Why This Matters

AI models have knowledge cutoffs. Perplexity helps with live search, but Live Data mode ensures **all five providers** have access to current information, not just Perplexity.

---

## 11. Prompt Enhancement Engine

KorumOS includes an AI-powered prompt engineering tool that transforms rough input into structured, strategic prompts.

### How It Works

1. User types a rough query (e.g., "tell me about drones in china")
2. Clicks "Enhance"
3. The engine rewrites it into a professional prompt:
   > "Assess Chinese drone capabilities including military UAS platforms, autonomous systems, swarm technology, and counter-UAS vulnerabilities. Analyze implications for Pacific theater operations and U.S. defense posture."
4. Enhanced prompt is placed in the input field, ready to submit

### What the Enhancer Does
- Fixes grammar and clarity
- Adds strategic structure
- Maintains the user's original intent
- Adds context placeholders for vague queries
- Uses Gemini Flash for speed, GPT-4o as fallback

---

## 12. File Upload & Vision APIs

KorumOS supports multi-modal analysis — upload images, PDFs, Word documents, or Excel files alongside your query, and all five AI providers will analyze them.

### Supported File Types

| Type | Formats | Processing |
|------|---------|------------|
| **Images** | JPG, PNG, GIF, WebP | Converted to base64, sent to vision APIs |
| **Documents** | PDF | Text extracted from up to 50 pages |
| **Documents** | DOCX | Paragraph text extracted |
| **Spreadsheets** | XLSX | Up to 5 sheets, 200 rows each |

### Vision API Integration

Each provider receives images in their native format:
- **OpenAI**: Uses GPT-4o vision capabilities
- **Anthropic**: Native image support in Claude
- **Google**: Gemini inline data format
- **Mistral**: Automatically switches to Pixtral Large (vision model)

### Use Cases
- Upload a satellite image and ask the Defense Council to assess terrain
- Upload a financial spreadsheet and have the Finance Desk analyze it
- Upload a network diagram and run a Code Audit for security vulnerabilities
- Upload a legal document and have Legal Review identify risks

---

## 13. Research Dock

The Research Dock is a persistent note-taking system for collecting and synthesizing intelligence snippets across multiple council sessions.

### How It Works

1. **Collect**: Save important snippets from council responses to the dock
2. **Accumulate**: Build a collection of findings across multiple queries
3. **Synthesize**: Click "Summarize" to have AI synthesize all snippets into an executive brief
4. **Export**: Use the export suite to generate reports from synthesized findings

### Features
- Persistent storage (up to 50 snippets, 500KB)
- AI-powered synthesis (identifies themes, metrics, actionable insights)
- Drag-and-drop snippet management
- Integrates with the export suite

---

## 14. Export Suite

KorumOS exports intelligence to 10 professional formats, ready for briefings, reports, and data analysis.

### Available Formats

| Format | File Type | Best For |
|--------|-----------|----------|
| **Board Brief** | PDF | Executive presentations, printed briefs |
| **Research Paper** | PDF | Academic-style analysis with citations |
| **Executive Memo** | DOCX | Editable Word document for distribution |
| **Research Paper** | DOCX | Editable research paper format |
| **Intelligence Workbook** | XLSX | 5-sheet Excel: Summary, Sections, Metrics, Actions, Risks |
| **Flat Data** | CSV | Data import into any analytics tool |
| **Raw Intelligence** | JSON | API integration, programmatic access |
| **Markdown Brief** | MD | Documentation, wiki pages |
| **Text Report** | TXT | Plain text for email or messaging |
| **PowerPoint Deck** | PPTX | Slide presentation with title + section slides |

### What Every Export Includes
- Title, timestamp, models used
- Composite truth score
- Section-by-section analysis
- Key metrics tables
- Action items
- Risk assessments
- Intelligence tags (cleaned for readability)

---

## 15. Security & Authentication

KorumOS implements enterprise-grade security controls designed to meet the baseline requirements for government and defense environments.

### Authentication
- **Session-based auth** with Flask-Login
- **Password requirements**: 12+ characters, uppercase, lowercase, number
- **Rate limiting**: 200/min global, 10/min login, 20/hr registration
- **Session lifetime**: 1 hour with secure cookie configuration
- **Role-based access**: Admin and User roles
- **First registered user** automatically becomes admin

### Security Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
```

### Audit Logging
Every security event is logged to the database:
- Login attempts (success and failure)
- Registration events
- Logout events
- Access denied events
- IP address, user agent, timestamp, endpoint

### HTTPS Enforcement
- All traffic redirected to HTTPS in production
- Secure cookies (HttpOnly, SameSite=Lax, Secure flag)

### Input Validation
- Server-side email validation
- Password strength enforcement
- Query sanitization before processing
- File upload validation (type, size, content)

### Infrastructure
- **Hosting**: Railway (US East Virginia)
- **Database**: PostgreSQL (encrypted at rest)
- **Domain**: Network Solutions with SSL/TLS
- **Environment**: Isolated containers, no shared tenancy

---

## 16. Defense & Intelligence Use Cases

### Threat Assessment
**Workflow**: Defense Council
**Query**: "Assess counter-UAS capabilities against Iranian drone swarms in the Gulf region"
**What you get**: Five-perspective analysis covering drone ops, cyber vulnerabilities, signal intelligence, open-source intel with citations, and adversarial exploitation vectors. Truth-scored with cross-provider verification.

### Cyber Incident Response
**Workflow**: Cyber Command
**Query**: "Analyze TTPs used in SolarWinds-style supply chain attacks and recommend detection strategies"
**What you get**: Cyber ops analysis, counterintelligence perspective, SIGINT assessment, live threat intel from Perplexity, and red team exploitation paths.

### Intelligence Briefing
**Workflow**: Intel Brief
**Query**: "Produce an OSINT assessment of North Korean missile program developments in the last 6 months"
**What you get**: Multi-source intelligence analysis with Perplexity providing live-sourced, cited information. Truth scoring flags unverified claims.

### Procurement Analysis
**Persona**: defense_acq
**Query**: "Evaluate SBIR Phase II opportunities for autonomous counter-UAS systems"
**What you get**: DOD acquisition framework analysis, FedRAMP considerations, ITAR compliance requirements, and competitive landscape.

### Red Team Exercise
**Mode**: Red Team ON + Defense Council
**Query**: "Assess our proposed drone defense perimeter for Camp Humphreys"
**What you get**: Full council analysis PLUS adversarial red team pass that identifies fatal flaws, blind spots, and attack vectors the council missed.

---

## 17. FedRAMP Readiness

KorumOS has implemented baseline security controls aligned with FedRAMP requirements. Current status and roadmap:

### Implemented
- [x] Authentication and access control (AC)
- [x] Audit logging and accountability (AU)
- [x] HTTPS/TLS encryption in transit (SC)
- [x] Input validation and sanitization (SI)
- [x] Security headers (SC)
- [x] Rate limiting (SC)
- [x] Session management (AC)
- [x] Role-based access control (AC)

### Roadmap
- [ ] Multi-factor authentication (MFA/TOTP — infrastructure ready, pyotp installed)
- [ ] Data encryption at rest (database-level)
- [ ] Continuous monitoring and alerting
- [ ] Incident response procedures
- [ ] System Security Plan (SSP) documentation
- [ ] Third-party security assessment (3PAO)
- [ ] Vulnerability scanning and remediation
- [ ] Configuration management
- [ ] Contingency planning

### Architecture Advantages for FedRAMP
- **No PII in AI queries**: KorumOS processes queries, not personal data
- **Auditable**: Every query, response, and auth event is logged
- **Provider-agnostic**: Can swap providers to meet compliance requirements
- **Local fallback**: Air-gapped LLM option for classified environments
- **Role-based access**: Admin/user separation with audit trail

---

## Appendix: Quick Reference

### Keyboard & UI Controls
- **Click provider card**: Cycle through available personas
- **Workflow tabs**: One-click preset activation (top nav bar)
- **Red Team toggle**: Enable adversarial analysis
- **Live Data toggle**: Enable real-time search enrichment
- **Enhance button**: AI-powered prompt improvement
- **Export dropdown**: Generate reports in any format
- **Research Dock**: Save and synthesize snippets

### Color Legend (UI)

| Element | Color | Meaning |
|---------|-------|---------|
| Yellow highlight | Amber | Consensus synthesis / council verdict |
| Red tag | Red | Risk vector — identified threat or vulnerability |
| Blue tag | Blue | Decision candidate — actionable recommendation |
| Purple tag | Purple | Key metric — important number or statistic |
| Green tag | Green | Verified fact — cross-checked across providers |
| Truth score % | Variable | Provider agreement level (higher = more consensus) |

### Workflow Tab Colors

| Tab | Color | Domain |
|-----|-------|--------|
| War Room | Red | Crisis response |
| Research | Teal | Academic analysis |
| Creative | Pink | Content & marketing |
| Audit | Orange | Code & security review |
| System | White | General purpose |
| Legal | Gold | Regulatory compliance |
| Medical | Red | Healthcare & clinical |
| Finance | Green | Investment & accounting |
| Science | Blue | Research & experimentation |
| Startup | Purple | Business strategy |
| Tech | Cyan | Infrastructure & architecture |
| Defense | Army Green | Military operations |
| Cyber | Threat Red | Cybersecurity operations |
| Intel | Amber Gold | Intelligence analysis |

---

*KorumOS is developed and maintained as a proprietary multi-source AI intelligence platform. For inquiries, contact via korum-os.com.*
