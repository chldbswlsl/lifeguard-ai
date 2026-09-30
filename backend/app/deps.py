from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Senior, User, UserRole
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    user_id = decode_access_token(token)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자만 사용할 수 있습니다")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def get_accessible_senior(senior_id: int, db: DbSession, user: CurrentUser) -> Senior:
    """관리자는 모든 어르신, 보호자는 연결된 어르신만 접근할 수 있다.
    연결되지 않은 어르신은 존재 여부도 알 수 없도록 404로 응답한다."""
    senior = db.get(Senior, senior_id)
    if senior is None or (user.role != UserRole.ADMIN and user not in senior.guardians):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="어르신 정보를 찾을 수 없습니다")
    return senior


AccessibleSenior = Annotated[Senior, Depends(get_accessible_senior)]
