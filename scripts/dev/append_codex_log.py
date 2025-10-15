#!/usr/bin/env python3
"""Append a Codex session entry to docs/codex_log.md."""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from typing import Sequence


def run(cmd: Sequence[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def main(args: Sequence[str]) -> None:
    if len(args) < 3:
        raise SystemExit("Usage: append_codex_log.py <agent> <prompt> <result> [next_steps]")

    agent, prompt, result, *rest = args
    next_steps = rest[0] if rest else ""

    repo_root = run(["git", "rev-parse", "--show-toplevel"])
    log_path = os.path.join(repo_root, "docs", "codex_log.md")
    if not os.path.exists(log_path):
        raise SystemExit(f"Fant ikke codex_log.md på forventet sted: {log_path}")

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit_hash = run(["git", "rev-parse", "--short", "HEAD"])
    today = datetime.date.today().isoformat()

    lines = [
        "",
        f"### {today} — {agent}",
        f"**Agent:** {agent}",
        f"**Prompt:** {prompt}",
        f"**Resultat:** {result} (branch `{branch}`)",
        f"**Commit:** `{commit_hash}`",
        f"**Neste steg:** {next_steps}" if next_steps else "**Neste steg:**",
    ]

    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    print(f"Appended log entry to {log_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
