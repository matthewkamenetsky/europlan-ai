import os
from utils.travel_utils import haversine, format_travel_time
from services.geodata import get_day_trip_candidates

def build_city_blocks(ordered: list, day_allocation: dict[str, int], city_attractions: dict, main_city_names: list[str], interests: list[str], db) -> str:
    blocks = []
    for idx, (name, country_code, lat, lon) in enumerate(ordered):
        days = day_allocation.get(name, 1)
        attractions_str = ", ".join(city_attractions[name]) or "No specific attractions found"

        if days >= 2:
            day_trips = get_day_trip_candidates(lat, lon, exclude_names=main_city_names, interests=interests, db=db)
            day_trip_str = "; ".join(
                f"{n} ({d}km, ~{t} by train) — {a}" for n, d, t, a in day_trips
            ) if day_trips else "None"
        else:
            day_trip_str = "None — not enough days"

        if idx == 0:
            travel_note = "Starting city"
        else:
            prev = ordered[idx - 1]
            dist = round(haversine(prev[2], prev[3], lat, lon))
            travel_note = f"~{dist}km from {prev[0]}, ~{format_travel_time(dist)} by train"

        blocks.append(
            f"- {name} ({country_code}) — {days} day(s)\n"
            f"  Travel from previous: {travel_note}\n"
            f"  Attractions: {attractions_str}\n"
            f"  Day trip options (only suggest if days allow): {day_trip_str}"
        )
    return "\n".join(blocks)

def build_trip_structure(ordered: list, day_allocation: dict[str, int]) -> str:
    lines = []
    current_day = 1
    for idx, (name, country_code, lat, lon) in enumerate(ordered):
        days = day_allocation.get(name, 1)

        if idx == 0:
            lines.append(f"- Day {current_day}: {name} — no travel (first city)")
        else:
            prev = ordered[idx - 1]
            dist = round(haversine(prev[2], prev[3], lat, lon))
            lines.append(f"- Day {current_day}: Travel {prev[0]} → {name} (~{dist}km, ~{format_travel_time(dist)} by train) — sleep: {name}")

        if days > 1:
            lines.append(f"- Days {current_day + 1}–{current_day + days - 1}: {name} — no travel")

        current_day += days
    return "\n".join(lines)

def build_regen_prompt(
    day_number: int,
    interests: list[str],
    ordered: list,
    day_allocation: dict[str, int],
    city_attractions: dict,
    main_city_names: list[str],
    existing_itinerary: str,
    db,
) -> str:
    trip_structure_str = build_trip_structure(ordered, day_allocation)

    day_context_line = ""
    for line in trip_structure_str.splitlines():
        cleaned = line.strip().lstrip("- ")
        if cleaned.startswith(f"Day {day_number}"):
            day_context_line = cleaned
            break
    print(f"DEBUG: day_context_line='{day_context_line}'")

    is_travel_day = "Travel" in day_context_line
    if is_travel_day:
        relevant_cities = [c for c in ordered if c[0] in day_context_line]
    else:
        day_city = None
        current_day = 0
        for city, days in day_allocation.items():
            current_day += days
            if day_number <= current_day:
                day_city = city
                break
        relevant_cities = [c for c in ordered if c[0] == day_city] if day_city else ordered

    city_blocks_str = build_city_blocks(
        relevant_cities, day_allocation, city_attractions, main_city_names, interests, db
    )

    banned_items = []
    if existing_itinerary:
        for line in existing_itinerary.splitlines():
            stripped = line.strip().lstrip("*- ").strip()
            if stripped and (" — " in stripped or stripped[0].isupper()):
                name = stripped.split(" — ")[0].split(" in the ")[0].split(" in ")[0].strip()
                if name and len(name) > 4:
                    banned_items.append(name)
    banned_list = "\n".join(f"- {item}" for item in banned_items) if banned_items else "- (none yet)"
    print(f"DEBUG: Banned list has {len(banned_items)} items")

    if is_travel_day:
        travel_rules = (
            "TRAVEL DAY RULES — this is a travel day, these are mandatory:\n"
            "- You MUST include a Travel line immediately after the Day heading, before any activities.\n"
            f"- The Travel line must be formatted exactly as: Travel: [info copied verbatim from {day_context_line}]\n"
            "- Do not paraphrase or invent travel details. Copy them exactly.\n"
            "- All morning activities must be in the departure city.\n"
            "- All afternoon and evening activities must be in the arrival city.\n"
            "- If travel is more than 2 hours, keep it light — 1 activity in departure city, 1 in arrival city."
        )
    else:
        travel_rules = (
            "NON-TRAVEL DAY RULES:\n"
            "- Do NOT include any Travel line.\n"
            "- Only mention the city named in the day heading. Never reference any other city."
        )

    prompt_path = os.path.join(os.path.dirname(__file__), "../llm/prompts/regen_prompt.txt")
    with open(prompt_path) as f:
        prompt = f.read().format(
            interests=", ".join(interests),
            day_context_line=day_context_line,
            city_blocks=city_blocks_str,
            travel_rules=travel_rules,
            banned_list=banned_list,
        )

    print(f"DEBUG: Regen prompt built for Day {day_number}: {day_context_line}, travel={is_travel_day}")
    return prompt