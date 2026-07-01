from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class vehicle(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    startLat: float = Field(ge=-90, le=90)
    startLng: float = Field(ge=-180, le=180)
    capacityKg: float = Field(ge=0)
    currentLoadKg: float = Field(ge=0)
    
class Destination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["TPA", "RDF", "TPS_3R"]
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    demandKg: float = Field(ge=0)
    priority: int
    serviceMinutes: int = Field(ge=0)
    historicalVolumeAvg: float = Field(ge=0)
    lowVolumeFlag: bool
    
    
class DistanceMatrixRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    mode: Literal["mapbox", "haversine_fallback"]
    rows: list[DistanceMatrixRow]
    
class DistanceMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["mapbox", "haversine_fallback"]
    rows: list[DistanceMatrixRow]


class Constraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maxRouteMinutes: int = Field(gt=0)
    finalDepotId: str
    skipLowVolume: bool
    lowVolumeThreshold: float = Field(ge=0, le=1)


class SolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["daily_plan", "swarm_recovery"]
    vehicles: list[Vehicle]
    destinations: list[Destination]
    distanceMatrix: DistanceMatrix
    constraints: Constraints