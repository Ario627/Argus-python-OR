import random
import time

from app.schemas.request import SolveRequest
from app.schemas.response import Route, SkippedDestination, SolveResponse, Stop

def _build_lookup(request: SolveRequest) -> dict[tuple[str, str], dict]:
    return {(r.from_, r.to): {"meters": r.meters, "seconds": r.seconds} for r in request.distanceMatrix.rows}

def _avg_meters(lookup: dict) -> float:
    return sum(r["meters"] for r in lookup.values()) / len(lookup) if lookup else 1000.0


def _avg_seconds(lookup: dict) -> float:
    return sum(r["seconds"] for r in lookup.values()) / len(lookup) if lookup else 60.0


def _is_low_volume(dest, constraints) -> bool:
    return dest.historicalVolumeAvg < constraints.lowVolumeThreshold


def generate_stub(request: SolveRequest) -> SolveResponse:
    vehicles = request.vehicles
    destinations = request.destinations
    constraints = request.constraints
    v_count = len(vehicles)

    lookup = _build_lookup(request)
    fallback_m = _avg_meters(lookup)
    fallback_s = _avg_seconds(lookup)
    base_epoch = int(time.time())

    skip_low = request.mode == "daily_plan" and constraints.skipLowVolume

    assignments: dict[int, list] = {i: [] for i in range(v_count)}
    skipped: list[SkippedDestination] = []

    for i, dest in enumerate(destinations):
        v_idx = i % v_count
        if skip_low and _is_low_volume(dest, constraints) and i >= v_count:
            skipped.append(SkippedDestination(destId=dest.id, reason="low_volume"))
        else:
            assignments[v_idx].append(dest)

    routes: list[Route] = []
    for v_idx, dests in assignments.items():
        if not dests:
            continue
        stops: list[Stop] = []
        cum_km = 0.0
        cum_secs = 0
        for order, dest in enumerate(dests, 1):
            stops.append(Stop(
                destId=dest.id,
                order=order,
                etaEpoch=base_epoch + cum_secs,
                cumulativeKm=round(cum_km, 2),
            ))
            cum_secs += dest.serviceMinutes * 60
            if order < len(dests):
                next_dest = dests[order]
                key = (dest.id, next_dest.id)
                row = lookup.get(key, {})
                cum_km += row.get("meters", fallback_m) / 1000
                cum_secs += int(row.get("seconds", fallback_s))

        routes.append(Route(
            vehicleId=vehicles[v_idx].id,
            stops=stops,
            totalKm=round(cum_km, 2),
            totalMinutes=cum_secs // 60,
        ))

    return SolveResponse(
        status="OK",
        routes=routes,
        skipped=skipped,
        solverDurationMs=random.randint(50, 200),
    )