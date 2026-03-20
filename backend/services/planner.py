import sqlite3
import os
import requests
import itertools
from typing import Generator
from llm.ollama_client import stream_llm
from utils.travel_utils import haversine
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/europlan.db"

INTEREST_MAP = {
    "history":       "historic,archaeology,monuments_and_memorials",
    "architecture":  "architecture,historic_architecture",
    "art":           "museums,art_galleries,urban_environment",
    "museums":       "museums",
    "religion":      "religion,churches,cathedrals,monasteries",
    "nature":        "natural,nature_reserves,national_parks",
    "beaches":       "beaches",
    "hiking":        "natural,geological_formations,mountain_peaks",
    "skiing":        "winter_sports,skiing",
    "food":          "foods,restaurants,cafes,pubs,bars",
    "nightlife":     "nightclubs,bars,alcohol",
    "amusements":    "amusements,amusement_parks,water_parks",
    "sport":         "sport,stadiums,diving,climbing,surfing",
    "thermal baths": "baths_and_saunas,thermal_baths",
    "shopping":      "shops,malls,marketplaces",
    "viewpoints":    "view_points",
    "gardens":       "gardens_and_parks",
}

TRAIN_KMH = 120

def get_city(city_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cleaned = city_name.strip()
    if not cleaned:
        conn.close()
        return None

    cursor.execute("""
        SELECT name, country_code, lat, lon FROM cities
        WHERE LOWER(name) = LOWER(?)
           OR LOWER(asciiname) = LOWER(?)
           OR LOWER(',' || alternatenames || ',') LIKE LOWER(?)
        LIMIT 1
    """, (cleaned, cleaned, f"%,{cleaned},%"))

    result = cursor.fetchone()
    conn.close()
    return result

def get_day_trip_candidates(lat: float, lon: float, exclude_names: list[str], interests: list[str], max_distance_km: int = 120):
    """
    Return cities within day trip range (~120km) excluding the main itinerary
    cities. Each candidate includes distance, travel time, and top attractions
    matching the user's interests.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, country_code, lat, lon FROM cities")
    all_cities = cursor.fetchall()
    conn.close()

    candidates = []
    for city in all_cities:
        name, country_code, city_lat, city_lon = city
        if name in exclude_names:
            continue
        distance = haversine(lat, lon, city_lat, city_lon)
        if 10 < distance <= max_distance_km:
            total_minutes = round(distance / TRAIN_KMH * 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if hours == 0:
                time_str = f"{minutes}min"
            elif minutes == 0:
                time_str = f"{hours}h"
            else:
                time_str = f"{hours}h {minutes}min"
            candidates.append((name, round(distance), time_str, city_lat, city_lon))

    candidates.sort(key=lambda x: x[1])
    top_candidates = candidates[:5]

    # Fetch attractions for each day trip candidate
    result = []
    for name, distance, time_str, city_lat, city_lon in top_candidates:
        attractions = get_attractions(city_lat, city_lon, interests, limit=5)
        attractions_str = ", ".join(attractions) if attractions else "no specific attractions found"
        result.append((name, distance, time_str, attractions_str))

    return result

def get_attractions(lat: float, lon: float, interests: list[str], radius: int = 10000, limit: int = 20) -> list[str]:
    kinds = ",".join([INTEREST_MAP[i] for i in interests if i in INTEREST_MAP])
    if not kinds:
        kinds = "cultural,historic,museums"

    url = "https://api.opentripmap.com/0.1/en/places/radius"
    params = {
        "radius": radius,
        "lon": lon,
        "lat": lat,
        "kinds": kinds,
        "rate": "3h",
        "format": "json",
        "limit": limit,
        "apikey": os.getenv("OPENTRIPMAP_KEY")
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return [place.get("name") for place in data if place.get("name")]
    except Exception as e:
        print(f"Failed to fetch attractions for ({lat}, {lon}): {e}")
        return []

def allocate_days(city_attraction_counts: list[tuple[str, int]], trip_length: int) -> dict[str, int]:
    """
    Distribute trip_length days across cities weighted by attraction count.
    Each city gets at least 1 day. Remaining days are distributed proportionally.
    """
    n = len(city_attraction_counts)
    if n == 0:
        return {}

    if trip_length <= n:
        return {name: 1 for name, _ in city_attraction_counts[:trip_length]}

    base = {name: 1 for name, _ in city_attraction_counts}
    remaining = trip_length - n
    total_attractions = sum(count for _, count in city_attraction_counts) or 1

    extras = {}
    for name, count in city_attraction_counts:
        weight = count / total_attractions
        extras[name] = round(weight * remaining)

    diff = remaining - sum(extras.values())
    if diff != 0:
        top_city = max(city_attraction_counts, key=lambda x: x[1])[0]
        extras[top_city] += diff

    return {name: base[name] + extras[name] for name in base}

def route_distance(ordered: list) -> float:
    """Calculate total Haversine distance for an ordered list of cities."""
    total = 0.0
    for i in range(len(ordered) - 1):
        total += haversine(ordered[i][2], ordered[i][3], ordered[i+1][2], ordered[i+1][3])
    return total

def find_best_order(resolved: list) -> list:
    """
    Find the optimal city ordering using brute force for <= 8 cities,
    falling back to nearest-neighbour for larger inputs.
    Solves the open TSP (no return to start).
    """
    if len(resolved) <= 1:
        return resolved

    if len(resolved) <= 8:
        best_order = None
        best_distance = float("inf")

        for permutation in itertools.permutations(resolved):
            dist = route_distance(list(permutation))
            if dist < best_distance:
                best_distance = dist
                best_order = list(permutation)

        return best_order

    else:
        best_order = None
        best_distance = float("inf")

        for start in resolved:
            ordered = [start]
            remaining = [c for c in resolved if c != start]
            while remaining:
                last = ordered[-1]
                nearest = min(remaining, key=lambda c: haversine(last[2], last[3], c[2], c[3]))
                ordered.append(nearest)
                remaining.remove(nearest)

            dist = route_distance(ordered)
            if dist < best_distance:
                best_distance = dist
                best_order = ordered

        return best_order

def plan_trip_stream(cities: list[str], trip_length: int, interests: list[str]) -> Generator[str, None, None]:
    print(f"DEBUG: Starting plan_trip_stream for {cities}")

    resolved = []
    for city_name in cities:
        city = get_city(city_name)
        print(f"DEBUG: Resolved '{city_name}' -> {city}")
        if not city:
            yield f"Error: City '{city_name}' not found.\n"
            return
        resolved.append(city)

    print("DEBUG: Fetching attractions...")
    city_attractions = {}
    for name, country_code, lat, lon in resolved:
        attractions = get_attractions(lat, lon, interests)
        print(f"DEBUG: {name} got {len(attractions)} attractions")
        city_attractions[name] = attractions

    attraction_counts = [(name, len(city_attractions[name])) for name, *_ in resolved]
    day_allocation = allocate_days(attraction_counts, trip_length)
    print(f"DEBUG: Day allocation: {day_allocation}")

    ordered = find_best_order(resolved)
    print(f"DEBUG: Optimal order: {[c[0] for c in ordered]}")

    main_city_names = [c[0] for c in ordered]
    city_blocks = []

    for idx, (name, country_code, lat, lon) in enumerate(ordered):
        days = day_allocation.get(name, 1)
        attractions_str = ", ".join(city_attractions[name]) if city_attractions[name] else "No specific attractions found"

        if days >= 2:
            day_trips = get_day_trip_candidates(lat, lon, exclude_names=main_city_names, interests=interests)
            if day_trips:
                day_trip_lines = []
                for dt_name, dt_dist, dt_time, dt_attractions in day_trips:
                    day_trip_lines.append(
                        f"{dt_name} ({dt_dist}km, ~{dt_time} by train) — {dt_attractions}"
                    )
                day_trip_str = "; ".join(day_trip_lines)
            else:
                day_trip_str = "None"
        else:
            day_trip_str = "None — not enough days"

        if idx == 0:
            travel_note = "Starting city"
        else:
            prev = ordered[idx - 1]
            dist = round(haversine(prev[2], prev[3], lat, lon))
            total_minutes = round(dist / TRAIN_KMH * 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if hours == 0:
                time_str = f"{minutes}min"
            elif minutes == 0:
                time_str = f"{hours}h"
            else:
                time_str = f"{hours}h {minutes}min"
            travel_note = f"~{dist}km from {prev[0]}, ~{time_str} by train"

        city_blocks.append(
            f"- {name} ({country_code}) — {days} day(s)\n"
            f"  Travel from previous: {travel_note}\n"
            f"  Attractions: {attractions_str}\n"
            f"  Day trip options (only suggest if days allow): {day_trip_str}"
        )

    city_blocks_str = "\n".join(city_blocks)

    prompt_path = os.path.join(
        os.path.dirname(__file__), "../llm/prompts/planner_prompt.txt"
    )
    with open(prompt_path) as f:
        prompt_template = f.read()

    prompt = prompt_template.format(
        trip_length=trip_length,
        interests=", ".join(interests),
        city_blocks=city_blocks_str
    )

    print("DEBUG: About to call LLM...")
    yield from stream_llm(prompt)
    print("DEBUG: LLM stream finished")
