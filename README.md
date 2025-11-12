# NimbusFlags

> **Status:** MVP / Active Development  
> Lightweight feature flags service with clean architecture.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What is this?

NimbusFlags is a **feature flags service** that lets you control feature rollouts dynamically.

**Core flow:**
1. Create a flag with conditions (admin)
2. Evaluate it against user context (public API)
3. Get instant `enabled: true/false` + optional parameters

**Why this exists:** Portfolio/learning project exploring Flask best practices, Clean Architecture, and OpenAPI-first design.

---

## Quick Start
```bash
# Clone
git clone https://github.com/adam-dri/NimbusFlags.git
cd NimbusFlags/backend

# Setup
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run
python app.py
# → http://127.0.0.1:8000
```

**Health check:**
```bash
curl http://127.0.0.1:8000/health/
# {"status":"ok"}
```

**API Docs:** http://127.0.0.1:8000/docs

---

## Project Structure
```
NimbusFlags/
├── backend/
│   ├── app.py
│   ├── blueprints/          # Routes (admin, flags, system, docs)
│   ├── services/            # Business logic
│   ├── repositories/        # Data access (in-memory → future: SQLite)
│   ├── validators/          # JSON Schema validation
│   ├── errors/              # Error handling
│   ├── schemas/             # JSON Schema files
│   ├── docs/                # openapi.yaml
│   └── tests/
├── README.md
└── LICENSE
```

**Architecture:** Clean separation (Routes → Services → Repositories)

---

## API Endpoints

### System
- `GET /health/` — Health check

### Admin **No auth (dev only)**
- `POST /admin/flags/` — Create/update flag
- `GET /admin/flags/{key}` — Get flag config

**Example flag:**
```json
{
  "key": "premium_discount",
  "enabled": true,
  "conditions": [
    {"attribute": "subscription", "operator": "equals", "value": "premium"},
    {"attribute": "country", "operator": "in", "value": ["CA", "US"]}
  ],
  "parameters": {"discount_percentage": 40}
}
```

### Public
- `POST /evaluate/` — Evaluate flag for user

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/evaluate/ \
  -H "Content-Type: application/json" \
  -d '{
    "flag_key": "premium_discount",
    "user_attributes": {"subscription": "premium", "country": "CA"}
  }'
# Response: {"enabled": true, "parameters": {"discount_percentage": 40}}
```

---

## Tests
```bash
cd backend
source venv/bin/activate
python -m pytest
```

---

## Design Decisions

**Architecture:**
- Repository pattern for data abstraction (easy to swap memory → SQLite)
- Service layer for business logic (testable, reusable)
- Validators for input validation (JSON Schema based)
- Blueprints for route organization

**Current limitations (intentional for MVP):**
- In-memory storage only
- No authentication
- No persistence
- Single instance

---

## Roadmap

- [ ] SQLite persistence
- [ ] API key authentication for admin
- [ ] `GET /admin/flags/` (list all)
- [ ] GitHub Actions CI
- [ ] Rate limiting

---

## Author

**Adam Driouich**  
Montréal, QC

- GitHub: [@adam-dri](https://github.com/adam-dri)
- LinkedIn: [adam-driouich](https://www.linkedin.com/in/adam-driouich/)

---

## License

MIT License - see [LICENSE](LICENSE) file.

Copyright © 2025 Adam Driouich