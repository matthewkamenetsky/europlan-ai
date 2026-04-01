import os
from typing import Generator
from services.trips_db import fetch_trip, fetch_conversation, update_conversation, update_itinerary
from llm.ollama_client import stream_llm

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../llm/prompts/chat_prompt.txt")

def _load_prompt(trip: dict) -> str:
    """Load and format the chat system prompt from file."""
    with open(PROMPT_PATH) as f:
        template = f.read()
    return template.format(
        cities=", ".join(trip["cities"]),
        trip_length=trip["trip_length"],
        interests=", ".join(f"#{i+1} {interest}" for i, interest in enumerate(trip["interests"])),
        itinerary=trip.get("itinerary") or "(not yet generated)",
    )

def _messages_to_prompt(system: str, history: list[dict], user_message: str, day_ref: int | None) -> str:
    """Flatten system prompt + history + new user message into a single Ollama prompt string."""
    user_content = f"[Re: Day {day_ref}] {user_message}" if day_ref else user_message

    parts = [f"SYSTEM:\n{system}"]
    for msg in history:
        role = msg["role"].upper()
        parts.append(f"{role}:\n{msg['content']}")
    parts.append(f"USER:\n{user_content}")
    parts.append("ASSISTANT:")

    return "\n\n---\n\n".join(parts)

def chat_turn_stream(trip_id: int, user_message: str, day_ref: int | None) -> Generator[str, None, None] | None:
    """
    Stream a chat response for a trip. Yields tokens.
    After streaming completes, persists the updated conversation and itinerary to DB.
    Returns None if the trip is not found.
    """
    trip = fetch_trip(trip_id)
    if not trip:
        return None

    history = fetch_conversation(trip_id)
    system = _load_prompt(trip)
    prompt = _messages_to_prompt(system, history, user_message, day_ref)

    print(f"DEBUG: Chat turn for trip {trip_id}, day_ref={day_ref}, history_len={len(history)}")

    full_response = []

    def _generate():
        for token in stream_llm(prompt):
            full_response.append(token)
            yield token

        response_text = "".join(full_response)

        user_content = f"[Re: Day {day_ref}] {user_message}" if day_ref else user_message
        new_history = history + [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": response_text},
        ]
        update_conversation(trip_id, new_history)

        if "UPDATED_ITINERARY:" in response_text:
            updated = response_text.split("UPDATED_ITINERARY:", 1)[1].strip()
            if updated:
                update_itinerary(trip_id, updated)
                print(f"DEBUG: Itinerary updated via chat for trip {trip_id}")

    return _generate()