"""
Europlan-AI MCP Server
----------------------
Exposes geographic lookup, attraction retrieval, and distance calculation
as MCP-compliant tools. Run alongside the FastAPI app:

    python backend/mcp_server.py

The LLM can then call these tools dynamically during itinerary generation
rather than receiving a pre-built context block.
"""

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from services.geodata import (
    get_city as _get_city,
    get_attractions as _get_attractions,
    get_day_trip_candidates as _get_day_trip_candidates,
    allocate_days as _allocate_days,
    find_best_order as _find_best_order,
)
from utils.travel_utils import haversine as _haversine, format_travel_time as _format_travel_time
from services.trips_db import get_db

mcp = FastMCP("europlan")

@mcp.tool()
def lookup_city(city_name: str) -> dict:
    """Look up a city by name and return its coordinates and country code.
    Use this first for every city before fetching attractions or computing distances.

    Returns a dict with keys: name, country_code, lat, lon.
    Returns None if the city is not found in the Schengen database.
    """
    with get_db() as db:
        result = _get_city(city_name, db)
    if result is None:
        return {"error": f"City '{city_name}' not found in the Schengen database."}
    name, country_code, lat, lon = result
    return {"name": name, "country_code": country_code, "lat": lat, "lon": lon}


@mcp.tool()
def fetch_attractions(
    lat: float,
    lon: float,
    interests: list[str],
    days_in_city: int = 1,
) -> list[str]:
    """Fetch real attractions near a city for a given list of ranked interests.

    Attractions are filtered to those with complete data and a Wikipedia article (rate=3h).
    The number of attractions returned scales with the number of interests and days allocated.
    Always pass interests in priority order — most important first.

    Returns a list of attraction name strings.
    """
    return _get_attractions(lat, lon, interests, days_in_city=days_in_city)


@mcp.tool()
def fetch_day_trip_candidates(
    lat: float,
    lon: float,
    exclude_names: list[str],
    interests: list[str],
) -> list[dict]:
    """Find nearby cities suitable for day trips from a base city (within 120km).

    exclude_names should contain all main trip cities so they are not suggested as day trips.

    Returns a list of dicts, each with: name, distance_km, travel_time, attractions.
    """
    with get_db() as db:
        candidates = _get_day_trip_candidates(lat, lon, exclude_names, interests, db)
    return [
        {"name": name, "distance_km": dist, "travel_time": time_str, "attractions": attractions}
        for name, dist, time_str, attractions in candidates
    ]


@mcp.tool()
def allocate_days(
    city_names: list[str],
    attraction_counts: list[int],
    trip_length: int,
) -> dict[str, int]:
    """Distribute trip days across cities weighted by their attraction counts.

    city_names and attraction_counts must be the same length and in the same order.
    trip_length is the total number of days for the trip.

    Returns a dict mapping city name → number of days allocated.
    """
    pairs = list(zip(city_names, attraction_counts))
    return _allocate_days(pairs, trip_length)


@mcp.tool()
def optimise_city_order(cities: list[dict]) -> list[dict]:
    """Find the shortest travel route through a list of cities (open TSP).

    Each city dict must have keys: name, country_code, lat, lon
    (as returned by lookup_city).

    Uses brute-force for up to 8 cities, nearest-neighbour heuristic for 9+.
    Returns the cities list reordered for minimum total travel distance.
    """
    tuples = [(c["name"], c["country_code"], c["lat"], c["lon"]) for c in cities]
    ordered = _find_best_order(tuples)
    return [{"name": n, "country_code": cc, "lat": lat, "lon": lon} for n, cc, lat, lon in ordered]


@mcp.tool()
def compute_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> dict:
    """Compute the great-circle distance between two coordinates using the Haversine formula.

    Returns distance in km and a human-readable estimated train travel time.
    Assumes an average train speed of 120 km/h.
    """
    dist = round(_haversine(lat1, lon1, lat2, lon2))
    return {
        "distance_km": dist,
        "estimated_train_time": _format_travel_time(dist),
    }


if __name__ == "__main__":
    mcp.run()