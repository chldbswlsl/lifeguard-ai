import datetime as dt
import re
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models import RecordSource, UserRole


# ---------- 공통 입력 타입 ----------
def _blank_to_none(v: object) -> object:
    """앞뒤 공백을 지우고, 빈 문자열은 None으로 바꾼다 (선택 입력 칸용)."""
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def _check_password(v: str) -> str:
    if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
        raise ValueError("비밀번호는 영문과 숫자를 모두 포함해야 합니다")
    return v


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


def OptionalText(max_len: int):  # noqa: N802 - 타입처럼 쓰는 함수
    """선택 입력 텍스트: 공백만 있으면 None, 글자 수 제한은 값이 있을 때만."""
    return Annotated[Annotated[str, StringConstraints(max_length=max_len)] | None, BeforeValidator(_blank_to_none)]


Phone = Annotated[
    Annotated[str, StringConstraints(max_length=20, pattern=r"^[0-9+\-() ]+$")] | None,
    BeforeValidator(_blank_to_none),
]
NewPassword = Annotated[str, Field(min_length=8, max_length=128), AfterValidator(_check_password)]


class _Input(BaseModel):
    # 정의하지 않은 필드가 오면 거절한다 (오타로 인한 조용한 무시 방지)
    model_config = ConfigDict(extra="forbid")


class _PartialUpdate(_Input):
    """PATCH용: 보낸 필드만 수정한다. 필수 항목(name)을 null로 보내면 거절한다."""

    @model_validator(mode="after")
    def _required_not_null(self):
        if "name" in self.model_fields_set and getattr(self, "name", None) is None:
            raise ValueError("이름은 비울 수 없습니다")
        return self


# ---------- 사용자 / 인증 ----------
class UserCreate(_Input):
    email: EmailStr
    password: NewPassword
    name: Name
    phone: Phone = None

    @model_validator(mode="after")
    def _password_not_email(self):
        email = self.email.lower()
        if self.password.lower() in (email, email.split("@")[0]):
            raise ValueError("이메일과 같은 비밀번호는 사용할 수 없습니다")
        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    phone: str | None
    role: UserRole


class UserUpdate(_PartialUpdate):
    name: Name | None = None
    phone: Phone = None


class PasswordChange(_Input):
    current_password: str = Field(max_length=128)
    new_password: NewPassword


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 어르신 ----------
BirthYear = Annotated[int, Field(ge=1900, le=2100)] | None


class SeniorCreate(_Input):
    name: Name
    birth_year: BirthYear = None
    phone: Phone = None
    address: OptionalText(255) = None
    notes: OptionalText(2000) = None

    @field_validator("birth_year")
    @classmethod
    def _not_future(cls, v: int | None) -> int | None:
        if v is not None and v > dt.date.today().year:
            raise ValueError("출생연도가 올해보다 클 수 없습니다")
        return v


class SeniorUpdate(_PartialUpdate):
    name: Name | None = None
    birth_year: BirthYear = None
    phone: Phone = None
    address: OptionalText(255) = None
    notes: OptionalText(2000) = None


class SeniorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    birth_year: int | None
    phone: str | None
    address: str | None
    notes: str | None
    created_at: dt.datetime


class SeniorListItem(SeniorOut):
    """목록 화면용: 기본 정보 + 가장 최근 생활 기록 요약."""

    guardian_count: int
    last_record_date: dt.date | None = None
    last_activity_level: int | None = None


class GuardianLink(_Input):
    email: EmailStr


# ---------- 생활 기록 ----------
# 상한은 센서 오류·입력 실수로 터무니없는 값이 저장되는 것을 막기 위한 것 (AI 분석 결과를 망가뜨린다)
MAX_DAILY_ACTIVITY = 1_000_000
MAX_HOURLY_ACTIVITY = 100_000


class DailyRecordFields(BaseModel):
    wake_time: dt.time | None = None
    sleep_time: dt.time | None = None
    activity_level: Annotated[int, Field(ge=0, le=MAX_DAILY_ACTIVITY)] | None = None
    hourly_activity: list[int] | None = None
    meal_count: Annotated[int, Field(ge=0, le=10)] | None = None
    meal_times: Annotated[list[dt.time], Field(max_length=10)] | None = None
    outing_minutes: Annotated[int, Field(ge=0, le=1440)] | None = None
    appliance_usage: Annotated[int, Field(ge=0, le=10_000)] | None = None
    source: RecordSource = RecordSource.MANUAL
    memo: str | None = None


class DailyRecordIn(DailyRecordFields):
    model_config = ConfigDict(extra="forbid")

    memo: OptionalText(1000) = None

    @field_validator("hourly_activity")
    @classmethod
    def _check_hourly(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if len(v) != 24:
            raise ValueError("hourly_activity는 0~23시에 해당하는 24개의 값이어야 합니다")
        if any(x < 0 or x > MAX_HOURLY_ACTIVITY for x in v):
            raise ValueError(f"hourly_activity 값은 0 이상 {MAX_HOURLY_ACTIVITY:,} 이하여야 합니다")
        return v

    def to_db_values(self) -> dict:
        """DailyRecord 컬럼에 그대로 넣을 수 있는 dict. meal_times는 JSON 컬럼이라 "HH:MM" 문자열로 바꾼다."""
        values = self.model_dump()
        if self.meal_times is not None:
            values["meal_times"] = [t.strftime("%H:%M") for t in self.meal_times]
        return values


class DailyRecordOut(DailyRecordFields):
    """응답용. 입력 검증(상한 등)은 다시 하지 않도록 DailyRecordIn이 아니라 필드 정의만 공유한다."""

    model_config = ConfigDict(from_attributes=True)

    activity_level: int | None = None
    meal_count: int | None = None
    meal_times: list[dt.time] | None = None
    outing_minutes: int | None = None
    appliance_usage: int | None = None

    id: int
    senior_id: int
    date: dt.date
    updated_at: dt.datetime
