import datetime as dt
import enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _enum(cls: type[enum.Enum]) -> Enum:
    # DB에는 enum 이름(GUARDIAN)이 아니라 값(guardian)을 문자열로 저장한다.
    return Enum(cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class UserRole(str, enum.Enum):
    GUARDIAN = "guardian"  # 보호자
    ADMIN = "admin"  # 사회복지사·관리자


class RecordSource(str, enum.Enum):
    MANUAL = "manual"  # 직접 입력
    SIMULATED = "simulated"  # 가상 데이터
    SENSOR = "sensor"  # 센서 수집


# 보호자 ↔ 어르신 (한 어르신에 여러 보호자, 한 보호자가 여러 어르신 가능)
guardian_senior = Table(
    "guardian_senior",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("senior_id", ForeignKey("seniors.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.GUARDIAN)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    seniors: Mapped[list["Senior"]] = relationship(secondary=guardian_senior, back_populates="guardians")


class Senior(Base):
    """관리 대상 어르신."""

    __tablename__ = "seniors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    birth_year: Mapped[int | None]
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    guardians: Mapped[list[User]] = relationship(secondary=guardian_senior, back_populates="seniors")
    records: Mapped[list["DailyRecord"]] = relationship(
        back_populates="senior", cascade="all, delete-orphan", passive_deletes=True
    )


class DailyRecord(Base):
    """하루 단위 생활 기록. 어르신 1명당 날짜별로 1건."""

    __tablename__ = "daily_records"
    __table_args__ = (UniqueConstraint("senior_id", "date", name="uq_record_senior_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    senior_id: Mapped[int] = mapped_column(ForeignKey("seniors.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date]

    wake_time: Mapped[dt.time | None]
    sleep_time: Mapped[dt.time | None]  # 자정 이후 취침이면 00:30처럼 기록
    activity_level: Mapped[int | None]  # 하루 전체 움직임 감지 횟수(또는 걸음 수)
    hourly_activity: Mapped[list[int] | None] = mapped_column(JSON)  # 0~23시 시간대별 움직임 (24칸)
    meal_count: Mapped[int | None]
    meal_times: Mapped[list[str] | None] = mapped_column(JSON)  # ["08:00", "12:30", ...]
    outing_minutes: Mapped[int | None]
    appliance_usage: Mapped[int | None]  # 냉장고·TV 등 생활기기 사용 횟수
    source: Mapped[RecordSource] = mapped_column(_enum(RecordSource), default=RecordSource.MANUAL)
    memo: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    senior: Mapped[Senior] = relationship(back_populates="records")
