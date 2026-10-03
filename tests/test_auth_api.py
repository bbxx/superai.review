from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from superai_review.api.app import create_app
from superai_review.api.dependencies import get_db
from superai_review.auth.identity import Identity
from superai_review.auth.types import UserRole
from superai_review.db.models import Invite, User


class StaticVerifier:
    def __init__(self, identity: Identity) -> None:
        self._identity = identity

    def verify(self, token: str) -> Identity:
        assert token
        return self._identity


def client_for(db: Session, identity: Identity) -> TestClient:
    app = create_app(identity_verifier=StaticVerifier(identity))

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def add_admin(db: Session) -> User:
    admin = User(
        issuer="https://issuer.example",
        subject="admin",
        email="admin@example.com",
        email_normalized="admin@example.com",
        role=UserRole.ADMIN.value,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def test_private_api_requires_bearer_token(db: Session) -> None:
    response = client_for(
        db,
        Identity(
            issuer="https://issuer.example",
            subject="nobody",
            email="nobody@example.com",
        ),
    ).get("/api/me")

    assert response.status_code == 401


def test_invited_user_can_resolve_me(db: Session) -> None:
    admin = add_admin(db)
    db.add(
        Invite(
            email_normalized="friend@example.com",
            role=UserRole.USER.value,
            invited_by_user_id=admin.id,
        )
    )
    db.commit()

    response = client_for(
        db,
        Identity(
            issuer="https://issuer.example",
            subject="friend",
            email="friend@example.com",
            display_name="Friend",
        ),
    ).get("/api/me", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert response.json()["email"] == "friend@example.com"
    assert response.json()["role"] == "user"


def test_admin_can_create_invite(db: Session) -> None:
    add_admin(db)
    response = client_for(
        db,
        Identity(
            issuer="https://issuer.example",
            subject="admin",
            email="admin@example.com",
        ),
    ).post(
        "/api/admin/invites",
        headers={"Authorization": "Bearer token"},
        json={"email": "new@example.com", "role": "user"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"


def test_normal_user_cannot_use_admin_api(db: Session) -> None:
    add_admin(db)
    user = User(
        issuer="https://issuer.example",
        subject="user",
        email="user@example.com",
        email_normalized="user@example.com",
        role=UserRole.USER.value,
    )
    db.add(user)
    db.commit()

    response = client_for(
        db,
        Identity(
            issuer="https://issuer.example",
            subject="user",
            email="user@example.com",
        ),
    ).get("/api/admin/users", headers={"Authorization": "Bearer token"})

    assert response.status_code == 403
