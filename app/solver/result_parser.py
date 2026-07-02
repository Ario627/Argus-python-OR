from ortools.constraint_solver import pywrapcp

from app.schemas.request import SolveRequest
from app.schemas.response import Route, SkippedDestination, SolveResponse, Stop

_FEASIBLE_MARGIN_MS = 500


def _determine_status(solution, duration_ms: int, time_limit_ms: int) -> str:
    if not solution:
        return "NO_SOLUTION"
    return "FEASIBLE" if duration_ms >= time_limit_ms - _FEASIBLE_MARGIN_MS else "OK"


def _build_lookups(request: SolveRequest) -> tuple[dict, dict, dict]:
    dist_lookup = {}
    time_lookup = {}
    for r in request.distanceMatrix.rows:
        dist_lookup[(r.from_, r.to)] = r.meters
        time_lookup[(r.from_, r.to)] = r.seconds
    dest_map = {d.id: d for d in request.destinations}
    return dist_lookup, time_lookup, dest_map


def _avg_meters(lookup: dict) -> float:
    return sum(lookup.values()) / len(lookup) if lookup else 1000.0


def _avg_seconds(lookup: dict) -> float:
    return sum(lookup.values()) / len(lookup) if lookup else 60.0


def _skip_reason(dest_id: str, dest_map: dict, constraints) -> str:
    dest = dest_map.get(dest_id)
    if dest and constraints.skipLowVolume and dest.historicalVolumeAvg < constraints.lowVolumeThreshold:
        return "low_volume"
    return "capacity_or_time"


def parse(
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    solution,
    request: SolveRequest,
    index_to_id: dict[int, str],
    duration_ms: int,
    time_limit_ms: int,
    base_epoch: int,
) -> SolveResponse:
    if not solution:
        return SolveResponse(status="NO_SOLUTION", routes=[], skipped=[], solverDurationMs=duration_ms)

    status = _determine_status(solution, duration_ms, time_limit_ms)
    dist_lookup, time_lookup, dest_map = _build_lookups(request)
    fallback_m = _avg_meters(dist_lookup)
    fallback_s = _avg_seconds(time_lookup)
    v_count = len(request.vehicles)
    all_dest_ids = set(dest_map.keys())

    routes: list[Route] = []
    visited: set[str] = set()

    for v_idx in range(v_count):
        stops: list[Stop] = []
        cum_km = 0.0
        cum_secs = 0
        order = 1
        index = routing.Start(v_idx)

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            dest_id = index_to_id.get(node, "")

            if node >= v_count and dest_id in dest_map:
                dest = dest_map[dest_id]
                visited.add(dest_id)
                stops.append(Stop(
                    destId=dest_id,
                    order=order,
                    etaEpoch=base_epoch + cum_secs,
                    cumulativeKm=round(cum_km, 2),
                ))
                cum_secs += dest.serviceMinutes * 60
                order += 1

            next_index = solution.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(next_index)
            from_id = index_to_id.get(node, "")
            to_id = index_to_id.get(next_node, "")
            cum_km += dist_lookup.get((from_id, to_id), fallback_m) / 1000
            cum_secs += int(time_lookup.get((from_id, to_id), fallback_s))
            index = next_index

        # Node "End" tidak pernah masuk badan loop di atas (loop berhenti sebelum
        # memprosesnya), padahal kalau finalDepotId sama dengan salah satu destinasi,
        # vehicle memang benar-benar berakhir/mengunjungi node itu. Tanpa ini, node
        # tersebut salah dianggap "skipped" walau sebenarnya dikunjungi.
        end_node = manager.IndexToNode(index)
        end_dest_id = index_to_id.get(end_node, "")
        if end_node >= v_count and end_dest_id in dest_map and end_dest_id not in visited:
            dest = dest_map[end_dest_id]
            visited.add(end_dest_id)
            stops.append(Stop(
                destId=end_dest_id,
                order=order,
                etaEpoch=base_epoch + cum_secs,
                cumulativeKm=round(cum_km, 2),
            ))
            order += 1

        if stops:
            routes.append(Route(
                vehicleId=request.vehicles[v_idx].id,
                stops=stops,
                totalKm=round(cum_km, 2),
                totalMinutes=cum_secs // 60,
            ))

    skipped = [
        SkippedDestination(destId=did, reason=_skip_reason(did, dest_map, request.constraints))
        for did in all_dest_ids - visited
    ]

    return SolveResponse(status=status, routes=routes, skipped=skipped, solverDurationMs=duration_ms)