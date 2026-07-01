from typing import Literal
from pydantic import BaseModel


class Stop(BaseModel):
    destId: str
    order: int
    etaEpoch: int
    cumulativeKm: float


class Route(BaseModel):
    vehicleId: str
    stops: list[Stop]
    totalKm: float
    totalMinutes: int


class SkippedDestination(BaseModel):
    destId: str
    reason: str


class SolveResponse(BaseModel):
    status: Literal["OK", "FEASIBLE", "NO_SOLUTION"]
    routes: list[Route]
    skipped: list[SkippedDestination]
    solverDurationMs: int
