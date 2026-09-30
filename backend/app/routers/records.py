import datetime as dt

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import AccessibleSenior, DbSession
from app.models import DailyRecord
from app.schemas import DailyRecordIn, DailyRecordOut

router = APIRouter(prefix="/seniors/{senior_id}/records", tags=["생활 기록"])

MAX_RANGE_DAYS = 366
NOT_FOUND = "해당 날짜의 기록이 없습니다"


def _find(db: DbSession, senior_id: int, date: dt.date) -> DailyRecord | None:
    return db.scalar(select(DailyRecord).where(DailyRecord.senior_id == senior_id, DailyRecord.date == date))


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


@router.get("", response_model=list[DailyRecordOut])
def list_records(
    senior: AccessibleSenior,
    db: DbSession,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> list[DailyRecord]:
    """기간 조회 (start, end 모두 포함, 날짜 오름차순). 한 번에 최대 366일.
    start를 생략하면 end(생략 시 오늘)로부터 366일 전부터 조회한다."""
    end = end or dt.date.today()
    start = start or end - dt.timedelta(days=MAX_RANGE_DAYS - 1)
    if start > end:
        raise _bad_request("시작 날짜가 끝 날짜보다 늦습니다")
    if (end - start).days >= MAX_RANGE_DAYS:
        raise _bad_request(f"한 번에 최대 {MAX_RANGE_DAYS}일까지 조회할 수 있습니다")

    query = (
        select(DailyRecord)
        .where(DailyRecord.senior_id == senior.id, DailyRecord.date >= start, DailyRecord.date <= end)
        .order_by(DailyRecord.date)
    )
    return list(db.scalars(query))


@router.put("/{date}", response_model=DailyRecordOut)
def upsert_record(
    date: dt.date, data: DailyRecordIn, senior: AccessibleSenior, db: DbSession, response: Response
) -> DailyRecord:
    """해당 날짜 기록을 저장한다. 이미 있으면 전체를 덮어쓰고(200), 없으면 새로 만든다(201)."""
    if date > dt.date.today() + dt.timedelta(days=1):  # 시차를 고려해 내일까지는 허용
        raise _bad_request("미래 날짜의 기록은 저장할 수 없습니다")

    values = data.to_db_values()
    record = _find(db, senior.id, date)
    created = record is None
    if created:
        record = DailyRecord(senior_id=senior.id, date=date, **values)
        db.add(record)
    else:
        for field, value in values.items():
            setattr(record, field, value)

    try:
        db.commit()
    except IntegrityError:
        # 같은 날짜를 거의 동시에 처음 저장한 경우: 먼저 저장된 기록을 덮어쓴다
        db.rollback()
        record = _find(db, senior.id, date)
        if record is None:
            raise
        created = False
        for field, value in values.items():
            setattr(record, field, value)
        db.commit()

    if created:
        response.status_code = status.HTTP_201_CREATED
    db.refresh(record)
    return record


@router.get("/{date}", response_model=DailyRecordOut)
def get_record(date: dt.date, senior: AccessibleSenior, db: DbSession) -> DailyRecord:
    record = _find(db, senior.id, date)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return record


@router.delete("/{date}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(date: dt.date, senior: AccessibleSenior, db: DbSession) -> None:
    record = _find(db, senior.id, date)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    db.delete(record)
    db.commit()
