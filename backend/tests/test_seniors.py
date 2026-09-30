def create_senior(client, headers, name="홍길동") -> int:
    res = client.post("/seniors", json={"name": name, "birth_year": 1945}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_guardian_sees_only_own_seniors(client, guardian, other_guardian):
    mine = create_senior(client, guardian, "내 어르신")
    create_senior(client, other_guardian, "남의 어르신")

    res = client.get("/seniors", headers=guardian)
    assert [s["id"] for s in res.json()] == [mine]


def test_other_guardian_gets_404(client, guardian, other_guardian):
    sid = create_senior(client, guardian)
    assert client.get(f"/seniors/{sid}", headers=other_guardian).status_code == 404
    assert client.patch(f"/seniors/{sid}", json={"name": "x"}, headers=other_guardian).status_code == 404


def test_admin_sees_all(client, guardian, other_guardian, admin):
    create_senior(client, guardian)
    create_senior(client, other_guardian)
    assert len(client.get("/seniors", headers=admin).json()) == 2


def test_partial_update(client, guardian):
    sid = create_senior(client, guardian)
    res = client.patch(f"/seniors/{sid}", json={"address": "서울시"}, headers=guardian)
    assert res.status_code == 200
    assert res.json()["address"] == "서울시"
    assert res.json()["birth_year"] == 1945  # 보내지 않은 필드는 그대로


def test_only_admin_can_delete(client, guardian, admin):
    sid = create_senior(client, guardian)
    assert client.delete(f"/seniors/{sid}", headers=guardian).status_code == 403
    assert client.delete(f"/seniors/{sid}", headers=admin).status_code == 204
    assert client.get(f"/seniors/{sid}", headers=admin).status_code == 404


def test_admin_links_guardian(client, guardian, other_guardian, admin):
    sid = create_senior(client, guardian)
    res = client.post(f"/seniors/{sid}/guardians", json={"email": "other@test.com"}, headers=admin)
    assert res.status_code == 200
    assert {g["email"] for g in res.json()} == {"guardian@test.com", "other@test.com"}
    # 이제 두 번째 보호자도 볼 수 있다
    assert client.get(f"/seniors/{sid}", headers=other_guardian).status_code == 200


def test_list_includes_latest_record(client, guardian):
    sid = create_senior(client, guardian)
    empty = client.get("/seniors", headers=guardian).json()[0]
    assert empty["last_record_date"] is None and empty["guardian_count"] == 1

    for day, level in (("2026-09-28", 300), ("2026-09-29", 250)):
        client.put(f"/seniors/{sid}/records/{day}", json={"activity_level": level}, headers=guardian)
    item = client.get("/seniors", headers=guardian).json()[0]
    assert item["last_record_date"] == "2026-09-29"
    assert item["last_activity_level"] == 250
