from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from app.config import settings
from app.core.exceptions import IncompleteDistanceMatrixError
from app.schemas.request import SolveRequest

def _build_distance_lookup(request: SolveRequest) -> dict[tuple[str, str], dict]:
    return {(r.from_, r.to): {"meters": r.meters, "seconds": r.seconds} for r in request.distanceMatrix.rows}

def _resolve_depot(depot_id: str, dest_ids: list[str], v_count: int, d_count: int) -> tuple[int, bool]:
    if depot_id not in dest_ids:
        return v_count + dest_ids.index(depot_id), False
    return v_count + d_count, True

def _build_node_ids(vehicle_ids: list[str], dest_ids: list[str], depot_id: str, depot_is_new: bool) -> list[str]:
    ids = vehicle_ids + dest_ids
    if depot_is_new:
        ids.append(depot_id)
    return ids

def _validate_pairs(node_ids: list[str], lookup: dict) -> None:
    for from_id in node_ids:
        for to_id in node_ids:
            if from_id != to_id and (from_id, to_id) not in lookup:
                raise IncompleteDistanceMatrixError(f"missing distance row: {from_id} -> {to_id}")
            

def _build_metrices(
    num_nodes: int, node_ids: list[str], lookup: dict, destinations: list, v_count: int
) -> tuple[list[list[int]], list[list[int]]]:
    cost_matrix = [[0] * num_nodes for _ in range(num_nodes)]
    time_matrix = [[0] * num_nodes for _ in range(num_nodes)]
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i == j:
                continue
            row = lookup[(node_ids[i], node_ids[j])]
            secs = int(row["seconds"])
            cost_matrix[i][j] = secs
            service = 0
            if v_count <= j < v_count + len(destinations):
                service = destinations[j - v_count].serviceMinutes * 60
            time_matrix[i][j] = secs + service
    return cost_matrix, time_matrix


def _apply_disjunctions(routing, manager, destinations: list, v_count: int, skip_low_volume: bool, threshold: float) -> None:
    for i, dest in enumerate(destinations):
        node = v_count + i
        if skip_low_volume and dest.historicalVolumeAvg < threshold:
            routing.AddDisjunction([manager.NodeToIndex(node)], settings.LOW_VOLUME_SKIP_PENALTY)
        else:
            routing.AddDisjunction([manager.NodeToIndex(node)], settings.MANDATORY_PENALTY)


def build_model(
    request: SolveRequest,
) -> tuple[pywrapcp.RoutingIndexManager, pywrapcp.RoutingModel, dict[int, str], dict[str, int]]:
    vehicles = request.vehicles
    destinations = request.destinations
    constraints = request.constraints

    lookup = _build_distance_lookup(request)
    vehicle_ids = [v.id for v in vehicles]
    dest_ids = [d.id for d in destinations]

    depot_index, depot_is_new = _resolve_depot(constraints.finalDepotId, dest_ids, len(vehicle_ids), len(dest_ids))
    node_ids = _build_node_ids(vehicle_ids, dest_ids, constraints.finalDepotId, depot_is_new)
    _validate_pairs(node_ids, lookup)

    num_nodes = len(node_ids)
    starts = list(range(len(vehicle_ids)))
    ends = [depot_index] * len(vehicle_ids) if constraints.finalDepotId else starts

    manager = pywrapcp.RoutingIndexManager(num_nodes, len(vehicle_ids), starts, ends)
    routing = pywrapcp.RoutingModel(manager)

    index_to_id = {i: node_ids[i] for i in range(num_nodes)}
    cost_matrix, time_matrix = _build_matrices(num_nodes, node_ids, lookup, destinations, len(vehicle_ids))

    def cost_callback(from_index: int, to_index: int) -> int:
        return cost_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    cost_idx = routing.RegisterTransitCallback(cost_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(cost_idx)

    def demand_callback(from_index: int) -> int:
        node = manager.IndexToNode(from_index)
        if len(vehicle_ids) <= node < len(vehicle_ids) + len(destinations):
            return int(destinations[node - len(vehicle_ids)].demandKg)
        return 0

    demand_idx = routing.RegisterUnaryTransitCallback(demand_callback)
    capacities = [int(v.capacityKg - v.currentLoadKg) for v in vehicles]
    routing.AddDimensionWithVehicleCapacity(demand_idx, 0, capacities, True, "Capacity")

    def time_callback(from_index: int, to_index: int) -> int:
        return time_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    time_idx = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_idx, 30 * 60, constraints.maxRouteMinutes * 60, True, "Time")

    skip_low = request.mode == "daily_plan" and constraints.skipLowVolume
    _apply_disjunctions(routing, manager, destinations, len(vehicle_ids), skip_low, constraints.lowVolumeThreshold)

    return manager, routing, index_to_id, {nid: i for i, nid in enumerate(node_ids)}