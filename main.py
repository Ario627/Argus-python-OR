from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import logger
from app.routers import health, solve

@asynccontextmanager
async def lifespan(app: FastAPI):
  
    logger.info("ARGUS Optimization Service starting | MOCK_MODE=%s", settings.MOCK_MODE)
    
    yield  
    
    logger.info("ARGUS Optimization Service shutting down")

app = FastAPI(
    title="ARGUS Optimization Service", 
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(health.router)
app.include_router(solve.router)
register_exception_handlers(app)
