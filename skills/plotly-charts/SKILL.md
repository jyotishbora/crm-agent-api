---
name: plotly-charts
description: Generate interactive Plotly.js chart configurations from CRM data. Use this skill when the user asks to visualize, chart, graph, or plot any CRM data (e.g. "show me a bar chart of funds by size", "pie chart of deals by stage", "plot fundraisers over time").
metadata:
  author: crm-agent
  version: "1.0"
---

# Plotly Charts Skill

## Overview
This skill enables you to generate interactive Plotly.js charts from CRM data. When a user asks for a visualization, you query the data using MCP tools, then return a JSON chart specification that the frontend renders using Plotly.js.

## Instructions

### When to use this skill
Activate this skill when the user asks to:
- Visualize, chart, graph, or plot data
- Show a bar chart, pie chart, line chart, scatter plot, etc.
- Compare entities visually (e.g. "compare fund sizes")
- Show distribution, breakdown, or trends

### Step-by-step workflow

1. **Understand what to chart**: Identify what data the user wants visualized and what chart type fits best.
2. **Query the data**: Use the appropriate MCP tools (get_table_schema first, then query_table_data or execute_query) to fetch the data needed for the chart. Remember to use WHERE IS NOT NULL for numeric columns being sorted.
3. **Build the Plotly JSON**: Construct a valid Plotly.js chart specification and return it wrapped in a special code block.

### How to return the chart

Return the Plotly chart as a JSON object inside a fenced code block with the language tag `plotly`. The frontend will detect this and render it.

Format:
```plotly
{
  "data": [...],
  "layout": {...}
}
```

### Chart type guidelines

**Bar chart** — use for comparing values across categories (e.g. fund sizes, deal amounts):
```plotly
{
  "data": [{
    "type": "bar",
    "x": ["Fund A", "Fund B", "Fund C"],
    "y": [1000000, 2000000, 3000000],
    "marker": {"color": "#3b82f6"}
  }],
  "layout": {
    "title": "Top Funds by Size",
    "xaxis": {"title": "Fund"},
    "yaxis": {"title": "Size ($)"},
    "template": "plotly_dark",
    "paper_bgcolor": "#0f172a",
    "plot_bgcolor": "#1e293b",
    "font": {"color": "#e2e8f0"}
  }
}
```

**Horizontal bar chart** — use when labels are long:
```plotly
{
  "data": [{
    "type": "bar",
    "x": [3000000, 2000000, 1000000],
    "y": ["Fund C", "Fund B", "Fund A"],
    "orientation": "h",
    "marker": {"color": "#3b82f6"}
  }],
  "layout": {
    "title": "Funds by Size",
    "xaxis": {"title": "Size ($)"},
    "template": "plotly_dark",
    "paper_bgcolor": "#0f172a",
    "plot_bgcolor": "#1e293b",
    "font": {"color": "#e2e8f0"},
    "margin": {"l": 200}
  }
}
```

**Pie/Donut chart** — use for proportions and breakdowns (e.g. deals by stage, funds by type):
```plotly
{
  "data": [{
    "type": "pie",
    "labels": ["Stage A", "Stage B", "Stage C"],
    "values": [10, 20, 30],
    "hole": 0.4,
    "marker": {"colors": ["#3b82f6", "#60a5fa", "#93c5fd", "#2563eb", "#1d4ed8"]}
  }],
  "layout": {
    "title": "Deals by Stage",
    "template": "plotly_dark",
    "paper_bgcolor": "#0f172a",
    "plot_bgcolor": "#1e293b",
    "font": {"color": "#e2e8f0"}
  }
}
```

**Line chart** — use for trends over time:
```plotly
{
  "data": [{
    "type": "scatter",
    "mode": "lines+markers",
    "x": ["2023-01", "2023-06", "2024-01"],
    "y": [100, 200, 350],
    "line": {"color": "#3b82f6"}
  }],
  "layout": {
    "title": "Trend Over Time",
    "xaxis": {"title": "Date"},
    "yaxis": {"title": "Value"},
    "template": "plotly_dark",
    "paper_bgcolor": "#0f172a",
    "plot_bgcolor": "#1e293b",
    "font": {"color": "#e2e8f0"}
  }
}
```

### Styling rules
- ALWAYS use dark theme to match the app: `"template": "plotly_dark"`, `"paper_bgcolor": "#0f172a"`, `"plot_bgcolor": "#1e293b"`, `"font": {"color": "#e2e8f0"}`
- Primary color: `#3b82f6` (blue). Use shades: `#60a5fa`, `#93c5fd`, `#2563eb`, `#1d4ed8` for multiple series.
- Keep chart titles concise and descriptive.
- Format large numbers with appropriate axis formatting (e.g. use tickprefix "$" for money).
- Limit bar charts to ~15 items max for readability. If more, show top N.

### Important
- Always include both the chart AND a brief text summary of the data (e.g. "Here's a bar chart of the top 10 funds by size. Hercules Capital leads at $6B.").
- The plotly JSON must be valid JSON (no trailing commas, no comments).
- Only use standard Plotly.js trace types: bar, scatter, pie, histogram, box, heatmap.
