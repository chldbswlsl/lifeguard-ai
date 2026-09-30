import datetime as dt
import random

import pytest

from app.simulate import LifeProfile, generate_normal_day

TODAY = dt.date.today()


def day(days_ago: int) -> str:
    return (TODAY - dt.timedelta(days=days_ago)).isoformat()


@pytest.fixture
def senior_id(client, guardian) -> int:
    return client.post("/seniors", json={"name": "홍길동"}, headers=guardian).json()["id"]


RECORD = {
    "wake_time": "07:05",
    "sleep_time": "22:10",
    "activity_level": 420,
    "hourly_activity": [0] * 7 + [30] * 15 + [0] * 2,
    "meal_count": 3,
    "meal_times": ["08:00", "12:30", "18:10"],
    "outing_minutes": 60,
    "appliance_usage": 14,
}


def test_처음_저장은_201_다시_저장은_덮어쓰기_200(client, guardian, senior_id):
    url = f"/seniors/{senior_id}/records/{day(1)}"
    res = client.put(url, json=RECORD, headers=guardian)
    assert res.status_code == 201
    assert res.json()["meal_times"] == ["08:00:00", "12:30:00", "18:10:00"]

    res = client.put(url, json={"activity_level": 100}, headers=guardian)
    assert res.status_code == 200
    assert res.json()["activity_level"] == 100
    assert res.json()["wake_time"] is None  # 보내지 않은 항목은 비워진다 (전체 덮어쓰기)
    assert len(client.get(f"/seniors/{senior_id}/records", headers=guardian).json()) == 1


def test_기간_조회(client, guardian, senior_id):
    for d in (30, 15, 1):
        client.put(f"/seniors/{senior_id}/records/{day(d)}", json=RECORD, headers=guardian)
    res = client.get(f"/seniors/{senior_id}/records?start={day(20)}&end={day(0)}", headers=guardian)
    assert [r["date"] for r in res.json()] == [day(15), day(1)]


def test_기간_조회_제한(client, guardian, senior_id):
    base = f"/seniors/{senior_id}/records"
    assert client.get(f"{base}?start={day(5)}&end={day(0)}", headers=guardian).status_code == 200
    assert (
        client.get(f"{base}?start={day(1)}&end={day(3)}", headers=guardian).status_code == 422
    )  # start > end (1일 전 > 3일 전)
    assert client.get(f"{base}?start={day(400)}&end={day(0)}", headers=guardian).status_code == 422  # 366일 초과
    assert client.get(f"{base}?start=2026-13-01", headers=guardian).json()["errors"][0]["field"] == "start"


def test_미래_날짜는_저장_불가(client, guardian, senior_id):
    tomorrow = (TODAY + dt.timedelta(days=1)).isoformat()
    later = (TODAY + dt.timedelta(days=2)).isoformat()
    assert client.put(f"/seniors/{senior_id}/records/{tomorrow}", json=RECORD, headers=guardian).status_code == 201
    res = client.put(f"/seniors/{senior_id}/records/{later}", json=RECORD, headers=guardian)
    assert res.status_code == 422
    assert res.json()["detail"] == "미래 날짜의 기록은 저장할 수 없습니다"


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"hourly_activity": [1] * 23}, "hourly_activity"),
        ({"hourly_activity": [-1] + [0] * 23}, "hourly_activity"),
        ({"hourly_activity": [200_000] + [0] * 23}, "hourly_activity"),
        ({"activity_level": -1}, "activity_level"),
        ({"activity_level": 10_000_000}, "activity_level"),
        ({"outing_minutes": 1441}, "outing_minutes"),
        ({"meal_times": ["25:00"]}, "meal_times"),
        ({"meal_times": ["08:00"] * 11}, "meal_times"),
        ({"source": "hacker"}, "source"),
        ({"unknown_field": 1}, "unknown_field"),
        ({"memo": "가" * 1001}, "memo"),
    ],
)
def test_잘못된_값은_422(client, guardian, senior_id, patch, field):
    res = client.put(f"/seniors/{senior_id}/records/{day(1)}", json={**RECORD, **patch}, headers=guardian)
    assert res.status_code == 422, res.text
    assert res.json()["errors"][0]["field"] == field


def test_조회와_삭제(client, guardian, senior_id):
    url = f"/seniors/{senior_id}/records/{day(1)}"
    assert client.get(url, headers=guardian).status_code == 404
    assert client.delete(url, headers=guardian).status_code == 404
    client.put(url, json=RECORD, headers=guardian)
    assert client.get(url, headers=guardian).status_code == 200
    assert client.delete(url, headers=guardian).status_code == 204
    assert client.get(url, headers=guardian).status_code == 404


def test_담당이_아니면_기록도_404(client, guardian, other_guardian, senior_id):
    url = f"/seniors/{senior_id}/records/{day(1)}"
    client.put(url, json=RECORD, headers=guardian)
    assert client.get(url, headers=other_guardian).status_code == 404
    assert client.put(url, json=RECORD, headers=other_guardian).status_code == 404
    assert client.delete(url, headers=other_guardian).status_code == 404
    assert client.get(f"/seniors/{senior_id}/records", headers=other_guardian).status_code == 404


def test_가상_데이터는_검증을_통과하고_저장된다(client, guardian, senior_id):
    rng = random.Random(0)
    for profile in (LifeProfile(), LifeProfile(wake=5.0, sleep=23.5, activity_scale=2.0)):
        d = generate_normal_day(profile, rng)
        assert len(d.hourly_activity) == 24
        assert d.activity_level == sum(d.hourly_activity)
        res = client.put(f"/seniors/{senior_id}/records/{day(1)}", json=d.model_dump(mode="json"), headers=guardian)
        assert res.status_code in (200, 201)
        assert res.json()["source"] == "simulated"
