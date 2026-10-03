from datetime import datetime

from pydantic import BaseModel, EmailStr

from superai_review.auth.types import UserRole
from superai_review.db.models import Invite, User


class UserView(BaseModel):
    id: str
    email: str
    display_name: str | None
    role: UserRole
    created_at: datetime
    disabled_at: datetime | None

    @classmethod
    def from_model(cls, user: User) -> "UserView":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=UserRole(user.role),
            created_at=user.created_at,
            disabled_at=user.disabled_at,
        )


class InviteCreate(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.USER


class InviteView(BaseModel):
    id: str
    email: str
    role: UserRole
    created_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None

    @classmethod
    def from_model(cls, invite: Invite) -> "InviteView":
        return cls(
            id=invite.id,
            email=invite.email_normalized,
            role=UserRole(invite.role),
            created_at=invite.created_at,
            used_at=invite.used_at,
            revoked_at=invite.revoked_at,
        )
