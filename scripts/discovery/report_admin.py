#!/usr/bin/env python3
"""Render an HTML admin snapshot of source diagnostics and discovery status."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

from .report import build_report

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "docs" / "status" / "sources.html"


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _render_table(rows, title, empty_text):
    if not rows:
        return f"<section><h2>{_html_escape(title)}</h2><p>{_html_escape(empty_text)}</p></section>"
    headers = rows[0].keys()
    head = "".join(f"<th>{_html_escape(str(h).title())}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_html_escape(str(row.get(col, '')))}</td>" for col in headers)
        body_rows.append(f"<tr>{cells}</tr>")
    body = "\n".join(body_rows)
    return f"""
    <section>
      <h2>{_html_escape(title)}</h2>
      <table>
        <thead><tr>{head}</tr></thead>
        <tbody>
          {body}
        </tbody>
      </table>
    </section>
    """


def build_html(report):
    generated = datetime.now().isoformat(timespec="seconds")
    events = report.get("events", {})
    sources = report.get("sources", {})
    failing = sources.get("failing", [])
    inactive = sources.get("inactive", [])
    candidates = report.get("candidates", {})

    snapshot = [
        {"Metric": "Last updated", "Value": events.get("last_updated") or "n/a"},
        {"Metric": "Total events", "Value": events.get("total_events", 0)},
        {"Metric": "Source count", "Value": events.get("source_count", 0)},
        {"Metric": "Generated at", "Value": generated},
    ]

    failing_rows = [
        {"Name": entry.get("name", "Unknown"), "Status": entry.get("status", ""), "Events": entry.get("events", 0)}
        for entry in failing
    ]

    inactive_rows = [
        {"Name": entry.get("name", "Unknown"), "Status": entry.get("status", "")}
        for entry in inactive
    ]

    candidate_rows = [
        {
            "Name": entry.get("name"),
            "Source": entry.get("source"),
            "Status": entry.get("status"),
            "Confidence": entry.get("confidence", ""),
        }
        for entry in (candidates.get("entries") or [])
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Spontis Source Diagnostics</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    :root {{
      font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
      background: #0b1220;
      color: #f5f9fd;
      line-height: 1.6;
    }}
    body {{
      margin: 0;
      padding: 2.5rem clamp(1rem, 4vw, 3rem);
      background: linear-gradient(160deg, rgba(11,18,32,1) 0%, rgba(25,44,67,1) 60%, rgba(12,24,40,1) 100%);
    }}
    h1 {{
      margin-top: 0;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    section {{
      margin-bottom: 2rem;
      background: rgba(15, 28, 45, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 1.5rem;
      box-shadow: 0 24px 40px rgba(0, 0, 0, 0.35);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.75rem 0.9rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }}
    th {{
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      color: rgba(255,255,255,0.72);
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      padding: 0.25rem 0.6rem;
      margin-right: 0.4rem;
      border-radius: 999px;
      background: rgba(244,124,103,0.22);
      color: #ffd9d0;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    ul {{
      list-style: none;
      padding: 0;
      margin: 0.75rem 0 0;
      display: grid;
      gap: 0.4rem;
    }}
    li {{
      background: rgba(255,255,255,0.04);
      padding: 0.6rem 0.75rem;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.06);
    }}
  </style>
</head>
<body>
  <h1>Source Diagnostics</h1>
  {_render_table(snapshot, "Snapshot", "Ingen data")}
  {_render_table(failing_rows, "Failing Sources", "Alle kilder svarer som forventet.")}
  {_render_table(inactive_rows, "Inactive / Zero Event Sources", "Alle aktive kilder rapporterer events.")}
  {_render_table(candidate_rows, "Discovery Candidates", "Ingen kandidater registrert.")}
</body>
</html>
"""


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_PATH.write_text(build_html(report), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
