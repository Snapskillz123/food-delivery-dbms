import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.routers import analytics, orders, payments, restaurants, users

logging.basicConfig(level=settings.log_level)
app = FastAPI(title=settings.app_name, version="1.0.0", description="Database-first food delivery operations and analytics API")
for router in (users.router, restaurants.router, orders.router, payments.router, analytics.router):
    app.include_router(router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    logging.getLogger(__name__).warning("Database constraint rejected request: %s", exc.orig)
    return JSONResponse(status_code=409, content={"detail": "The request violates a uniqueness or data-integrity rule"})


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/site-assets", StaticFiles(directory=WEB_DIR / "assets"), name="site-assets")


@app.get("/", include_in_schema=False)
async def website():
    return FileResponse(WEB_DIR / "index.html")
