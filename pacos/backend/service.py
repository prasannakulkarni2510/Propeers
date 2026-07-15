"""Service layer: bridges the FastAPI routes to the store + LangGraph pipeline."""
from __future__ import annotations

import threading
from datetime import datetime

from dataclasses import asdict

from pacos.chat import chat_turn
from pacos.config import Config, load
from pacos.discovery import build_searches
from pacos.inbox_monitor import run_monitor
from pacos.jd_parser import parse_jd
from pacos.leads import append_lead_to_csv, build_lead, load_leads
from pacos.llm import NemotronClient
from pacos.pipeline import Pipeline
from pacos.store import PacosStore


class Service:
    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or load()
        self.store = PacosStore(self.cfg.db_path)
        if self.store.leads_empty() and self.cfg.leads_csv.exists():
            self.store.ingest_leads(load_leads(self.cfg.leads_csv))
        self._pipeline: Pipeline | None = None
        self._client: NemotronClient | None = None
        self._lock = threading.Lock()

    def _llm(self) -> NemotronClient:
        if self._client is None:
            self._client = NemotronClient(self.cfg)
        return self._client

    def _pipe(self) -> Pipeline:
        if self._pipeline is None:
            self._pipeline = Pipeline(self.cfg, self.store, client=self._llm())
        return self._pipeline

    # ── leads / assets ───────────────────────────────────────────────────
    def leads_with_state(self) -> list[dict]:
        return self.store.get_leads()

    def chat(self, messages: list[dict]) -> tuple[str, dict | None, list[str], bool]:
        """One assistant turn. May return a lead proposal — never writes it."""
        return chat_turn(self._llm(), self.stats(), messages)

    def discover(self, company: str, role: str = "", city: str = "",
                 keywords: list[str] | None = None) -> list[dict]:
        """Boolean people-search variants for a job. Read-only: writes nothing."""
        return [asdict(v) for v in build_searches(company, role, city, keywords)]

    def parse_jd(self, text: str) -> tuple[dict, list[str], bool]:
        """Extract proposed lead fields from JD text. Read-only: writes nothing."""
        return parse_jd(self._llm(), text)

    def add_lead(self, raw: dict) -> tuple[dict, bool, str, list[str]]:
        """Add one lead to the lead sheet (leads.csv) and the tracker store.

        Returns (lead_row, created, message, warnings). Raises ValueError when
        the payload can't produce a usable lead_id.
        """
        with self._lock:
            lead = build_lead(raw)
            if not lead.lead_id:
                raise ValueError(
                    "could not derive a lead_id — full_name and company_name "
                    "must contain at least one alphanumeric character"
                )
            csv_written = append_lead_to_csv(self.cfg.leads_csv, raw)
            created = self.store.add_lead(lead)
            row = self.store.get_lead(lead.lead_id)
            row["warnings"] = lead.warnings
            if created:
                msg = f"Lead {lead.lead_id} added to lead sheet and tracker."
            elif csv_written:
                msg = f"Lead {lead.lead_id} re-added to lead sheet; tracker updated."
            else:
                msg = f"Lead {lead.lead_id} already exists — details updated in tracker."
            return row, created, msg, lead.warnings

    def assets_for(self, lead_id: str) -> dict | None:
        lead = self.store.get_lead(lead_id)
        if lead is None:
            return None
        folder = self.cfg.output_dir / lead["folder_name"]
        files = []
        for name in ("cold_email.txt", "cold_dm.txt", "cover_letter.txt", "cv_notes.txt"):
            fp = folder / name
            files.append({"name": name,
                          "content": fp.read_text(encoding="utf-8") if fp.exists() else ""})
        return {"lead_id": lead_id, "folder_name": lead["folder_name"],
                "generated": folder.exists(), "files": files}

    # ── generation ───────────────────────────────────────────────────────
    def generate(self, *, dry_run: bool, limit: int, lead_id: str | None,
                 review_hooks: bool = False) -> dict:
        with self._lock:
            self.store.ingest_leads(load_leads(self.cfg.leads_csv))
            leads = load_leads(self.cfg.leads_csv)
            if lead_id:
                leads = [ld for ld in leads if ld.lead_id == lead_id]
            elif limit:
                leads = leads[:limit]

            pipe = self._pipe()
            dry = dry_run or pipe.dry_by_default
            self.store.reset_agent_status("queued")
            generated, errors = 0, []
            for ld in leads:
                try:
                    # review_hooks in the API auto-approves the proposed hook
                    # (the UI can later expose an edit step per lead).
                    hook = pipe.personalize(ld, dry_run=dry) if review_hooks else None
                    pipe.run_for_lead(ld, dry_run=dry, hook=hook)
                    generated += 1
                except Exception as e:
                    errors.append(f"{ld.folder_name}: {type(e).__name__}: {e}")
            return {"requested": len(leads), "generated": generated,
                    "dry_run": dry, "model": self.cfg.nemotron_model, "errors": errors}

    # ── approvals ────────────────────────────────────────────────────────
    @staticmethod
    def _d(s):
        return datetime.strptime(s, "%Y-%m-%d").date() if s else None

    def mark_sent(self, lead_id, channel, date_s):
        if self.store.mark_sent(lead_id, channel=channel, sent_date=self._d(date_s),
                                follow_up_days=self.cfg.follow_up_days):
            return True, f"Sent via {channel}. Follow-up due {self.store.get_lead(lead_id)['follow_up_due']}."
        return False, "lead_id not found"

    def mark_reply(self, lead_id, intent, date_s):
        if self.store.mark_reply(lead_id, intent=intent, reply_date=self._d(date_s)):
            return True, f"Reply recorded ({intent})."
        return False, "lead_id not found"

    def mark_status(self, lead_id, status):
        if self.store.mark_status(lead_id, status):
            return True, f"Status -> {status}."
        return False, "lead_id not found"

    # ── inbox scan ───────────────────────────────────────────────────────
    def scan_inbox(self, days: int = 1) -> dict:
        """One-shot read-only Gmail scan. Raises GmailUnavailable if not set up
        or if the Gmail API rejects the call (disabled API, expired consent…)."""
        from googleapiclient.errors import HttpError

        from pacos.inbox_monitor import GmailUnavailable

        with self._lock:
            try:
                return asdict(run_monitor(self.cfg, self.store, days=days))
            except HttpError as e:
                self.store.set_agent_status("inbox_monitor", "error", "Gmail API error")
                raise GmailUnavailable(f"Gmail API error: {e.reason}") from e

    def job_alerts(self) -> list[dict]:
        """Job alerts collected by inbox scans (new_jobs.csv), deduped by URL,
        newest first. Empty list when no scan has run yet."""
        import csv

        path = self.cfg.new_jobs_csv
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("url") or "").strip()]
        by_url: dict[str, dict] = {}
        for r in rows:  # later rows win, so re-scans refresh the date
            by_url[r["url"]] = r
        return sorted(by_url.values(), key=lambda r: r.get("date", ""), reverse=True)

    # ── unmatched replies ────────────────────────────────────────────────
    def unmatched(self) -> list[dict]:
        return self.store.list_unmatched()

    def associate(self, reply_id: int, lead_id: str):
        if self.store.associate_reply(reply_id, lead_id):
            return True, f"Reply #{reply_id} associated with {lead_id}."
        return False, "reply not found"

    # ── dashboard ────────────────────────────────────────────────────────
    def stats(self) -> dict:
        rows = self.store.get_leads()
        return {
            "total": len(rows),
            "status_counts": self.store.status_counts(),
            "followups_due": len(self.store.due_followups()),
            "with_assets": sum(1 for r in rows if r["assets_generated"] == "true"),
        }

    def agents(self) -> list[dict]:
        return self.store.get_agent_status()
