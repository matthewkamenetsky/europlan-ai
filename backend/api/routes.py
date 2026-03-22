import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.planner import create_trip, plan_trip_stream, save_itinerary

router = APIRouter()
executor = ThreadPoolExecutor()

DB_PATH = "data/europlan.db"

_DONE = object()

def _next(gen):
    try:
        return next(gen)
    except StopIteration:
        return _DONE


class TripRequest(BaseModel):
    cities: list[str]
    trip_length: int
    interests: list[str]

    @field_validator("cities")
    @classmethod
    def at_least_one_city(cls, v):
        if not v:
            raise ValueError("At least one city must be provided.")
        return v

    @field_validator("trip_length")
    @classmethod
    def positive_trip_length(cls, v):
        if v < 1:
            raise ValueError("trip_length must be at least 1.")
        return v


async def stream_generator(trip_id: int, prompt: str):
    loop = asyncio.get_event_loop()
    gen = plan_trip_stream(prompt)
    accumulator = []

    while True:
        token = await loop.run_in_executor(executor, _next, gen)
        if token is _DONE:
            break
        accumulator.append(token)
        yield token

    full_itinerary = "".join(accumulator)
    await loop.run_in_executor(executor, save_itinerary, trip_id, full_itinerary)


@router.post("/plan-trip")
async def plan_trip(request: TripRequest):
    result = create_trip(request.cities, request.trip_length, request.interests)
    if result is None:
        raise HTTPException(status_code=404, detail="One or more cities could not be found.")

    trip_id, prompt = result

    return StreamingResponse(
        stream_generator(trip_id, prompt),
        media_type="text/plain",
        headers={"X-Trip-Id": str(trip_id)}
    )


@router.get("/trips")
def get_trips():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, cities, trip_length, interests, created_at
        FROM trips
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "cities": json.loads(row["cities"]),
            "trip_length": row["trip_length"],
            "interests": json.loads(row["interests"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.get("/trips/{trip_id}")
def get_trip(trip_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Trip not found.")

    return {
        "id": row["id"],
        "name": row["name"],
        "cities": json.loads(row["cities"]),
        "trip_length": row["trip_length"],
        "interests": json.loads(row["interests"]),
        "itinerary": row["itinerary"],
        "created_at": row["created_at"],
    }


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Trip not found.")

    return {"ok": True}