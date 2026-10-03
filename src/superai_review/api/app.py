from fastapi import FastAPI

from superai_review import __version__
from superai_review.api.auth_routes import router as auth_router
from superai_review.api.document_routes import router as document_router
from superai_review.auth.config import AuthSettings, get_auth_settings
from superai_review.auth.identity import (
    DisabledIdentityVerifier,
    IdentityVerifier,
    OIDCIdentityVerifier,
)


def _build_identity_verifier(settings: AuthSettings) -> IdentityVerifier:
    if not settings.configured:
        return DisabledIdentityVerifier()
    return OIDCIdentityVerifier(
        issuer=settings.issuer,
        audience=settings.audience,
        jwks_url=settings.jwks_url,
        algorithms=settings.allowed_algorithms,
        require_email_verified=settings.require_email_verified,
    )


def create_app(identity_verifier: IdentityVerifier | None = None) -> FastAPI:
    application = FastAPI(
        title="SuperAI.review",
        version=__version__,
        description="Multi-model review and synthesis platform.",
    )
    application.state.identity_verifier = identity_verifier or _build_identity_verifier(
        get_auth_settings()
    )
    application.include_router(auth_router)
    application.include_router(document_router)

    @application.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "SuperAI.review",
            "tagline": "Ask once. Let AI argue. Get the best answer.",
            "version": __version__,
        }

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "superai.review", "version": __version__}

    return application


app = create_app()
