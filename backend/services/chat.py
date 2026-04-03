import os
from typing import Generator
from services.trips_db import fetch_trip, fetch_conversation, update_conversation, update_itinerary
from llm.client import stream_completion

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../llm/prompts/chat_prompt.txt")

def _load_prompt(trip: dict) -> str:
    with open(PROMPT_PATH) as f:
        template = f.read()
    return template.format(
        cities=", ".join(trip["cities"]),
        trip_length=trip["trip_length"],
        interests=", ".join(f"#{i+1} {interest}" for i, interest in enumerate(trip["interests"])),
        itinerary=trip.get("itinerary") or "(not yet generated)",
    )

def chat_turn_stream(trip_id: int, user_message: str, day_ref: int | None) -> Generator[str, None, None] | None:
    trip = fetch_trip(trip_id)
    if not trip:
        return None

    history = fetch_conversation(trip_id)
    system = _load_prompt(trip)
    user_content = f"[Re: Day {day_ref}] {user_message}" if day_ref else user_message

    messages = [{"role": "system", "content": system}]
    messages += history
    messages.append({"role": "user", "content": user_content})

    full_response = []

    def _generate():
        for token in stream_completion(messages):
            full_response.append(token)
            yield token

        response_text = "".join(full_response)

        new_history = history + [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": response_text},
        ]
        update_conversation(trip_id, new_history)

        if "UPDATED_ITINERARY:" in response_text:
            updated = response_text.split("UPDATED_ITINERARY:", 1)[1].strip()
            if updated:
                update_itinerary(trip_id, updated)

    return _generate()