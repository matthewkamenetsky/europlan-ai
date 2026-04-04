# Europlan-AI

An AI-powered Schengen travel planner. Enter a list of cities, trip length, and ranked interests — the system generates a day-by-day itinerary grounded in real attraction data, critiques it for transport feasibility and pacing, and lets you refine it through a chat interface. Individual days can be regenerated, and an agentic planner path lets the LLM dynamically fetch geographic data via tool calling instead of receiving a pre-built context block.

---

## Running locally

Create `backend/.env`:
```
CEREBRAS_API_KEY=csk-...
OPENTRIPMAP_KEY=your_key
```

Create `frontend/.env`:
```
REACT_APP_API_URL=http://localhost:8000
```

```bash
docker compose up --build
```

Frontend at `localhost:3000`, backend at `localhost:8000`.

---

## MCP server (optional)

Exposes the same geographic tools via the Model Context Protocol so Claude Desktop or Cursor can call them directly.

```bash
pip install mcp
python backend/mcp_server.py
```

On Windows (Claude Desktop Store install), add the server to:
```
~\Claude\claude_desktop_config.json
```