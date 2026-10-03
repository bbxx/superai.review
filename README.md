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

## Authentication

SuperAI.review does not own user passwords. Private API requests use a bearer token
issued by a configured OpenID Connect provider. The backend verifies signature, issuer,
audience, expiry, subject and (by default) a verified email against the configured JWKS.

OIDC proves identity but does **not** create a public signup path. A new local account is
provisioned only when its normalized email has an active invite, or when the email is in
`SUPERAI_AUTH_BOOTSTRAP_ADMIN_EMAILS`. Disabled local accounts stay blocked even when
the external OIDC identity is still valid.

This design keeps the application independent from a specific identity vendor: a future
frontend or access proxy may use Auth0, Google, Cloudflare Access, Keycloak or another
standards-compatible OIDC issuer.

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
