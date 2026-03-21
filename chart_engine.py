"""
Chart Abstraction Layer — Phase 1
Charts are defined by meaning, not by library. Libraries are interchangeable — standards are not.

Registry routes chart types to renderers. SVG builders produce print-ready charts
with semantic colors. Mermaid types pass through to the existing frontend pipeline.
"""

# ── Semantic Colors ──────────────────────────────────────────────────────────
SEM_GREEN  = "#2E7D32"   # positive / verified
SEM_RED    = "#C62828"    # negative / flagged / risk
SEM_AMBER  = "#F57F17"   # conditional / caution
SEM_BLUE   = "#1565C0"   # total / structure / neutral
SEM_GREY   = "#616161"   # baseline / label
SEM_TEAL   = "#00695C"   # secondary positive
SEM_PURPLE = "#6A1B9A"   # accent / differentiation

PALETTE = [SEM_BLUE, SEM_GREEN, SEM_RED, SEM_AMBER, SEM_TEAL, SEM_PURPLE, SEM_GREY]

# ── Chart Registry ───────────────────────────────────────────────────────────
CHART_REGISTRY = {
    "waterfall":      {"renderer": "svg_native", "purpose": "variance"},
    "horizontal_bar": {"renderer": "svg_native", "purpose": "comparison"},
    "stacked_bar":    {"renderer": "svg_native", "purpose": "composition"},
    "pie":            {"renderer": "mermaid",     "purpose": "composition"},
    "bar":            {"renderer": "mermaid",     "purpose": "comparison"},
    "line":           {"renderer": "mermaid",     "purpose": "trend"},
    "flowchart":      {"renderer": "mermaid",     "purpose": "process"},
    "auto":           {"renderer": "mermaid",     "purpose": "auto"},
}

def get_renderer(chart_type: str) -> str:
    entry = CHART_REGISTRY.get(chart_type, CHART_REGISTRY["auto"])
    return entry["renderer"]


# ── SVG Primitives ───────────────────────────────────────────────────────────
def _esc(text):
    """Escape text for SVG XML."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def svg_rect(x, y, w, h, fill, rx=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" rx="{rx}"/>'

def svg_text(x, y, text, anchor="middle", size=13, color="#333", weight="normal"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-size="{size}" fill="{color}" font-weight="{weight}" '
            f'font-family="Segoe UI, Arial, sans-serif">{_esc(text)}</text>')

def svg_line(x1, y1, x2, y2, stroke="#999", width=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"{d}/>'

def semantic_color(value_type: str) -> str:
    mapping = {
        "positive": SEM_GREEN, "negative": SEM_RED, "total": SEM_BLUE,
        "verified": SEM_GREEN, "conditional": SEM_AMBER, "flagged": SEM_RED,
        "neutral": SEM_GREY, "baseline": SEM_GREY,
    }
    return mapping.get(value_type, SEM_GREY)


# ── Waterfall Chart ──────────────────────────────────────────────────────────
def build_waterfall_svg(spec: dict) -> str:
    """
    spec: {labels: [...], values: [...], value_types: ["total","positive","negative",...]}
    Waterfall with connector lines showing build-up.
    """
    labels = spec.get("labels", [])
    values = spec.get("values", [])
    value_types = spec.get("value_types", [])
    title = spec.get("title", "")

    n = len(labels)
    if n == 0:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><text x="400" y="250" text-anchor="middle">No data</text></svg>'

    W, H = 800, 500
    margin_left, margin_right, margin_top, margin_bottom = 80, 40, 70, 80
    chart_w = W - margin_left - margin_right
    chart_h = H - margin_top - margin_bottom

    # Compute running totals for bar positions
    running = []
    cumulative = 0
    for i, v in enumerate(values):
        vt = value_types[i] if i < len(value_types) else "positive"
        if vt == "total":
            running.append((0, v))
            cumulative = v
        elif vt == "negative":
            running.append((cumulative - abs(v), abs(v)))
            cumulative -= abs(v)
        else:  # positive
            running.append((cumulative, abs(v)))
            cumulative += abs(v)

    # Scale
    all_tops = [base + height for base, height in running]
    all_bottoms = [base for base, _ in running]
    max_val = max(all_tops) if all_tops else 1
    min_val = min(min(all_bottoms), 0)
    val_range = max_val - min_val or 1

    bar_area = chart_w / n
    bar_w = max(bar_area * 0.55, 30)
    gap = (bar_area - bar_w) / 2

    def y_pos(val):
        return margin_top + chart_h - ((val - min_val) / val_range) * chart_h

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        svg_rect(0, 0, W, H, "white"),
    ]

    # Title
    if title:
        elements.append(svg_text(W / 2, 30, title, size=16, weight="bold", color="#1a1a1a"))

    # Y-axis baseline
    zero_y = y_pos(0)
    elements.append(svg_line(margin_left, zero_y, W - margin_right, zero_y, stroke="#ccc", width=1))

    # Grid lines (4 ticks)
    tick_count = 4
    for i in range(tick_count + 1):
        val = min_val + (val_range * i / tick_count)
        gy = y_pos(val)
        elements.append(svg_line(margin_left, gy, W - margin_right, gy, stroke="#eee", width=1))
        label = _format_number(val)
        elements.append(svg_text(margin_left - 10, gy + 4, label, anchor="end", size=11, color=SEM_GREY))

    # Bars + connectors
    for i in range(n):
        base, height = running[i]
        vt = value_types[i] if i < len(value_types) else "positive"
        color = semantic_color(vt)

        x = margin_left + i * bar_area + gap
        bar_top = y_pos(base + height)
        bar_bottom = y_pos(base)
        bar_h = bar_bottom - bar_top

        elements.append(svg_rect(x, bar_top, bar_w, max(bar_h, 1), color, rx=2))

        # Value label above/below bar
        val_label = _format_number(values[i])
        if vt == "negative":
            elements.append(svg_text(x + bar_w / 2, bar_bottom + 16, f"-{val_label}", size=11, color=color, weight="bold"))
        else:
            elements.append(svg_text(x + bar_w / 2, bar_top - 6, val_label, size=11, color=color, weight="bold"))

        # Category label
        elements.append(svg_text(x + bar_w / 2, H - margin_bottom + 20, labels[i], size=11, color=SEM_GREY))

        # Connector line to next bar
        if i < n - 1:
            next_vt = value_types[i + 1] if i + 1 < len(value_types) else "positive"
            connector_y = y_pos(base + height) if vt != "negative" else y_pos(base)
            if next_vt == "total":
                pass  # No connector to totals
            else:
                next_x = margin_left + (i + 1) * bar_area + gap
                elements.append(svg_line(x + bar_w, connector_y, next_x, connector_y, stroke="#999", width=1, dash="4,3"))

    elements.append('</svg>')
    return '\n'.join(elements)


# ── Horizontal Bar Chart ─────────────────────────────────────────────────────
def build_horizontal_bar_svg(spec: dict) -> str:
    """
    spec: {categories: [...], values: [...], status: ["verified","conditional","flagged",...]}
    Horizontal bars colored by status.
    """
    categories = spec.get("categories", [])
    values = spec.get("values", [])
    statuses = spec.get("status", [])
    title = spec.get("title", "")

    n = len(categories)
    if n == 0:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><text x="400" y="200" text-anchor="middle">No data</text></svg>'

    W = 800
    bar_height = 36
    bar_gap = 14
    margin_left, margin_right, margin_top, margin_bottom = 180, 80, 70, 30
    chart_h = n * (bar_height + bar_gap)
    H = max(400, margin_top + chart_h + margin_bottom)
    chart_w = W - margin_left - margin_right

    max_val = max(abs(v) for v in values) if values else 1

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        svg_rect(0, 0, W, H, "white"),
    ]

    if title:
        elements.append(svg_text(W / 2, 30, title, size=16, weight="bold", color="#1a1a1a"))

    for i in range(n):
        status = statuses[i] if i < len(statuses) else "neutral"
        color = semantic_color(status)
        val = values[i]
        bar_w = (abs(val) / max_val) * chart_w if max_val else 0

        y = margin_top + i * (bar_height + bar_gap)

        # Category label (left)
        elements.append(svg_text(margin_left - 12, y + bar_height / 2 + 5, categories[i],
                                 anchor="end", size=13, color="#333"))

        # Bar
        elements.append(svg_rect(margin_left, y, bar_w, bar_height, color, rx=3))

        # Value label (right of bar)
        val_label = _format_number(val)
        elements.append(svg_text(margin_left + bar_w + 10, y + bar_height / 2 + 5, val_label,
                                 anchor="start", size=12, color=color, weight="bold"))

    # Legend
    legend_items = []
    seen = set()
    for s in statuses:
        if s not in seen:
            seen.add(s)
            legend_items.append((s, semantic_color(s)))
    if legend_items:
        lx = margin_left
        ly = H - 15
        for label, color in legend_items:
            elements.append(svg_rect(lx, ly - 10, 12, 12, color, rx=2))
            elements.append(svg_text(lx + 18, ly, label.capitalize(), anchor="start", size=11, color=SEM_GREY))
            lx += len(label) * 8 + 40

    elements.append('</svg>')
    return '\n'.join(elements)


# ── Stacked Bar Chart ────────────────────────────────────────────────────────
def build_stacked_bar_svg(spec: dict) -> str:
    """
    spec: {categories: [...], series: [{label, values, color?}, ...]}
    Vertical stacked bars with legend.
    """
    categories = spec.get("categories", [])
    series = spec.get("series", [])
    title = spec.get("title", "")

    n = len(categories)
    if n == 0 or not series:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><text x="400" y="250" text-anchor="middle">No data</text></svg>'

    W, H = 800, 500
    margin_left, margin_right, margin_top, margin_bottom = 80, 40, 80, 80
    chart_w = W - margin_left - margin_right
    chart_h = H - margin_top - margin_bottom

    # Compute max stack height
    max_stack = 0
    for ci in range(n):
        stack = sum(s["values"][ci] for s in series if ci < len(s.get("values", [])))
        max_stack = max(max_stack, stack)
    max_stack = max_stack or 1

    bar_area = chart_w / n
    bar_w = max(bar_area * 0.6, 40)
    gap = (bar_area - bar_w) / 2

    def y_pos(val):
        return margin_top + chart_h - (val / max_stack) * chart_h

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        svg_rect(0, 0, W, H, "white"),
    ]

    if title:
        elements.append(svg_text(W / 2, 30, title, size=16, weight="bold", color="#1a1a1a"))

    # Grid lines
    tick_count = 4
    for i in range(tick_count + 1):
        val = max_stack * i / tick_count
        gy = y_pos(val)
        elements.append(svg_line(margin_left, gy, W - margin_right, gy, stroke="#eee", width=1))
        elements.append(svg_text(margin_left - 10, gy + 4, _format_number(val), anchor="end", size=11, color=SEM_GREY))

    # Bars
    for ci in range(n):
        x = margin_left + ci * bar_area + gap
        cumulative = 0
        for si, s in enumerate(series):
            val = s["values"][ci] if ci < len(s.get("values", [])) else 0
            color = s.get("color", PALETTE[si % len(PALETTE)])
            bar_top = y_pos(cumulative + val)
            bar_bottom = y_pos(cumulative)
            bar_h = bar_bottom - bar_top

            elements.append(svg_rect(x, bar_top, bar_w, max(bar_h, 1), color, rx=2))

            # Segment label (if tall enough)
            if bar_h > 18:
                elements.append(svg_text(x + bar_w / 2, bar_top + bar_h / 2 + 4,
                                         _format_number(val), size=10, color="white", weight="bold"))

            cumulative += val

        # Category label
        elements.append(svg_text(x + bar_w / 2, H - margin_bottom + 20, categories[ci],
                                 size=12, color=SEM_GREY))

    # Legend (top)
    lx = margin_left
    ly = margin_top - 20
    for si, s in enumerate(series):
        color = s.get("color", PALETTE[si % len(PALETTE)])
        elements.append(svg_rect(lx, ly - 10, 12, 12, color, rx=2))
        elements.append(svg_text(lx + 18, ly, s.get("label", f"Series {si+1}"),
                                 anchor="start", size=11, color="#333"))
        lx += len(s.get("label", f"Series {si+1}")) * 7 + 35

    elements.append('</svg>')
    return '\n'.join(elements)


# ── Utilities ────────────────────────────────────────────────────────────────
def _format_number(val):
    """Format numbers for chart labels: 1500000 → 1.5M, 45000 → 45K, 123 → 123."""
    val = float(val)
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val/1_000_000:.1f}M"
    elif abs_val >= 10_000:
        return f"{sign}{abs_val/1_000:.0f}K"
    elif abs_val >= 1_000:
        return f"{sign}{abs_val/1_000:.1f}K"
    elif abs_val == int(abs_val):
        return f"{sign}{int(abs_val)}"
    else:
        return f"{sign}{abs_val:.1f}"


# ── Router ───────────────────────────────────────────────────────────────────
def generate_svg_chart(spec: dict) -> str:
    """Route a chart spec to its SVG builder. Only handles svg_native types."""
    builders = {
        "waterfall": build_waterfall_svg,
        "horizontal_bar": build_horizontal_bar_svg,
        "stacked_bar": build_stacked_bar_svg,
    }
    chart_type = spec.get("type", "")
    builder = builders.get(chart_type)
    if not builder:
        raise ValueError(f"No SVG builder for chart type: {chart_type}")
    return builder(spec)
