import time
from fastapi import APIRouter
from app.config import settings
from app.core.exceptions import EmptyInputError
from app.core.logging_config import logger
from app.mock.stub_responses import generate_stub
from app.schemas.request import SolveRequest
from app.schemas.response import SolveResponse
from app.solver import model_builder, result_parser, vrp_solver

router = APIRouter()

def _validate_inputs(request: SolveRequest) -> None:
    if not request.vehicles:
        raise EmptyInputError("vehicles must not be empty")
    if not request.destinations:
        raise EmptyInputError("destinations must not be empty")


def _solve_real(request: SolveRequest) -> SolveResponse:
    manager, routing, index_to_id, _ = model_builder.build_model(request)
    solution, duration_ms, time_limit_ms = vrp_solver.solve(routing, request.mode, len(index_to_id))
    return result_parser.parse(
        manager, routing, solution, request,
        index_to_id, duration_ms, time_limit_ms, int(time.time()),
    )


@router.post("/solve", response_model=SolveResponse)
async def solve(request: SolveRequest) -> SolveResponse:
    _validate_inputs(request)

    if settings.MOCK_MODE:
        response = generate_stub(request)
    else:
        response = _solve_real(request)

    logger.info(
        "solve mode=%s vehicles=%d destinations=%d durationMs=%d status=%s",
        request.mode, len(request.vehicles), len(request.destinations),
        response.solverDurationMs, response.status,
    )
    return response