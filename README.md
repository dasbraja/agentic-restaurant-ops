# Restaurant Agent

A multi-agent restaurant operations system built on [Google ADK](https://google.github.io/adk-docs/) and [Firestore](https://firebase.google.com/docs/firestore). A single conversational API endpoint routes staff and customer questions to the right specialist agent — orders, wait times, inventory, or store locations — and supports open-ended analytics queries by auto-generating Firestore queries from plain English using Gemini.

---

## Architecture

### System overview

<!-- Diagram 1: Full stack -->
<p align="center">
<img src="docs/architecture.svg" alt="System architecture" width="100%"/>
</p>

---

### Memory layers

<!-- Diagram 2: Memory architecture -->
<p align="center">
<img src="docs/memory-layers.svg" alt="Memory layers" width="100%"/>
</p>

Every user gets a persistent identity and context that survives server restarts and new sessions.

| Firestore collection | Purpose |
|---|---|
| `user_contexts` | Stores `last_location`, `last_active_table`, `last_seen` per user |
| `conversation_logs/{session_id}/turns` | Full audit trail of every message and agent response |

On every new session, `main.py` fetches the user's prior context from Firestore and seeds `session.state` with their last known location and table — so agents can pick up where they left off without asking again.

#### Session state keys (shared across all agents)

| Key | Set by | Purpose |
|---|---|---|
| `active_location` | Any tool call with `location_id` | Default location for the current session |
| `active_table` | POS tool calls with `table_id` | Active table being worked on |
| `prior_context` | `main.py` on session create | User's context from their previous session |


---

### What changes between domains

<!-- Diagram 3: Declarative config generalisation -->
<p align="center">
<img src="docs/domain-config.svg" alt="Domain portability" width="100%"/>
</p>
---

## Project structure

```
restaurant_agent/
├── main.py                 FastAPI app — /api/chat, session management, lifespan
├── agents.py               Declarative agent factory — reads agents_config.json
├── agents_config.json      ★ All agent definitions — edit this to change agent behaviour
├── config.py               Env settings + all Firestore collection name constants
├── db.py                   Firestore client, CRUD helpers, vector search, audit helpers
├── seed_firestore.py       One-time seed script — populates all collections
├── models.py               Pydantic request/response schemas
├── tools/
│   ├── pos_tools.py        Order, payment, and revenue tools
│   ├── queue_tools.py      Wait time, peak-hour blend, and waitlist tools
│   ├── inventory_tools.py  Food and beverage availability + semantic search tools
│   ├── location_tools.py   Store finder, hours, and capacity tools
│   ├── query_tool.py       natural_language_query — Gemini → JSON plan → Firestore
│   └── __init__.py
├── restaurant-chat-app/    React + MUI chat frontend (Vite)
│   ├── src/
│   │   ├── App.jsx         Full chat UI with session management
│   │   ├── theme.js        MUI dark theme (amber/charcoal palette)
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the React chat UI)
- A [Google AI Studio API key](https://aistudio.google.com/apikey)
- A [Google Cloud project](https://console.cloud.google.com) with:
  - **Firestore** enabled in Native mode
  - A service account with the **Cloud Datastore User** IAM role
  - Service account JSON key downloaded locally

### 1 — Install Python dependencies

```bash
cd restaurant_agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Gemini API key — https://aistudio.google.com/apikey
GOOGLE_API_KEY=your_gemini_api_key_here

ADK_MODEL=gemini-2.5-flash
APP_NAME=restaurant_agent
PORT=8020

# Google Cloud — for Firestore
GCP_PROJECT_ID=your_gcp_project_id_here
FIRESTORE_DATABASE=your_firestore_database_id

# Service account (local dev only — use Workload Identity on Cloud Run/GKE)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Session storage — SQLite (default, no setup) or Postgres
SESSION_DB_URL=sqlite+aiosqlite:///./restaurant_sessions.db
# SESSION_DB_URL=postgresql+asyncpg://user:pass@localhost/restaurant_sessions
```

### 3 — Create Firestore vector indexes

Two composite indexes are required for vector search. Run both commands once and wait 5–10 minutes for them to build.

**`menu_items` — semantic menu search**
```bash
gcloud firestore indexes composite create \
  --project=YOUR_PROJECT_ID \
  --database="YOUR_DATABASE_ID" \
  --collection-group=menu_items \
  --query-scope=COLLECTION \
  --field-config=order=ASCENDING,field-path=available \
  --field-config='vector-config={"dimension":"768","flat": "{}"},field-path=embedding'
```

**`query_examples` — few-shot retrieval for the NL query engine**
```bash
gcloud firestore indexes composite create \
  --project=YOUR_PROJECT_ID \
  --database="YOUR_DATABASE_ID" \
  --collection-group=query_examples \
  --query-scope=COLLECTION \
  --field-config='vector-config={"dimension":"768","flat": "{}"},field-path=embedding'
```

> Track build progress at: https://console.firebase.google.com/project/YOUR_PROJECT_ID/firestore/indexes

### 4 — Seed Firestore

Run once to populate all collections and subcollections:

```bash
python seed_firestore.py
```

### 5 — Start the API server

```bash
python main.py
# API at http://localhost:8020
# Swagger docs at http://localhost:8020/docs
```

### 6 — Start the React chat UI

```bash
cd restaurant-chat-app
npm install
npm run dev   # → http://localhost:5173
```

---

## Session persistence

Sessions are stored in a SQL database via `DatabaseSessionService` (SQLAlchemy async).

| Backend | URL format | When to use |
|---|---|---|
| **SQLite** (default) | `sqlite+aiosqlite:///./restaurant_sessions.db` | Local dev — zero setup, file created automatically |
| **PostgreSQL** | `postgresql+asyncpg://user:pass@host/db` | Production / multi-worker deployments |

To use Postgres locally:

```bash
# Install
brew install postgresql@16
brew services start postgresql@16

# Create DB
psql postgres -c "CREATE USER restaurant_user WITH PASSWORD 'yourpass';"
psql postgres -c "CREATE DATABASE restaurant_sessions OWNER restaurant_user;"

# Install async driver
pip install asyncpg

# Set in .env
SESSION_DB_URL=postgresql+asyncpg://restaurant_user:yourpass@localhost/restaurant_sessions
```

---

## Agents config

All agent behaviour is defined in `agents_config.json`. The Python factory in `agents.py` reads this file at startup and wires everything together.

**To tune an agent's behaviour** — edit its `instruction` field in the JSON and restart.

**To add a new agent:**
1. Implement tools in `tools/`, add to `tools/__init__.py`
2. Register tool names in `TOOL_REGISTRY` in `agents.py`
3. Add an entry to `agents_config.json`
4. Add the agent name to the orchestrator's `sub_agents` list
5. Restart — done

**To swap the model** for all agents, change `default_model` at the top of the JSON. To use a different model for one specific agent, add a `"model"` field to that agent's entry.

---

## Natural language query engine

`natural_language_query(question)` lets the orchestrator answer any open-ended analytics question.

**Flow:**
1. Embed the question and retrieve the 3 closest stored example question→plan pairs (few-shot)
2. Send to Gemini with the full Firestore schema — returns a structured JSON query plan
3. Execute the plan against Firestore
4. Save the successful plan back to `query_examples` (library grows automatically)

**Example questions:**

| Question | Firestore target |
|---|---|
| "Which tables have a discount applied?" | `orders` where `discount_pct > 0` |
| "Show all vegan menu items" | `menu_items` where `dietary_tags array_contains vegan` |
| "List Friday peak slots over 25 min wait" | `peak_patterns` where `p50 > 25` |
| "How many parties are on the downtown waitlist?" | count on `waitlists` where `status == waiting` |
| "Which beverages are low stock at Bellevue?" | `inventory` where `category == beverage AND qty <= 5` |

---

## Firestore data model

```
locations/{location_id}                     store metadata
locations/{location_id}/inventory/          stock items
locations/{location_id}/waitlists/          waiting parties
locations/{location_id}/peak_patterns/      historical wait slots
locations/{location_id}/daily_revenue/      revenue by date

orders/{table_id}                           active and closed orders
menu_items/{item_id}                        menu with embeddings + dietary tags
turn_records/{auto_id}                      completed seatings for analytics
query_examples/{auto_id}                    few-shot NL query plans

user_contexts/{user_id}                     cross-session user memory
conversation_logs/{session_id}/turns/       per-session audit trail
```

Location IDs: `loc_downtown` · `loc_bellevue` · `loc_pike`

---

## API reference

### `POST /api/chat`

```json
{ "message": "How long is the wait downtown?", "user_id": "staff_01" }
```

Include `session_id` on subsequent turns to maintain conversation context.

**Response:**
```json
{
  "response": "Current wait at downtown is approximately 15 minutes...",
  "session_id": "f3a8c2d1-...",
  "user_id": "staff_01",
  "agent_used": "customer_experience_agent"
}
```

### `GET /api/sessions/{session_id}?user_id=...`

Inspect `session.state` — useful for debugging agent state sharing.

### `DELETE /api/sessions/{session_id}?user_id=...`

Clear a session. Next message with this ID starts fresh.

### `GET /health`

```json
{ "status": "ok", "model": "gemini-2.5-flash", "app": "restaurant_agent" }
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8020"]
```

On Cloud Run, omit `GOOGLE_APPLICATION_CREDENTIALS` — use Workload Identity instead. Switch `SESSION_DB_URL` to a Cloud SQL Postgres instance.

### Build the React UI for production

```bash
cd restaurant-chat-app
npm run build
# Deploy /dist to any static host (Netlify, Vercel, GCS, etc.)
```

---

## Extending the system

**Add a new domain agent** — add entry to `agents_config.json`, register tools in `TOOL_REGISTRY`.

**Change the LLM** — update `default_model` in `agents_config.json` or set `ADK_MODEL` in `.env`.

**New Firestore collection** — add its name as a constant in `config.py`, update `SCHEMA_DESCRIPTION` so the NL query engine knows about it.

**Switch session backend** — change `SESSION_DB_URL` in `.env`. SQLite for dev, Postgres for production. No code changes needed.

---

## License

MIT