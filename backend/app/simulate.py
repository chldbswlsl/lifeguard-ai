"""테스트용 가상 생활 데이터 생성기.

실제 센서 데이터를 구하기 전까지 이 모듈로 '평소 생활' 데이터를 만든다.
10월 AI 개발 때 이상 상황(활동량 감소, 식사 거름, 장시간 무활동 등) 시나리오를 여기에 추가할 예정.
"""

import datetime as dt
import random
from dataclasses import dataclass

from app.models import RecordSource
from app.schemas import DailyRecordIn


@dataclass(frozen=True)
class LifeProfile:
    """어르신 한 명의 평소 생활 습관. 시각은 소수 시간(7.5 = 07:30)."""

    wake: float = 7.0
    sleep: float = 22.0
    meal_hours: tuple[int, ...] = (8, 12, 18)
    outing_hour: int = 14
    outing_minutes: int = 90
    activity_scale: float = 1.0  # 활동량 배율 (활발한 분 > 1)
    appliance_usage: int = 15


def _to_time(hours: float) -> dt.time:
    hours = min(max(hours, 0.0), 23 + 59 / 60)
    h = int(hours)
    return dt.time(h, int(round((hours - h) * 60)) % 60)


def generate_normal_day(profile: LifeProfile, rng: random.Random) -> DailyRecordIn:
    """평소와 비슷한 하루를 만든다. 매일 조금씩 흔들림(노이즈)을 준다."""
    wake = profile.wake + rng.gauss(0, 0.33)  # ±20분 정도
    sleep = profile.sleep + rng.gauss(0, 0.33)
    outing = max(0, round(rng.gauss(profile.outing_minutes, 20)))

    hourly: list[int] = []
    remaining_outing = outing
    for h in range(24):
        if not (wake <= h + 0.5 < sleep):
            hourly.append(rng.choice([0, 0, 0, 1, 2]))  # 자는 중 (화장실 등 가끔 움직임)
            continue
        value = rng.randint(15, 35) * profile.activity_scale
        if h in profile.meal_hours:
            value += rng.randint(10, 20)  # 식사 준비·식사
        if h >= profile.outing_hour and remaining_outing > 0:
            away = min(remaining_outing, 60)
            value *= 1 - away / 60  # 외출 중에는 집 안 움직임이 줄어든다
            remaining_outing -= away
        hourly.append(round(value))

    meal_times = [_to_time(h + rng.uniform(0, 0.5)) for h in profile.meal_hours]
    return DailyRecordIn(
        wake_time=_to_time(wake),
        sleep_time=_to_time(sleep),
        activity_level=sum(hourly),
        hourly_activity=hourly,
        meal_count=len(meal_times),
        meal_times=meal_times,
        outing_minutes=outing,
        appliance_usage=max(0, round(rng.gauss(profile.appliance_usage, 3))),
        source=RecordSource.SIMULATED,
    )
