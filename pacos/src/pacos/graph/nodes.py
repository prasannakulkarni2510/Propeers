"""Agent nodes. Each is a closure over (cfg, client, store) so the graph stays
model-agnostic and can report live status to the store as it runs.
"""
from __future__ import annotations

from ..config import Config
from ..llm import NemotronClient
from . import prompts
from .state import PacosState


def _candidate(cfg: Config) -> dict:
    return {
        "name": cfg.candidate_name,
        "headline": cfg.candidate_headline,
        "email": cfg.candidate_email,
        "linkedin": cfg.candidate_linkedin,
    }


def _base_cv(cfg: Config) -> str:
    return cfg.base_cv.read_text(encoding="utf-8") if cfg.base_cv.exists() else ""


def make_personalization_node(cfg: Config, client: NemotronClient, store):
    def personalization(state: PacosState) -> dict:
        lead = state["lead"]
        store.set_agent_status("personalization", "running", lead.get("folder_name", ""))

        # Review mode pre-seeds an approved hook — pass it straight through.
        if state.get("hook"):
            store.set_agent_status("personalization", "done", "approved hook")
            return {"domain_read": state.get("domain_read", "")}

        if state.get("dry_run") or not client.available:
            hook = prompts.tmpl_hook(lead)
            domain_read = prompts.tone_for(lead.get("domain_tag", ""))
        else:
            data = client.complete_json(
                system=prompts.SYSTEM_PERSONALIZATION,
                user=prompts.build_personalization_user(lead, _candidate(cfg), _base_cv(cfg)),
                max_tokens=400,
            )
            hook = str(data.get("hook", "")).strip()
            domain_read = str(data.get("domain_read", "")).strip()

        store.set_agent_status("personalization", "done", hook[:50])
        return {"hook": hook, "domain_read": domain_read}

    return personalization


def make_asset_node(asset_key: str, cfg: Config, client: NemotronClient, store):
    filename, _ = prompts.ASSET_SPECS[asset_key]

    def node(state: PacosState) -> dict:
        lead = state["lead"]
        hook = state.get("hook", "")
        domain_read = state.get("domain_read", "")
        store.set_agent_status(asset_key, "running", lead.get("folder_name", ""))

        if state.get("dry_run") or not client.available:
            text = prompts.tmpl_asset(asset_key, lead, _candidate(cfg), hook)
        else:
            text = client.complete_text(
                system=prompts.SYSTEM_ASSET,
                user=prompts.build_asset_user(
                    asset_key, lead, _candidate(cfg), _base_cv(cfg), hook, domain_read),
                max_tokens=900,
            )

        store.set_agent_status(asset_key, "done", "")
        return {"assets": {filename: text}}

    node.__name__ = f"{asset_key}_node"
    return node
