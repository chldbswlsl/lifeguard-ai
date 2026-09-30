import datetime as dt

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.deps import AccessibleSenior, DbSession
from app.models import DailyRecord
from app.schemas import DailyRecordIn, DailyRecordOut

router = APIRouter(prefix="/seniors/{senior_id}/records", tags=["생활 기록"])


def _find(db: DbSession, senior_id: int, date: dt.date) -> DailyRecord | None:
    return db.scalar(select(DailyRecord).where(DailyRecord.senior_id == senior_id, DailyRecord.date == date))


@router.get("", response_model=list[DailyRecordOut])
def list_records(
    senior: AccessibleSenior,
    db: DbSession,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> list[DailyRecord]:
    """기간 조회 (start, end 모두 포함). 날짜 오름차순."""
    query = select(DailyRecord).where(DailyRecord.senior_id == senior.id)
    if start:
        query = query.where(DailyRecord.date >= start)
    if end:
        query = query.where(DailyRecord.date <= end)
    return list(db.scalars(query.order_by(DailyRecord.date)))


@router.put("/{date}", response_model=DailyRecordOut)
def upsert_record(
    date: dt.date, data: DailyRecordIn, senior: AccessibleSenior, db: DbSession, response: Response
) -> DailyRecord:
    """해당 날짜 기록을 저장한다. 이미 있으면 덮어쓰고(200), 없으면 새로 만든다(201)."""
    record = _find(db, senior.id, date)
    if record is None:
        record = DailyRecord(senior_id=senior.id, date=date)
        db.add(record)
        response.status_code = status.HTTP_201_CREATED
    for field, value in data.to_db_values().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{date}", response_model=DailyRecordOut)
def get_record(date: dt.date, senior: AccessibleSenior, db: DbSession) -> DailyRecord:
    record = _find(db, senior.id, date)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 날짜의 기록이 없습니다")
    return record


@router.delete("/{date}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(date: dt.date, senior: AccessibleSenior, db: DbSession) -> None:
    record = _find(db, senior.id, date)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 날짜의 기록이 없습니다")
    db.delete(record)
    db.commit()
