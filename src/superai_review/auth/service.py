from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from superai_review.auth.identity import Identity
from superai_review.auth.types import UserRole
from superai_review.db.models import Invite, User


class InviteRequiredError(PermissionError):
    pass


class UserDisabledError(PermissionError):
    pass


class IdentityConflictError(PermissionError):
    pass


class InviteAlreadyExistsError(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().casefold()


class AuthService:
    def __init__(self, db: Session, bootstrap_admin_emails: frozenset[str] = frozenset()) -> None:
        self._db = db
        self._bootstrap_admin_emails = bootstrap_admin_emails

    def resolve_or_provision(self, identity: Identity) -> User:
        email_normalized = normalize_email(identity.email)
        user = self._db.scalar(
            select(User).where(User.issuer == identity.issuer, User.subject == identity.subject)
        )
        if user is not None:
            if user.disabled_at is not None:
                raise UserDisabledError("user is disabled")
            self._refresh_profile(user, identity, email_normalized)
            return user

        email_owner = self._db.scalar(
            select(User).where(User.email_normalized == email_normalized)
        )
        if email_owner is not None:
            raise IdentityConflictError("email belongs to a different OIDC subject")

        invite = None
        role = UserRole.ADMIN if email_normalized in self._bootstrap_admin_emails else None
        if role is None:
            invite = self._db.scalar(
                select(Invite)
                .where(
                    Invite.email_normalized == email_normalized,
                    Invite.used_at.is_(None),
                    Invite.revoked_at.is_(None),
                )
                .order_by(Invite.created_at.desc())
            )
            if invite is None:
                raise InviteRequiredError("an active invite is required")
            role = UserRole(invite.role)

        user = User(
            issuer=identity.issuer,
            subject=identity.subject,
            email=identity.email.strip(),
            email_normalized=email_normalized,
            display_name=identity.display_name,
            role=role.value,
        )
        self._db.add(user)
        self._db.flush()

        if invite is not None:
            invite.used_at = datetime.now(UTC)
            invite.used_by_user_id = user.id

        self._db.commit()
        self._db.refresh(user)
        return user

    def create_invite(self, *, email: str, role: UserRole, invited_by: User) -> Invite:
        email_normalized = normalize_email(email)
        existing_user = self._db.scalar(
            select(User).where(User.email_normalized == email_normalized)
        )
        if existing_user is not None:
            raise InviteAlreadyExistsError("a user with this email already exists")

        existing_invite = self._db.scalar(
            select(Invite).where(
                Invite.email_normalized == email_normalized,
                Invite.used_at.is_(None),
                Invite.revoked_at.is_(None),
            )
        )
        if existing_invite is not None:
            raise InviteAlreadyExistsError("an active invite already exists")

        invite = Invite(
            email_normalized=email_normalized,
            role=role.value,
            invited_by_user_id=invited_by.id,
        )
        self._db.add(invite)
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def list_invites(self) -> list[Invite]:
        return list(self._db.scalars(select(Invite).order_by(Invite.created_at.desc())))

    def list_users(self) -> list[User]:
        return list(self._db.scalars(select(User).order_by(User.created_at)))

    def disable_user(self, user_id: str) -> User | None:
        user = self._db.get(User, user_id)
        if user is None:
            return None
        if user.disabled_at is None:
            user.disabled_at = datetime.now(UTC)
            self._db.commit()
            self._db.refresh(user)
        return user

    def _refresh_profile(self, user: User, identity: Identity, email_normalized: str) -> None:
        changed = False
        if user.email_normalized != email_normalized:
            conflict = self._db.scalar(
                select(User).where(
                    User.email_normalized == email_normalized,
                    User.id != user.id,
                )
            )
            if conflict is not None:
                raise IdentityConflictError("updated email belongs to another user")
            user.email = identity.email.strip()
            user.email_normalized = email_normalized
            changed = True

        if user.display_name != identity.display_name:
            user.display_name = identity.display_name
            changed = True

        if changed:
            self._db.commit()
            self._db.refresh(user)
