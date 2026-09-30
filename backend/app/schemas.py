import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import RecordSource, UserRole


# ---------- 사용자 / 인증 ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    phone: str | None
    role: UserRole


class UserUpdate(BaseModel):
    """보낸 필드만 수정한다."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 어르신 ----------
class SeniorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class SeniorUpdate(BaseModel):
    """보낸 필드만 수정한다."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class SeniorOut(SeniorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: dt.datetime


class SeniorListItem(SeniorOut):
    """목록 화면용: 기본 정보 + 가장 최근 생활 기록 요약."""

    guardian_count: int
    last_record_date: dt.date | None = None
    last_activity_level: int | None = None


class GuardianLink(BaseModel):
    email: EmailStr


# ---------- 생활 기록 ----------
class DailyRecordIn(BaseModel):
    wake_time: dt.time | None = None
    sleep_time: dt.time | None = None
    activity_level: int | None = Field(default=None, ge=0)
    hourly_activity: list[int] | None = None
    meal_count: int | None = Field(default=None, ge=0, le=10)
    meal_times: list[dt.time] | None = None
    outing_minutes: int | None = Field(default=None, ge=0, le=1440)
    appliance_usage: int | None = Field(default=None, ge=0)
    source: RecordSource = RecordSource.MANUAL
    memo: str | None = None

    @field_validator("hourly_activity")
    @classmethod
    def _check_hourly(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if len(v) != 24:
            raise ValueError("hourly_activity는 0~23시에 해당하는 24개의 값이어야 합니다")
        if any(x < 0 for x in v):
            raise ValueError("hourly_activity 값은 0 이상이어야 합니다")
        return v

    def to_db_values(self) -> dict:
        """DailyRecord 컬럼에 그대로 넣을 수 있는 dict. meal_times는 JSON 컬럼이라 "HH:MM" 문자열로 바꾼다."""
        values = self.model_dump()
        if self.meal_times is not None:
            values["meal_times"] = [t.strftime("%H:%M") for t in self.meal_times]
        return values


class DailyRecordOut(DailyRecordIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    senior_id: int
    date: dt.date
    updated_at: dt.datetime
