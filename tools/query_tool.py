"""
Natural language → Firestore query tool with few-shot retrieval.

Flow per query:
  1. Embed the question and retrieve the 3 closest stored (question, plan) examples
  2. Inject those examples into the Gemini prompt alongside the schema
  3. Gemini produces a structurally accurate JSON query plan
  4. Execute the plan against Firestore
  5. On success, save the (question, plan) pair back to the example store
     so the library improves automatically over time
"""
import json
import logging
from google import genai
from google.genai import types as genai_types

from db import (query_collection, query_subcollection, collection_count,
                save_query_example, retrieve_similar_examples)
from config import GOOGLE_API_KEY, ADK_MODEL, SCHEMA_DESCRIPTION, COL_LOCATIONS

log = logging.getLogger("restaurant_agent.query_tool")

_client = genai.Client(api_key=GOOGLE_API_KEY)

# ---------------------------------------------------------------------------
# Base system prompt — schema only, examples injected dynamically
# ---------------------------------------------------------------------------

_BASE_SYSTEM = f"""You are a Firestore query planner for a restaurant operations system.

Given a natural language question, output ONLY a valid JSON object — no markdown,
no explanation — with this exact structure:

{{
  "type": "collection" | "subcollection" | "count",
  "collection": "<top-level collection name>",
  "parent_id": "<location_id if subcollection, else null>",
  "sub_collection": "<subcollection name if type=subcollection, else null>",
  "filters": [ ["<field>", "<operator>", <value>] ],
  "order_by": "<field or null>",
  "direction": "asc" | "desc",
  "limit": <integer 1-100>,
  "summary_hint": "<one sentence describing what this query returns>"
}}

Operators: == != < <= > >= in array_contains
Values must be JSON-compatible (string, number, boolean, list).

Schema reference:
{SCHEMA_DESCRIPTION}

Critical rules:
- For dietary tag queries ALWAYS use array_contains, never ==
- For inventory/waitlists/peak_patterns/daily_revenue always use type=subcollection
- For orders/menu_items/turn_records use type=collection
- location_id values are: loc_downtown, loc_bellevue, loc_pike
  (map "downtown"->loc_downtown, "bellevue"->loc_bellevue, "pike place"->loc_pike)
- If the question asks "how many", use type=count
- Default location_id is loc_downtown when not specified
"""


def _build_system_prompt(examples: list[dict]) -> str:
    """Inject retrieved few-shot examples into the system prompt."""
    if not examples:
        return _BASE_SYSTEM
    shots = "\n\nFew-shot examples (closest matches to this question — use as structural anchors):\n"
    for i, ex in enumerate(examples, 1):
        shots += f"\nExample {i}:\n"
        shots += f"  Q: {ex['question']}\n"
        shots += f"  Plan: {json.dumps(ex['plan'], separators=(',', ':'))}\n"
    return _BASE_SYSTEM + shots


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def natural_language_query(question: str,
                            location_id: str = "loc_downtown") -> dict:
    """Answer a custom analytics or lookup question by auto-generating and executing a Firestore query.

    Uses few-shot retrieval: before calling Gemini, the closest stored example
    question-plan pairs are retrieved and injected as anchors, producing more
    accurate filters for edge cases (array_contains, subcollections, counts, etc.).
    Successful plans are saved back automatically so the library improves over time.

    Use this for open-ended questions such as:
    - "Which tables have a discount applied?"
    - "Show me all low-stock beverages at Bellevue"
    - "List all Friday peak slots where the wait exceeds 25 minutes"
    - "How many parties are currently on the downtown waitlist?"
    - "Which menu items are vegan and gluten-free?"

    Args:
        question:    The natural language question to answer.
        location_id: Default location for subcollection queries when not
                     specified in the question.
    """
    # ── Step 1: retrieve nearest examples ────────────────────────────────────
    examples = retrieve_similar_examples(question, limit=3)
    log.info("Retrieved %d few-shot examples for: '%s'", len(examples), question[:60])

    # ── Step 2: call Gemini with examples in the prompt ───────────────────────
    system_prompt = _build_system_prompt(examples)
    user_prompt   = f"Question: {question}\nDefault location_id: {location_id}"

    try:
        response = _client.models.generate_content(
            model=ADK_MODEL,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0,
                max_output_tokens=512,
            ),
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan = json.loads(raw)
    except Exception as exc:
        log.exception("Query plan generation failed: %s", exc)
        return {
            "success": False,
            "error": f"Could not generate query plan: {exc}",
            "question": question,
            "examples_used": len(examples),
        }

    log.info("Query plan: %s", plan)

    # ── Step 3: execute plan ──────────────────────────────────────────────────
    col        = plan.get("collection", "")
    sub_col    = plan.get("sub_collection")
    parent_id  = plan.get("parent_id") or location_id
    filters    = [tuple(f) for f in plan.get("filters", [])]
    order_by   = plan.get("order_by")
    direction  = plan.get("direction", "asc")
    limit      = int(plan.get("limit", 20))
    query_type = plan.get("type", "collection")

    try:
        if query_type == "count":
            count   = collection_count(col, filters)
            results = [{"count": count}]
        elif query_type == "subcollection" and sub_col:
            results = query_subcollection(
                COL_LOCATIONS if col == "locations" else col,
                parent_id, sub_col,
                filters=filters, order_by=order_by,
                direction=direction, limit=limit,
            )
        else:
            results = query_collection(
                col, filters=filters, order_by=order_by,
                direction=direction, limit=limit,
            )
    except Exception as exc:
        log.exception("Firestore execution failed: %s", exc)
        return {
            "success": False,
            "error": f"Query execution failed: {exc}",
            "plan": plan,
            "question": question,
            "examples_used": len(examples),
        }

    # ── Step 4: save successful plan for future retrieval ────────────────────
    try:
        save_query_example(question, plan)
    except Exception as exc:
        log.warning("Could not save query example (non-fatal): %s", exc)

    return {
        "success":      True,
        "question":     question,
        "plan":         plan,
        "summary_hint": plan.get("summary_hint", ""),
        "result_count": len(results),
        "results":      results,
        "examples_used": len(examples),
    }
