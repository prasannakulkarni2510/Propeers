"""Service layer: bridges the FastAPI routes to the store + LangGraph pipeline."""
from __future__ import annotations

import threading
from datetime import datetime

from pacos.config import Config, load
from pacos.leads import load_leads
from pacos.pipeline import Pipeline
from pacos.store import PacosStore


class Service:
    def __init__(self, cfg: Config | None = None):
        self.cfg = cfg or load()
        self.store = PacosStore(self.cfg.db_path)
        if self.store.leads_empty() and self.cfg.leads_csv.exists():
            self.store.ingest_leads(load_leads(self.cfg.leads_csv))
        self._pipeline: Pipeline | None = None
        self._lock = threading.Lock()

    def _pipe(self) -> Pipeline:
        if self._pipeline is None:
            self._pipeline = Pipeline(self.cfg, self.store)
        return self._pipeline

    # ── leads / assets ───────────────────────────────────────────────────
    def leads_with_state(self) -> list[dict]:
        return self.store.get_leads()

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
