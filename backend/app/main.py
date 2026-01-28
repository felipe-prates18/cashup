import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .database import Base, engine
from .routers import accounts, cashflow, categories, reconciliation, reports, titles, transactions, users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cashup")

app = FastAPI(title="CashUp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def _sanitize_errors(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return [_sanitize_errors(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_errors(item) for key, item in value.items()}
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    sanitized = _sanitize_errors(exc.errors())
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, sanitized)
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(sanitized)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(titles.router)
app.include_router(cashflow.router)
app.include_router(reconciliation.router)
app.include_router(reports.router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
