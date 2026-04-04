"""
backend/services/planner_mcp.py

Agentic planner — uses Cerebras native tool calling (tool_completion) instead
of the pre-built _resolve_trip_context() + build_city_blocks() pipeline.

The LLM fetches city coordinates, attractions, day allocation, and route order
via tool calls during generation rather than consuming a single pre-assembled
context block.

Old planner.py is completely untouched — both paths run side by side:
  POST /plan-trip      → planner.py        (prompt-context path, streaming)
  POST /plan-trip-mcp  → planner_mcp.py    (agentic tool-calling path, non-streaming)

Note: Cerebras does not support streaming during tool-call rounds, so
plan_trip_mcp() returns a complete itinerary string rather than a generator.
"""

import os
from llm.client import tool_completion
from llm.tools import TOOLS, dispatch
from services.trips_db import insert_trip, update_itinerary


def _load_mcp_prompt() -> str:
    prompt_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../llm/prompts/planner_prompt_mcp.txt")
    )
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()


def plan_trip_mcp(
    cities: list[str],
    trip_length: int,
    interests: list[str],
    existing_trip_id: int | None = None,
) -> tuple[int, str]:
    """
    Run the agentic planning pipeline:
      1. Build initial user message from planner_prompt_mcp.txt
      2. Insert (or reuse) a DB row
      3. Call tool_completion() — LLM fetches geodata via tool rounds, then writes itinerary
      4. Persist itinerary to DB
      5. Return (trip_id, itinerary_text)

    The caller (routes.py) is responsible for returning the itinerary to the frontend.
    """
    template = _load_mcp_prompt()

    user_message = template.format(
        cities=", ".join(cities),
        trip_length=trip_length,
        interests=", ".join(interests),
        interests_ranked="\n".join(
            f"{i + 1}. {interest}" for i, interest in enumerate(interests)
        ),
    )

    messages = [{"role": "user", "content": user_message}]

    if existing_trip_id is not None:
        trip_id = existing_trip_id
    else:
        name = f"{', '.join(cities)} — {trip_length} days"
        trip_id = insert_trip(name, cities, trip_length, interests)

    itinerary = tool_completion(
        messages=messages,
        tools=TOOLS,
        dispatcher=dispatch,
    )

    update_itinerary(trip_id, itinerary)
    return trip_id, itinerary