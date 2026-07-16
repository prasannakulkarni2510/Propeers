"""Generation pipeline — orchestrates the LangGraph graph for a lead, writes the
asset files, and records state in the store.

Two entry points support the --review-hooks toggle:
  • run_for_lead(...)        — full automatic run (personalization + assets)
  • personalize(...)         — phase 1 of review: produce the hook only
  • run_for_lead(hook=...)   — phase 2 of review: assets using the approved hook
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .graph import prompts
from .graph.edges import build_graph
from .graph.nodes import _base_cv, _candidate, make_personalization_node
from .graph.prompts import ASSET_SPECS
from .leads import Lead
from .llm import NemotronClient
from .store import PacosStore


def lead_to_dict(lead: Lead) -> dict:
    return {
        "lead_id": lead.lead_id,
        "full_name": lead.full_name,
        "first_name": lead.first_name,
        "job_title": lead.job_title,
        "company_name": lead.company_name,
        "city": lead.city,
        "linkedin_url": lead.linkedin_url,
        "persona_tag": lead.persona_tag,
        "domain_tag": lead.domain_tag,
        "email": lead.email,
        "company_size": lead.company_size,
        "industry": lead.industry,
        "company_website": lead.company_website,
        "funding_stage": lead.funding_stage,
        "folder_name": lead.folder_name,
        "has_email": lead.has_email,
    }


@dataclass
class Generated:
    lead_id: str
    folder: Path
    hook: str
    dry_run: bool


class Pipeline:
    def __init__(self, cfg: Config, store: PacosStore, client: NemotronClient | None = None):
        self.cfg = cfg
        self.store = store
        self.client = client or NemotronClient(cfg)
        self.graph = build_graph(cfg, self.client, store, cfg.db_path)
        # standalone personalization for review phase 1
        self._personalize_node = make_personalization_node(cfg, self.client, store)

    @property
    def dry_by_default(self) -> bool:
        return not self.client.available

    def personalize(self, lead: Lead, *, dry_run: bool = False) -> str:
        """Phase 1 of review mode: compute just the hook for approval."""
        state = {"lead": lead_to_dict(lead), "dry_run": dry_run or self.dry_by_default}
        out = self._personalize_node(state)
        return out.get("hook", "")

    def run_for_lead(self, lead: Lead, *, dry_run: bool = False,
                     hook: str | None = None) -> Generated:
        dry = dry_run or self.dry_by_default
        state: dict = {"lead": lead_to_dict(lead), "dry_run": dry, "assets": {}}
        if hook is not None:
            state["hook"] = hook
        config = {"configurable": {"thread_id": lead.lead_id}}
        result = self.graph.invoke(state, config=config)

        assets = result.get("assets", {})
        folder = self._write_assets(lead, assets)
        used_hook = result.get("hook", hook or "")
        self.store.upsert_from_generation(lead.lead_id, used_hook)
        return Generated(lead_id=lead.lead_id, folder=folder, hook=used_hook, dry_run=dry)

    def regenerate_asset(self, lead: Lead, asset_key: str, *,
                         dry_run: bool = False) -> str:
        """Rewrite a single asset for a lead, reusing the hook from the last run
        so the message stays consistent with the others. Runs at a higher
        temperature than a first pass so the rewrite is genuinely different, not
        the same sentences shuffled."""
        if asset_key not in ASSET_SPECS:
            raise KeyError(f"unknown asset '{asset_key}'")
        dry = dry_run or self.dry_by_default
        lead_d = lead_to_dict(lead)
        filename, _ = ASSET_SPECS[asset_key]

        hook = self.store.get_hook(lead.lead_id) or self.personalize(lead, dry_run=dry)
        domain_read = prompts.tone_for(lead_d.get("domain_tag", ""))

        self.store.set_agent_status(asset_key, "running", lead.folder_name)
        if dry:
            text = prompts.tmpl_asset(asset_key, lead_d, _candidate(self.cfg), hook)
        else:
            text = self.client.complete_text(
                system=prompts.SYSTEM_ASSET,
                user=prompts.build_asset_user(
                    asset_key, lead_d, _candidate(self.cfg), _base_cv(self.cfg),
                    hook, domain_read),
                temperature=0.9,  # more spread than the 0.6 first pass
                max_tokens=1600,
            )
        text = prompts.strip_dashes(text)
        self.store.set_agent_status(asset_key, "done", "regenerated")

        # Persist to the durable store and refresh the convenience file copy.
        self.store.save_assets(lead.lead_id, {filename: text})
        folder = self.cfg.output_dir / lead.folder_name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_text(text, encoding="utf-8")
        return text

    def _write_assets(self, lead: Lead, assets: dict) -> Path:
        # Always produce all four filenames; a skipped agent leaves a note.
        files = {}
        for _, (filename, _spec) in ASSET_SPECS.items():
            content = assets.get(filename)
            if content is None:
                content = "(not generated — lead has no email, so no cold email)"
            files[filename] = content
        # The store is the durable copy (cloud filesystems are ephemeral);
        # the files under output/ are the operator-friendly convenience copy.
        self.store.save_assets(lead.lead_id, files)
        folder = self.cfg.output_dir / lead.folder_name
        folder.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (folder / filename).write_text(content, encoding="utf-8")
        return folder
