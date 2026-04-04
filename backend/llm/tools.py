"""
backend/llm/tools.py

Cerebras-native tool definitions and dispatcher for the agentic planner path.

Tool JSON schemas are passed to tool_completion() in client.py.
The dispatcher maps tool names -> actual Python functions in geodata.py
and travel_utils.py. No logic lives here — this is pure glue.

Key signature notes (from real source):
  - get_city(city_name, db)         needs a db connection
  - get_attractions(lat, lon, interests, radius, limit, days_in_city)
  - get_day_trip_candidates(lat, lon, exclude_names, interests, db)
  - allocate_days(city_attraction_counts: list[tuple[str,int]], trip_length)
  - find_best_order(resolved: list)  resolved items are (name, cc, lat, lon) tuples
  - haversine(lat1, lon1, lat2, lon2)
  - format_travel_time(dist_km)
"""

import json
from services.geodata import (
    get_city,
    get_attractions,
    get_day_trip_candidates,
    allocate_days,
    find_best_order,
)
from utils.travel_utils import haversine, format_travel_time
from services.trips_db import get_db


# ---------------------------------------------------------------------------
# Tool schemas (Cerebras / OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_city",
            "description": (
                "Look up a city by name and return its name, country_code, lat, and lon. "
                "Call this first for every city before fetching attractions or computing distances."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "City name to look up, e.g. 'Paris' or 'Amsterdam'.",
                    }
                },
                "required": ["city_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_attractions",
            "description": (
                "Fetch real attractions near a city for a list of ranked interest categories. "
                "Returns a flat list of attraction name strings. "
                "Always pass interests in priority order — most important first. "
                "The number of attractions returned scales with len(interests) and days_in_city."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "City latitude."},
                    "lon": {"type": "number", "description": "City longitude."},
                    "interests": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ranked interest categories, e.g. ['history', 'art', 'food']. Most important first.",
                    },
                    "days_in_city": {
                        "type": "integer",
                        "description": "Days the traveller spends in this city. Scales the attraction cap.",
                    },
                },
                "required": ["lat", "lon", "interests", "days_in_city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_day_trip_candidates",
            "description": (
                "Find cities within ~120km of a base city suitable for a day trip. "
                "Pass all main trip cities in exclude_names so they are not suggested. "
                "Returns a list of dicts: {name, distance_km, travel_time, attractions}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude of the base city."},
                    "lon": {"type": "number", "description": "Longitude of the base city."},
                    "exclude_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "City names already in the main itinerary to exclude.",
                    },
                    "interests": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ranked user interests to filter candidate attractions.",
                    },
                },
                "required": ["lat", "lon", "exclude_names", "interests"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "allocate_days",
            "description": (
                "Distribute total trip days across cities weighted by attraction density. "
                "city_names and attraction_counts must be the same length and same order. "
                "Returns a dict mapping city name -> days allocated."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered list of city names.",
                    },
                    "attraction_counts": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Attraction count per city, same order as city_names.",
                    },
                    "trip_length": {
                        "type": "integer",
                        "description": "Total trip days to distribute.",
                    },
                },
                "required": ["city_names", "attraction_counts", "trip_length"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "optimise_city_order",
            "description": (
                "Find the shortest open-route visit order through a list of cities. "
                "Each city must have keys: name, country_code, lat, lon "
                "(exactly as returned by lookup_city). "
                "Uses brute-force TSP for <=8 cities, nearest-neighbour for 9+. "
                "Returns cities reordered for minimum total travel distance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name":         {"type": "string"},
                                "country_code": {"type": "string"},
                                "lat":          {"type": "number"},
                                "lon":          {"type": "number"},
                            },
                            "required": ["name", "country_code", "lat", "lon"],
                        },
                        "description": "List of city objects from lookup_city results.",
                    }
                },
                "required": ["cities"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_distance",
            "description": (
                "Compute the great-circle distance in km between two lat/lon points "
                "and return an estimated train travel time (assuming 120 km/h average). "
                "Use for every city-to-city leg to get accurate travel day information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lat1": {"type": "number"},
                    "lon1": {"type": "number"},
                    "lat2": {"type": "number"},
                    "lon2": {"type": "number"},
                },
                "required": ["lat1", "lon1", "lat2", "lon2"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch(tool_name: str, args: dict) -> str:
    """
    Called by tool_completion() in client.py for each tool call the LLM requests.
    Returns a JSON string that gets appended as a tool result message.
    """
    try:
        if tool_name == "lookup_city":
            with get_db() as db:
                result = get_city(args["city_name"], db)
            if result is None:
                return json.dumps({"error": f"City '{args['city_name']}' not found."})
            name, country_code, lat, lon = result
            return json.dumps({"name": name, "country_code": country_code, "lat": lat, "lon": lon})

        elif tool_name == "fetch_attractions":
            attractions = get_attractions(
                lat=args["lat"],
                lon=args["lon"],
                interests=args["interests"],
                days_in_city=args.get("days_in_city", 1),
            )
            return json.dumps({"attractions": attractions})

        elif tool_name == "fetch_day_trip_candidates":
            with get_db() as db:
                candidates = get_day_trip_candidates(
                    lat=args["lat"],
                    lon=args["lon"],
                    exclude_names=args.get("exclude_names", []),
                    interests=args["interests"],
                    db=db,
                )
            return json.dumps({
                "candidates": [
                    {"name": name, "distance_km": dist, "travel_time": t, "attractions": a}
                    for name, dist, t, a in candidates
                ]
            })

        elif tool_name == "allocate_days":
            # allocate_days() expects list[tuple[str, int]]
            pairs = list(zip(args["city_names"], args["attraction_counts"]))
            allocation = allocate_days(pairs, args["trip_length"])
            return json.dumps({"allocation": allocation})

        elif tool_name == "optimise_city_order":
            # find_best_order() expects list of (name, country_code, lat, lon) tuples
            tuples = [
                (c["name"], c["country_code"], c["lat"], c["lon"])
                for c in args["cities"]
            ]
            ordered = find_best_order(tuples)
            return json.dumps({
                "ordered_cities": [
                    {"name": n, "country_code": cc, "lat": lat, "lon": lon}
                    for n, cc, lat, lon in ordered
                ]
            })

        elif tool_name == "compute_distance":
            dist_km = haversine(args["lat1"], args["lon1"], args["lat2"], args["lon2"])
            dist_km_rounded = round(dist_km)
            return json.dumps({
                "distance_km": dist_km_rounded,
                "estimated_train_time": format_travel_time(dist_km_rounded),
            })

        else:
            return json.dumps({"error": f"Unknown tool: '{tool_name}'"})

    except Exception as e:
        return json.dumps({"error": f"Tool '{tool_name}' failed: {str(e)}"})