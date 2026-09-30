"""개발용 초기 데이터 넣기:  uv run python -m app.seed

- 관리자 / 보호자 계정
- 어르신 3명 + 최근 28일치 가상 생활 기록
이미 계정이 있으면 건너뛴다.
"""

import datetime as dt
import random

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import DailyRecord, Senior, User, UserRole
from app.security import hash_password
from app.simulate import LifeProfile, generate_normal_day

ADMIN = ("admin@lifeguard.dev", "admin1234", "관리자")
GUARDIAN = ("guardian@lifeguard.dev", "guardian1234", "김보호")
DAYS = 28

SENIORS = [
    ("A 어르신", 1945, LifeProfile()),
    ("B 어르신", 1941, LifeProfile(wake=6.0, sleep=21.0, meal_hours=(7, 12, 17), activity_scale=0.8)),
    ("C 어르신", 1950, LifeProfile(wake=7.5, sleep=23.0, outing_minutes=150, activity_scale=1.2)),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    rng = random.Random(42)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == ADMIN[0])):
            print("이미 seed 데이터가 있습니다. 건너뜁니다.")
            return

        admin = User(email=ADMIN[0], password_hash=hash_password(ADMIN[1]), name=ADMIN[2], role=UserRole.ADMIN)
        guardian = User(email=GUARDIAN[0], password_hash=hash_password(GUARDIAN[1]), name=GUARDIAN[2])
        db.add_all([admin, guardian])

        today = dt.date.today()
        for i, (name, birth_year, profile) in enumerate(SENIORS):
            senior = Senior(name=name, birth_year=birth_year)
            if i == 0:
                senior.guardians.append(guardian)  # 보호자는 A 어르신만 담당
            db.add(senior)
            for d in range(DAYS, 0, -1):
                day = generate_normal_day(profile, rng)
                senior.records.append(DailyRecord(date=today - dt.timedelta(days=d), **day.to_db_values()))

        db.commit()

    print("seed 완료")
    print(f"  관리자: {ADMIN[0]} / {ADMIN[1]}")
    print(f"  보호자: {GUARDIAN[0]} / {GUARDIAN[1]}  (A 어르신 담당)")
    print(f"  어르신 {len(SENIORS)}명 × {DAYS}일 가상 생활 기록")


if __name__ == "__main__":
    main()
