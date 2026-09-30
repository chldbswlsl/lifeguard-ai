import datetime as dt


def create_senior(client, headers, name="홍길동") -> int:
    res = client.post("/seniors", json={"name": name, "birth_year": 1945}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_보호자는_담당_어르신만_보인다(client, guardian, other_guardian):
    mine = create_senior(client, guardian, "내 어르신")
    create_senior(client, other_guardian, "남의 어르신")

    res = client.get("/seniors", headers=guardian)
    assert [s["id"] for s in res.json()] == [mine]


def test_담당이_아니면_404(client, guardian, other_guardian):
    sid = create_senior(client, guardian)
    assert client.get(f"/seniors/{sid}", headers=other_guardian).status_code == 404
    assert client.patch(f"/seniors/{sid}", json={"name": "x"}, headers=other_guardian).status_code == 404
    assert client.get(f"/seniors/{sid}/guardians", headers=other_guardian).status_code == 404


def test_관리자는_전체가_보인다(client, guardian, other_guardian, admin):
    create_senior(client, guardian)
    create_senior(client, other_guardian)
    assert len(client.get("/seniors", headers=admin).json()) == 2


def test_부분_수정(client, guardian):
    sid = create_senior(client, guardian)
    res = client.patch(f"/seniors/{sid}", json={"address": " 서울시 "}, headers=guardian)
    assert res.status_code == 200
    assert res.json()["address"] == "서울시"  # 앞뒤 공백 제거
    assert res.json()["birth_year"] == 1945  # 보내지 않은 필드는 그대로
    # 선택 항목은 빈 문자열을 보내면 비워진다
    assert client.patch(f"/seniors/{sid}", json={"address": ""}, headers=guardian).json()["address"] is None
    # 필수 항목(이름)은 비울 수 없다
    assert client.patch(f"/seniors/{sid}", json={"name": None}, headers=guardian).status_code == 422


def test_출생연도_검증(client, guardian):
    future = dt.date.today().year + 1
    assert client.post("/seniors", json={"name": "a", "birth_year": future}, headers=guardian).status_code == 422
    assert client.post("/seniors", json={"name": "a", "birth_year": 1800}, headers=guardian).status_code == 422


def test_삭제는_관리자만_기록도_함께_삭제(client, guardian, admin):
    sid = create_senior(client, guardian)
    today = dt.date.today().isoformat()
    client.put(f"/seniors/{sid}/records/{today}", json={"activity_level": 1}, headers=guardian)

    assert client.delete(f"/seniors/{sid}", headers=guardian).status_code == 403
    assert client.delete(f"/seniors/{sid}", headers=admin).status_code == 204
    assert client.get(f"/seniors/{sid}", headers=admin).status_code == 404
    assert client.delete(f"/seniors/{sid}", headers=admin).status_code == 404

    from app.database import SessionLocal
    from app.models import DailyRecord

    with SessionLocal() as db:
        assert db.query(DailyRecord).count() == 0  # ON DELETE CASCADE


def test_관리자가_보호자_연결_해제(client, guardian, other_guardian, admin):
    sid = create_senior(client, guardian)
    res = client.post(f"/seniors/{sid}/guardians", json={"email": "other@test.com"}, headers=admin)
    assert res.status_code == 200
    assert {g["email"] for g in res.json()} == {"guardian@test.com", "other@test.com"}
    assert client.get(f"/seniors/{sid}", headers=other_guardian).status_code == 200

    # 두 번 연결해도 중복되지 않는다
    again = client.post(f"/seniors/{sid}/guardians", json={"email": "other@test.com"}, headers=admin)
    assert len(again.json()) == 2

    other_id = next(g["id"] for g in res.json() if g["email"] == "other@test.com")
    assert client.delete(f"/seniors/{sid}/guardians/{other_id}", headers=guardian).status_code == 403
    res = client.delete(f"/seniors/{sid}/guardians/{other_id}", headers=admin)
    assert [g["email"] for g in res.json()] == ["guardian@test.com"]
    assert client.get(f"/seniors/{sid}", headers=other_guardian).status_code == 404
    assert client.delete(f"/seniors/{sid}/guardians/{other_id}", headers=admin).status_code == 404


def test_보호자_연결_오류(client, guardian, admin):
    sid = create_senior(client, guardian)
    assert client.post(f"/seniors/{sid}/guardians", json={"email": "nobody@test.com"}, headers=admin).status_code == 404
    # 관리자 계정은 보호자로 연결할 수 없다
    assert client.post(f"/seniors/{sid}/guardians", json={"email": "admin@test.com"}, headers=admin).status_code == 404
    assert client.post("/seniors/999/guardians", json={"email": "guardian@test.com"}, headers=admin).status_code == 404
    assert client.delete("/seniors/999/guardians/1", headers=admin).status_code == 404


def test_목록에_최근_기록_요약(client, guardian):
    sid = create_senior(client, guardian)
    empty = client.get("/seniors", headers=guardian).json()[0]
    assert empty["last_record_date"] is None and empty["guardian_count"] == 1

    today = dt.date.today()
    for days_ago, level in ((2, 300), (1, 250)):
        day = (today - dt.timedelta(days=days_ago)).isoformat()
        client.put(f"/seniors/{sid}/records/{day}", json={"activity_level": level}, headers=guardian)
    item = client.get("/seniors", headers=guardian).json()[0]
    assert item["last_record_date"] == (today - dt.timedelta(days=1)).isoformat()
    assert item["last_activity_level"] == 250
