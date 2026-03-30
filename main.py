# app/main.py
# ──────────────────────────────────────────────────────────────
# FastAPI application entry point.
# Registers all routers and handles startup/shutdown lifecycle
# events (MongoDB connection pool).
# ──────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.connection import connect_db, close_db
from app.routes import story


# ── Lifespan: open / close the MongoDB connection pool ────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open resources on startup, release on shutdown."""
    await connect_db()
    yield
    await close_db()


# ── Application factory ───────────────────────────────────────
app = FastAPI(
    title="AI Novel Generator",
    description=(
        "A production-ready backend that generates full novels "
        "with characters, chapters, and style consistency using Claude AI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (open for local dev; lock down in production) ────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──────────────────────────────────────────
app.include_router(story.router, tags=["Story"])


# ── Health-check ──────────────────────────────────────────────
@app.get("/", summary="Health check")
async def root():
    return {"status": "ok", "message": "AI Novel Generator is running 📖"}
