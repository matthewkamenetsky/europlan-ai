import os
from typing import Generator
from dotenv import load_dotenv
from llm.ollama_client import stream_llm
from services.geodata import get_city, get_attractions, allocate_days, find_best_order
from utils.prompt_builder import build_city_blocks, build_trip_structure
from services.trips_db import get_db, insert_trip, save_itinerary

load_dotenv()


def create_trip(cities: list[str], trip_length: int, interests: list[str]) -> tuple[int, str] | None:
    """
    Resolve cities, build the prompt, insert a pending DB row, return (trip_id, prompt).
    Returns None if any city cannot be resolved.
    """
    print(f"DEBUG: Starting create_trip for {cities}")

    with get_db() as db:
        resolved = []
        for city_name in cities:
            city = get_city(city_name, db)
            print(f"DEBUG: Resolved '{city_name}' -> {city}")
            if not city:
                return None
            resolved.append(city)

        city_attractions = {}
        for name, country_code, lat, lon in resolved:
            city_attractions[name] = get_attractions(lat, lon, interests)
            print(f"DEBUG: {name} got {len(city_attractions[name])} attractions")

        attraction_counts = [(name, len(city_attractions[name])) for name, *_ in resolved]
        day_allocation = allocate_days(attraction_counts, trip_length)
        print(f"DEBUG: Day allocation: {day_allocation}")

        ordered = find_best_order(resolved)
        print(f"DEBUG: Optimal order: {[c[0] for c in ordered]}")

        main_city_names = [c[0] for c in ordered]
        city_blocks_str = build_city_blocks(ordered, day_allocation, city_attractions, main_city_names, interests, db)
        trip_structure_str = build_trip_structure(ordered, day_allocation)
        print(f"DEBUG: Trip structure:\n{trip_structure_str}")

    prompt_path = os.path.join(os.path.dirname(__file__), "../llm/prompts/planner_prompt.txt")
    with open(prompt_path) as f:
        prompt = f.read().format(
            trip_length=trip_length,
            interests=", ".join(interests),
            city_blocks=city_blocks_str,
            trip_structure=trip_structure_str,
        )

    trip_name = ", ".join(main_city_names) + f" — {trip_length} days"
    trip_id = insert_trip(trip_name, main_city_names, trip_length, interests)
    print(f"DEBUG: Created trip row with id={trip_id}")

    return trip_id, prompt


def plan_trip_stream(prompt: str) -> Generator[str, None, None]:
    """Stream the LLM response for a pre-built prompt."""
    print("DEBUG: About to call LLM...")
    yield from stream_llm(prompt)
    print("DEBUG: LLM stream finished")
    