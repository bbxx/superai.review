from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from superai_review.auth.config import get_auth_settings
from superai_review.auth.identity import (
    AuthNotConfiguredError,
    Identity,
    IdentityVerifier,
    InvalidIdentityTokenError,
)
from superai_review.auth.service import (
    AuthService,
    IdentityConflictError,
    InviteRequiredError,
    UserDisabledError,
)
from superai_review.auth.types import UserRole
from superai_review.config import get_settings
from superai_review.db.models import User
from superai_review.db.session import build_engine, build_session_factory

_engine = build_engine(get_settings().database_url)
_session_factory = build_session_factory(_engine)
_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    with _session_factory() as db:
        yield db


DbDependency = Annotated[Session, Depends(get_db)]


def get_identity_verifier(request: Request) -> IdentityVerifier:
    return request.app.state.identity_verifier


CredentialsDependency = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(_bearer),
]
VerifierDependency = Annotated[IdentityVerifier, Depends(get_identity_verifier)]


def get_identity(
    credentials: CredentialsDependency,
    verifier: VerifierDependency,
) -> Identity:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verifier.verify(credentials.credentials)
    except AuthNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC authentication is not configured",
        ) from exc
    except InvalidIdentityTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid identity token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


IdentityDependency = Annotated[Identity, Depends(get_identity)]


def get_current_user(
    identity: IdentityDependency,
    db: DbDependency,
) -> User:
    service = AuthService(db, get_auth_settings().bootstrap_admin_email_set)
    try:
        return service.resolve_or_provision(identity)
    except InviteRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invite required") from exc
    except UserDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user disabled") from exc
    except IdentityConflictError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="identity conflict") from exc


CurrentUserDependency = Annotated[User, Depends(get_current_user)]


def get_current_admin(user: CurrentUserDependency) -> User:
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    return user


CurrentAdminDependency = Annotated[User, Depends(get_current_admin)]
