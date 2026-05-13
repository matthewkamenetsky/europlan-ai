import os
import requests
import itertools
from utils.travel_utils import haversine, format_travel_time

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


def attraction_limit(num_interests: int, days_in_city: int = 1) -> int:
    """Dynamic attraction cap: scales with interest count and days allocated.
    Floor of 5, ceiling of 60 to keep prompts sane."""
    return min(10 + num_interests * 3 + days_in_city * 5, 60)


def get_city(city_name: str, db):
    cleaned = city_name.strip()
    if not cleaned:
        return None
    cursor = db.cursor()
    # Try exact name/asciiname match first to avoid alternate name collisions
    cursor.execute("""
        SELECT name, country_code, lat, lon FROM cities
        WHERE LOWER(name) = LOWER(?)
           OR LOWER(asciiname) = LOWER(?)
        LIMIT 1
    """, (cleaned, cleaned))
    row = cursor.fetchone()
    if row:
        return row
    # Fall back to alternatenames only if no exact match found
    cursor.execute("""
        SELECT name, country_code, lat, lon FROM cities
        WHERE LOWER(',' || alternatenames || ',') LIKE LOWER(?)
        LIMIT 1
    """, (f"%,{cleaned},%",))
    return cursor.fetchone()


def get_attractions(lat: float, lon: float, interests: list[str], radius: int = 10000, limit: int = None, days_in_city: int = 1) -> list[str]:
    if limit is None:
        limit = attraction_limit(len(interests), days_in_city)
    kinds = ",".join([INTEREST_MAP[i] for i in interests if i in INTEREST_MAP]) or "cultural,historic,museums"
    try:
        response = requests.get(
            "https://api.opentripmap.com/0.1/en/places/radius",
            params={
                "radius": radius, "lon": lon, "lat": lat,
                "kinds": kinds, "rate": "3h", "format": "json",
                "limit": limit, "apikey": os.getenv("OPENTRIPMAP_KEY"),
            },
            timeout=10,
        )
        return [p.get("name") for p in response.json() if p.get("name")]
    except Exception as e:
        print(f"Failed to fetch attractions for ({lat}, {lon}): {e}")
        return []


def get_day_trip_candidates(lat: float, lon: float, exclude_names: list[str], interests: list[str], db, max_distance_km: int = 120):
    cursor = db.cursor()
    cursor.execute("SELECT name, country_code, lat, lon FROM cities")
    all_cities = cursor.fetchall()

    candidates = []
    for name, country_code, city_lat, city_lon in all_cities:
        if name in exclude_names:
            continue
        distance = haversine(lat, lon, city_lat, city_lon)
        if 10 < distance <= max_distance_km:
            candidates.append((name, round(distance), format_travel_time(distance), city_lat, city_lon))

    candidates.sort(key=lambda x: x[1])

    result = []
    for name, distance, time_str, city_lat, city_lon in candidates[:5]:
        attractions = get_attractions(city_lat, city_lon, interests, limit=5)
        attractions_str = ", ".join(attractions) if attractions else "no specific attractions found"
        result.append((name, distance, time_str, attractions_str))

    return result


def allocate_days(city_attraction_counts: list[tuple[str, int]], trip_length: int) -> dict[str, int]:
    n = len(city_attraction_counts)
    if n == 0:
        return {}
    if trip_length <= n:
        return {name: 1 for name, _ in city_attraction_counts[:trip_length]}

    base = {name: 1 for name, _ in city_attraction_counts}
    remaining = trip_length - n
    total_attractions = sum(count for _, count in city_attraction_counts) or 1
    extras = {name: round(count / total_attractions * remaining) for name, count in city_attraction_counts}

    diff = remaining - sum(extras.values())
    if diff != 0:
        extras[max(city_attraction_counts, key=lambda x: x[1])[0]] += diff

    return {name: base[name] + extras[name] for name in base}


def route_distance(ordered: list) -> float:
    return sum(
        haversine(ordered[i][2], ordered[i][3], ordered[i+1][2], ordered[i+1][3])
        for i in range(len(ordered) - 1)
    )


def find_best_order(resolved: list) -> list:
    if len(resolved) <= 1:
        return resolved

    if len(resolved) <= 8:
        return list(min(itertools.permutations(resolved), key=lambda p: route_distance(list(p))))

    best_order, best_distance = None, float("inf")
    for start in resolved:
        ordered, remaining = [start], [c for c in resolved if c != start]
        while remaining:
            nearest = min(remaining, key=lambda c: haversine(ordered[-1][2], ordered[-1][3], c[2], c[3]))
            ordered.append(nearest)
            remaining.remove(nearest)
        dist = route_distance(ordered)
        if dist < best_distance:
            best_order, best_distance = ordered, dist
    return best_order