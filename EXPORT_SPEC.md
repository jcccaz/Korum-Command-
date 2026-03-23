# KorumOS Report Exporter Specification

The **KorumOS Exporter** is the final stage of the intelligence pipeline. It converts raw, redacted AI council discussions and structured JSON decision packets into executive-grade dossiers in PDF and Microsoft Word (DOCX) formats.

## 1. Visual Identity & Themes

The exporter supports multiple high-impact visual themes that reserve "Signal Red" for critical alerts and use high-contrast palettes for legibility.

| Theme | Tone | Core Palette | Best For |
| :--- | :--- | :--- | :--- |
| **BONE_FIELD** | Desktop Default | HSL(210, 20%, 98%) | Default scanning. |
| **ARCHITECT** | Corporate High-Trust | HSL(215, 25%, 27%) | Executive board reviews. |
| **NEON_DESERT** | High-Impact Dark | HSL(24, 95%, 58%) | Rapid situational awareness. |
| **CARBON_STEEL** | Technical Rigor | HSL(220, 15%, 15%) | Forensic and IT audits. |
| **STEEL_RUBY** | Strategic Alert | HSL(350, 85%, 45%) | High-stakes decision briefings. |

## 2. Intelligence Hygiene (The "Cleanse")

Before any text is written to the report, it passes through a normalization layer to ensure professional quality.

*   **Markdown Stripping**: Removes `**`, `##`, and code fence markers (```).
*   **Tag Suppression**: Strips internal council tags like `[VERIFIED]`, `[CRITICAL]`, and `[ROOT CAUSE]`.
*   **Provider Anonymization**: 
    *   Replaces "OpenAI/GPT-4", "Google/Gemini", and "Anthropic/Claude" with authoritative source attributions.
    *   **Attribution Logic**: If the context involves numbers/metrics, it is labeled **"Input Data"**. If it involves synthesis, it is labeled **"Korum OS (Analytical Inference)"**.

## 3. Evidence Artifacts & Layout

KorumOS reports prioritize structured data over raw prose.

### 3.1 The Artifact Dock Integration
*   **Structured Tables**: Supports `[STRUCTURED_TABLE]` JSON injection for deterministic data rendering.
*   **Chart Rendering**: Automatically embeds SVG/Chart artifacts into the report if the `includeInReport` flag is active.
*   **Phase Pull-Quotes**: Attributions use anonymized phase titles (**ANALYST**, **ARCHITECT**, **CRITIC**, **INTEGRATOR**, **COMPOSER**) to maintain council decorum.

### 3.2 Evidence Blocks
*   **Source Verification**: Renders a dedicated block for every primary record (source_ref) used in the decision.
*   **Interrogation Chains**: If a user runs an AI Interrogation, the chain of "Question -> Response -> Rebuttal" is appended as a forensic appendix.

## 4. Technical Export Engines

*   **PDF (ReportLab)**: Generates highly formatted, print-ready dossiers with precise layout control and "Produced by KorumOS" cryptographic stamps.
*   **Word (Python-Docx)**: Produces editable versions of the report with native Word tables and styles, intended for integration into internal stakeholder documents.

---
*Produced by Korum-OS Decision Intelligence / Export Logic v2.2*
