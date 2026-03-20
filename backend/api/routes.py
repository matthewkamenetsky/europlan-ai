import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from services.planner import plan_trip_stream

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


async def stream_generator(cities, trip_length, interests):
    loop = asyncio.get_event_loop()
    gen = plan_trip_stream(cities, trip_length, interests)
    while True:
        token = await loop.run_in_executor(executor, _next, gen)
        if token is _DONE:
            break
        yield token


@router.post("/plan-trip")
async def plan_trip(request: TripRequest):
    return StreamingResponse(
        stream_generator(request.cities, request.trip_length, request.interests),
        media_type="text/plain"
    )