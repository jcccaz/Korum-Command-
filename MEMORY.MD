# KorumOS Memory

Last updated: 2026-03-18

## Purpose

This file is the short-term handoff memory for agents working in this repository.
Use it to avoid duplicate implementation, preserve recent feature state, and keep future work grounded in the latest verified repo context.

## Directives

1. Check the current worktree and recent commits before proposing or writing code.
2. Assume a feature may already be implemented if the user references prior agent work. Verify first.
3. Do one implementation job at a time unless the user explicitly approves bundling.
4. Before coding, state root cause, fix plan, affected files, regression risk, acceptance criteria, and concrete before/after behavior.
5. Do not mark work complete without verification. If verification is partial, say exactly what remains unverified.
6. If a feature touches multiple surfaces such as UI, persistence, and export, verify each surface explicitly.
7. Treat the Production Stabilization Directive below as the active operating policy until explicitly replaced.
8. Update this file when a completed change materially alters current project behavior, implementation status, or agent workflow.

## Production Stabilization Directive

### Objective

Korum OS must behave as a deterministic decision engine:

- Same input must produce consistent, structured, decision-grade output
- No new features
- No experimentation
- Prioritize consistency, control, and production-quality output

### Locked Pipeline

The execution flow is fixed and non-negotiable:

1. Input
2. Falcon Protocol
3. Multi-AI Role Execution
4. Audit and Validation
5. Normalization Layer
6. Render Layer
7. Export Layer

Rules:

- No step skipping
- No step merging
- No direct AI output to the render layer
- All outputs must pass through normalization

### Falcon Protocol

Falcon is the mandatory front layer for redaction and controlled exposure.

- Replace sensitive data with structured placeholders
- Preserve relationships and numerical integrity
- Prevent AI from processing raw proprietary data
- Do not break tables, charts, or other structured outputs

### Role-Based Orchestration

Operate on roles, not model names.

- Generator: structured analysis only, no formatting, no scope expansion
- Auditor: validate logic, structure, completeness, and enforce clear decisions
- Challenger or Critic: stress-test conclusions and identify weaknesses
- Synthesizer: consolidate validated outputs
- Finalizer: optional hidden role that unifies tone and structure without adding conclusions

Rules:

- Roles are fixed
- Models are interchangeable
- The system must not behave like a panel discussion

### Structured Output Contract

All AI output must conform to a structured schema:

- `executive_summary` with a maximum of 5 bullets
- `key_findings` entries containing `finding`, `impact`, `action`, and `confidence` with reason
- `tables` as structured objects only
- `charts` as structured objects only
- `recommendations` that are clear and decisive

Enforcement:

- If output is unstructured, reject and regenerate

### Normalization Layer

The normalization layer is mandatory and is the critical control point.

- Convert all markdown tables into structured tables
- Convert chart descriptions into chart objects
- Remove raw markdown and raw text artifacts before rendering
- The render layer must never receive raw AI output

### Render and Export Standards

All reports must follow the same layout:

1. Header
2. Executive Summary
3. Key Findings
4. Data Evidence
5. Recommendations

Requirements:

- Consistent formatting throughout the document
- No markdown leakage
- Charts must be embedded, not described
- Tables must be uniform

Excel export rules:

- Excel receives only structured tables
- No narrative or mixed content
- No markdown
- Exports must have correct population, consistent headers, and no empty or malformed output

### Decision Enforcement

Outputs must be decisive.

- No 50/50 answers
- No "it depends" without a final recommendation
- Every finding must include a decision, action, and confidence
- Avoid terms like "might", "could", and "possibly" unless explicitly justified

### Card Architecture

Cards represent process. Personalities represent perspective.

- Cards must map to pipeline stages
- Personalities must remain constrained per role
- Do not model the system as random opinion cards

### Mistral Verification Requirement

Observed state to verify in future implementation or review work:

- 5 AIs appear active
- 4 visible cards appear in the UI

Determine whether Mistral is:

1. A hidden Finalizer
2. Merged into the synthesis layer
3. A fallback model
4. Not executing due to a bug

If it is the Finalizer, enforce:

- No new conclusions
- Refinement and unification only

### Consistency Testing Requirement

Mandatory test:

- Run the same prompt 3 times

Expected pass behavior:

- Identical structure
- Consistent sections
- Stable tables and charts
- Consistent tone
- Pass threshold of at least 80 to 90 percent consistency

### Failure Conditions

Treat the following as production failures:

- Summary replaces full output
- Markdown tables leak into the report
- Charts are described instead of rendered
- Formatting is inconsistent
- Excel export is empty or misaligned
- AI roles are violated
- Output varies significantly across runs

### Success Criteria

Korum OS must:

- Run end-to-end without manual correction
- Produce consistent outputs across runs
- Generate clean, professional reports
- Deliver decisive, actionable insights
- Maintain data protection via Falcon Protocol

Core principle:

- Structure -> Consistency -> Trust -> Value

## Current Repo State

- The repository had a clean worktree when this file was created.
- Recent shipped work appears to already cover dock rendering, Mermaid chart handling, and export upgrades.
- Relevant recent commits:
  - `4f42b92` `feat: implement dock rendering, mermaid charts, and dynamic evaluation card states`
  - `47d6791` `Render docked Mermaid charts in exports`
  - `a5db3ba` `Strategic Export Upgrade: Premium Markdown, PPTX/XLSX Suite, and Branding Engine`

## Working Assumptions

- If a user says another agent may have already finished the code, inspect `git log`, `git status`, and the affected files before planning new implementation.
- Prefer review or verification work before writing code when the request sounds like a handoff, recovery, or duplicate-effort situation.
- Treat documentation changes separately from feature implementation unless the user explicitly asks for both together.

## Update Protocol

When you finish a meaningful task, append or revise only what changed:

- New directive that future agents must follow
- Current implementation status that would prevent duplicate work
- Verification notes if a cross-surface feature was only partially confirmed
- Known risks or open questions that should survive the current session
