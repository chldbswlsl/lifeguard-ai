import random

import pytest

from app.simulate import LifeProfile, generate_normal_day


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


def test_upsert_creates_then_updates(client, guardian, senior_id):
    url = f"/seniors/{senior_id}/records/2026-09-29"
    res = client.put(url, json=RECORD, headers=guardian)
    assert res.status_code == 201
    assert res.json()["meal_times"] == ["08:00:00", "12:30:00", "18:10:00"]

    res = client.put(url, json={**RECORD, "activity_level": 100}, headers=guardian)
    assert res.status_code == 200
    assert res.json()["activity_level"] == 100
    assert len(client.get(f"/seniors/{senior_id}/records", headers=guardian).json()) == 1


def test_list_with_date_range(client, guardian, senior_id):
    for day in ("2026-09-01", "2026-09-15", "2026-09-29"):
        client.put(f"/seniors/{senior_id}/records/{day}", json=RECORD, headers=guardian)
    res = client.get(f"/seniors/{senior_id}/records?start=2026-09-10&end=2026-09-29", headers=guardian)
    assert [r["date"] for r in res.json()] == ["2026-09-15", "2026-09-29"]


def test_hourly_activity_must_have_24_values(client, guardian, senior_id):
    res = client.put(
        f"/seniors/{senior_id}/records/2026-09-29", json={**RECORD, "hourly_activity": [1] * 23}, headers=guardian
    )
    assert res.status_code == 422


def test_get_and_delete(client, guardian, senior_id):
    url = f"/seniors/{senior_id}/records/2026-09-29"
    assert client.get(url, headers=guardian).status_code == 404
    client.put(url, json=RECORD, headers=guardian)
    assert client.get(url, headers=guardian).status_code == 200
    assert client.delete(url, headers=guardian).status_code == 204
    assert client.get(url, headers=guardian).status_code == 404


def test_other_guardian_cannot_access_records(client, guardian, other_guardian, senior_id):
    url = f"/seniors/{senior_id}/records/2026-09-29"
    client.put(url, json=RECORD, headers=guardian)
    assert client.get(url, headers=other_guardian).status_code == 404
    assert client.put(url, json=RECORD, headers=other_guardian).status_code == 404


def test_simulated_day_is_valid_and_saves(client, guardian, senior_id):
    day = generate_normal_day(LifeProfile(), random.Random(0))
    assert len(day.hourly_activity) == 24
    assert day.activity_level == sum(day.hourly_activity)
    res = client.put(
        f"/seniors/{senior_id}/records/2026-09-29", json=day.model_dump(mode="json"), headers=guardian
    )
    assert res.status_code == 201
    assert res.json()["source"] == "simulated"
