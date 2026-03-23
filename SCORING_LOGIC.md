# KorumOS Scoring & Confidence Logic

KorumOS does not generate "vibes-based" scores. Every confidence percentage is the result of a deterministic **Truth Decision Matrix** and the **Confidence Governor's** scoring floors and caps.

## 1. The Confidence Bands

The system maps numerical scores to strict linguistic archetypes. This prevents the AI from using hedging language (e.g., "Moderate Confidence") when the data indicates a failure.

| Score Range | Band | Tone Directive |
| :--- | :--- | :--- |
| **80% - 100%** | **HIGH** | "Recommended." Requires primary source verification. |
| **60% - 79%** | **OPERATIONAL** | "Conditional." Requires 3+ verified facts & root cause analysis. |
| **40% - 59%** | **MARINAL** | "Caution." Low factual density or unresolved core claims. |
| **0% - 39%** | **LOW** | "Fail." Forced to "Very Low Confidence" labels; suppresses "Moderate" claims. |

## 2. Scoring Floors & Intelligence Boosts

To prevent "Technical Perfectionism" from suppressing valid intelligence, the Governor applies operational floors.

*   **The Operational Floor (62% Boost)**: 
    *   **Trigger**: If the mission has **3+ verified facts** AND **no critical missing data**.
    *   **Logic**: Prevents systems that are 80%+ complete from being trapped in the "Caution" range (50s) due to minor analytical gaps. 
    *   **Result**: Forces the score to at least **62** (Operational Band).
*   **The Baseline Floor (50%)**:
    *   **Trigger**: Applied when a minimum amount of verified data prevents a total system failure but isn't yet operational.

## 3. Caps & Constraints (Analytical Discipline)

KorumOS aggressively penalizes uncertainty.

*   **Root Cause Cap (55%)**: If core claims are unresolved AND no root cause is identified, the score is capped at **55**, regardless of other supporting evidence.
*   **Source Concentration Penalty**: If >60% of claims originate from a single AI provider, the score is penalized and capped to prevent "echo chamber" reasoning.
*   **Conflict Penalty**: Every `CONFLICTING` claim reduces the composite score by 10 points.

## 4. Diagnostic-First Re-Framing

In early-stage or high-uncertainty missions (**Diagnostic-First** posture), KorumOS shifts from "Solutioning" to "Investigation."

*   **Mitigation vs. Investigation**: Instead of proposing premature solutions, the system labels risk responses as **"Investigation Focus Areas."**
*   **Internal Key**: `mitigation` field in JSON is renamed to `investigation_focus` to maintain forensic integrity.

## 5. Source Strength Weighting

Not all evidence is created equal.

| Source Class | Strength Rank | Weight |
| :--- | :--- | :--- |
| **Primary** | 3 | Official Records, Archival Documents, Log Data. |
| **Secondary** | 2 | Press Reports, Summaries, Indirect Accounts. |
| **Tertiary** | 1 | Unverified Testimony, General Context, Speculation. |

---
*Produced by Korum-OS Decision Intelligence / Governor Core v2.2*
