"""
Agent factory — loads agent definitions declaratively from agents_config.json.

To add, remove, or retune an agent:
  1. Edit agents_config.json  (no Python changes needed)
  2. Restart the server

The only things that live in Python are:
  - The tool registry (TOOL_REGISTRY) — maps string names → callable objects
  - The factory function (build_agents) — wires config → LlmAgent instances
"""
import json
import logging
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from config import ADK_MODEL
import tools as _tools_module

log = logging.getLogger("restaurant_agent.agents")

# ---------------------------------------------------------------------------
# Tool registry — every tool callable must be listed here.
# Adding a new tool: implement it in tools/, import it in tools/__init__.py,
# then add one line here. No other file needs to change.
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, Any] = {
    # POS / sales
    "get_current_order":        _tools_module.get_current_order,
    "add_item_to_order":        _tools_module.add_item_to_order,
    "remove_item_from_order":   _tools_module.remove_item_from_order,
    "apply_discount":           _tools_module.apply_discount,
    "close_table_and_split":    _tools_module.close_table_and_split,
    "get_daily_revenue":        _tools_module.get_daily_revenue,
    # Queue / wait times
    "get_live_queue_depth":     _tools_module.get_live_queue_depth,
    "get_peak_forecast":        _tools_module.get_peak_forecast,
    "get_blended_wait_estimate":_tools_module.get_blended_wait_estimate,
    "add_party_to_waitlist":    _tools_module.add_party_to_waitlist,
    "seat_next_party":          _tools_module.seat_next_party,
    "notify_party_table_ready": _tools_module.notify_party_table_ready,
    # Inventory / menu
    "check_item_availability":  _tools_module.check_item_availability,
    "get_full_inventory":       _tools_module.get_full_inventory,
    "get_low_stock_items":      _tools_module.get_low_stock_items,
    "mark_item_unavailable":    _tools_module.mark_item_unavailable,
    "restock_item":             _tools_module.restock_item,
    "search_menu_items":        _tools_module.search_menu_items,
    # Locations
    "get_all_locations":        _tools_module.get_all_locations,
    "get_location_info":        _tools_module.get_location_info,
    "get_location_hours":       _tools_module.get_location_hours,
    "get_location_capacity":    _tools_module.get_location_capacity,
    "find_nearest_location":    _tools_module.find_nearest_location,
    # Analytics
    "natural_language_query":   _tools_module.natural_language_query,
}

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
_CONFIG_PATH = Path(__file__).parent / "agents_config.json"


def _resolve_tools(names: list[str]) -> list[Any]:
    """Look up tool callables by name, raising clearly if any are missing."""
    resolved = []
    for name in names:
        if name not in TOOL_REGISTRY:
            raise KeyError(
                f"Tool '{name}' not found in TOOL_REGISTRY. "
                f"Add it to the registry in agents.py."
            )
        resolved.append(TOOL_REGISTRY[name])
    return resolved


def build_agents(
    config_path: Path = _CONFIG_PATH,
    model_override: str | None = None,
) -> LlmAgent:
    """Read agents_config.json and return the root LlmAgent.

    Args:
        config_path:    Path to the JSON config file. Defaults to
                        agents_config.json next to this file.
        model_override: Override the model for all agents (useful for testing).

    Returns:
        The root LlmAgent (the one with ``"is_root": true`` in the config).
    """
    with open(config_path) as f:
        config = json.load(f)

    default_model = model_override or config.get("default_model") or ADK_MODEL

    # Pass 1 — build all leaf agents (no sub_agents yet)
    built: dict[str, LlmAgent] = {}
    agent_defs = config["agents"]

    for defn in agent_defs:
        name = defn["name"]
        model = defn.get("model") or default_model
        built[name] = LlmAgent(
            name=name,
            model=model,
            description=defn["description"],
            instruction=defn["instruction"],
            tools=_resolve_tools(defn.get("tools", [])),
            # sub_agents wired in pass 2
        )
        log.debug("Built agent: %s (model=%s, tools=%s)",
                  name, model, defn.get("tools", []))

    # Pass 2 — wire sub_agents now that all instances exist
    root: LlmAgent | None = None
    for defn in agent_defs:
        sub_names = defn.get("sub_agents", [])
        if sub_names:
            agent = built[defn["name"]]
            agent.sub_agents = [built[n] for n in sub_names]
            log.debug("Wired sub_agents for %s: %s", defn["name"], sub_names)
        if defn.get("is_root"):
            root = built[defn["name"]]

    if root is None:
        raise ValueError(
            "No agent with \"is_root\": true found in agents_config.json. "
            "Mark exactly one agent as the root orchestrator."
        )

    log.info(
        "Agent hierarchy built from %s — root: %s, total agents: %d",
        config_path.name,
        root.name,
        len(built),
    )
    return root


# ---------------------------------------------------------------------------
# Module-level root agent — imported by main.py
# ---------------------------------------------------------------------------
restaurant_orchestrator = build_agents()