import pytest
from sqlalchemy.orm import Session

from superai_review.auth.ownership import ResourceNotFoundError, require_owned_session
from superai_review.auth.types import UserRole
from superai_review.db.models import ReviewSession, User


def add_user(db: Session, subject: str, email: str) -> User:
    user = User(
        issuer="https://issuer.example",
        subject=subject,
        email=email,
        email_normalized=email,
        role=UserRole.USER.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_session_owner_can_access(db: Session) -> None:
    owner = add_user(db, "a", "a@example.com")
    review = ReviewSession(user_id=owner.id, objective="test")
    db.add(review)
    db.commit()
    db.refresh(review)

    assert require_owned_session(db, owner, review.id).id == review.id


def test_foreign_session_is_reported_as_not_found(db: Session) -> None:
    owner = add_user(db, "a", "a@example.com")
    stranger = add_user(db, "b", "b@example.com")
    review = ReviewSession(user_id=owner.id, objective="test")
    db.add(review)
    db.commit()
    db.refresh(review)

    with pytest.raises(ResourceNotFoundError):
        require_owned_session(db, stranger, review.id)
