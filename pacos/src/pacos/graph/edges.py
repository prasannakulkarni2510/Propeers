"""Graph wiring: START → personalization → (conditional fan-out) → asset agents → END.

The conditional edge is where the 'skip cold_email when no email' decision lives.
Each asset agent runs in parallel and writes to END; the assets reducer merges
their outputs, so no explicit join node is needed.
"""
from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from ..config import Config
from ..llm import NemotronClient
from .nodes import make_asset_node, make_personalization_node
from .state import PacosState

ASSET_KEYS = ["cold_email", "cold_dm", "cover_letter", "cv_notes"]


def route_assets(state: PacosState) -> list[str]:
    """Fan out to the asset agents, skipping cold_email when the lead has no email."""
    lead = state["lead"]
    targets = list(ASSET_KEYS)
    if not lead.get("has_email"):
        targets.remove("cold_email")
    return targets


def build_graph(cfg: Config, client: NemotronClient, store, db_path):
    g = StateGraph(PacosState)
    g.add_node("personalization", make_personalization_node(cfg, client, store))
    for key in ASSET_KEYS:
        g.add_node(key, make_asset_node(key, cfg, client, store))

    g.add_edge(START, "personalization")
    g.add_conditional_edges("personalization", route_assets, ASSET_KEYS)
    for key in ASSET_KEYS:
        g.add_edge(key, END)

    # Checkpointer in the same SQLite file → resume a failed 500-lead batch.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return g.compile(checkpointer=checkpointer)
