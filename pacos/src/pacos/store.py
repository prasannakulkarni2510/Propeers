"""SQLite store — the authoritative source of truth (ADR 0003).

Holds leads, tracker state, live per-agent status, and unmatched inbox replies in
one local file (`pacos.db`). Atomic writes end the lost-update races that the old
whole-file `tracker.csv` approach had. `tracker.csv` is now a read-only export.

One connection per call (sqlite3 handles file locking); WAL + busy_timeout keep
the FastAPI threads and CLI from stepping on each other.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from .leads import Lead

# Logical agents whose live status the dashboard shows.
AGENT_NODES = [
    ("personalization", "Personalization"),
    ("cold_email", "Cold Email"),
    ("cold_dm", "Cold DM"),
    ("cover_letter", "Cover Letter"),
    ("cv_notes", "CV Notes"),
    ("inbox_monitor", "Inbox Monitor"),
]

# tracker.csv export column order (kept compatible with the old CSV).
EXPORT_COLUMNS = [
    "lead_id", "full_name", "company_name", "job_title", "city", "persona_tag",
    "domain_tag", "email", "assets_generated", "outreach_sent_date", "channel",
    "status", "last_reply_date", "reply_intent", "follow_up_due", "notes",
]

STATUS_ORDER = ["pending", "sent", "replied", "interested", "interview", "offer"]
TERMINAL_STATUSES = {"offer", "rejected"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    full_name TEXT, first_name TEXT, job_title TEXT, company_name TEXT,
    city TEXT, linkedin_url TEXT, persona_tag TEXT, domain_tag TEXT,
    email TEXT, company_size TEXT, industry TEXT, company_website TEXT,
    funding_stage TEXT, folder_name TEXT
);
CREATE TABLE IF NOT EXISTS tracker (
    lead_id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'pending',
    assets_generated TEXT DEFAULT 'false',
    personalization_hook TEXT DEFAULT '',
    outreach_sent_date TEXT DEFAULT '',
    channel TEXT DEFAULT '',
    last_reply_date TEXT DEFAULT '',
    reply_intent TEXT DEFAULT '',
    follow_up_due TEXT DEFAULT '',
    notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS agent_status (
    node TEXT PRIMARY KEY,
    status TEXT DEFAULT 'idle',
    detail TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS unmatched_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_date TEXT, sender TEXT, subject TEXT, intent TEXT,
    associated_lead_id TEXT DEFAULT ''
);
"""


class PacosStore:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._conn() as c:
            c.executescript(_SCHEMA)
            for node, _ in AGENT_NODES:
                c.execute(
                    "INSERT OR IGNORE INTO agent_status(node, status) VALUES (?, 'idle')",
                    (node,),
                )

    # ── leads ────────────────────────────────────────────────────────────
    def leads_empty(self) -> bool:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"] == 0

    def ingest_leads(self, leads: list[Lead]) -> int:
        with self._conn() as c:
            for ld in leads:
                c.execute(
                    """INSERT INTO leads(lead_id, full_name, first_name, job_title,
                        company_name, city, linkedin_url, persona_tag, domain_tag,
                        email, company_size, industry, company_website, funding_stage,
                        folder_name)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(lead_id) DO UPDATE SET
                        full_name=excluded.full_name, first_name=excluded.first_name,
                        job_title=excluded.job_title, company_name=excluded.company_name,
                        city=excluded.city, linkedin_url=excluded.linkedin_url,
                        persona_tag=excluded.persona_tag, domain_tag=excluded.domain_tag,
                        email=excluded.email, company_size=excluded.company_size,
                        industry=excluded.industry, company_website=excluded.company_website,
                        funding_stage=excluded.funding_stage, folder_name=excluded.folder_name
                    """,
                    (ld.lead_id, ld.full_name, ld.first_name, ld.job_title,
                     ld.company_name, ld.city, ld.linkedin_url, ld.persona_tag,
                     ld.domain_tag, ld.email, ld.company_size, ld.industry,
                     ld.company_website, ld.funding_stage, ld.folder_name),
                )
                c.execute(
                    "INSERT OR IGNORE INTO tracker(lead_id, status) VALUES (?, 'pending')",
                    (ld.lead_id,),
                )
        return len(leads)

    def add_lead(self, lead: Lead) -> bool:
        """Upsert a single lead; return True if it was newly created."""
        created = self.get_lead(lead.lead_id) is None
        self.ingest_leads([lead])
        return created

    def _lead_row(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        email = d.get("email", "") or ""
        d["has_email"] = bool(email and "@" in email)
        d["warnings"] = []
        # tracker columns may be NULL if no tracker row yet
        for k in ("status", "assets_generated", "outreach_sent_date", "channel",
                  "last_reply_date", "reply_intent", "follow_up_due", "notes"):
            d[k] = d.get(k) or ""
        return d

    def get_leads(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT l.*, t.status, t.assets_generated, t.outreach_sent_date,
                          t.channel, t.last_reply_date, t.reply_intent,
                          t.follow_up_due, t.notes
                   FROM leads l LEFT JOIN tracker t ON t.lead_id = l.lead_id
                   ORDER BY l.company_name, l.first_name"""
            ).fetchall()
            return [self._lead_row(r) for r in rows]

    def get_lead(self, lead_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                """SELECT l.*, t.status, t.assets_generated, t.outreach_sent_date,
                          t.channel, t.last_reply_date, t.reply_intent,
                          t.follow_up_due, t.notes
                   FROM leads l LEFT JOIN tracker t ON t.lead_id = l.lead_id
                   WHERE l.lead_id = ?""",
                (lead_id,),
            ).fetchone()
            return self._lead_row(row) if row else None

    def lead_email(self, lead_id: str) -> str:
        with self._conn() as c:
            row = c.execute("SELECT email FROM leads WHERE lead_id=?", (lead_id,)).fetchone()
            return (row["email"] if row else "") or ""

    def find_lead_by_email(self, email: str) -> str | None:
        email = (email or "").strip().lower()
        if not email:
            return None
        with self._conn() as c:
            row = c.execute(
                "SELECT lead_id FROM leads WHERE lower(email) = ?", (email,)
            ).fetchone()
            return row["lead_id"] if row else None

    # ── tracker writes ───────────────────────────────────────────────────
    def _tracker_update(self, lead_id: str, **cols) -> bool:
        sets = ", ".join(f"{k}=?" for k in cols)
        params = list(cols.values()) + [lead_id]
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO tracker(lead_id) VALUES (?)", (lead_id,))
            cur = c.execute(f"UPDATE tracker SET {sets} WHERE lead_id=?", params)
            return cur.rowcount > 0

    def upsert_from_generation(self, lead_id: str, hook: str) -> None:
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO tracker(lead_id) VALUES (?)", (lead_id,))
            row = c.execute(
                "SELECT status, notes FROM tracker WHERE lead_id=?", (lead_id,)
            ).fetchone()
            status = (row["status"] or "").strip() or "pending"
            notes = (row["notes"] or "").strip() or hook
            c.execute(
                """UPDATE tracker SET assets_generated='true',
                   personalization_hook=?, status=?, notes=? WHERE lead_id=?""",
                (hook, status, notes, lead_id),
            )

    def mark_sent(self, lead_id, *, channel, sent_date=None, follow_up_days=5) -> bool:
        d = sent_date or date.today()
        due = d + timedelta(days=follow_up_days)
        return self._tracker_update(
            lead_id, outreach_sent_date=d.isoformat(), channel=channel,
            status="sent", follow_up_due=due.isoformat(),
        )

    def mark_reply(self, lead_id, *, intent, reply_date=None) -> bool:
        d = reply_date or date.today()
        status = {"interested": "interested", "rejected": "rejected",
                  "follow-up": "replied"}.get(intent, "replied")
        cols = dict(last_reply_date=d.isoformat(), reply_intent=intent, status=status)
        if status in TERMINAL_STATUSES:
            cols["follow_up_due"] = ""
        return self._tracker_update(lead_id, **cols)

    def mark_status(self, lead_id, status) -> bool:
        cols = {"status": status}
        if status in TERMINAL_STATUSES:
            cols["follow_up_due"] = ""
        return self._tracker_update(lead_id, **cols)

    # ── queries ──────────────────────────────────────────────────────────
    def due_followups(self, on: date | None = None) -> list[dict]:
        on = on or date.today()
        out = []
        for r in self.get_leads():
            due = r.get("follow_up_due", "")
            if not due or r.get("status") != "sent":
                continue
            try:
                if datetime.strptime(due, "%Y-%m-%d").date() <= on:
                    out.append(r)
            except ValueError:
                continue
        return out

    def by_status(self, status: str) -> list[dict]:
        return [r for r in self.get_leads() if r.get("status") == status]

    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.get_leads():
            s = (r.get("status") or "").strip()
            if s:
                counts[s] = counts.get(s, 0) + 1
        return counts

    # ── live agent status ────────────────────────────────────────────────
    def set_agent_status(self, node: str, status: str, detail: str = "") -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO agent_status(node, status, detail, updated_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(node) DO UPDATE SET
                     status=excluded.status, detail=excluded.detail,
                     updated_at=excluded.updated_at""",
                (node, status, detail, datetime.now().isoformat(timespec="seconds")),
            )

    def reset_agent_status(self, detail: str = "") -> None:
        for node, _ in AGENT_NODES:
            if node != "inbox_monitor":
                self.set_agent_status(node, "idle", detail)

    def get_agent_status(self) -> list[dict]:
        labels = dict(AGENT_NODES)
        with self._conn() as c:
            rows = c.execute("SELECT * FROM agent_status").fetchall()
        by_node = {r["node"]: dict(r) for r in rows}
        return [
            {"name": n, "label": labels[n],
             "status": by_node.get(n, {}).get("status", "idle"),
             "detail": by_node.get(n, {}).get("detail", "")}
            for n, _ in AGENT_NODES
        ]

    # ── unmatched replies ────────────────────────────────────────────────
    def add_unmatched_reply(self, *, received_date, sender, subject, intent) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO unmatched_replies(received_date, sender, subject, intent)
                   VALUES (?,?,?,?)""",
                (received_date, sender, subject, intent),
            )

    def list_unmatched(self, include_associated: bool = False) -> list[dict]:
        q = "SELECT * FROM unmatched_replies"
        if not include_associated:
            q += " WHERE associated_lead_id = ''"
        q += " ORDER BY id DESC"
        with self._conn() as c:
            return [dict(r) for r in c.execute(q).fetchall()]

    def associate_reply(self, reply_id: int, lead_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT intent FROM unmatched_replies WHERE id=?", (reply_id,)
            ).fetchone()
            if not row:
                return False
            c.execute(
                "UPDATE unmatched_replies SET associated_lead_id=? WHERE id=?",
                (lead_id, reply_id),
            )
        self.mark_reply(lead_id, intent=row["intent"])
        return True

    # ── export ───────────────────────────────────────────────────────────
    def export_csv(self, path: str | Path) -> Path:
        import csv

        path = Path(path)
        rows = self.get_leads()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in EXPORT_COLUMNS})
        return path
