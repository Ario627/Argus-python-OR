from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.logging_config import logger

class EmptyInputError(Exception):
    pass

class IncompleteDistanceMatrixError(Exception):
    pass

class InfeasibleModelError(Exception):
    pass


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmptyInputError)
    async def _empty_input_handler(_: Request, exc: EmptyInputError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    
    @app.exception_handler(Exception)
    async def _generic_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "internal solver error"})