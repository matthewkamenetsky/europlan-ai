import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.planner import create_trip, create_regen_prompt, plan_trip_stream
from services.trips_db import save_itinerary, fetch_all_trips, fetch_trip, delete_trip

router = APIRouter()
executor = ThreadPoolExecutor()

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

class RegenDayRequest(BaseModel):
    trip_id: int
    day_number: int

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

async def stream_regen(prompt: str):
    loop = asyncio.get_event_loop()
    gen = plan_trip_stream(prompt)

    while True:
        token = await loop.run_in_executor(executor, _next, gen)
        if token is _DONE:
            break
        yield token

@router.post("/plan-trip")
async def plan_trip(request: TripRequest):
    result = create_trip(request.cities, request.trip_length, request.interests)
    if result is None:
        raise HTTPException(status_code=404, detail="One or more cities could not be found.")

    trip_id, prompt = result
    return StreamingResponse(
        stream_generator(trip_id, prompt),
        media_type="text/plain",
        headers={"X-Trip-Id": str(trip_id)},
    )

@router.post("/regen-day")
async def regen_day(request: RegenDayRequest):
    prompt = create_regen_prompt(request.trip_id, request.day_number)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Trip not found or cities could not be resolved.")

    return StreamingResponse(
        stream_regen(prompt),
        media_type="text/plain",
    )

@router.get("/trips")
def get_trips():
    return fetch_all_trips()

@router.get("/trips/{trip_id}")
def get_trip(trip_id: int):
    trip = fetch_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return trip

@router.delete("/trips/{trip_id}")
def delete_trip_route(trip_id: int):
    if not delete_trip(trip_id):
        raise HTTPException(status_code=404, detail="Trip not found.")
    return {"ok": True}