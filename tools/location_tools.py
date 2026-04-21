"""Location tools — Firestore-backed store finder, hours, and capacity."""
from google.adk.tools import ToolContext
from db import get_doc, query_collection
from config import COL_LOCATIONS


def get_all_locations(tool_context: ToolContext = None) -> dict:
    """Get a summary list of all restaurant locations."""
    docs = query_collection(COL_LOCATIONS, limit=20)
    return {
        "locations": [
            {"id": d["_id"], "name": d.get("name"), "address": d.get("address")}
            for d in docs
        ]
    }


def get_location_info(location_id: str, tool_context: ToolContext = None) -> dict:
    """Get full details for a specific location.

    Args:
        location_id: Location identifier (loc_downtown, loc_bellevue, loc_pike).
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    doc = get_doc(COL_LOCATIONS, location_id)
    if not doc:
        return {"found": False, "message": f"Location '{location_id}' not found."}
    return {"found": True, **doc}


def get_location_hours(location_id: str, tool_context: ToolContext = None) -> dict:
    """Get opening and closing hours for a location.

    Args:
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    doc = get_doc(COL_LOCATIONS, location_id)
    if not doc:
        return {"found": False, "message": f"Location '{location_id}' not found."}
    return {
        "found": True, "location_id": location_id,
        "name": doc.get("name"),
        "open":  doc.get("hours_open"),
        "close": doc.get("hours_close"),
    }


def get_location_capacity(location_id: str, tool_context: ToolContext = None) -> dict:
    """Get seating capacity and outdoor seating availability.

    Args:
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    doc = get_doc(COL_LOCATIONS, location_id)
    if not doc:
        return {"found": False, "message": f"Location '{location_id}' not found."}
    return {
        "found": True, "location_id": location_id,
        "name": doc.get("name"),
        "seating_capacity": doc.get("seating_capacity"),
        "outdoor_seating":  doc.get("outdoor_seating"),
    }


def find_nearest_location(landmark_or_area: str,
                            tool_context: ToolContext = None) -> dict:
    """Find the nearest restaurant location to a landmark or area.

    Args:
        landmark_or_area: Landmark or area, e.g. 'Space Needle', 'Bellevue', 'Pike Place'.
    """
    docs  = query_collection(COL_LOCATIONS, limit=20)
    query = landmark_or_area.lower()

    scored = []
    for d in docs:
        score = 0
        name    = d.get("name", "").lower()
        address = d.get("address", "").lower()
        loc_id  = d.get("_id", "")
        if query in name:    score += 3
        if query in address: score += 2
        if "space needle" in query and loc_id == "loc_downtown":   score += 2
        if "pike" in query and loc_id == "loc_pike":               score += 3
        if ("bellevue" in query or "east" in query) and loc_id == "loc_bellevue":
            score += 3
        scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    nearest = scored[0][1] if scored else None

    if tool_context and nearest:
        tool_context.state["active_location"] = nearest.get("_id", "loc_downtown")

    return {
        "nearest_location": nearest,
        "note": "Distances are approximated; check Google Maps for exact routing.",
    }