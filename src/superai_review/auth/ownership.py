from sqlalchemy.orm import Session

from superai_review.db.models import ReviewSession, User


class ResourceNotFoundError(LookupError):
    """Used for missing and foreign resources to avoid ownership enumeration."""


def require_owned_session(db: Session, user: User, session_id: str) -> ReviewSession:
    session = db.get(ReviewSession, session_id)
    if session is None or session.user_id != user.id:
        raise ResourceNotFoundError("review session not found")
    return session


def require_owner(*, owner_user_id: str, user: User) -> None:
    if owner_user_id != user.id:
        raise ResourceNotFoundError("resource not found")
