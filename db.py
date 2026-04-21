"""
Firestore client, CRUD helpers, and vector search utilities.
All tools import from here — swap the implementation to change the backend.
"""
import logging
from datetime import datetime, date
from functools import lru_cache
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google import genai
from google.genai import types as genai_types

from config import (GCP_PROJECT_ID, EMBEDDING_MODEL, MENU_EMBED_FIELD,
                     FIRESTORE_DATABASE, COL_USER_CONTEXTS, COL_CONV_LOGS)

log = logging.getLogger("restaurant_agent.db")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _sanitize_value(v):
    """Recursively convert Firestore-specific types to JSON-safe primitives."""
    if isinstance(v, Vector):
        return None  # sentinel; dropped by _sanitize_doc
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(i) for i in v]
    return v


def _sanitize_doc(doc):
    """Return a copy of a Firestore doc with all non-JSON types converted.
    Vector (embedding) fields are dropped entirely.
    """
    return {k: _sanitize_value(v) for k, v in doc.items() if not isinstance(v, Vector)}



# ---------------------------------------------------------------------------
# Clients  (created once, reused)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def fs() -> firestore.Client:
    """Return a cached Firestore client."""
    return firestore.Client(
        project=GCP_PROJECT_ID or None,
        database=FIRESTORE_DATABASE or None,
    )


@lru_cache(maxsize=1)
def _genai_client() -> genai.Client:
    """Return a cached Gemini client used for embeddings via Vertex AI."""
    return genai.Client(
        vertexai=True,
        project=GCP_PROJECT_ID or None,
        location="us-central1",
    )


# ---------------------------------------------------------------------------
# Filter normalization helper
# ---------------------------------------------------------------------------

def _normalize_filter(f: Any) -> tuple[str, str, Any]:
    """
    Accept either:
      - {"field": "...", "op": "...", "value": ...}
      - ("field", "op", value)
      - ["field", "op", value]

    Returns:
        (field, op, value)
    """
    if isinstance(f, dict):
        return f["field"], f["op"], f["value"]

    if isinstance(f, (list, tuple)) and len(f) == 3:
        return f[0], f[1], f[2]

    raise ValueError(f"Invalid filter format: {f!r}")


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    """
    Embed a string using the configured embedding model.
    Returns a float list suitable for storing in Firestore and querying with
    find_nearest().

    Args:
        text: The text to embed (menu description, search query, etc.)
    """
    result = _genai_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
    )
    return result.embeddings[0].values


def build_menu_embed_text(item: dict) -> str:
    """
    Build the text that gets embedded for a menu item.
    Combines name, description, category, and dietary tags for rich semantic matching.

    Args:
        item: Menu item dict with keys: name, description, category, dietary_tags.
    """
    tags = ", ".join(item.get("dietary_tags", [])) or "none"
    return (
        f"{item['name']}. "
        f"{item.get('description', '')}. "
        f"Category: {item.get('category', '')}. "
        f"Dietary: {tags}."
    )


# ---------------------------------------------------------------------------
# Vector search helper
# ---------------------------------------------------------------------------

def vector_search(
    collection: str,
    query_text: str,
    vector_field: str = MENU_EMBED_FIELD,
    limit: int = 5,
    distance_measure: DistanceMeasure = DistanceMeasure.COSINE,
    pre_filters: list[Any] | None = None,
) -> list[dict]:
    """
    Embed query_text and run a Firestore find_nearest() vector search.

    Args:
        collection:       Top-level Firestore collection name.
        query_text:       The natural language search query to embed.
        vector_field:     Field in each document that holds the embedding vector.
        limit:            Maximum number of results to return.
        distance_measure: COSINE (default) | EUCLIDEAN | DOT_PRODUCT
        pre_filters:      Optional list of filters applied before vector search.
                          Supports either:
                            - {"field": "...", "op": "...", "value": ...}
                            - (field, op, value)

    Returns:
        List of matching document dicts, each with '_id' and '_distance' fields.
        Lower distance = closer match (for COSINE/EUCLIDEAN).
        Sorted closest-first.
    """
    query_vec = embed_text(query_text)

    col_ref: Any = fs().collection(collection)

    for f in (pre_filters or []):
        field, op, value = _normalize_filter(f)
        col_ref = col_ref.where(filter=FieldFilter(field, op, value))

    vq = col_ref.find_nearest(
        vector_field=vector_field,
        query_vector=Vector(query_vec),
        distance_measure=distance_measure,
        limit=limit,
        distance_result_field="_distance",
    )

    results = []
    for snap in vq.stream():
        doc = _sanitize_doc(snap.to_dict())
        doc["_id"] = snap.id
        doc.pop(MENU_EMBED_FIELD, None)
        results.append(doc)

    results.sort(key=lambda d: d.get("_distance", 1.0))
    return results


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------

def get_doc(collection: str, doc_id: str) -> dict | None:
    """Fetch a single document. Returns None if not found."""
    ref = fs().collection(collection).document(doc_id)
    snap = ref.get()
    return _sanitize_doc(snap.to_dict()) if snap.exists else None


def set_doc(collection: str, doc_id: str, data: dict) -> None:
    """Create or fully overwrite a document."""
    fs().collection(collection).document(doc_id).set(data)


def update_doc(collection: str, doc_id: str, data: dict) -> None:
    """Merge-update a document (only provided fields are changed)."""
    fs().collection(collection).document(doc_id).set(data, merge=True)


def delete_doc(collection: str, doc_id: str) -> None:
    """Delete a document."""
    fs().collection(collection).document(doc_id).delete()


def get_subcollection_doc(
    parent_col: str,
    parent_id: str,
    sub_col: str,
    doc_id: str,
) -> dict | None:
    """Fetch a document from a subcollection."""
    ref = (
        fs().collection(parent_col)
        .document(parent_id)
        .collection(sub_col)
        .document(doc_id)
    )
    snap = ref.get()
    return _sanitize_doc(snap.to_dict()) if snap.exists else None


def set_subcollection_doc(
    parent_col: str,
    parent_id: str,
    sub_col: str,
    doc_id: str,
    data: dict,
) -> None:
    """Create or overwrite a subcollection document."""
    (
        fs().collection(parent_col)
        .document(parent_id)
        .collection(sub_col)
        .document(doc_id)
        .set(data)
    )


def update_subcollection_doc(
    parent_col: str,
    parent_id: str,
    sub_col: str,
    doc_id: str,
    data: dict,
) -> None:
    """Merge-update a subcollection document."""
    (
        fs().collection(parent_col)
        .document(parent_id)
        .collection(sub_col)
        .document(doc_id)
        .set(data, merge=True)
    )


def list_subcollection(parent_col: str, parent_id: str, sub_col: str) -> list[dict]:
    """Return all documents from a subcollection as a list of dicts."""
    ref = fs().collection(parent_col).document(parent_id).collection(sub_col)
    return [_sanitize_doc({"_id": s.id, **s.to_dict()}) for s in ref.stream()]


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def query_collection(
    collection: str,
    filters: list[Any] | None = None,
    order_by: str | None = None,
    direction: str = "asc",
    limit: int = 50,
) -> list[dict]:
    """
    Query a top-level collection with optional filters, ordering, and limit.

    filters supports:
      - {"field": "...", "op": "...", "value": ...}
      - (field, op, value)

    Operators: ==  !=  <  <=  >  >=  in  array_contains

    Returns a list of dicts, each including '_id' (document ID).
    """
    ref: Any = fs().collection(collection)

    for f in (filters or []):
        field, op, value = _normalize_filter(f)
        ref = ref.where(filter=FieldFilter(field, op, value))

    if order_by:
        dir_enum = (
            firestore.Query.ASCENDING
            if direction.lower() == "asc"
            else firestore.Query.DESCENDING
        )
        ref = ref.order_by(order_by, direction=dir_enum)

    ref = ref.limit(limit)
    return [_sanitize_doc({"_id": s.id, **s.to_dict()}) for s in ref.stream()]


def query_subcollection(
    parent_col: str,
    parent_id: str,
    sub_col: str,
    filters: list[Any] | None = None,
    order_by: str | None = None,
    direction: str = "asc",
    limit: int = 50,
) -> list[dict]:
    """Same as query_collection but targets a subcollection."""
    ref: Any = (
        fs().collection(parent_col)
        .document(parent_id)
        .collection(sub_col)
    )

    for f in (filters or []):
        field, op, value = _normalize_filter(f)
        ref = ref.where(filter=FieldFilter(field, op, value))

    if order_by:
        dir_enum = (
            firestore.Query.ASCENDING
            if direction.lower() == "asc"
            else firestore.Query.DESCENDING
        )
        ref = ref.order_by(order_by, direction=dir_enum)

    ref = ref.limit(limit)
    return [_sanitize_doc({"_id": s.id, **s.to_dict()}) for s in ref.stream()]


def add_to_subcollection(
    parent_col: str,
    parent_id: str,
    sub_col: str,
    data: dict,
) -> str:
    """Add a new document with auto-generated ID to a subcollection. Returns doc ID."""
    ref = (
        fs().collection(parent_col)
        .document(parent_id)
        .collection(sub_col)
        .document()
    )
    ref.set(data)
    return ref.id


def collection_count(collection: str, filters: list[Any] | None = None) -> int:
    """Return the count of documents matching the filters."""
    ref: Any = fs().collection(collection)

    for f in (filters or []):
        field, op, value = _normalize_filter(f)
        ref = ref.where(filter=FieldFilter(field, op, value))

    agg = ref.count()
    result = agg.get()
    return result[0][0].value


# ---------------------------------------------------------------------------
# Query example helpers  (few-shot retrieval store)
# ---------------------------------------------------------------------------

def save_query_example(question: str, plan: dict) -> str:
    """
    Embed a (question, plan) pair and save it to the query_examples collection.
    Called automatically after every successful natural_language_query so the
    library grows over time without manual curation.

    Args:
        question: The original natural language question.
        plan:     The validated Firestore query plan dict that produced good results.

    Returns:
        The auto-generated Firestore document ID.
    """
    from config import COL_QUERY_EXAMPLES

    embedding = embed_text(question)
    ref = fs().collection(COL_QUERY_EXAMPLES).document()
    ref.set({
        "question": question,
        "plan": plan,
        "embedding": Vector(embedding),
    })
    return ref.id


def retrieve_similar_examples(question: str, limit: int = 3) -> list[dict]:
    """
    Find the closest stored (question, plan) examples to the incoming question.
    Returns a list of dicts with 'question' and 'plan' keys, sorted closest-first.

    Args:
        question: The incoming natural language question to find examples for.
        limit:    Maximum number of examples to return (default 3).
    """
    from config import COL_QUERY_EXAMPLES

    try:
        results = vector_search(
            collection=COL_QUERY_EXAMPLES,
            query_text=question,
            limit=limit,
        )
        return [
            {"question": r["question"], "plan": r["plan"]}
            for r in results
            if "question" in r and "plan" in r
        ]
    except Exception:
        # If the collection is empty or index not ready, return nothing gracefully
        return []

# ---------------------------------------------------------------------------
# User context helpers  (cross-session long-term memory)
# ---------------------------------------------------------------------------

def get_user_context(user_id: str) -> dict:
    """Fetch the persisted context for a user (last location, table, session).

    Returns an empty dict if no context has been saved yet.

    Args:
        user_id: The stable user identifier from the frontend.
    """
    return get_doc(COL_USER_CONTEXTS, user_id) or {}


def save_user_context(user_id: str, context: dict) -> None:
    """Merge-update the persisted context for a user.

    Called after every chat turn so the next session can resume with the
    user's last known location, active table, and session ID.

    Args:
        user_id: The stable user identifier.
        context: Dict of fields to persist (last_location, last_active_table, etc.)
    """
    update_doc(COL_USER_CONTEXTS, user_id, context)


# ---------------------------------------------------------------------------
# Conversation audit trail
# ---------------------------------------------------------------------------

def log_conversation_turn(
    session_id: str,
    user_id: str,
    message: str,
    response: str,
    agent_used: str,
) -> None:
    """Append a single conversation turn to the audit log in Firestore.

    Stored under: conversation_logs/{session_id}/turns/{auto_id}

    Args:
        session_id: The ADK session ID for this conversation.
        user_id:    The stable user identifier.
        message:    The user's message text.
        response:   The agent's response text.
        agent_used: Name of the agent that produced the response.
    """
    add_to_subcollection(
        COL_CONV_LOGS,
        session_id,
        "turns",
        {
            "user_id":    user_id,
            "message":    message,
            "response":   response,
            "agent_used": agent_used,
            "timestamp":  datetime.utcnow().isoformat(),
        },
    )