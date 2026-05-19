# TaskFlow API

A secure, scalable REST API for task management with JWT authentication and role-based access control, built with FastAPI and PostgreSQL.

---

## Features

- **JWT Authentication** — access + refresh token flow with bcrypt password hashing
- **Role-Based Access Control** — `user` and `admin` roles with route-level enforcement
- **Full Task CRUD** — create, read, update (PATCH), and soft-delete tasks
- **Pagination & Filtering** — filter by status/priority, paginate results
- **Input Validation** — Pydantic v2 schemas with custom validators
- **Structured Logging** — every request traced with request-id and duration
- **Auto API Docs** — Swagger UI at `/docs`, ReDoc at `/redoc`
- **Docker Ready** — one-command setup with PostgreSQL

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| Validation | Pydantic v2 |
| Logging | structlog |
| Testing | pytest + httpx |
| Deployment | Docker + docker-compose |

---

## Quick Start

### Option A — Docker (Recommended)

```bash
git clone <your-repo-url>
cd taskflow
cp .env.example .env          # edit SECRET_KEY in .env
docker-compose up --build
```

API is live at **http://localhost:8000**  
Swagger docs at **http://localhost:8000/docs**

### Option B — Local setup

```bash
# 1. Clone and install dependencies
git clone <your-repo-url>
cd taskflow
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials and SECRET_KEY

# 3. Run the server (tables auto-created on first run)
uvicorn app.main:app --reload
```

### Frontend

Open `frontend/index.html` in your browser (no build step needed).  
Make sure the backend is running on `http://localhost:8000`.

---

## Project Structure

```
taskflow/
├── app/
│   ├── api/
│   │   ├── deps.py              # Auth dependencies (get_current_user, require_admin)
│   │   └── v1/
│   │       ├── auth.py          # /auth — register, login, refresh, me, logout
│   │       ├── tasks.py         # /tasks — full CRUD
│   │       └── users.py         # /users — admin user management
│   ├── core/
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── security.py          # JWT + bcrypt helpers
│   │   └── logging.py           # structlog setup
│   ├── middleware/
│   │   └── logging.py           # Request logging middleware
│   ├── models/
│   │   └── models.py            # User, Task SQLAlchemy models
│   ├── schemas/
│   │   └── schemas.py           # Pydantic request/response schemas
│   └── main.py                  # FastAPI app, CORS, routers, lifespan
├── tests/
│   ├── conftest.py              # Fixtures, SQLite test DB
│   ├── test_auth.py             # Auth endpoint tests
│   └── test_tasks.py            # Task CRUD tests
├── frontend/
│   └── index.html               # Single-file React UI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## API Reference

All endpoints are versioned under `/api/v1/`.

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Register new user |
| POST | `/auth/login` | — | Login, get tokens |
| POST | `/auth/refresh` | — | Refresh access token |
| GET | `/auth/me` | ✅ | Get current user |
| POST | `/auth/logout` | ✅ | Logout (invalidate client-side) |

### Tasks

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/tasks/` | ✅ | user | Create task |
| GET | `/tasks/` | ✅ | user | List own tasks (paginated, filterable) |
| GET | `/tasks/{id}` | ✅ | user | Get single task |
| PATCH | `/tasks/{id}` | ✅ | user | Update task |
| DELETE | `/tasks/{id}` | ✅ | user | Soft-delete task |
| GET | `/tasks/admin/all` | ✅ | admin | List ALL tasks |

**Query Parameters for GET /tasks/**
- `page` (int, default 1)
- `page_size` (int, default 10, max 100)
- `status` (todo | in_progress | done)
- `priority` (low | medium | high)

### Users (Admin only)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/` | admin | List all users |
| GET | `/users/{id}` | admin | Get user by ID |
| PATCH | `/users/{id}` | admin | Update user (role, status) |
| DELETE | `/users/{id}` | admin | Deactivate user |

---

## Database Schema

```sql
-- Users
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    username        VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            ENUM('user','admin') DEFAULT 'user',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE tasks (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      ENUM('todo','in_progress','done') DEFAULT 'todo',
    priority    ENUM('low','medium','high') DEFAULT 'medium',
    due_date    TIMESTAMPTZ,
    is_deleted  BOOLEAN DEFAULT FALSE,   -- soft delete
    owner_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Running Tests

```bash
pytest                      # run all tests
pytest -v                   # verbose output
pytest --cov=app tests/     # with coverage report
pytest tests/test_auth.py   # specific file
```

Tests use an in-memory SQLite database and do not require a running Postgres instance.

---

## Security Practices

| Practice | Implementation |
|----------|---------------|
| Password hashing | bcrypt via passlib |
| JWT signing | HS256 with configurable secret |
| Token expiry | Access: 30 min / Refresh: 7 days |
| Input validation | Pydantic v2 with strict types |
| Role enforcement | Dependency injection at route level |
| Soft deletes | Tasks are never hard-deleted |
| CORS | Configured for specific origins |

---

## Scalability Note

### Current Architecture
Single FastAPI instance → PostgreSQL

### Horizontal Scaling Path

```
           Load Balancer (nginx / AWS ALB)
                    │
        ┌───────────┼───────────┐
     API Pod 1   API Pod 2   API Pod 3    ← stateless FastAPI workers
        └───────────┼───────────┘
                    │
         PostgreSQL (Primary/Replica)
```

**Why this scales:**
- **Stateless API** — JWT tokens carry all session state; any pod can serve any request
- **Connection pooling** — SQLAlchemy pool_size=10 / max_overflow=20 per pod; add PgBouncer for 1000s of pods
- **Read replicas** — Route `GET` queries to read replicas via SQLAlchemy multiple engines

### Caching Layer (Redis)
```python
# Add to list endpoints:
cache_key = f"tasks:user:{user_id}:page:{page}"
cached = await redis.get(cache_key)
if cached: return json.loads(cached)
```
- Cache task list results with 60s TTL
- Invalidate on create/update/delete

### Microservices Split (future)
| Service | Responsibility |
|---------|---------------|
| auth-service | JWT, users, sessions |
| task-service | CRUD, business logic |
| notification-service | Due-date alerts, emails |

### Additional Production Recommendations
- **Rate limiting** — SlowAPI (already in requirements) or nginx `limit_req`
- **Token blacklist** — Store logged-out JWTs in Redis until expiry
- **Database migrations** — Use Alembic instead of `create_all()`
- **Observability** — Export structlog to Datadog / Grafana Loki
- **CI/CD** — GitHub Actions: lint → test → build Docker → deploy

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `SECRET_KEY` | — | JWT signing secret (min 32 chars) |
| `ALGORITHM` | HS256 | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token TTL |
| `ENVIRONMENT` | development | development / production / testing |

---

## Making Your First Request

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","username":"yourname","password":"Password1"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"Password1"}'

# 3. Create a task (use token from step 2)
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"My first task","priority":"high"}'
```

Or just open the Swagger UI at **http://localhost:8000/docs** — it has a built-in "Authorize" button.
