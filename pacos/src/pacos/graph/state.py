"""Shared graph state + reducers."""
from __future__ import annotations

from typing import Annotated, TypedDict


def merge_assets(current: dict, update: dict) -> dict:
    """Reducer: merge parallel asset-agent outputs into one dict."""
    return {**(current or {}), **(update or {})}


class PacosState(TypedDict, total=False):
    # inputs
    lead: dict          # lead fields incl. folder_name, first_name, has_email
    dry_run: bool       # produce templates instead of calling Nemotron

    # produced by the personalization agent (or pre-seeded in review mode)
    hook: str
    domain_read: str

    # produced by the asset agents, merged in parallel
    assets: Annotated[dict, merge_assets]
