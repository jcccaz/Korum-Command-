"""
Chart Abstraction Layer — Phase 1
Charts are defined by meaning, not by library. Libraries are interchangeable — standards are not.

Registry routes chart types to renderers. SVG builders produce print-ready charts
with semantic colors. Mermaid types pass through to the existing frontend pipeline.
"""

# ── Semantic Colors (muted / earthy — print-friendly) ────────────────────────
SEM_GREEN  = "#5B7F5E"   # positive / verified — sage
SEM_RED    = "#A45A52"   # negative / flagged / risk — dusty clay
SEM_AMBER  = "#B8893E"   # conditional / caution — warm ochre
SEM_BLUE   = "#4A6A7A"   # total / structure / neutral — steel slate
SEM_GREY   = "#7A7A72"   # baseline / label — warm grey
SEM_TEAL   = "#5A7A6E"   # secondary positive — muted sage-teal
SEM_PURPLE = "#7A6178"   # accent / differentiation — dusty mauve

PALETTE = [SEM_BLUE, SEM_GREEN, SEM_RED, SEM_AMBER, SEM_TEAL, SEM_PURPLE, SEM_GREY]

# ── Chart Registry ───────────────────────────────────────────────────────────
CHART_REGISTRY = {
    "waterfall":      {"renderer": "svg_native", "purpose": "variance"},
    "horizontal_bar": {"renderer": "svg_native", "purpose": "comparison"},
    "stacked_bar":    {"renderer": "svg_native", "purpose": "composition"},
    "pie":            {"renderer": "svg_native", "purpose": "composition"},
    "donut":          {"renderer": "svg_native", "purpose": "composition"},
    "bar":            {"renderer": "svg_native", "purpose": "comparison"},
    "line":           {"renderer": "svg_native", "purpose": "trend"},
    "flowchart":      {"renderer": "mermaid",    "purpose": "process"},
    "auto":           {"renderer": "svg_native", "purpose": "auto"},
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


def _paired_slices(labels, values, *extras):
    """Trim parallel chart arrays to the shortest usable length."""
    limit = min(len(labels or []), len(values or []))
    paired = [list((labels or [])[:limit]), list((values or [])[:limit])]
    for extra in extras:
        paired.append(list((extra or [])[:limit]))
    return paired


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


# ── Vertical Bar Chart ───────────────────────────────────────────────────────
def build_bar_svg(spec: dict) -> str:
    """
    spec: {labels: [...], values: [...], value_types?: ["positive","negative","neutral",...]}
    Vertical bars with semantic coloring. value_types defaults to palette cycling.
    """
    labels = spec.get("labels", []) or spec.get("categories", [])
    values = spec.get("values", [])
    value_types = spec.get("value_types", [])
    title = spec.get("title", "")

    labels, values, value_types = _paired_slices(labels, values, value_types)

    n = len(labels)
    if n == 0:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><text x="400" y="250" text-anchor="middle">No data</text></svg>'

    W, H = 800, 500
    margin_left, margin_right, margin_top, margin_bottom = 80, 40, 70, 80
    chart_w = W - margin_left - margin_right
    chart_h = H - margin_top - margin_bottom

    max_val = max(abs(v) for v in values) if values else 1
    min_val = min(min(values), 0) if values else 0
    val_range = max_val - min_val or 1

    bar_area = chart_w / n
    bar_w = max(min(bar_area * 0.6, 80), 20)
    gap = (bar_area - bar_w) / 2

    def y_pos(val):
        return margin_top + chart_h - ((val - min_val) / val_range) * chart_h

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        svg_rect(0, 0, W, H, "white"),
    ]

    if title:
        elements.append(svg_text(W / 2, 30, title, size=16, weight="bold", color="#1a1a1a"))

    # Grid lines
    tick_count = 4
    for i in range(tick_count + 1):
        val = min_val + (val_range * i / tick_count)
        gy = y_pos(val)
        elements.append(svg_line(margin_left, gy, W - margin_right, gy, stroke="#eee", width=1))
        elements.append(svg_text(margin_left - 10, gy + 4, _format_number(val), anchor="end", size=11, color=SEM_GREY))

    # Baseline at zero if negative values exist
    if min_val < 0:
        zero_y = y_pos(0)
        elements.append(svg_line(margin_left, zero_y, W - margin_right, zero_y, stroke="#ccc", width=1))

    # Bars
    for i in range(n):
        val = values[i]
        if i < len(value_types) and value_types[i]:
            color = semantic_color(value_types[i])
        else:
            color = PALETTE[i % len(PALETTE)]

        x = margin_left + i * bar_area + gap
        bar_top = y_pos(max(val, 0))
        bar_bottom = y_pos(min(val, 0))
        bar_h = max(bar_bottom - bar_top, 1)

        elements.append(svg_rect(x, bar_top, bar_w, bar_h, color, rx=2))

        # Value label above bar (or below for negatives)
        val_label = _format_number(val)
        if val < 0:
            elements.append(svg_text(x + bar_w / 2, bar_bottom + 16, val_label, size=11, color=color, weight="bold"))
        else:
            elements.append(svg_text(x + bar_w / 2, bar_top - 6, val_label, size=11, color=color, weight="bold"))

        # Category label
        elements.append(svg_text(x + bar_w / 2, H - margin_bottom + 20, labels[i], size=11, color=SEM_GREY))

    elements.append('</svg>')
    return '\n'.join(elements)


# ── Line Chart ──────────────────────────────────────────────────────────────
def build_line_svg(spec: dict) -> str:
    """
    spec: {labels: [...], series: [{label, values, color?}, ...]}
    Or simple: {labels: [...], values: [...]}
    Line chart with dots, grid lines, and optional multi-series.
    """
    labels = spec.get("labels", []) or spec.get("categories", [])
    title = spec.get("title", "")

    # Normalize to multi-series format
    raw_series = spec.get("series", [])
    if not raw_series and spec.get("values"):
        raw_series = [{"label": title or "Value", "values": spec["values"]}]

    n = len(labels)
    if n == 0 or not raw_series:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><text x="400" y="250" text-anchor="middle">No data</text></svg>'

    W, H = 800, 500
    margin_left, margin_right, margin_top, margin_bottom = 80, 40, 70, 80
    chart_w = W - margin_left - margin_right
    chart_h = H - margin_top - margin_bottom

    # Compute global min/max across all series
    all_vals = []
    for s in raw_series:
        all_vals.extend(v for v in s.get("values", []) if v is not None)
    if not all_vals:
        all_vals = [0]
    data_min = min(all_vals)
    data_max = max(all_vals)
    # Add 10% padding so lines don't sit on edges
    padding = (data_max - data_min) * 0.1 or 1
    min_val = data_min - padding
    max_val = data_max + padding
    val_range = max_val - min_val or 1

    def x_pos(idx):
        return margin_left + (idx / max(n - 1, 1)) * chart_w

    def y_pos(val):
        return margin_top + chart_h - ((val - min_val) / val_range) * chart_h

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        svg_rect(0, 0, W, H, "white"),
    ]

    if title:
        elements.append(svg_text(W / 2, 30, title, size=16, weight="bold", color="#1a1a1a"))

    # Grid lines
    tick_count = 4
    for i in range(tick_count + 1):
        val = min_val + (val_range * i / tick_count)
        gy = y_pos(val)
        elements.append(svg_line(margin_left, gy, W - margin_right, gy, stroke="#eee", width=1))
        elements.append(svg_text(margin_left - 10, gy + 4, _format_number(val), anchor="end", size=11, color=SEM_GREY))

    # X-axis labels
    for i in range(n):
        lx = x_pos(i)
        elements.append(svg_text(lx, H - margin_bottom + 20, labels[i], size=11, color=SEM_GREY))

    # Series lines + dots
    for si, s in enumerate(raw_series):
        color = s.get("color", PALETTE[si % len(PALETTE)])
        vals = s.get("values", [])
        points = []
        for i in range(min(n, len(vals))):
            if vals[i] is not None:
                points.append((i, vals[i]))

        # Polyline
        if len(points) >= 2:
            path_points = " ".join(f"{x_pos(i)},{y_pos(v)}" for i, v in points)
            elements.append(
                f'<polyline points="{path_points}" fill="none" '
                f'stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
            )

        # Dots + value labels
        for i, v in points:
            cx, cy = x_pos(i), y_pos(v)
            elements.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{color}" stroke="white" stroke-width="1.5"/>')
            # Label on first, last, and every ~3rd point to avoid clutter
            if i == points[0][0] or i == points[-1][0] or i % 3 == 0:
                elements.append(svg_text(cx, cy - 10, _format_number(v), size=10, color=color, weight="bold"))

    # Legend (if multiple series)
    if len(raw_series) > 1:
        lx = margin_left
        ly = margin_top - 20
        for si, s in enumerate(raw_series):
            color = s.get("color", PALETTE[si % len(PALETTE)])
            label = s.get("label", f"Series {si + 1}")
            elements.append(svg_line(lx, ly - 4, lx + 20, ly - 4, stroke=color, width=2.5))
            elements.append(f'<circle cx="{lx + 10}" cy="{ly - 4}" r="3" fill="{color}"/>')
            elements.append(svg_text(lx + 26, ly, label, anchor="start", size=11, color="#333"))
            lx += len(label) * 7 + 50

    elements.append('</svg>')
    return '\n'.join(elements)


# ── Pie / Donut Chart ───────────────────────────────────────────────────────
import math

def build_pie_svg(spec: dict) -> str:
    """
    spec: {labels: [...], values: [...], title?: str}
    Set spec["donut"] = True for donut variant (hollow center).
    """
    labels = spec.get("labels", []) or spec.get("categories", [])
    values = spec.get("values", [])
    title = spec.get("title", "")
    is_donut = spec.get("donut", False)

    labels, values = _paired_slices(labels, values)

    n = len(labels)
    if n == 0 or not values:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><text x="400" y="250" text-anchor="middle">No data</text></svg>'

    # Ensure all values are positive
    values = [max(abs(float(v)), 0) for v in values]
    total = sum(values) or 1

    W, H = 800, 500
    cx, cy = 340, 270  # center offset left to make room for legend
    outer_r = 180
    inner_r = 110 if is_donut else 0
    title_y = 35

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        svg_rect(0, 0, W, H, "white"),
    ]

    if title:
        elements.append(svg_text(W / 2, title_y, title, size=16, weight="bold", color="#1a1a1a"))

    # Build slices
    angle = -math.pi / 2  # start at 12 o'clock
    for i in range(n):
        frac = values[i] / total
        sweep = frac * 2 * math.pi
        color = PALETTE[i % len(PALETTE)]

        if n == 1:
            # Full circle — special case (arc path can't draw 360°)
            if is_donut:
                elements.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{outer_r}" fill="{color}"/>'
                    f'<circle cx="{cx}" cy="{cy}" r="{inner_r}" fill="white"/>'
                )
            else:
                elements.append(f'<circle cx="{cx}" cy="{cy}" r="{outer_r}" fill="{color}"/>')
        else:
            # Arc slice
            x1_o = cx + outer_r * math.cos(angle)
            y1_o = cy + outer_r * math.sin(angle)
            x2_o = cx + outer_r * math.cos(angle + sweep)
            y2_o = cy + outer_r * math.sin(angle + sweep)
            large_arc = 1 if sweep > math.pi else 0

            if is_donut:
                x1_i = cx + inner_r * math.cos(angle)
                y1_i = cy + inner_r * math.sin(angle)
                x2_i = cx + inner_r * math.cos(angle + sweep)
                y2_i = cy + inner_r * math.sin(angle + sweep)
                # Outer arc forward, line to inner, inner arc backward, close
                d = (
                    f"M {x1_o:.2f} {y1_o:.2f} "
                    f"A {outer_r} {outer_r} 0 {large_arc} 1 {x2_o:.2f} {y2_o:.2f} "
                    f"L {x2_i:.2f} {y2_i:.2f} "
                    f"A {inner_r} {inner_r} 0 {large_arc} 0 {x1_i:.2f} {y1_i:.2f} Z"
                )
            else:
                d = (
                    f"M {cx} {cy} "
                    f"L {x1_o:.2f} {y1_o:.2f} "
                    f"A {outer_r} {outer_r} 0 {large_arc} 1 {x2_o:.2f} {y2_o:.2f} Z"
                )
            elements.append(f'<path d="{d}" fill="{color}" stroke="white" stroke-width="2"/>')

        # Percentage label on slice (mid-angle, between inner and outer)
        pct = frac * 100
        if pct >= 4:  # only label slices >= 4%
            mid_angle = angle + sweep / 2
            label_r = (outer_r + inner_r) / 2 if is_donut else outer_r * 0.6
            lx = cx + label_r * math.cos(mid_angle)
            ly = cy + label_r * math.sin(mid_angle)
            elements.append(svg_text(lx, ly + 4, f"{pct:.0f}%", size=11, color="white", weight="bold"))

        angle += sweep

    # Donut center label (total)
    if is_donut:
        elements.append(svg_text(cx, cy - 5, _format_number(total), size=22, weight="bold", color="#1a1a1a"))
        elements.append(svg_text(cx, cy + 16, "TOTAL", size=10, color=SEM_GREY, weight="bold"))

    # Legend (right side)
    legend_x = 560
    legend_y = 100
    for i in range(n):
        color = PALETTE[i % len(PALETTE)]
        ly = legend_y + i * 28
        pct = (values[i] / total) * 100
        elements.append(svg_rect(legend_x, ly - 8, 14, 14, color, rx=2))
        label_text = labels[i] if len(labels[i]) <= 22 else labels[i][:20] + ".."
        elements.append(svg_text(legend_x + 22, ly + 4, label_text, anchor="start", size=12, color="#333"))
        elements.append(svg_text(legend_x + 22, ly + 18, f"{_format_number(values[i])} ({pct:.1f}%)",
                                 anchor="start", size=10, color=SEM_GREY))

    elements.append('</svg>')
    return '\n'.join(elements)


def build_donut_svg(spec: dict) -> str:
    """Donut chart — delegates to pie with donut=True."""
    spec = dict(spec)
    spec["donut"] = True
    return build_pie_svg(spec)


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
        "bar": build_bar_svg,
        "line": build_line_svg,
        "pie": build_pie_svg,
        "donut": build_donut_svg,
    }
    chart_type = spec.get("type", "")
    builder = builders.get(chart_type)
    if not builder:
        raise ValueError(f"No SVG builder for chart type: {chart_type}")
    return builder(spec)
