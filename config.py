import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ADK_MODEL      = os.getenv("ADK_MODEL", "gemini-2.5-flash")
APP_NAME       = os.getenv("APP_NAME", "restaurant_agent")
PORT           = int(os.getenv("PORT", "8020"))
SESSION_DB_URL = os.getenv("SESSION_DB_URL", "sqlite+aiosqlite:///./restaurant_sessions.db")
GCP_PROJECT_ID   = os.getenv("GCP_PROJECT_ID", ".....")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "....")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
VECTOR_DIMS      = 768   # text-embedding-004 output dimensions
MENU_EMBED_FIELD = "embedding"   # field name stored in each menu_items doc


# ---------------------------------------------------------------------------
# Firestore collection names
# ---------------------------------------------------------------------------
COL_LOCATIONS      = "locations"
COL_ORDERS         = "orders"
COL_MENU           = "menu_items"
COL_TURN_RECORDS   = "turn_records"
COL_QUERY_EXAMPLES   = "query_examples"    # few-shot retrieval store
COL_USER_CONTEXTS    = "user_contexts"     # cross-session user memory
COL_CONV_LOGS        = "conversation_logs" # per-session audit trail

# Subcollection names  (under locations/{location_id}/)
SUB_INVENTORY = "inventory"
SUB_WAITLISTS = "waitlists"
SUB_PEAK      = "peak_patterns"
SUB_REVENUE   = "daily_revenue"

# ---------------------------------------------------------------------------
# Firestore schema reference  — used by the NL query generator as context
# ---------------------------------------------------------------------------
SCHEMA_DESCRIPTION = """
Firestore collections and their document fields:

COLLECTION: orders
  Fields: table_id (str), location_id (str), items (list of {name,qty,price}),
          discount_pct (float), status (str: open|closed), created_at (timestamp)

COLLECTION: menu_items
  Fields: name (str), category (str: food|beverage), price (float),
          description (str), dietary_tags (list of str), available (bool)

COLLECTION: turn_records
  Fields: location_id (str), table_id (str), party_size (int),
          actual_wait_mins (int), queue_depth_at_join (int),
          day_of_week (str), hour (int), timestamp (timestamp)

SUBCOLLECTION: locations/{location_id}/inventory
  Fields: name (str), category (str: food|beverage), available (bool),
          qty (int), unit (str), threshold (int)

SUBCOLLECTION: locations/{location_id}/waitlists
  Fields: name (str), party_size (int), joined_at (str HH:MM), status (str)

SUBCOLLECTION: locations/{location_id}/peak_patterns
  Fields: slot (str e.g. Friday_19), p50 (int), p90 (int), sample_count (int)

SUBCOLLECTION: locations/{location_id}/daily_revenue
  Fields: date (str YYYY-MM-DD), total_usd (float), covers (int)

TOP-LEVEL DOCUMENT: locations/{location_id}
  Fields: id (str), name (str), address (str), phone (str),
          hours_open (str HH:MM), hours_close (str HH:MM),
          seating_capacity (int), outdoor_seating (bool)

Known location IDs: loc_downtown, loc_bellevue, loc_pike
"""