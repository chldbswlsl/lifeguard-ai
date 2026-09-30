from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import AccessibleSenior, AdminUser, CurrentUser, DbSession
from app.models import DailyRecord, Senior, User, UserRole
from app.schemas import GuardianLink, SeniorCreate, SeniorListItem, SeniorOut, SeniorUpdate, UserOut

router = APIRouter(prefix="/seniors", tags=["어르신"])


@router.post("", response_model=SeniorOut, status_code=status.HTTP_201_CREATED)
def create_senior(data: SeniorCreate, db: DbSession, user: CurrentUser) -> Senior:
    """보호자가 등록하면 자동으로 본인과 연결된다."""
    senior = Senior(**data.model_dump())
    if user.role == UserRole.GUARDIAN:
        senior.guardians.append(user)
    db.add(senior)
    db.commit()
    db.refresh(senior)
    return senior


@router.get("", response_model=list[SeniorListItem])
def list_seniors(db: DbSession, user: CurrentUser) -> list[SeniorListItem]:
    query = select(Senior).options(selectinload(Senior.guardians)).order_by(Senior.id)
    if user.role != UserRole.ADMIN:
        query = query.where(Senior.guardians.contains(user))
    seniors = list(db.scalars(query))

    # 어르신별 가장 최근 기록 한 건씩
    latest_date = (
        select(DailyRecord.senior_id, func.max(DailyRecord.date).label("date"))
        .where(DailyRecord.senior_id.in_([s.id for s in seniors]))
        .group_by(DailyRecord.senior_id)
        .subquery()
    )
    latest = {
        r.senior_id: r
        for r in db.scalars(
            select(DailyRecord).join(
                latest_date,
                (DailyRecord.senior_id == latest_date.c.senior_id) & (DailyRecord.date == latest_date.c.date),
            )
        )
    }

    return [
        SeniorListItem(
            **SeniorOut.model_validate(s).model_dump(),
            guardian_count=len(s.guardians),
            last_record_date=latest[s.id].date if s.id in latest else None,
            last_activity_level=latest[s.id].activity_level if s.id in latest else None,
        )
        for s in seniors
    ]


@router.get("/{senior_id}", response_model=SeniorOut)
def get_senior(senior: AccessibleSenior) -> Senior:
    return senior


@router.patch("/{senior_id}", response_model=SeniorOut)
def update_senior(data: SeniorUpdate, senior: AccessibleSenior, db: DbSession) -> Senior:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(senior, field, value)
    db.commit()
    db.refresh(senior)
    return senior


@router.delete("/{senior_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_senior(senior_id: int, db: DbSession, _: AdminUser) -> None:
    senior = db.get(Senior, senior_id)
    if senior is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="어르신 정보를 찾을 수 없습니다")
    db.delete(senior)
    db.commit()


@router.get("/{senior_id}/guardians", response_model=list[UserOut])
def list_guardians(senior: AccessibleSenior) -> list[User]:
    return senior.guardians


@router.post("/{senior_id}/guardians", response_model=list[UserOut])
def link_guardian(senior_id: int, data: GuardianLink, db: DbSession, _: AdminUser) -> list[User]:
    """관리자가 가입된 보호자 계정을 어르신과 연결한다."""
    senior = db.get(Senior, senior_id)
    if senior is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="어르신 정보를 찾을 수 없습니다")
    guardian = db.scalar(select(User).where(User.email == data.email.lower(), User.role == UserRole.GUARDIAN))
    if guardian is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 이메일의 보호자가 없습니다")
    if guardian not in senior.guardians:
        senior.guardians.append(guardian)
        db.commit()
    return senior.guardians


@router.delete("/{senior_id}/guardians/{user_id}", response_model=list[UserOut])
def unlink_guardian(senior_id: int, user_id: int, db: DbSession, _: AdminUser) -> list[User]:
    """관리자가 보호자 연결을 해제한다. 보호자 계정 자체는 지워지지 않는다."""
    senior = db.get(Senior, senior_id)
    if senior is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="어르신 정보를 찾을 수 없습니다")
    guardian = next((g for g in senior.guardians if g.id == user_id), None)
    if guardian is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연결된 보호자가 아닙니다")
    senior.guardians.remove(guardian)
    db.commit()
    return senior.guardians
