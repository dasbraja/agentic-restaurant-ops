"""Queue and wait time tools — Firestore-backed waitlist and peak-hour estimates."""
import math
from datetime import datetime
from google.adk.tools import ToolContext
from db import (list_subcollection, add_to_subcollection,
                get_subcollection_doc, query_subcollection,
                update_subcollection_doc)
from config import COL_LOCATIONS, SUB_WAITLISTS, SUB_PEAK


def get_live_queue_depth(location_id: str = "loc_downtown",
                          tool_context: ToolContext = None) -> dict:
    """Get the current number of parties waiting at a location.

    Args:
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    parties = list_subcollection(COL_LOCATIONS, location_id, SUB_WAITLISTS)
    active  = [p for p in parties if p.get("status", "waiting") == "waiting"]
    return {"location_id": location_id, "queue_depth": len(active), "parties": active}


def get_peak_forecast(location_id: str = "loc_downtown",
                      day_of_week: str = "", hour: int = -1,
                      tool_context: ToolContext = None) -> dict:
    """Look up the historical average wait for this location, day, and hour.

    Args:
        location_id: Location identifier.
        day_of_week: Day name e.g. 'Friday'. Blank = use today.
        hour: 24h hour e.g. 19. -1 = use current hour.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    now = datetime.now()
    if not day_of_week:
        day_of_week = now.strftime("%A")
    if hour == -1:
        hour = now.hour
    slot = f"{day_of_week}_{hour}"
    doc  = get_subcollection_doc(COL_LOCATIONS, location_id, SUB_PEAK, slot)
    if not doc:
        return {"found": False, "location_id": location_id,
                "slot": slot, "p50_mins": None, "p90_mins": None}
    return {"found": True, "location_id": location_id,
            "slot": slot, "p50_mins": doc["p50"], "p90_mins": doc["p90"]}


def get_blended_wait_estimate(location_id: str = "loc_downtown",
                               tool_context: ToolContext = None) -> dict:
    """Calculate a blended wait estimate combining live queue depth with peak history.

    Args:
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    live  = get_live_queue_depth(location_id)
    fcst  = get_peak_forecast(location_id)
    depth = live["queue_depth"]
    alpha = max(0.1, 1.0 - (depth / 10.0))

    if fcst["found"]:
        blended    = alpha * fcst["p50_mins"] + (1 - alpha) * depth * 5
        confidence = "high"
    else:
        blended    = depth * 5
        confidence = "low"

    now  = datetime.now()
    day  = now.strftime("%A")
    future_slots = query_subcollection(
        COL_LOCATIONS, location_id, SUB_PEAK,
        filters=[("slot", ">=", f"{day}_{now.hour + 1}")],
        order_by="p50", direction="asc", limit=1,
    )
    next_lull = future_slots[0]["slot"].split("_")[1] + ":00" if future_slots else None

    return {
        "location_id":   location_id,
        "queue_depth":   depth,
        "estimate_mins": math.ceil(blended),
        "forecast_p50":  fcst.get("p50_mins"),
        "confidence":    confidence,
        "is_peak_hour":  fcst.get("found", False),
        "next_lull_at":  next_lull,
        "alpha":         round(alpha, 2),
    }


def add_party_to_waitlist(location_id: str, party_name: str, party_size: int,
                           tool_context: ToolContext = None) -> dict:
    """Add a party to the waitlist at a location.

    Args:
        location_id: Location identifier.
        party_name: Guest's last name or name.
        party_size: Number of people in the party.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    joined_at = datetime.now().strftime("%H:%M")
    doc_id    = add_to_subcollection(COL_LOCATIONS, location_id, SUB_WAITLISTS, {
        "name": party_name, "party_size": party_size,
        "joined_at": joined_at, "status": "waiting",
    })
    estimate = get_blended_wait_estimate(location_id)
    return {
        "success": True, "doc_id": doc_id,
        "party_name": party_name,
        "estimate_mins": estimate["estimate_mins"],
        "joined_at": joined_at,
    }


def seat_next_party(location_id: str = "loc_downtown",
                    tool_context: ToolContext = None) -> dict:
    """Seat the next waiting party at a location.

    Args:
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    parties = query_subcollection(
        COL_LOCATIONS, location_id, SUB_WAITLISTS,
        filters=[("status", "==", "waiting")],
        order_by="joined_at", direction="asc", limit=1,
    )
    if not parties:
        return {"success": False, "message": "Waitlist is empty."}
    party = parties[0]
    update_subcollection_doc(COL_LOCATIONS, location_id, SUB_WAITLISTS,
                             party["_id"], {"status": "seated"})
    remaining = get_live_queue_depth(location_id)["queue_depth"]
    return {"success": True, "seated_party": party,
            "remaining_in_queue": remaining - 1}


def notify_party_table_ready(location_id: str, party_name: str,
                              tool_context: ToolContext = None) -> dict:
    """Send a table-ready notification to a specific party (simulated SMS).

    Args:
        location_id: Location identifier.
        party_name: Name of the party to notify.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    return {
        "success": True,
        "message": f"Notification sent to {party_name} at {location_id}. Their table is ready.",
    }