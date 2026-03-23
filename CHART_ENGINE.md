# KorumOS Chart Engine Specification

The **KorumOS Chart Engine** is a semantic visualization layer designed for strategic scanning. Unlike traditional charting libraries that prioritize aesthetics, KorumOS charts are defined by **meaning**, ensuring that every visual proves a specific insight.

## 1. Semantic Color Palette

KorumOS uses a muted, print-friendly palette that reserves high-intensity colors for "Signal" events.

| Color | Hex Code | Semantic Meaning |
| :--- | :--- | :--- |
| **Sage** | `#5B7F5E` | Positive movement / **VERIFIED** evidence. |
| **Dusty Clay** | `#A45A52` | Negative movement / **FLAGGED** risk. |
| **Ochre** | `#B8893E` | **CONDITIONAL** confidence / Caution. |
| **Steel Slate** | `#4A6A7A` | Neutral / Structural total / Baseline. |
| **Warm Grey** | `#7A7A72` | Secondary labels / Background context. |

## 2. Visualization Registry

The engine routes data to specific "Intent-Based" renderers.

| Chart Type | Purpose | Rendering Engine |
| :--- | :--- | :--- |
| **Waterfall** | **Variance Analysis**: Shows how start value became end value. | SVG Native |
| **Horizontal Bar** | **Comparison**: Colors bars by **Verified/Flagged** status. | SVG Native |
| **Stacked Bar** | **Composition**: Shows part-to-whole over categories. | SVG Native |
| **Pie / Donut** | **Market Share**: Proportional breakdowns (max 6 slices).| SVG Native |
| **Line Chart** | **Trend**: Strategic forecasting and historical trace. | SVG Native |
| **Flowchart** | **Process**: Step-by-step logic or hierarchy. | Mermaid.js |

## 3. The "Insight-First" Rule

The Chart Engine enforces strict labeling requirements via its JSON schema.

*   **Insight Titles**: Generic titles like "Sales Data" are rejected. Titles must state the conclusion (e.g., "Enterprise accounts for 60% of total revenue").
*   **Signal Status**: Horizontal bars must include a `status` field (`verified`, `conditional`, `flagged`) which automatically applies the corresponding semantic color.
*   **Automatic Scaling**: Values are formatted for readability (e.g., `1.5M`, `45K`) to ensure the dashboard remains uncluttered.

## 4. Native SVG Rendering

To ensure reports are identical across PDF, Word, and Web, KorumOS uses a pure Python **SVG Native** builder. 
*   **No External Dependencies**: Charts are rendered server-side as XML.
*   **Vector Fidelity**: Every chart is infinitely scalable and print-ready at 300+ DPI.
*   **Theme Integration**: Charts automatically inherit the active mission theme (BONE_FIELD, ARCHITECT, etc.) by adjusting their background and text contrast layers.

---
*Produced by Korum-OS Decision Intelligence / Visual Logic v2.2*
