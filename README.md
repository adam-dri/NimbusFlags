# NimbusFlags

> Multi-tenant feature flags service built with Flask and PostgreSQL.  
> Portfolio project focused on clean backend architecture and realistic constraints.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What is this?

NimbusFlags is a backend service that lets product teams:

- Register as clients (tenants)
- Define feature flags with conditions
- Evaluate flags at runtime via a public API

It is designed as a **portfolio project** that looks and behaves like a small production service:
structured codebase, database migrations, tests, Docker, and OpenAPI docs.

The backend lives in `backend/` and is fully implemented and tested.  
A React dashboard will be added in a later sprint and will consume the existing API.

For all technical details (architecture, tables, endpoints, auth), see:

> [`backend/README.md`](backend/README.md)

---

## Quick start (local, without Docker)

```bash
# Clone
git clone https://github.com/adam-dri/NimbusFlags.git
cd NimbusFlags/backend

# Create and activate virtualenv
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (example)
export DATABASE_URL=postgresql://postgres@localhost:5432/nimbusflags_dev
export DEBUG=true

# Run database migrations
alembic upgrade head

# Start the API
python app.py
# → http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health/
# {"status": "ok"}
```

Swagger UI and OpenAPI:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI YAML: http://127.0.0.1:8000/openapi.yaml

---

## Quick start with Docker

From the project root:

```bash
docker compose up --build
# API → http://localhost:8000
```

The compose file starts:

- A PostgreSQL instance
- The Flask backend (running migrations on startup)

---

## Tech stack

- **Backend:** Flask 3, Python 3.11
- **Database:** PostgreSQL (psycopg, Alembic migrations)
- **API style:** JSON over HTTP, OpenAPI 3.1
- **Auth:**
  - API keys for machine-to-machine access
  - Session tokens for future React dashboard
- **Testing:** pytest

For API examples and data model, go to [`backend/README.md`](backend/README.md).

---

## Author

**Adam Driouich** – Montréal, QC

- GitHub: [@adam-dri](https://github.com/adam-dri)
- LinkedIn: [adam-driouich](https://www.linkedin.com/in/adam-driouich/)

---

## License

MIT License – see [LICENSE](LICENSE).