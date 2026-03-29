import os
import json
from typing import Generator
from dotenv import load_dotenv
from llm.ollama_client import stream_llm
from services.geodata import get_city, get_attractions, allocate_days, find_best_order
from utils.prompt_builder import build_city_blocks, build_trip_structure, build_regen_prompt
from services.trips_db import get_db, insert_trip, save_itinerary, fetch_trip

load_dotenv()

def _resolve_trip_context(cities: list[str], trip_length: int, interests: list[str], db):
    """Resolve cities, fetch attractions, allocate days, find order. Returns context dict or None."""
    resolved = []
    for city_name in cities:
        city = get_city(city_name, db)
        print(f"DEBUG: Resolved '{city_name}' -> {city}")
        if not city:
            return None
        resolved.append(city)

    attraction_counts_raw = []
    for name, country_code, lat, lon in resolved:
        preview = get_attractions(lat, lon, interests, limit=60)
        attraction_counts_raw.append((name, len(preview)))
        print(f"DEBUG: {name} preview count: {len(preview)}")

    day_allocation = allocate_days(attraction_counts_raw, trip_length)
    ordered = find_best_order(resolved)
    main_city_names = [c[0] for c in ordered]

    print(f"DEBUG: Day allocation: {day_allocation}")
    print(f"DEBUG: Optimal order: {main_city_names}")

    city_attractions = {}
    for name, country_code, lat, lon in resolved:
        days = day_allocation.get(name, 1)
        city_attractions[name] = get_attractions(lat, lon, interests, days_in_city=days)
        print(f"DEBUG: {name} ({days}d) got {len(city_attractions[name])} attractions")

    return dict(
        resolved=resolved,
        city_attractions=city_attractions,
        day_allocation=day_allocation,
        ordered=ordered,
        main_city_names=main_city_names,
    )

def create_trip(cities: list[str], trip_length: int, interests: list[str]) -> tuple[int, str] | None:
    """Resolve cities, build prompt, insert pending DB row, return (trip_id, prompt)."""
    print(f"DEBUG: Starting create_trip for {cities}")

    with get_db() as db:
        ctx = _resolve_trip_context(cities, trip_length, interests, db)
        if ctx is None:
            return None

        city_blocks_str = build_city_blocks(
            ctx["ordered"], ctx["day_allocation"], ctx["city_attractions"],
            ctx["main_city_names"], interests, db
        )
        trip_structure_str = build_trip_structure(ctx["ordered"], ctx["day_allocation"])
        print(f"DEBUG: Trip structure:\n{trip_structure_str}")

    prompt_path = os.path.join(os.path.dirname(__file__), "../llm/prompts/planner_prompt.txt")
    with open(prompt_path) as f:
        prompt = f.read().format(
            trip_length=trip_length,
            interests=", ".join(interests),
            city_blocks=city_blocks_str,
            trip_structure=trip_structure_str,
        )

    trip_name = ", ".join(ctx["main_city_names"]) + f" — {trip_length} days"
    trip_id = insert_trip(trip_name, ctx["main_city_names"], trip_length, interests)
    print(f"DEBUG: Created trip row with id={trip_id}")

    return trip_id, prompt

def create_regen_prompt(trip_id: int, day_number: int) -> str | None:
    """Fetch trip from DB, rebuild context, delegate prompt building to prompt_builder."""
    trip = fetch_trip(trip_id)
    if not trip:
        return None

    cities = trip["cities"]
    trip_length = trip["trip_length"]
    interests = trip["interests"]
    existing_itinerary = trip.get("itinerary") or ""

    with get_db() as db:
        ctx = _resolve_trip_context(cities, trip_length, interests, db)
        if ctx is None:
            return None

        return build_regen_prompt(
            day_number=day_number,
            interests=interests,
            ordered=ctx["ordered"],
            day_allocation=ctx["day_allocation"],
            city_attractions=ctx["city_attractions"],
            main_city_names=ctx["main_city_names"],
            existing_itinerary=existing_itinerary,
            db=db,
        )

def plan_trip_stream(prompt: str) -> Generator[str, None, None]:
    """Stream the LLM response for a pre-built prompt."""
    print("DEBUG: About to call LLM...")
    yield from stream_llm(prompt)
    print("DEBUG: LLM stream finished")