# Restaurant Agent

A multi-agent restaurant operations system built on [Google ADK](https://google.github.io/adk-docs/) and [Firestore](https://firebase.google.com/docs/firestore). A single conversational API endpoint routes staff and customer questions to the right specialist agent — orders, wait times, inventory, or store locations — and supports open-ended analytics queries by auto-generating Firestore queries from plain English using Gemini.

---

## Architecture

### System overview

<!-- Diagram 1: Full stack -->
<p align="center">
<svg width="100%" viewBox="0 0 680 720" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>Restaurant Agent — full system architecture</title>
  <style>
    .th{font-family:sans-serif;font-size:13px;font-weight:600;fill:#1f2328}
    .ts{font-family:sans-serif;font-size:11px;font-weight:400;fill:#57606a}
    .arr{stroke:#8c959f;stroke-width:1.5;fill:none}
  </style>
  <defs>
    <marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#8c959f" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- Chat UI -->
  <rect x="40" y="30" width="600" height="52" rx="10" fill="#f0eef8" stroke="#8c7ae6" stroke-width="0.5"/>
  <text class="th" x="340" y="52" text-anchor="middle" dominant-baseline="central">React + MUI chat interface</text>
  <text class="ts" x="340" y="68" text-anchor="middle" dominant-baseline="central">Vite · stable userId (localStorage) · session badge · health ping</text>
  <line x1="340" y1="82" x2="340" y2="108" class="arr" marker-end="url(#ar)"/>
  <text class="ts" x="356" y="99" dominant-baseline="central">POST /api/chat</text>
  <!-- FastAPI -->
  <rect x="40" y="108" width="600" height="52" rx="10" fill="#e6f4f1" stroke="#0f6e56" stroke-width="0.5"/>
  <text class="th" x="340" y="130" text-anchor="middle" dominant-baseline="central">FastAPI  (main.py)</text>
  <text class="ts" x="340" y="146" text-anchor="middle" dominant-baseline="central">Lifespan init · prior context injection · audit log · session cleanup</text>
  <line x1="340" y1="160" x2="340" y2="188" class="arr" marker-end="url(#ar)"/>
  <text class="ts" x="356" y="178" dominant-baseline="central">runner.run_async()</text>
  <!-- Orchestrator -->
  <rect x="140" y="188" width="400" height="52" rx="10" fill="#fdf0eb" stroke="#993c1d" stroke-width="0.5"/>
  <text class="th" x="340" y="210" text-anchor="middle" dominant-baseline="central">restaurant_orchestrator</text>
  <text class="ts" x="340" y="226" text-anchor="middle" dominant-baseline="central">Semantic routing · natural_language_query · reads session.state</text>
  <!-- fan-out arrows -->
  <path d="M220 240 L220 268 L95 268 L95 310" fill="none" stroke="#8c959f" stroke-width="1.5" marker-end="url(#ar)"/>
  <path d="M280 240 L280 268 L245 268 L245 310" fill="none" stroke="#8c959f" stroke-width="1.5" marker-end="url(#ar)"/>
  <path d="M400 240 L400 268 L435 268 L435 310" fill="none" stroke="#8c959f" stroke-width="1.5" marker-end="url(#ar)"/>
  <path d="M460 240 L460 268 L585 268 L585 310" fill="none" stroke="#8c959f" stroke-width="1.5" marker-end="url(#ar)"/>
  <!-- 4 agents -->
  <rect x="40" y="310" width="120" height="56" rx="8" fill="#e6f0fb" stroke="#185fa5" stroke-width="0.5"/>
  <text class="th" x="100" y="333" text-anchor="middle" dominant-baseline="central">sales_pos</text>
  <text class="ts" x="100" y="351" text-anchor="middle" dominant-baseline="central">orders · payments</text>
  <rect x="190" y="310" width="120" height="56" rx="8" fill="#e6f0fb" stroke="#185fa5" stroke-width="0.5"/>
  <text class="th" x="250" y="333" text-anchor="middle" dominant-baseline="central">customer_exp</text>
  <text class="ts" x="250" y="351" text-anchor="middle" dominant-baseline="central">waits · waitlist</text>
  <rect x="370" y="310" width="120" height="56" rx="8" fill="#e6f0fb" stroke="#185fa5" stroke-width="0.5"/>
  <text class="th" x="430" y="333" text-anchor="middle" dominant-baseline="central">inventory</text>
  <text class="ts" x="430" y="351" text-anchor="middle" dominant-baseline="central">stock · vector search</text>
  <rect x="520" y="310" width="120" height="56" rx="8" fill="#e6f0fb" stroke="#185fa5" stroke-width="0.5"/>
  <text class="th" x="580" y="333" text-anchor="middle" dominant-baseline="central">locations</text>
  <text class="ts" x="580" y="351" text-anchor="middle" dominant-baseline="central">hours · nearest</text>
  <!-- arrows to tools -->
  <line x1="100" y1="366" x2="100" y2="408" class="arr" marker-end="url(#ar)"/>
  <line x1="250" y1="366" x2="250" y2="408" class="arr" marker-end="url(#ar)"/>
  <line x1="430" y1="366" x2="430" y2="408" class="arr" marker-end="url(#ar)"/>
  <line x1="580" y1="366" x2="580" y2="408" class="arr" marker-end="url(#ar)"/>
  <!-- Tools band -->
  <rect x="40" y="408" width="600" height="44" rx="8" fill="none" stroke="#d0d7de" stroke-width="0.5" stroke-dasharray="4 3"/>
  <text class="ts" x="56" y="422" dominant-baseline="central" opacity="0.6">tools/</text>
  <rect x="74" y="418" width="86" height="24" rx="4" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="117" y="430" text-anchor="middle" dominant-baseline="central">pos_tools</text>
  <rect x="170" y="418" width="96" height="24" rx="4" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="218" y="430" text-anchor="middle" dominant-baseline="central">queue_tools</text>
  <rect x="276" y="418" width="108" height="24" rx="4" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="330" y="430" text-anchor="middle" dominant-baseline="central">inventory_tools</text>
  <rect x="394" y="418" width="104" height="24" rx="4" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="446" y="430" text-anchor="middle" dominant-baseline="central">location_tools</text>
  <rect x="508" y="418" width="118" height="24" rx="4" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="567" y="430" text-anchor="middle" dominant-baseline="central">nl_query tool</text>
  <!-- db.py -->
  <line x1="340" y1="452" x2="340" y2="478" class="arr" marker-end="url(#ar)"/>
  <rect x="200" y="478" width="280" height="44" rx="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="340" y="496" text-anchor="middle" dominant-baseline="central">db.py</text>
  <text class="ts" x="340" y="512" text-anchor="middle" dominant-baseline="central">CRUD · vector search · sanitise · audit helpers</text>
  <!-- fan to stores -->
  <path d="M260 522 L260 548 L130 548 L130 574" fill="none" stroke="#8c959f" stroke-width="1.5" marker-end="url(#ar)"/>
  <line x1="340" y1="522" x2="340" y2="574" class="arr" marker-end="url(#ar)"/>
  <path d="M420 522 L420 548 L550 548 L550 574" fill="none" stroke="#8c959f" stroke-width="1.5" marker-end="url(#ar)"/>
  <!-- 3 stores -->
  <rect x="40" y="574" width="176" height="80" rx="8" fill="#fdf6e3" stroke="#854f0b" stroke-width="0.5"/>
  <text class="th" x="128" y="596" text-anchor="middle" dominant-baseline="central">Firestore</text>
  <text class="ts" x="128" y="613" text-anchor="middle" dominant-baseline="central">orders · menu_items</text>
  <text class="ts" x="128" y="629" text-anchor="middle" dominant-baseline="central">locations · analytics</text>
  <rect x="252" y="574" width="176" height="80" rx="8" fill="#eaf3de" stroke="#3b6d11" stroke-width="0.5"/>
  <text class="th" x="340" y="596" text-anchor="middle" dominant-baseline="central">SQLite / Postgres</text>
  <text class="ts" x="340" y="613" text-anchor="middle" dominant-baseline="central">sessions · session.state</text>
  <text class="ts" x="340" y="629" text-anchor="middle" dominant-baseline="central">DatabaseSessionService</text>
  <rect x="464" y="574" width="176" height="80" rx="8" fill="#fdf0eb" stroke="#993c1d" stroke-width="0.5"/>
  <text class="th" x="552" y="596" text-anchor="middle" dominant-baseline="central">Firestore (memory)</text>
  <text class="ts" x="552" y="613" text-anchor="middle" dominant-baseline="central">user_contexts</text>
  <text class="ts" x="552" y="629" text-anchor="middle" dominant-baseline="central">conversation_logs</text>
  <!-- agents_config annotation -->
  <line x1="140" y1="214" x2="52" y2="214" stroke="#d0d7de" stroke-width="0.5" stroke-dasharray="3 3" fill="none" opacity="0.7"/>
  <line x1="52" y1="214" x2="52" y2="688" stroke="#d0d7de" stroke-width="0.5" stroke-dasharray="3 3" fill="none" opacity="0.7"/>
  <line x1="52" y1="688" x2="88" y2="688" stroke="#d0d7de" stroke-width="0.5" stroke-dasharray="3 3" fill="none" opacity="0.7" marker-end="url(#ar)"/>
  <rect x="88" y="672" width="504" height="34" rx="6" fill="#f0eef8" stroke="#8c7ae6" stroke-width="0.5"/>
  <text class="th" x="340" y="689" text-anchor="middle" dominant-baseline="central">agents_config.json — declarative agent definitions, loaded at startup</text>
</svg>
</p>

---

### Memory layers

<!-- Diagram 2: Memory architecture -->
<p align="center">
<svg width="100%" viewBox="0 0 680 420" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>Three memory layers: session.state, user_contexts, conversation_logs</title>
  <style>
    .th{font-family:sans-serif;font-size:13px;font-weight:600;fill:#1f2328}
    .ts{font-family:sans-serif;font-size:11px;font-weight:400;fill:#57606a}
  </style>
  <defs>
    <marker id="ar2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#8c959f" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- tier labels -->
  <rect x="40" y="30" width="180" height="44" rx="8" fill="#e6f0fb" stroke="#185fa5" stroke-width="0.5"/>
  <text class="th" x="130" y="48" text-anchor="middle" dominant-baseline="central">session.state</text>
  <text class="ts" x="130" y="64" text-anchor="middle" dominant-baseline="central">within one conversation</text>
  <rect x="250" y="30" width="180" height="44" rx="8" fill="#e6f4f1" stroke="#0f6e56" stroke-width="0.5"/>
  <text class="th" x="340" y="48" text-anchor="middle" dominant-baseline="central">user_contexts</text>
  <text class="ts" x="340" y="64" text-anchor="middle" dominant-baseline="central">across sessions</text>
  <rect x="460" y="30" width="180" height="44" rx="8" fill="#fdf6e3" stroke="#854f0b" stroke-width="0.5"/>
  <text class="th" x="550" y="48" text-anchor="middle" dominant-baseline="central">conversation_logs</text>
  <text class="ts" x="550" y="64" text-anchor="middle" dominant-baseline="central">audit trail</text>
  <!-- down arrows -->
  <line x1="130" y1="74" x2="130" y2="110" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <line x1="340" y1="74" x2="340" y2="110" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <line x1="550" y1="74" x2="550" y2="110" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <!-- stored keys -->
  <rect x="40" y="110" width="180" height="80" rx="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="130" y="132" text-anchor="middle" dominant-baseline="central">active_location</text>
  <text class="ts" x="130" y="152" text-anchor="middle" dominant-baseline="central">active_table</text>
  <text class="ts" x="130" y="172" text-anchor="middle" dominant-baseline="central">prior_context</text>
  <rect x="250" y="110" width="180" height="80" rx="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="340" y="132" text-anchor="middle" dominant-baseline="central">last_location</text>
  <text class="ts" x="340" y="152" text-anchor="middle" dominant-baseline="central">last_active_table</text>
  <text class="ts" x="340" y="172" text-anchor="middle" dominant-baseline="central">last_seen</text>
  <rect x="460" y="110" width="180" height="80" rx="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="ts" x="550" y="132" text-anchor="middle" dominant-baseline="central">user_id · message</text>
  <text class="ts" x="550" y="152" text-anchor="middle" dominant-baseline="central">response · agent_used</text>
  <text class="ts" x="550" y="172" text-anchor="middle" dominant-baseline="central">timestamp</text>
  <!-- written by -->
  <line x1="130" y1="190" x2="130" y2="226" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <line x1="340" y1="190" x2="340" y2="226" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <line x1="550" y1="190" x2="550" y2="226" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <rect x="40" y="226" width="180" height="44" rx="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="130" y="244" text-anchor="middle" dominant-baseline="central">written by tools</text>
  <text class="ts" x="130" y="260" text-anchor="middle" dominant-baseline="central">via ToolContext.state</text>
  <rect x="250" y="226" width="180" height="44" rx="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="340" y="244" text-anchor="middle" dominant-baseline="central">written by main.py</text>
  <text class="ts" x="340" y="260" text-anchor="middle" dominant-baseline="central">after every chat turn</text>
  <rect x="460" y="226" width="180" height="44" rx="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="550" y="244" text-anchor="middle" dominant-baseline="central">written by main.py</text>
  <text class="ts" x="550" y="260" text-anchor="middle" dominant-baseline="central">every turn, every agent</text>
  <!-- persisted in -->
  <line x1="130" y1="270" x2="130" y2="306" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <line x1="340" y1="270" x2="340" y2="306" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <line x1="550" y1="270" x2="550" y2="306" stroke="#8c959f" stroke-width="1.5" fill="none" marker-end="url(#ar2)"/>
  <rect x="40" y="306" width="180" height="44" rx="8" fill="#eaf3de" stroke="#3b6d11" stroke-width="0.5"/>
  <text class="th" x="130" y="324" text-anchor="middle" dominant-baseline="central">SQLite / Postgres</text>
  <text class="ts" x="130" y="340" text-anchor="middle" dominant-baseline="central">sessions table</text>
  <rect x="250" y="306" width="180" height="44" rx="8" fill="#fdf6e3" stroke="#854f0b" stroke-width="0.5"/>
  <text class="th" x="340" y="324" text-anchor="middle" dominant-baseline="central">Firestore</text>
  <text class="ts" x="340" y="340" text-anchor="middle" dominant-baseline="central">user_contexts/{user_id}</text>
  <rect x="460" y="306" width="180" height="44" rx="8" fill="#fdf6e3" stroke="#854f0b" stroke-width="0.5"/>
  <text class="th" x="550" y="324" text-anchor="middle" dominant-baseline="central">Firestore</text>
  <text class="ts" x="550" y="340" text-anchor="middle" dominant-baseline="central">conv_logs/{session}/turns</text>
  <!-- feedback loop arrow -->
  <path d="M340 350 L340 388 L130 388 L130 356" fill="none" stroke="#0f6e56" stroke-width="0.5" stroke-dasharray="4 3" marker-end="url(#ar2)"/>
  <text class="ts" x="238" y="402" text-anchor="middle" dominant-baseline="central">injected into session.state on next login</text>
</svg>
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
<svg width="100%" viewBox="0 0 680 400" xmlns="http://www.w3.org/2000/svg" role="img">
  <title>What changes vs what stays the same across domains</title>
  <style>
    .th{font-family:sans-serif;font-size:13px;font-weight:600;fill:#1f2328}
    .ts{font-family:sans-serif;font-size:11px;font-weight:400;fill:#57606a}
  </style>
  <defs>
    <marker id="ar3" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#8c959f" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <!-- headers -->
  <rect x="40" y="30" width="270" height="36" rx="8" fill="#fdf0eb" stroke="#993c1d" stroke-width="0.5"/>
  <text class="th" x="175" y="48" text-anchor="middle" dominant-baseline="central">replace for each domain</text>
  <rect x="370" y="30" width="270" height="36" rx="8" fill="#e6f4f1" stroke="#0f6e56" stroke-width="0.5"/>
  <text class="th" x="505" y="48" text-anchor="middle" dominant-baseline="central">identical across all domains</text>
  <!-- left column -->
  <rect x="40" y="84" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="175" y="104" text-anchor="middle" dominant-baseline="central">agents_config.json</text>
  <text class="ts" x="175" y="122" text-anchor="middle" dominant-baseline="central">agent names, instructions, tools, model</text>
  <rect x="40" y="148" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="175" y="168" text-anchor="middle" dominant-baseline="central">tools/*.py</text>
  <text class="ts" x="175" y="186" text-anchor="middle" dominant-baseline="central">your API clients and business logic</text>
  <rect x="40" y="212" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="175" y="232" text-anchor="middle" dominant-baseline="central">TOOL_REGISTRY</text>
  <text class="ts" x="175" y="250" text-anchor="middle" dominant-baseline="central">map tool names to callables</text>
  <rect x="40" y="276" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="175" y="296" text-anchor="middle" dominant-baseline="central">SCHEMA_DESCRIPTION</text>
  <text class="ts" x="175" y="314" text-anchor="middle" dominant-baseline="central">your data schema for NL query engine</text>
  <!-- right column -->
  <rect x="370" y="84" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="505" y="104" text-anchor="middle" dominant-baseline="central">main.py</text>
  <text class="ts" x="505" y="122" text-anchor="middle" dominant-baseline="central">FastAPI, session lifecycle, memory, audit</text>
  <rect x="370" y="148" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="505" y="168" text-anchor="middle" dominant-baseline="central">agents.py factory</text>
  <text class="ts" x="505" y="186" text-anchor="middle" dominant-baseline="central">two-pass wiring, root agent resolution</text>
  <rect x="370" y="212" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="505" y="232" text-anchor="middle" dominant-baseline="central">React + MUI chat UI</text>
  <text class="ts" x="505" y="250" text-anchor="middle" dominant-baseline="central">App.jsx, theme.js, session badge</text>
  <rect x="370" y="276" width="270" height="52" rx="6" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.5"/>
  <text class="th" x="505" y="296" text-anchor="middle" dominant-baseline="central">db.py + memory arch.</text>
  <text class="ts" x="505" y="314" text-anchor="middle" dominant-baseline="central">sanitiser, user_contexts, audit log</text>
  <!-- divider -->
  <line x1="340" y1="30" x2="340" y2="340" stroke="#d0d7de" stroke-width="0.5" stroke-dasharray="4 3"/>
  <!-- domain pills -->
  <rect x="40" y="350" width="600" height="32" rx="8" fill="none" stroke="#d0d7de" stroke-width="0.5" stroke-dasharray="3 3"/>
  <rect x="108" y="358" width="84" height="16" rx="4" fill="#f0eef8" stroke="#8c7ae6" stroke-width="0.5"/>
  <text class="ts" x="150" y="366" text-anchor="middle" dominant-baseline="central">restaurant</text>
  <rect x="202" y="358" width="74" height="16" rx="4" fill="#f0eef8" stroke="#8c7ae6" stroke-width="0.5"/>
  <text class="ts" x="239" y="366" text-anchor="middle" dominant-baseline="central">IT helpdesk</text>
  <rect x="286" y="358" width="82" height="16" rx="4" fill="#f0eef8" stroke="#8c7ae6" stroke-width="0.5"/>
  <text class="ts" x="327" y="366" text-anchor="middle" dominant-baseline="central">supply chain</text>
  <rect x="378" y="358" width="100" height="16" rx="4" fill="#f0eef8" stroke="#8c7ae6" stroke-width="0.5"/>
  <text class="ts" x="428" y="366" text-anchor="middle" dominant-baseline="central">customer support</text>
  <rect x="488" y="358" width="108" height="16" rx="4" fill="#f0eef8" stroke="#8c7ae6" stroke-width="0.5"/>
  <text class="ts" x="542" y="366" text-anchor="middle" dominant-baseline="central">financial analysis</text>
  <!-- swap label -->
  <path d="M175 328 L175 344 L340 344 L340 350" fill="none" stroke="#993c1d" stroke-width="0.5" stroke-dasharray="3 3" marker-end="url(#ar3)"/>
  <text class="ts" x="260" y="341" text-anchor="middle" dominant-baseline="central" opacity="0.7">swap config, new domain</text>
</svg>
</p>
---

## Project structure

```
agentic-restaurant-ops/
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
cd agentic-restaurant-ops
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
cd app
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
