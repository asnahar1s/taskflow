from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import auth, tasks, users
from app.core.database import Base, engine
from app.core.logging import logger, setup_logging
from app.middleware.logging import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Auto-create tables (use Alembic migrations in production)
    Base.metadata.create_all(bind=engine)
    logger.info("taskflow_started")
    yield
    logger.info("taskflow_stopped")


app = FastAPI(
    title="TaskFlow API",
    description="""
## TaskFlow REST API

A secure, scalable task management API with JWT authentication and role-based access control.

### Features
- 🔐 JWT Authentication (access + refresh tokens)
- 👤 Role-Based Access Control (user / admin)
- ✅ Full CRUD for Tasks with filtering & pagination
- 🛡️ Input validation & sanitization
- 📋 Structured logging with request tracing
- 📖 Auto-generated OpenAPI documentation

### Roles
| Role  | Capabilities |
|-------|-------------|
| user  | Manage own tasks |
| admin | Manage all tasks + users |
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Health check")
def health():
    return {"status": "ok", "version": "1.0.0"}
