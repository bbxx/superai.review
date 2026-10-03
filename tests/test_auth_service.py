from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from superai_review.auth.identity import Identity
from superai_review.auth.service import (
    AuthService,
    IdentityConflictError,
    InviteRequiredError,
    UserDisabledError,
)
from superai_review.auth.types import UserRole
from superai_review.db.models import User


def identity(subject: str, email: str) -> Identity:
    return Identity(
        issuer="https://issuer.example",
        subject=subject,
        email=email,
        display_name=subject,
    )


def add_admin(db: Session) -> User:
    admin = User(
        issuer="https://issuer.example",
        subject="admin",
        email="admin@example.com",
        email_normalized="admin@example.com",
        display_name="Admin",
        role=UserRole.ADMIN.value,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def test_uninvited_identity_cannot_self_register(db: Session) -> None:
    with pytest.raises(InviteRequiredError):
        AuthService(db).resolve_or_provision(identity("new", "new@example.com"))


def test_invite_provisions_user_once(db: Session) -> None:
    admin = add_admin(db)
    service = AuthService(db)
    invite = service.create_invite(
        email="Friend@Example.com",
        role=UserRole.USER,
        invited_by=admin,
    )

    user = service.resolve_or_provision(identity("friend-sub", "friend@example.com"))

    assert user.role == UserRole.USER.value
    assert user.email_normalized == "friend@example.com"
    assert invite.used_at is not None
    assert invite.used_by_user_id == user.id

    same_user = service.resolve_or_provision(identity("friend-sub", "friend@example.com"))
    assert same_user.id == user.id


def test_bootstrap_admin_does_not_need_invite(db: Session) -> None:
    user = AuthService(db, frozenset({"owner@example.com"})).resolve_or_provision(
        identity("owner-sub", "OWNER@example.com")
    )
    assert user.role == UserRole.ADMIN.value


def test_disabled_user_stays_blocked(db: Session) -> None:
    user = AuthService(db, frozenset({"owner@example.com"})).resolve_or_provision(
        identity("owner-sub", "owner@example.com")
    )
    user.disabled_at = datetime.now(UTC)
    db.commit()

    with pytest.raises(UserDisabledError):
        AuthService(db).resolve_or_provision(identity("owner-sub", "owner@example.com"))


def test_same_email_cannot_be_silently_linked_to_new_subject(db: Session) -> None:
    AuthService(db, frozenset({"owner@example.com"})).resolve_or_provision(
        identity("subject-a", "owner@example.com")
    )

    with pytest.raises(IdentityConflictError):
        AuthService(db, frozenset({"owner@example.com"})).resolve_or_provision(
            identity("subject-b", "owner@example.com")
        )
