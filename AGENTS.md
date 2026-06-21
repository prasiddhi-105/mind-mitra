# AGENTS.md — MindMitra

## Project layout

- **Backend**: FastAPI app at `app/`, entrypoint `app.main:app`
- **Frontend**: React 19 + Vite + TypeScript at `mindmitra-frontend/`
- **Scripts**: One-off utilities in `scripts/` (DB init, cache tests, emotion fallback test)
- **Tests**: `tests/` (pytest, backend only — no frontend tests yet)
- **All API routes** are prefixed `/api/v1/` (`app/api/v1/api.py` wires them)
- **No CI/CD workflows** exist yet (`.github/workflows/` is empty)

## Commands

### Backend
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload          # dev server on :8000
pytest                                  # run tests (needs no real DB)
pytest --cov=app                        # coverage (enforced at 80% in pytest.ini)
pytest tests/test_auth_register.py      # run single file
pytest -k "test_login"                  # run matching test name
black .                                 # format
flake8 app/                             # lint
mypy app/                               # typecheck
```

### Frontend
```bash
cd mindmitra-frontend
npm install
npm run dev                             # Vite dev server on :5173
npm run lint                            # ESLint
npm run build                           # tsc + vite build
```

### Docker
```bash
docker compose up --build               # API + MongoDB + Redis + Celery
```

## Key gotchas

- **`PYTHONPATH=/app`** is set in the Dockerfile. If running outside Docker, run from the repo root so `app.*` imports resolve.
- **Tests use `mongomock-motor`**, not a real MongoDB. The test app in `conftest.py` is a minimal FastAPI app with only auth routes to avoid importing heavy ML libraries (DeepFace, torch, transformers). New test files that need more endpoints should follow this pattern.
- **pytest.ini `--cov-fail-under=80`** will fail CI if coverage drops. Coverage is measured only on specific modules listed in `pytest.ini`.
- **`app/main.py` line 41 has a syntax error** — `tags_metadata` list is incomplete (missing closing `}` and `]`). Fix before running the full app.
- **Root `package.json`** is not a workspace — it only holds shared i18next deps and Tailwind/PostCSS. The real frontend app is in `mindmitra-frontend/`.
- **Frontend dev server** proxies `/api` and `/uploads` to `localhost:8000` via Vite config (`mindmitra-frontend/vite.config.ts`).
- **`.gitignore` has unresolved merge conflict markers** (lines 1, 163, 317–320). Fix before committing.
- **Env vars**: Copy `env.example` → `.env`. The app needs MongoDB, Redis, Firebase, and Twilio keys to start. Many features are optional (Twilio, Firebase) but MongoDB and Redis are required.
- **`uploads/` directory** is created at startup if missing (lifespan handler in `app/main.py`).
- **Auth flow**: JWT bearer tokens. Register → Login → use `Authorization: Bearer <token>`. Refresh at `/api/v1/auth/refresh`. Login uses `data=` (form), not `json=`.
- **Branch naming**: `feat/your-feature-name` or `fix/bug-name` (conventional commits).
- **SSoC26**: Open-source contribution program. Issues are not pre-assigned; best PR wins.

## Available skills (`.agents/skills/`)

| Skill | What it does in this repo |
|---|---|
| `conventional-commit` | Generates properly formatted commit messages following Conventional Commits spec (`feat:`, `fix:`, `docs:`, etc.) — run when committing code |
| `docker-expert` | Reviews and improves `Dockerfile` + `docker-compose.yml` — covers layer caching, multi-stage builds, security hardening, health checks, and resource limits for the API + MongoDB + Redis + Celery stack |
| `fastapi-expert` | Builds FastAPI endpoints, Pydantic V2 schemas, async DB operations, and JWT auth — directly applicable to `app/api/v1/` routes and `app/services/` layer |
| `python-design-patterns` | Applies KISS, SRP, and composition patterns to Python code — useful when refactoring services in `app/services/` or adding new features to avoid God classes |
| `wcag-audit-patterns` | Audits the React frontend (`mindmitra-frontend/`) for WCAG 2.2 accessibility violations and provides fixes for contrast, keyboard nav, ARIA, and screen reader support |

## Architecture notes

- **Services layer** (`app/services/`): Business logic separated from route handlers. Auth, journal, chatbot, emotion analysis, SOS, notifications, cache, admin, depression flags.
- **Models** (`app/models/`): Pydantic models for request/response schemas.
- **Core** (`app/core/`): Config (pydantic-settings), database (Motor async), Redis, logging, middleware (rate limiting via slowapi).
- **Emotion detection**: VADER + BERT for text, DeepFace for images, librosa for audio. Models are heavy — import lazily where possible.
- **Celery workers** run in separate Docker containers for background tasks (SOS alerts, notifications).
- **MongoDB schema** is initialized via `scripts/init-mongo.js` (run by Docker entrypoint).
