# SuperAI.review

**Ask once. Let AI argue. Get the best answer.**

Private multi-model review and synthesis platform.

The product specification lives in `bbxx/agent-platform`, branch `superai`, at
`docs/superai/Proposal.md`. The MVP epic is #1.

## Foundation stack

- Python 3.12
- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic Settings
- pytest
- provider-agnostic domain layer

## Local development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn superai_review.api.app:app --reload
```

Run checks:

```bash
ruff check .
pytest
```

The default database is local SQLite. Production configuration is supplied through
environment variables; provider credentials are intentionally not part of the
application configuration committed to the repository.
