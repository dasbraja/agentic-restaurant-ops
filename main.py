"""
Restaurant Agent API
--------------------
POST  /api/chat           — send a message, get a response
GET   /api/sessions/{id}  — inspect session state
DELETE /api/sessions/{id} — clear a session
GET   /health             — healthcheck
"""
import os
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from config import APP_NAME, ADK_MODEL, GCP_PROJECT_ID, FIRESTORE_DATABASE, SESSION_DB_URL
from models import ChatRequest, ChatResponse, SessionStateResponse, HealthResponse
from agents import restaurant_orchestrator
from db import get_user_context, save_user_context, log_conversation_turn

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("restaurant_agent")

_DB_URL = SESSION_DB_URL

# ---------------------------------------------------------------------------
# session_service and runner are created inside lifespan so they bind to
# the correct asyncio event loop that uvicorn/FastAPI is running on.
# Creating asyncpg (or aiosqlite) connection pools at module level causes
# "Future attached to a different loop" errors.
# ---------------------------------------------------------------------------
session_service: DatabaseSessionService | None = None
runner: Runner | None = None


# ---------------------------------------------------------------------------
# Background session cleanup
# ---------------------------------------------------------------------------
async def _cleanup_sessions():
    """Periodically delete sessions idle for more than 8 hours."""
    while True:
        await asyncio.sleep(3600)
        try:
            # DatabaseSessionService does not expose a bulk-delete API,
            # so we reach into the underlying SQLAlchemy engine directly.
            from sqlalchemy import text
            cutoff = (datetime.utcnow() - timedelta(hours=8)).isoformat()
            async with session_service.engine.begin() as conn:
                result = await conn.execute(
                    text(
                        "DELETE FROM sessions "
                        "WHERE app_name = :app AND update_time < :cutoff"
                    ),
                    {"app": APP_NAME, "cutoff": cutoff},
                )
                if result.rowcount:
                    log.info("Session cleanup: deleted %d stale sessions", result.rowcount)
        except Exception as exc:
            log.warning("Session cleanup error (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# FastAPI lifespan — initialise services here so they share the event loop
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global session_service, runner

    log.info("Restaurant Agent API starting — model: %s  db: %s", ADK_MODEL, _DB_URL)

    # Initialise inside the running event loop
    session_service = DatabaseSessionService(db_url=_DB_URL)
    runner = Runner(
        agent=restaurant_orchestrator,
        app_name=APP_NAME,
        session_service=session_service,
    )

    cleanup_task = asyncio.create_task(_cleanup_sessions())
    yield
    cleanup_task.cancel()
    log.info("Restaurant Agent API shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Restaurant Agent API",
    description="Multi-agent restaurant operations system built on Google ADK.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse(status="ok", model=ADK_MODEL, app=APP_NAME)


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(req: ChatRequest):
    """
    Send a message to the restaurant agent.

    - Provide **session_id** to continue an existing conversation.
    - Omit **session_id** (or pass null) to start a new one.
    - The returned **session_id** must be sent back on subsequent turns.
    """
    user_id    = req.user_id or "guest"
    session_id = req.session_id or str(uuid.uuid4())

    existing = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if existing is None:
        prior_context = get_user_context(user_id)
        initial_state = {}
        if prior_context:
            initial_state["prior_context"]   = prior_context
            initial_state["active_location"] = prior_context.get("last_location", "loc_downtown")
            initial_state["active_table"]    = prior_context.get("last_active_table")
            log.info("Injected prior context for user %s: location=%s table=%s",
                     user_id,
                     initial_state.get("active_location"),
                     initial_state.get("active_table"))

        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state=initial_state,
        )
        log.info("New session created: %s (user: %s)", session_id, user_id)

    content = types.Content(
        role="user",
        parts=[types.Part(text=req.message)],
    )

    final_text = ""
    agent_name = "restaurant_orchestrator"
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_text = event.content.parts[0].text or ""
                if hasattr(event, "author") and event.author:
                    agent_name = event.author
                break
    except Exception as exc:
        log.exception("Agent runner error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    if not final_text:
        final_text = "I'm sorry, I couldn't generate a response. Please try again."

    log.info("session=%s  agent=%s  user=%s  q=%s",
             session_id, agent_name, user_id, req.message[:60])

    # Persist updated user context
    try:
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        state = dict(session.state) if session else {}
        save_user_context(user_id, {
            "last_session_id":   session_id,
            "last_active_table": state.get("active_table"),
            "last_location":     state.get("active_location", "loc_downtown"),
            "last_seen":         datetime.utcnow().isoformat(),
        })
    except Exception as exc:
        log.warning("Could not save user context (non-fatal): %s", exc)

    # Audit trail
    try:
        log_conversation_turn(session_id, user_id, req.message, final_text, agent_name)
    except Exception as exc:
        log.warning("Could not log conversation turn (non-fatal): %s", exc)

    return ChatResponse(
        response=final_text,
        session_id=session_id,
        user_id=user_id,
        agent_used=agent_name,
    )


@app.get("/api/sessions/{session_id}", response_model=SessionStateResponse, tags=["sessions"])
async def get_session(session_id: str, user_id: str = "guest"):
    """Inspect the current state dictionary of a session."""
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return SessionStateResponse(session_id=session_id, state=dict(session.state))


@app.delete("/api/sessions/{session_id}", tags=["sessions"])
async def delete_session(session_id: str, user_id: str = "guest"):
    """Clear a session."""
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    await session_service.delete_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    return {"deleted": True, "session_id": session_id}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    from config import PORT
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)