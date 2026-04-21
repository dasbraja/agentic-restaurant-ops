from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message text.")
    session_id: Optional[str] = Field(
        None,
        description="Conversation session ID. Omit to start a new conversation; "
                    "include in subsequent turns to continue the same session.",
    )
    user_id: Optional[str] = Field(
        "guest",
        description="Optional user identifier for tracking purposes.",
    )


class ChatResponse(BaseModel):
    response: str    = Field(..., description="The agent's reply.")
    session_id: str  = Field(..., description="Session ID to include in the next turn.")
    user_id: str     = Field(..., description="User ID echo.")
    agent_used: str  = Field(..., description="Name of the agent that produced the final answer.")


class SessionStateResponse(BaseModel):
    session_id: str
    state: dict


class HealthResponse(BaseModel):
    status: str
    model: str
    app: str
