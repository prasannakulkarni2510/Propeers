"""Daily digest — 'one place to see today's actions' (design §9, Week 3).

Reads the SQLite store (and new_jobs.csv if present) and prints a plain-text
summary: interview invites, warm leads, follow-ups due, unmatched replies to
associate, and new job alerts. Pure read: it never sends or mutates anything.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .config import Config
from .store import PacosStore


def _fmt_lead(row: dict) -> str:
    name = row.get("full_name", "?")
    company = row.get("company_name", "?")
    role = row.get("job_title", "")
    return f"{name} — {company}" + (f" ({role})" if role else "")


def build_digest(cfg: Config, store: PacosStore, on: date | None = None) -> str:
    on = on or date.today()
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"PACOS daily digest — {on.isoformat()}")
    lines.append("=" * 60)

    counts = store.status_counts()
    if counts:
        lines.append("Pipeline: " + "  ".join(f"{k}:{v}" for k, v in sorted(counts.items())))
    else:
        lines.append("Pipeline: (empty — run `pacos generate` first)")
    lines.append("")

    interviews = store.by_status("interview")
    lines.append(f"[!] Interview invites ({len(interviews)}):")
    for r in interviews:
        lines.append(f"    • {_fmt_lead(r)}  last_reply={r.get('last_reply_date','')}")
    if not interviews:
        lines.append("    (none)")
    lines.append("")

    interested = store.by_status("interested")
    lines.append(f"[*] Interested / warm ({len(interested)}):")
    for r in interested:
        lines.append(f"    • {_fmt_lead(r)}")
    if not interested:
        lines.append("    (none)")
    lines.append("")

    due = store.due_followups(on)
    lines.append(f"[>] Follow-ups due on/before {on.isoformat()} ({len(due)}):")
    for r in due:
        lines.append(f"    • {_fmt_lead(r)}  sent={r.get('outreach_sent_date','')}"
                     f"  due={r.get('follow_up_due','')}")
    if not due:
        lines.append("    (none)")
    lines.append("")

    unmatched = store.list_unmatched()
    lines.append(f"[?] Unmatched replies to associate ({len(unmatched)}):")
    for r in unmatched[:10]:
        lines.append(f"    • {r.get('sender','')}  \"{r.get('subject','')[:40]}\""
                     f"  ({r.get('intent','')})")
    if not unmatched:
        lines.append("    (none)")
    lines.append("")

    njp: Path = cfg.new_jobs_csv
    if njp.exists():
        try:
            nj = pd.read_csv(njp, dtype=str, keep_default_na=False).fillna("")
        except Exception:
            nj = pd.DataFrame()
        lines.append(f"[+] New job alerts in {njp.name} ({len(nj)}):")
        for _, r in nj.tail(10).iterrows():
            lines.append(f"    • {r.get('title', r.get('role','?'))} @ {r.get('company','?')}"
                         f"  ({r.get('source','')})")
        if len(nj) == 0:
            lines.append("    (none)")
    else:
        lines.append("[+] New job alerts: (no new_jobs.csv yet — run `pacos monitor`)")
    lines.append("")
    lines.append("Reminder: PACOS never auto-sends. Copy approved assets from output/.")
    lines.append("=" * 60)
    return "\n".join(lines)
