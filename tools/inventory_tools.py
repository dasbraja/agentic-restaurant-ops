"""Inventory tools — Firestore-backed food and beverage availability."""
from google.adk.tools import ToolContext
from db import (get_subcollection_doc, update_subcollection_doc,
                list_subcollection, query_subcollection, vector_search)
from config import COL_LOCATIONS, SUB_INVENTORY, COL_MENU


def check_item_availability(item_name: str, location_id: str = "loc_downtown",
                              tool_context: ToolContext = None) -> dict:
    """Check whether a specific menu item is available at a location.

    Args:
        item_name: Menu item name, e.g. 'Salmon' or 'Oat Milk'.
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    # Try exact doc ID first — get_subcollection_doc returns to_dict() with no _id field
    doc = get_subcollection_doc(COL_LOCATIONS, location_id, SUB_INVENTORY, item_name)
    matched_id = item_name  # we know the ID since we fetched by it

    if not doc:
        # Fall back to case-insensitive scan — list_subcollection includes _id
        all_items = list_subcollection(COL_LOCATIONS, location_id, SUB_INVENTORY)
        match = next((i for i in all_items
                      if i["_id"].lower() == item_name.lower()), None)
        if match:
            doc = match
            matched_id = match["_id"]

    if not doc:
        return {"found": False, "item": item_name, "location_id": location_id,
                "message": f"'{item_name}' not found in inventory for this location."}
    return {
        "found": True, "item": matched_id,
        "location_id": location_id,
        "available": doc["available"],
        "qty": doc["qty"], "unit": doc.get("unit", "portions"),
    }


def get_full_inventory(location_id: str = "loc_downtown",
                        tool_context: ToolContext = None) -> dict:
    """Get the complete inventory list for a location.

    Args:
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    items = list_subcollection(COL_LOCATIONS, location_id, SUB_INVENTORY)
    return {"location_id": location_id, "inventory": items, "count": len(items)}


def get_low_stock_items(location_id: str = "loc_downtown",
                         threshold: int = 5,
                         tool_context: ToolContext = None) -> dict:
    """Get items that are unavailable or running low at a location.

    Args:
        location_id: Location identifier.
        threshold: Qty at or below which an item is considered low stock.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    all_items = list_subcollection(COL_LOCATIONS, location_id, SUB_INVENTORY)
    low = [i for i in all_items
           if not i.get("available", True) or i.get("qty", 0) <= threshold]
    return {"location_id": location_id, "low_stock_items": low, "count": len(low)}


def mark_item_unavailable(item_name: str, location_id: str = "loc_downtown",
                           tool_context: ToolContext = None) -> dict:
    """Mark an item as sold out / 86'd at a location.

    Args:
        item_name: The menu item to mark unavailable.
        location_id: Location identifier.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    doc = get_subcollection_doc(COL_LOCATIONS, location_id, SUB_INVENTORY, item_name)
    if not doc:
        return {"success": False,
                "message": f"'{item_name}' not found in inventory for {location_id}."}
    update_subcollection_doc(COL_LOCATIONS, location_id, SUB_INVENTORY,
                             item_name, {"available": False, "qty": 0})
    return {"success": True, "item": item_name, "location_id": location_id,
            "message": f"'{item_name}' has been marked as unavailable (86'd)."}


def restock_item(item_name: str, location_id: str, quantity: int,
                  tool_context: ToolContext = None) -> dict:
    """Mark an item as available and update its quantity.

    Args:
        item_name: The menu item to restock.
        location_id: Location identifier.
        quantity: New stock quantity.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    update_subcollection_doc(COL_LOCATIONS, location_id, SUB_INVENTORY,
                             item_name, {"available": True, "qty": quantity})
    return {"success": True, "item": item_name,
            "location_id": location_id, "new_qty": quantity}


def search_menu_items(query: str, limit: int = 5,
                       only_available: bool = True,
                       tool_context: ToolContext = None) -> dict:
    """Search the menu semantically using vector similarity.

    Use this when a guest describes what they want in natural language rather
    than naming a specific item.

    Args:
        query: Natural language description of what the guest is looking for.
        limit: Maximum number of results to return (default 5).
        only_available: If True (default), filters to available items only.
    """
    pre_filters = [("available", "==", True)] if only_available else None

    results = vector_search(
        collection=COL_MENU,
        query_text=query,
        limit=limit,
        pre_filters=pre_filters,
    )

    if not results:
        return {
            "found": False,
            "query": query,
            "message": "No menu items found matching that description.",
        }

    matches = []
    for r in results:
        matches.append({
            "name":         r.get("name"),
            "category":     r.get("category"),
            "price":        r.get("price"),
            "description":  r.get("description"),
            "dietary_tags": r.get("dietary_tags", []),
            "available":    r.get("available", True),
            "similarity":   round(1 - r.get("_distance", 0), 3),
        })

    return {
        "found":   True,
        "query":   query,
        "matches": matches,
        "count":   len(matches),
    }