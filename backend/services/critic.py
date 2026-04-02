import os
import json
from services.trips_db import fetch_trip, get_db
from services.geodata import get_city
from utils.travel_utils import haversine, format_travel_time
from llm.client import stream_completion


def _build_transport_legs(ordered: list, day_allocation: dict[str, int]) -> list[dict]:
    """Compute Haversine transport legs between consecutive cities."""
    legs = []
    for i in range(len(ordered) - 1):
        from_city = ordered[i]
        to_city = ordered[i + 1]
        dist = round(haversine(from_city[2], from_city[3], to_city[2], to_city[3]))
        time_str = format_travel_time(dist)
        legs.append({
            "from": from_city[0],
            "to": to_city[0],
            "distance_km": dist,
            "estimated_time": time_str,
            "days_allocated": day_allocation.get(to_city[0], 1),
            "feasible": dist / 120 < 5,  # TRAIN_KMH = 120
        })
    return legs


def _format_transport_legs(legs: list[dict]) -> str:
    lines = []
    for leg in legs:
        feasible_str = "feasible" if leg["feasible"] else "LONG — consider lightening schedule"
        lines.append(
            f"- {leg['from']} → {leg['to']}: {leg['distance_km']}km, "
            f"~{leg['estimated_time']} by train ({feasible_str})"
        )
    return "\n".join(lines) if lines else "- No multi-city travel (single city trip)"


def _format_day_allocation(cities: list[str], day_allocation: dict[str, int]) -> str:
    return "\n".join(f"- {city}: {day_allocation.get(city, 1)} day(s)" for city in cities)


def build_critique(trip_id: int) -> dict | None:
    """Fetch trip, build critic prompt, call LLM, return parsed JSON critique."""
    trip = fetch_trip(trip_id)
    if not trip:
        return None

    itinerary = trip.get("itinerary")
    if not itinerary:
        return None

    cities = trip["cities"]
    interests = trip["interests"]
    trip_length = trip["trip_length"]

    # Resolve city coordinates from DB
    with get_db() as db:
        resolved = []
        for city_name in cities:
            city = get_city(city_name, db)
            if city:
                resolved.append(city)

    if not resolved:
        return None

    # Build day allocation from resolved cities (same order as stored)
    # We use a simple proportional allocation matching what the planner used
    from services.geodata import allocate_days
    attraction_counts = [(name, 10) for name, *_ in resolved]  # neutral counts — allocation was already decided at plan time
    day_allocation = allocate_days([(c, 10) for c in cities], trip_length)

    # Rebuild as dict keyed by city name
    day_alloc_dict = {city: day_allocation.get(city, 1) for city in cities}

    transport_legs = _build_transport_legs(resolved, day_alloc_dict)
    transport_legs_str = _format_transport_legs(transport_legs)
    day_allocation_str = _format_day_allocation(cities, day_alloc_dict)
    interests_str = "\n".join(f"#{i+1}: {interest}" for i, interest in enumerate(interests))

    prompt_path = os.path.join(os.path.dirname(__file__), "../llm/prompts/critic_prompt.txt")
    with open(prompt_path) as f:
        prompt = f.read().format(
            transport_legs=transport_legs_str,
            interests=interests_str,
            day_allocation=day_allocation_str,
            itinerary=itinerary,
        )

    print("DEBUG: Calling critic LLM...")

    # Collect full response (critic is not streamed)
    tokens = list(stream_completion(prompt))
    raw = "".join(tokens).strip()

    print(f"DEBUG: Critic raw response (first 200 chars): {raw[:200]}")

    # Strip markdown fences if the LLM added them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        critique = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"DEBUG: Failed to parse critic JSON: {e}")
        print(f"DEBUG: Raw response: {raw}")
        return {
            "error": "Critic LLM returned invalid JSON.",
            "raw": raw,
        }

    # Attach the computed transport legs regardless of what LLM returned
    critique["transport_legs"] = transport_legs

    return critique