from fastapi import APIRouter, HTTPException, status

from superai_review.api.dependencies import (
    CurrentAdminDependency,
    CurrentUserDependency,
    DbDependency,
)
from superai_review.auth.schemas import InviteCreate, InviteView, UserView
from superai_review.auth.service import AuthService, InviteAlreadyExistsError

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/me", response_model=UserView)
def me(user: CurrentUserDependency) -> UserView:
    return UserView.from_model(user)


@router.get("/admin/users", response_model=list[UserView])
def list_users(
    _: CurrentAdminDependency,
    db: DbDependency,
) -> list[UserView]:
    return [UserView.from_model(user) for user in AuthService(db).list_users()]


@router.post("/admin/invites", response_model=InviteView, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteCreate,
    admin: CurrentAdminDependency,
    db: DbDependency,
) -> InviteView:
    try:
        invite = AuthService(db).create_invite(
            email=str(payload.email),
            role=payload.role,
            invited_by=admin,
        )
    except InviteAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return InviteView.from_model(invite)


@router.get("/admin/invites", response_model=list[InviteView])
def list_invites(
    _: CurrentAdminDependency,
    db: DbDependency,
) -> list[InviteView]:
    return [InviteView.from_model(invite) for invite in AuthService(db).list_invites()]


@router.post("/admin/users/{user_id}/disable", response_model=UserView)
def disable_user(
    user_id: str,
    admin: CurrentAdminDependency,
    db: DbDependency,
) -> UserView:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin cannot disable own account",
        )
    user = AuthService(db).disable_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return UserView.from_model(user)
