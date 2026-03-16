from fastapi import APIRouter
from pydantic import BaseModel
from services.planner import plan_trip

router = APIRouter()

class TripRequest(BaseModel):
    starting_city: str
    trip_length: int
    interests: list[str]

@router.post("/plan-trip")
def plan_trip_route(request: TripRequest):
    return plan_trip(
        request.starting_city,
        request.trip_length,
        request.interests
    )