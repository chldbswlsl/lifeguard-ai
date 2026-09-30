from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession
from app.http import client_ip, ensure_not_limited
from app.models import User
from app.schemas import PasswordChange, Token, UserCreate, UserOut, UserUpdate
from app.security import (
    create_access_token,
    hash_password,
    login_limiter,
    password_limiter,
    signup_limiter,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["인증"])

DUPLICATE_EMAIL = "이미 가입된 이메일입니다"


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(request: Request, data: UserCreate, db: DbSession) -> User:
    """보호자 회원가입. 관리자 계정은 seed 스크립트로 만든다."""
    ip_key = f"ip:{client_ip(request)}"
    ensure_not_limited(signup_limiter, ip_key)
    signup_limiter.hit(ip_key)  # 성공·실패와 관계없이 센다 (계정 대량 생성 방지)

    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_EMAIL)
    user = User(email=email, password_hash=hash_password(data.password), name=data.name, phone=data.phone)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # 같은 이메일로 거의 동시에 가입한 경우
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_EMAIL) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(request: Request, form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """username 칸에 이메일을 넣는다 (OAuth2 표준 폼)."""
    email = form.username.strip().lower()[:255]
    keys = (f"email:{email}", f"ip:{client_ip(request)}")
    ensure_not_limited(login_limiter, *keys)

    user = db.scalar(select(User).where(User.email == email))
    # 없는 이메일이어도 해시 검증을 수행한다 → 응답 시간으로 가입 여부를 알 수 없다
    if not verify_password(form.password[:128], user.password_hash if user else None):
        login_limiter.hit(*keys)  # 실패만 센다
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_limiter.reset(f"email:{email}")
    return Token(access_token=create_access_token(user.id, user.token_version))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, user: CurrentUser, db: DbSession) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password", response_model=Token)
def change_password(data: PasswordChange, user: CurrentUser, db: DbSession) -> Token:
    """비밀번호를 바꾸면 다른 기기의 로그인은 모두 풀린다. 지금 기기에서 쓸 새 토큰을 돌려준다."""
    key = f"user:{user.id}"
    ensure_not_limited(password_limiter, key)

    if not verify_password(data.current_password, user.password_hash):
        password_limiter.hit(key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호가 올바르지 않습니다")
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="현재 비밀번호와 다른 비밀번호를 입력해 주세요"
        )
    if data.new_password.lower() in (user.email, user.email.split("@")[0]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이메일과 같은 비밀번호는 사용할 수 없습니다"
        )

    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    db.commit()
    password_limiter.reset(key)
    return Token(access_token=create_access_token(user.id, user.token_version))
