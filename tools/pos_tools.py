"""POS and sales tools — Firestore-backed order management and revenue."""
from datetime import date
from google.adk.tools import ToolContext
from db import (get_doc, set_doc, update_doc, delete_doc,
                query_collection, query_subcollection,
                get_subcollection_doc)
from config import COL_ORDERS, COL_LOCATIONS, SUB_REVENUE


def get_current_order(table_id: str, tool_context: ToolContext) -> dict:
    """Get the current open order for a table.

    Args:
        table_id: Table identifier, e.g. 'table_1' or 'table_7'.
    """
    # Persist the active table so other agents can reference it
    tool_context.state["active_table"] = table_id

    order = get_doc(COL_ORDERS, table_id)
    if not order:
        return {"found": False, "table_id": table_id,
                "message": f"No open order for {table_id}."}
    subtotal   = sum(i["price"] * i["qty"] for i in order.get("items", []))
    discounted = subtotal * (1 - order.get("discount_pct", 0) / 100)
    return {
        "found": True,
        "table_id": table_id,
        "items": order.get("items", []),
        "discount_pct": order.get("discount_pct", 0),
        "subtotal_usd": round(subtotal, 2),
        "total_after_discount_usd": round(discounted, 2),
    }


def add_item_to_order(table_id: str, location_id: str,
                      item_name: str, quantity: int, price_usd: float,
                      tool_context: ToolContext) -> dict:
    """Add an item to a table's order. Creates the order if it doesn't exist.

    Args:
        table_id: Table identifier.
        location_id: Location identifier.
        item_name: Name of the menu item.
        quantity: Number of portions to add.
        price_usd: Price per portion in USD.
    """
    tool_context.state["active_table"]    = table_id
    tool_context.state["active_location"] = location_id

    order = get_doc(COL_ORDERS, table_id) or {
        "table_id": table_id, "location_id": location_id,
        "items": [], "discount_pct": 0, "status": "open",
    }
    order["items"].append({"name": item_name, "qty": quantity, "price": price_usd})
    set_doc(COL_ORDERS, table_id, order)
    return {"success": True, "table_id": table_id, "added": item_name, "qty": quantity}


def remove_item_from_order(table_id: str, item_name: str,
                            tool_context: ToolContext) -> dict:
    """Remove an item from a table's order.

    Args:
        table_id: Table identifier.
        item_name: Name of the item to remove.
    """
    tool_context.state["active_table"] = table_id

    order = get_doc(COL_ORDERS, table_id)
    if not order:
        return {"success": False, "message": f"No order found for {table_id}."}
    before = len(order["items"])
    order["items"] = [i for i in order["items"]
                      if i["name"].lower() != item_name.lower()]
    removed = len(order["items"]) < before
    if removed:
        update_doc(COL_ORDERS, table_id, {"items": order["items"]})
    return {"success": removed, "table_id": table_id,
            "removed": item_name if removed else None}


def apply_discount(table_id: str, discount_pct: float,
                   tool_context: ToolContext) -> dict:
    """Apply a percentage discount to a table's order.

    Args:
        table_id: Table identifier.
        discount_pct: Discount percentage, e.g. 20 for 20% off.
    """
    tool_context.state["active_table"] = table_id

    order = get_doc(COL_ORDERS, table_id)
    if not order:
        return {"success": False, "message": f"No order found for {table_id}."}
    update_doc(COL_ORDERS, table_id, {"discount_pct": discount_pct})
    return {"success": True, "table_id": table_id, "discount_pct": discount_pct}


def close_table_and_split(table_id: str, split_ways: int = 1,
                           tool_context: ToolContext = None) -> dict:
    """Close a table's order and calculate the split amounts.

    Args:
        table_id: Table identifier.
        split_ways: Number of ways to split the bill (default 1 = no split).
    """
    if tool_context:
        # Clear active table since order is now closed
        tool_context.state["active_table"] = None

    order = get_doc(COL_ORDERS, table_id)
    if not order:
        return {"success": False, "message": f"No order found for {table_id}."}
    subtotal   = sum(i["price"] * i["qty"] for i in order.get("items", []))
    discounted = subtotal * (1 - order.get("discount_pct", 0) / 100)
    per_person = round(discounted / max(split_ways, 1), 2)
    update_doc(COL_ORDERS, table_id, {"status": "closed"})
    return {
        "success": True, "table_id": table_id,
        "total_usd": round(discounted, 2),
        "split_ways": split_ways,
        "per_person_usd": per_person,
    }


def get_daily_revenue(location_id: str, date_str: str = "",
                      tool_context: ToolContext = None) -> dict:
    """Get total revenue and cover count for a location on a given date.

    Args:
        location_id: Location identifier.
        date_str: Date in YYYY-MM-DD format. Defaults to today.
    """
    if tool_context:
        tool_context.state["active_location"] = location_id

    if not date_str:
        date_str = date.today().isoformat()
    doc = get_subcollection_doc(COL_LOCATIONS, location_id, SUB_REVENUE, date_str)
    if not doc:
        return {"found": False, "location_id": location_id, "date": date_str,
                "message": "No revenue record found for this date."}
    return {"found": True, "location_id": location_id, "date": date_str,
            "total_usd": doc.get("total_usd"), "covers": doc.get("covers")}