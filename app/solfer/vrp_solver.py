import time
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from app.config import settings

_TIME_LIMIT_MAP = {
    "daily_plan": "SOLVER_TIME_LIMIT_DAILY_MS",
    "swarm_recovery": "SOLVER_TIME_LIMIT_RECOVERY_MS",
}

_FIRST_STRATEGY = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

def solve(routing, mode: str) -> tuple:
    time_limit_ms = getattr(settings, _TIME_LIMIT_MAP[mode])
    
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = _FIRST_STRATEGY
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromMilliseconds(time_limit_ms)

    start = time.perf_counter()
    solution = routing.SolveWithParameters(params)
    duration_ms = int((time.perf_counter() - start) * 1000)

    return solution, duration_ms, time_limit_ms

