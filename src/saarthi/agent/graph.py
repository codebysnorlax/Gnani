import sqlite3
from pathlib import Path
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from saarthi.config import settings
from saarthi.agent.state import ConsumerDostState
from saarthi.agent.nodes import (
    node_ingest,
    node_scrub,
    node_parse,
    node_clarify,
    node_resolve,
    node_bundle,
    node_tts,
)


def should_clarify(state: ConsumerDostState) -> Literal["clarify", "resolve"]:
    """Conditional routing: if missing critical fields, route to clarify; else resolve."""
    missing = state.get("missing_fields", [])
    if missing:
        return "clarify"
    return "resolve"


def create_workflow() -> StateGraph:
    """Build the LangGraph conversational intake and dispute assessment workflow."""
    workflow = StateGraph(ConsumerDostState)

    workflow.add_node("ingest", node_ingest)
    workflow.add_node("scrub", node_scrub)
    workflow.add_node("parse", node_parse)
    workflow.add_node("clarify", node_clarify)
    workflow.add_node("resolve", node_resolve)

    workflow.set_entry_point("ingest")
    workflow.add_edge("ingest", "scrub")
    workflow.add_edge("scrub", "parse")

    workflow.add_conditional_edges(
        "parse",
        should_clarify,
        {
            "clarify": "clarify",
            "resolve": "resolve",
        },
    )

    workflow.add_edge("clarify", END)
    workflow.add_edge("resolve", END)

    return workflow


def create_generation_workflow() -> StateGraph:
    """Build the LangGraph atomic dossier generation workflow (bundle -> tts -> GENERATED)."""
    workflow = StateGraph(ConsumerDostState)

    workflow.add_node("bundle", node_bundle)
    workflow.add_node("tts", node_tts)

    workflow.set_entry_point("bundle")
    workflow.add_edge("bundle", "tts")
    workflow.add_edge("tts", END)

    return workflow


async def get_compiled_graph(checkpointer=None):
    """Compile conversational assessment workflow with optional checkpointer."""
    workflow = create_workflow()
    return workflow.compile(checkpointer=checkpointer)


async def get_compiled_generation_graph(checkpointer=None):
    """Compile atomic dossier generation workflow with optional checkpointer."""
    workflow = create_generation_workflow()
    return workflow.compile(checkpointer=checkpointer)


async def run_atomic_generation(state: ConsumerDostState) -> dict:
    """Execute bundle and TTS generation atomically via compiled LangGraph."""
    gen_graph = await get_compiled_generation_graph()
    result = await gen_graph.ainvoke(state)
    return result
