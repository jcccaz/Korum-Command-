# KorumOS Confidence Governor Specification

The **Confidence Governor** is the primary arbiter of truth within the KorumOS Council Engine. It ensures that no decision is presented with unearned certainty by enforcing a rigorous, dual-layered confidence model that balances factual evidence against decision risk.

## 1. The Dual-Confidence Model

KorumOS does not use a single "Confidence" score. Instead, it computes two independent vectors that must align before a "HIGH" confidence label is granted.

| Vector | Description | Primary Drivers |
| :--- | :--- | :--- |
| **Fact Confidence** | How certain we are about the **Ground Truth** (the 'What'). | Verified claims, quantified support, source strength. |
| **Decision Confidence** | How certain we are about the **Action** (the 'So What'). | Red Team challenges, unknown count, unresolved assumptions. |

### 1.1 Score Mapping (Legacy Score)
The internal legacy score (0-100) is derived from these vectors:
`Score = (Fact_Confidence * 0.4 + Decision_Confidence * 0.6) * 100`

## 2. Source-Strength Ranking (The Evidence Tier)

Not all sources are created equal. The Governor ranks evidence using the following hierarchy:

| Tier | Rank | Description |
| :--- | :--- | :--- |
| **Primary** | 3 | Official registries, civil records, church baptism/marriage/death, telemetry, datasets, filings, court transcripts. |
| **Secondary**| 2 | Newspapers, academic journals, historical biographies, museum records, finance models. |
| **Tertiary** | 1 | Blogs, forums, Reddit, Wikipedia, "Find A Grave," social media posts. |

### 2.1 The "Sparsity Penalizer"
*   If a claim is marked **VERIFIED** but depends on a **Rank 1 (Tertiary)** source, it is automatically downgraded to **LIKELY**.
*   If a claim is marked **VERIFIED** but has a **Rank 0 (Absent)** source, it is downgraded to **UNKNOWN**.

## 3. Mandatory Caps & Floors (The Governor Rules)

The Governor enforces hard caps to prevent AI "hallucination creep."

### 3.1 Hard Caps (The Ceilings)
*   **Zero-Fact Cap**: If `verified_count == 0`, Fact Confidence is hard-capped at **0.20**.
*   **Unknowns Cap**: If `unknowns > verified_facts`, Decision Confidence is hard-capped at **0.60**.
*   **Conflicting Claims Cap**: 
    *   1 Unresolved Conflict: Score is hard-capped at **60**.
    *   2+ Unresolved Conflicts: Score is hard-capped at **45**.
*   **Source Concentration Cap**: If >60% of claims depend on a single source, Fact Confidence is capped at **0.55** and Decision Confidence is capped at **0.60**.

### 3.2 The "Assumption Firewall"
If the number of unverified **Assumptions** exceeds the number of **Verified Facts**, the `GO` call is automatically downgraded to **CONDITIONAL GO**.

### 3.3 Score Floors
If the system has quantified support and at least 2 verified facts with zero conflicts, the score is floored at **50** to prevent "failure-range" scoring for legitimate but cautious findings.

## 4. The Validated Intelligence Estimate (VIE)
---
The Governor delivers its results through a structured **Validated Intelligence Estimate (VIE)**. This is not a simple summary; it is a high-fidelity intelligence brief that anchors the decision.

## 5. The "Diagnostic-First" Gate

If the engine detects the following conditions, it automatically injects a **"Diagnostic-First"** recommendation and blocks irreversible action:
*   Fewer than 2 verified facts AND fewer than 2 evidence points.
*   Critical baseline data is missing AND unknown count > verified count.
*   Critical baseline data is missing AND no quantified support is available.

---
*Produced by Korum-OS Decision Intelligence / Internal Logic Spec v2.2*
