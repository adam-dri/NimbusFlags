# NimbusFlags Backend

Backend service for the NimbusFlags feature flags platform.

This folder contains the Flask application, PostgreSQL integration, migrations,
tests, and API documentation used by both:

- Machine clients (via API keys)
- A future React dashboard (via session tokens)

---

## Table of contents

- [Architecture](#architecture)
- [Data model](#data-model)
- [Authentication](#authentication)
- [API overview](#api-overview)
- [Running the backend](#running-the-backend)
- [Testing](#testing)
- [Security notes](#security-notes)
- [Roadmap (backend scope)](#roadmap-backend-scope)

---

## Architecture

### High-level flow

```text
HTTP Request
    ↓
Blueprints (routes)
    ↓
Services (business logic)
    ↓
Repositories (raw SQL)
    ↓
PostgreSQL
```

### Directory structure

```
backend/
├── app.py                     # Flask app factory + entry point
├── requirements.txt           # Python dependencies
│
├── blueprints/
│   ├── admin/
│   │   └── flags_admin.py     # /admin/flags/* endpoints
│   ├── auth/
│   │   └── auth.py            # /auth/login, /auth/logout
│   ├── clients.py             # /clients/signup, /clients/me
│   ├── flags_runtime.py       # /evaluate/ endpoint
│   ├── system.py              # /health/ endpoint
│   └── docs.py                # /docs, /openapi.yaml
│
├── services/
│   ├── auth_service.py        # API key decorator and helpers
│   ├── clients_service.py     # Registration, password hashing, client lookup
│   ├── flag_service.py        # Flag evaluation logic
│   └── sessions_service.py    # Session token creation / lookup / revocation
│
├── repositories/
│   ├── db.py                  # psycopg connection helper
│   ├── clients_repo.py        # clients table CRUD
│   └── postgres_flags_repo.py # flags table CRUD
│
├── validators/
│   └── json_validator.py      # JSON Schema validation wrapper
│
├── schemas/                   # JSON Schema files
│   ├── client_signup_request.schema.json
│   ├── flag_config.schema.json
│   ├── EvaluateRequest.schema.json
│   └── EvaluateResponse.schema.json
│
├── errors/
│   └── handlers.py            # Centralized HTTP error handling
│
├── docs/
│   └── openapi.yaml           # OpenAPI 3.1 specification
│
├── migrations/                # Alembic migrations
│   └── versions/
│
└── tests/                     # pytest integration + service tests
    ├── conftest.py
    ├── test_app.py
    └── test_clients_service.py
```

The backend deliberately uses raw SQL with psycopg in the repositories.
Alembic + SQLAlchemy are only used for migrations.

---

## Data model

### `clients` (tenants)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `email` | VARCHAR(255) | Unique, not null |
| `password_hash` | TEXT | bcrypt hash |
| `api_key_hash` | TEXT | SHA-256 hash of API key |
| `subscription_tier` | VARCHAR(50) | "free" (for now) |
| `active` | BOOLEAN | Account status |
| `created_at` | TIMESTAMPTZ | Registration timestamp (UTC) |

**Indexes:**
- `UNIQUE (email)`
- `INDEX (api_key_hash)`

### `flags` (feature flags per client)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `client_id` | UUID | FK to `clients.id` |
| `key` | VARCHAR(255) | Flag identifier (per client) |
| `enabled` | BOOLEAN | Global on/off switch |
| `conditions` | JSONB | Array of condition objects |
| `parameters` | JSONB | Extra data returned when enabled |
| `created_at` | TIMESTAMPTZ | Creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | Last update (UTC) |

**Important constraint:**
- `UNIQUE (client_id, key)` ensures multi-tenant isolation.

### `sessions` (dashboard logins)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `client_id` | UUID | FK to `clients.id` |
| `token_hash` | TEXT | SHA-256 hash of session token |
| `created_at` | TIMESTAMPTZ | Creation timestamp (UTC) |
| `expires_at` | TIMESTAMPTZ | Expiration timestamp (UTC) |
| `revoked_at` | TIMESTAMPTZ | Optional revocation timestamp (NULL if active) |

Today, sessions have a TTL of 1 day (`SESSION_TTL_DAYS = 1`).

---

## Authentication

There are two forms of authentication, serving different use cases.

### 1. API keys (machine-to-machine)

**Used for:**
- `/clients/me`
- `/admin/flags/*`
- `/evaluate/`

**Header:**
```http
X-Api-Key: nf_live_XXXXXXXXXXXXXXXXXXXXXXXX
```

**Flow:**
1. API key is generated once at `/clients/signup`.
2. Only a SHA-256 hash is stored in the database.
3. `auth_service.require_api_key`:
   - Reads `X-Api-Key`
   - Hashes it
   - Resolves the client from `clients.api_key_hash`
   - Exposes `g.client` / `g.client_id` to route handlers

### 2. Session tokens (dashboard login)

**Used by:**
- `/auth/login`
- `/auth/logout`
- Future React dashboard endpoints

**Header:**
```http
X-Session-Token: nsess_XXXXXXXXXXXXXXXXXXXXXXXX
```

**Flow:**

**`/auth/login`:**
- Validates email/password
- Creates a `sessions` row with a hashed token
- Returns raw session token to the frontend

**`/auth/logout`:**
- Reads `X-Session-Token`
- Hashes it and deletes the corresponding `sessions` row
- Idempotent (204 even if already removed)

For now, the admin API still uses API keys. Session tokens are in place so that the
React dashboard can use them in the next sprint.

---

## API overview

For the full OpenAPI spec, see:
- `docs/openapi.yaml`
- `GET /openapi.yaml`
- `GET /docs` (Swagger UI)

**Summary of main endpoints:**

### System

**`GET /health/`**  
Liveness probe. Returns `{"status": "ok"}`.

### Clients

**`POST /clients/signup`**  
Register a new tenant and return:
- `client` object
- `api_key` (shown only once)

**`GET /clients/me`**  
Requires `X-Api-Key`. Returns the current client profile.

### Flags (admin)

Requires `X-Api-Key` for all calls.

**`POST /admin/flags/`**  
Upsert a flag for the current client.

**`GET /admin/flags/`**  
List flags for the current client. Supports `limit` / `offset`.

**`GET /admin/flags/{key}`**  
Get a single flag configuration.

**`DELETE /admin/flags/{key}`**  
Delete a flag.

### Runtime evaluation

**`POST /evaluate/`**  
Evaluate a flag for a set of user attributes:

```json
{
  "flag_key": "premium_discount",
  "user_attributes": {
    "subscription": "premium",
    "country": "CA"
  }
}
```

Response:

```json
{
  "flag_key": "premium_discount",
  "enabled": true,
  "parameters": {
    "discount_percentage": 40
  }
}
```

### Auth (dashboard)

**`POST /auth/login`**  
Body:

```json
{
  "email": "demo@example.com",
  "password": "secure_password_123"
}
```

Response:

```json
{
  "session_token": "nsess_...",
  "client": { "...": "..." }
}
```

**`POST /auth/logout`**  
Header:

```http
X-Session-Token: nsess_...
```

Response: `204 No Content`.

---

## Running the backend

### Local (without Docker)

From `backend/`:

```bash
# Create virtualenv
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Create a PostgreSQL database:

```bash
createdb nimbusflags_dev
```

Set environment variables (for example from the project root):

```bash
# .env at project root
DATABASE_URL=postgresql://postgres@localhost:5432/nimbusflags_dev
DEBUG=true
```

Then:

```bash
cd backend
export $(cat ../.env | xargs)

# Apply migrations
alembic upgrade head

# Run the app
python app.py
# → http://127.0.0.1:8000
```

### Docker

From the project root:

```bash
docker compose up --build
```

PostgreSQL and the backend start together.  
Alembic migrations are applied automatically on container startup.

---

## Testing

From the project root, with the virtualenv activated:

```bash
pytest backend/tests
```

Examples:

```bash
# Run a single file
pytest backend/tests/test_app.py

# Verbose
pytest backend/tests -v
```

**Tests cover:**
- Happy-path and error cases for `/clients/signup`
- API key resolution and client lookup
- Feature flag creation and evaluation
- Auth login/logout flows
- Basic health and docs endpoints

All tests are currently passing.

---

## Security notes

- Passwords are hashed with `bcrypt`.
- API keys and session tokens are never stored in plaintext:
  - SHA-256 hashes are stored in the database.
- All SQL queries use parameterized statements with `psycopg`.
- Error responses avoid leaking whether an email exists.

**Not implemented yet (future hardening):**
- Rate limiting (per API key / IP)
- API key rotation
- Audit logging for admin operations
- CSRF protection for the future web dashboard (handled at the frontend + proxy layer)

---

## Roadmap (backend scope)

Planned next steps for the backend:

- Expose selected admin endpoints secured by session tokens (`X-Session-Token`)
  for the React dashboard.
- Add simple rate limiting (per API key).
- Add basic request logging / audit trail.
- Wire a CI workflow to run `pytest backend/tests` on each push.

The current state is intentionally focused on a solid, well-tested backend
suitable for a portfolio and for integrating a React dashboard in the next sprint.