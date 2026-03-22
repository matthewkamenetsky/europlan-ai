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