"""
seed_firestore.py — run once to populate Firestore with initial restaurant data.

Usage:
    python seed_firestore.py
"""
from db import (set_doc, set_subcollection_doc, embed_text,
                build_menu_embed_text, save_query_example)
from google.cloud.firestore_v1.vector import Vector

# ---------------------------------------------------------------------------
# Location documents
# ---------------------------------------------------------------------------
LOCATIONS = {
    "loc_downtown": {
        "id": "loc_downtown", "name": "Downtown",
        "address": "123 Pike St, Seattle WA", "phone": "206-555-0101",
        "hours_open": "11:00", "hours_close": "22:00",
        "seating_capacity": 80, "outdoor_seating": True,
    },
    "loc_bellevue": {
        "id": "loc_bellevue", "name": "Bellevue",
        "address": "456 Bellevue Way, Bellevue WA", "phone": "425-555-0202",
        "hours_open": "11:00", "hours_close": "21:00",
        "seating_capacity": 60, "outdoor_seating": False,
    },
    "loc_pike": {
        "id": "loc_pike", "name": "Pike Place",
        "address": "789 1st Ave, Seattle WA", "phone": "206-555-0303",
        "hours_open": "10:00", "hours_close": "21:00",
        "seating_capacity": 45, "outdoor_seating": True,
    },
}

# ---------------------------------------------------------------------------
# Inventory per location
# ---------------------------------------------------------------------------
INVENTORY = {
    "loc_downtown": {
        "Cheeseburger": {"name": "Cheeseburger", "category": "food",  "available": True,  "qty": 40, "unit": "portions", "threshold": 5},
        "Salmon":       {"name": "Salmon",        "category": "food",  "available": True,  "qty": 8,  "unit": "portions", "threshold": 3},
        "Halibut":      {"name": "Halibut",       "category": "food",  "available": True,  "qty": 5,  "unit": "portions", "threshold": 3},
        "Risotto":      {"name": "Risotto",       "category": "food",  "available": True,  "qty": 12, "unit": "portions", "threshold": 4},
        "Caesar Salad": {"name": "Caesar Salad",  "category": "food",  "available": True,  "qty": 30, "unit": "portions", "threshold": 5},
        "Oat Milk":     {"name": "Oat Milk",      "category": "beverage", "available": False, "qty": 0,  "unit": "liters",   "threshold": 2},
        "Lemonade":     {"name": "Lemonade",      "category": "beverage", "available": True,  "qty": 50, "unit": "glasses",  "threshold": 10},
        "Draft Beer":   {"name": "Draft Beer",    "category": "beverage", "available": True,  "qty": 80, "unit": "pints",    "threshold": 10},
        "House Wine":   {"name": "House Wine",    "category": "beverage", "available": True,  "qty": 20, "unit": "bottles",  "threshold": 3},
    },
    "loc_bellevue": {
        "Cheeseburger": {"name": "Cheeseburger", "category": "food",  "available": True,  "qty": 35, "unit": "portions", "threshold": 5},
        "Salmon":       {"name": "Salmon",        "category": "food",  "available": True,  "qty": 6,  "unit": "portions", "threshold": 3},
        "Halibut":      {"name": "Halibut",       "category": "food",  "available": False, "qty": 0,  "unit": "portions", "threshold": 3},
        "Risotto":      {"name": "Risotto",       "category": "food",  "available": True,  "qty": 9,  "unit": "portions", "threshold": 4},
        "Caesar Salad": {"name": "Caesar Salad",  "category": "food",  "available": True,  "qty": 25, "unit": "portions", "threshold": 5},
        "Oat Milk":     {"name": "Oat Milk",      "category": "beverage", "available": True,  "qty": 3,  "unit": "liters",   "threshold": 2},
        "Lemonade":     {"name": "Lemonade",      "category": "beverage", "available": True,  "qty": 40, "unit": "glasses",  "threshold": 10},
        "Draft Beer":   {"name": "Draft Beer",    "category": "beverage", "available": True,  "qty": 60, "unit": "pints",    "threshold": 10},
        "House Wine":   {"name": "House Wine",    "category": "beverage", "available": True,  "qty": 15, "unit": "bottles",  "threshold": 3},
    },
    "loc_pike": {
        "Cheeseburger": {"name": "Cheeseburger", "category": "food",  "available": True,  "qty": 20, "unit": "portions", "threshold": 5},
        "Salmon":       {"name": "Salmon",        "category": "food",  "available": True,  "qty": 10, "unit": "portions", "threshold": 3},
        "Halibut":      {"name": "Halibut",       "category": "food",  "available": True,  "qty": 7,  "unit": "portions", "threshold": 3},
        "Risotto":      {"name": "Risotto",       "category": "food",  "available": True,  "qty": 5,  "unit": "portions", "threshold": 4},
        "Caesar Salad": {"name": "Caesar Salad",  "category": "food",  "available": True,  "qty": 18, "unit": "portions", "threshold": 5},
        "Oat Milk":     {"name": "Oat Milk",      "category": "beverage", "available": True,  "qty": 4,  "unit": "liters",   "threshold": 2},
        "Lemonade":     {"name": "Lemonade",      "category": "beverage", "available": True,  "qty": 35, "unit": "glasses",  "threshold": 10},
        "Draft Beer":   {"name": "Draft Beer",    "category": "beverage", "available": True,  "qty": 45, "unit": "pints",    "threshold": 10},
        "House Wine":   {"name": "House Wine",    "category": "beverage", "available": True,  "qty": 10, "unit": "bottles",  "threshold": 3},
    },
}

# ---------------------------------------------------------------------------
# Waitlists per location
# ---------------------------------------------------------------------------
WAITLISTS = {
    "loc_downtown": [
        {"name": "Henderson", "party_size": 4, "joined_at": "18:45", "status": "waiting"},
        {"name": "Martinez",  "party_size": 2, "joined_at": "18:52", "status": "waiting"},
        {"name": "Kim",       "party_size": 6, "joined_at": "19:01", "status": "waiting"},
    ],
    "loc_bellevue": [
        {"name": "Patel", "party_size": 3, "joined_at": "19:10", "status": "waiting"},
    ],
    "loc_pike": [],
}

# ---------------------------------------------------------------------------
# Peak patterns per location  (slot = DayOfWeek_Hour)
# ---------------------------------------------------------------------------
PEAK_PATTERNS = {
    "loc_downtown": {
        "Friday_17":   {"slot": "Friday_17",   "p50": 10, "p90": 18, "sample_count": 42},
        "Friday_18":   {"slot": "Friday_18",   "p50": 20, "p90": 32, "sample_count": 78},
        "Friday_19":   {"slot": "Friday_19",   "p50": 28, "p90": 42, "sample_count": 91},
        "Friday_20":   {"slot": "Friday_20",   "p50": 22, "p90": 35, "sample_count": 85},
        "Saturday_18": {"slot": "Saturday_18", "p50": 25, "p90": 38, "sample_count": 65},
        "Saturday_19": {"slot": "Saturday_19", "p50": 32, "p90": 48, "sample_count": 72},
        "Sunday_12":   {"slot": "Sunday_12",   "p50": 35, "p90": 50, "sample_count": 55},
        "Monday_12":   {"slot": "Monday_12",   "p50": 8,  "p90": 14, "sample_count": 30},
    },
    "loc_bellevue": {
        "Friday_18":   {"slot": "Friday_18",   "p50": 15, "p90": 25, "sample_count": 40},
        "Friday_19":   {"slot": "Friday_19",   "p50": 20, "p90": 30, "sample_count": 55},
        "Saturday_19": {"slot": "Saturday_19", "p50": 22, "p90": 34, "sample_count": 48},
        "Sunday_12":   {"slot": "Sunday_12",   "p50": 18, "p90": 28, "sample_count": 35},
    },
    "loc_pike": {
        "Friday_12":   {"slot": "Friday_12",   "p50": 30, "p90": 45, "sample_count": 60},
        "Saturday_12": {"slot": "Saturday_12", "p50": 38, "p90": 55, "sample_count": 70},
        "Sunday_11":   {"slot": "Sunday_11",   "p50": 25, "p90": 40, "sample_count": 50},
    },
}

# ---------------------------------------------------------------------------
# Active orders
# ---------------------------------------------------------------------------
ORDERS = {
    "table_1": {
        "table_id": "table_1", "location_id": "loc_downtown", "status": "open",
        "items": [{"name": "Cheeseburger", "qty": 2, "price": 14.99}],
        "discount_pct": 0,
    },
    "table_7": {
        "table_id": "table_7", "location_id": "loc_downtown", "status": "open",
        "items": [{"name": "Salmon",   "qty": 1, "price": 28.00},
                  {"name": "Lemonade", "qty": 2, "price": 4.50}],
        "discount_pct": 0,
    },
}

# ---------------------------------------------------------------------------
# Menu items (top-level collection)
# ---------------------------------------------------------------------------
MENU_ITEMS = {
    "cheeseburger":  {"name": "Cheeseburger",  "category": "food",     "price": 14.99, "description": "Beef patty, cheddar, lettuce, tomato, brioche bun", "dietary_tags": [],                  "available": True},
    "salmon":        {"name": "Salmon",         "category": "food",     "price": 28.00, "description": "Pan-seared salmon, seasonal vegetables, lemon butter", "dietary_tags": ["gluten-free"],  "available": True},
    "halibut":       {"name": "Halibut",        "category": "food",     "price": 32.00, "description": "Grilled halibut, capers, cherry tomatoes, white wine sauce", "dietary_tags": ["gluten-free"], "available": True},
    "risotto":       {"name": "Risotto",        "category": "food",     "price": 22.00, "description": "Wild mushroom risotto, parmesan, truffle oil", "dietary_tags": ["vegetarian", "gluten-free"], "available": True},
    "caesar_salad":  {"name": "Caesar Salad",   "category": "food",     "price": 14.00, "description": "Romaine, croutons, parmesan, classic Caesar dressing", "dietary_tags": ["vegetarian"], "available": True},
    "lemonade":      {"name": "Lemonade",       "category": "beverage", "price":  4.50, "description": "Fresh-squeezed lemonade, cane sugar, mint",              "dietary_tags": ["vegan", "gluten-free"], "available": True},
    "draft_beer":    {"name": "Draft Beer",     "category": "beverage", "price":  7.00, "description": "Rotating local craft beer on tap",                       "dietary_tags": [],              "available": True},
    "house_wine":    {"name": "House Wine",     "category": "beverage", "price": 10.00, "description": "Glass of house red or white wine",                       "dietary_tags": ["vegan", "gluten-free"], "available": True},
    "oat_latte":     {"name": "Oat Milk Latte", "category": "beverage", "price":  5.50, "description": "Espresso with steamed oat milk, dairy-free",             "dietary_tags": ["vegan", "dairy-free", "gluten-free"], "available": False},
}

# ---------------------------------------------------------------------------
# Curated query example library — (question, correct plan) pairs
# These cover the trickiest structural patterns:
#   array_contains vs ==, subcollection routing, count queries,
#   location_id mapping, compound filters
# ---------------------------------------------------------------------------

QUERY_EXAMPLES = [
    {
        "question": "Which menu items are vegan?",
        "plan": {
            "type": "collection",
            "collection": "menu_items",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "dietary_tags", "op": "array_contains", "value": "vegan"}
            ],
            "order_by": "name",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "All vegan menu items sorted by name",
        },
    },
    {
        "question": "What gluten-free food options do you have?",
        "plan": {
            "type": "collection",
            "collection": "menu_items",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "dietary_tags", "op": "array_contains", "value": "gluten-free"},
                {"field": "category", "op": "==", "value": "food"},
            ],
            "order_by": "price",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "Gluten-free food items sorted by price",
        },
    },
    {
        "question": "Any dairy-free beverages on the menu?",
        "plan": {
            "type": "collection",
            "collection": "menu_items",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "dietary_tags", "op": "array_contains", "value": "dairy-free"},
                {"field": "category", "op": "==", "value": "beverage"},
            ],
            "order_by": "name",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "Dairy-free beverage items",
        },
    },
    {
        "question": "Which tables have a discount applied?",
        "plan": {
            "type": "collection",
            "collection": "orders",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "discount_pct", "op": ">", "value": 0}
            ],
            "order_by": "discount_pct",
            "direction": "desc",
            "limit": 50,
            "summary_hint": "Open orders with a discount sorted highest discount first",
        },
    },
    {
        "question": "Show me all open orders",
        "plan": {
            "type": "collection",
            "collection": "orders",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "status", "op": "==", "value": "open"}
            ],
            "order_by": None,
            "direction": "asc",
            "limit": 50,
            "summary_hint": "All currently open table orders",
        },
    },
    {
        "question": "What beverages are running low at downtown?",
        "plan": {
            "type": "subcollection",
            "collection": "locations",
            "parent_id": "loc_downtown",
            "sub_collection": "inventory",
            "filters": [
                {"field": "category", "op": "==", "value": "beverage"},
                {"field": "qty", "op": "<=", "value": 5},
            ],
            "order_by": "qty",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "Low-stock beverages at the downtown location",
        },
    },
    {
        "question": "Which items are 86'd at Bellevue?",
        "plan": {
            "type": "subcollection",
            "collection": "locations",
            "parent_id": "loc_bellevue",
            "sub_collection": "inventory",
            "filters": [
                {"field": "available", "op": "==", "value": False}
            ],
            "order_by": "name",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "Unavailable items at the Bellevue location",
        },
    },
    {
        "question": "Show all food items running low at Pike Place",
        "plan": {
            "type": "subcollection",
            "collection": "locations",
            "parent_id": "loc_pike",
            "sub_collection": "inventory",
            "filters": [
                {"field": "category", "op": "==", "value": "food"},
                {"field": "qty", "op": "<=", "value": 5},
            ],
            "order_by": "qty",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "Low-stock food items at Pike Place",
        },
    },
    {
        "question": "How many parties are currently waiting downtown?",
        "plan": {
            "type": "count",
            "collection": "locations",
            "parent_id": "loc_downtown",
            "sub_collection": "waitlists",
            "filters": [
                {"field": "status", "op": "==", "value": "waiting"}
            ],
            "order_by": None,
            "direction": "asc",
            "limit": 100,
            "summary_hint": "Count of waiting parties at downtown location",
        },
    },
    {
        "question": "Show me the waitlist at Bellevue",
        "plan": {
            "type": "subcollection",
            "collection": "locations",
            "parent_id": "loc_bellevue",
            "sub_collection": "waitlists",
            "filters": [
                {"field": "status", "op": "==", "value": "waiting"}
            ],
            "order_by": "joined_at",
            "direction": "asc",
            "limit": 50,
            "summary_hint": "Active waitlist at Bellevue sorted by join time",
        },
    },
    {
        "question": "List Friday peak slots where wait exceeds 25 minutes",
        "plan": {
            "type": "subcollection",
            "collection": "locations",
            "parent_id": "loc_downtown",
            "sub_collection": "peak_patterns",
            "filters": [
                {"field": "slot", "op": ">=", "value": "Friday_0"},
                {"field": "p50", "op": ">", "value": 25},
            ],
            "order_by": "p50",
            "direction": "desc",
            "limit": 20,
            "summary_hint": "Friday peak slots with median wait over 25 minutes",
        },
    },
    {
        "question": "Which time slots have the longest average wait at downtown?",
        "plan": {
            "type": "subcollection",
            "collection": "locations",
            "parent_id": "loc_downtown",
            "sub_collection": "peak_patterns",
            "filters": [],
            "order_by": "p50",
            "direction": "desc",
            "limit": 10,
            "summary_hint": "Top 10 peak slots by median wait at downtown",
        },
    },
    {
        "question": "Show me all large party seatings with over 5 guests",
        "plan": {
            "type": "collection",
            "collection": "turn_records",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "party_size", "op": ">", "value": 5}
            ],
            "order_by": "party_size",
            "direction": "desc",
            "limit": 50,
            "summary_hint": "Turn records for parties larger than 5 guests",
        },
    },
    {
        "question": "Which menu items are currently unavailable?",
        "plan": {
            "type": "collection",
            "collection": "menu_items",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "available", "op": "==", "value": False}
            ],
            "order_by": "name",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "Menu items that are currently not available",
        },
    },
    {
        "question": "What food items do we have under $20?",
        "plan": {
            "type": "collection",
            "collection": "menu_items",
            "parent_id": None,
            "sub_collection": None,
            "filters": [
                {"field": "category", "op": "==", "value": "food"},
                {"field": "price", "op": "<", "value": 20},
            ],
            "order_by": "price",
            "direction": "asc",
            "limit": 20,
            "summary_hint": "Food items priced under $20 sorted by price",
        },
    },
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------

def seed():
    print("Seeding Firestore...")

    print("  Writing location documents...")
    for loc_id, data in LOCATIONS.items():
        set_doc("locations", loc_id, data)

    print("  Writing inventory subcollections...")
    for loc_id, items in INVENTORY.items():
        for item_name, item_data in items.items():
            set_subcollection_doc("locations", loc_id, "inventory", item_name, item_data)

    print("  Writing waitlist subcollections...")
    for loc_id, parties in WAITLISTS.items():
        for i, party in enumerate(parties):
            set_subcollection_doc("locations", loc_id, "waitlists", f"party_{i+1}", party)

    print("  Writing peak pattern subcollections...")
    for loc_id, slots in PEAK_PATTERNS.items():
        for slot_key, slot_data in slots.items():
            set_subcollection_doc("locations", loc_id, "peak_patterns", slot_key, slot_data)

    print("  Writing orders collection...")
    for table_id, order in ORDERS.items():
        set_doc("orders", table_id, order)

    print("  Writing menu_items collection (with embeddings)...")
    for item_id, item in MENU_ITEMS.items():
        embed_input = build_menu_embed_text(item)
        print(f"    Embedding: {item['name']}...", end=" ", flush=True)
        embedding   = embed_text(embed_input)
        doc         = {**item, "embedding": Vector(embedding)}
        set_doc("menu_items", item_id, doc)
        print("done")

    print(f"  Writing query_examples collection ({len(QUERY_EXAMPLES)} curated examples)...")
    for ex in QUERY_EXAMPLES:
        print(f"    Embedding: {ex['question'][:55]}...", end=" ", flush=True)
        save_query_example(ex["question"], ex["plan"])
        print("done")

    print("Done! Firestore seeded successfully.")
    print("\nCollections written:")
    print("  locations/             (3 docs)")
    print("  locations/*/inventory  (9 items × 3 locations)")
    print("  locations/*/waitlists  (4 parties)")
    print("  locations/*/peak_patterns (14 slots)")
    print("  orders/                (2 open orders)")
    print("  menu_items/            (9 items, each with 768-dim embedding)")
    print("  query_examples/        ({} curated examples, each with embedding)".format(
        len(QUERY_EXAMPLES)))


if __name__ == "__main__":
    seed()
