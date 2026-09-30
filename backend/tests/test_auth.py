from app.config import settings
from tests.conftest import PASSWORD, login


def signup(client, **overrides):
    body = {"email": "new@test.com", "password": PASSWORD, "name": "새보호자", **overrides}
    return client.post("/auth/signup", json=body)


def test_가입_로그인_내정보(client, guardian):
    res = client.get("/auth/me", headers=guardian)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "guardian@test.com"
    assert body["role"] == "guardian"
    assert "password_hash" not in body and "token_version" not in body


def test_같은_이메일은_대소문자가_달라도_중복(client, guardian):
    res = signup(client, email="GUARDIAN@test.com")
    assert res.status_code == 409
    assert res.json()["detail"] == "이미 가입된 이메일입니다"


def test_비밀번호_규칙(client):
    short = signup(client, password="ab1")
    assert short.status_code == 422
    assert short.json()["errors"][0] == {"field": "password", "label": "비밀번호", "message": "8자 이상 입력해 주세요"}

    assert "영문과 숫자" in signup(client, password="onlyletters").json()["detail"]
    assert "영문과 숫자" in signup(client, password="12345678").json()["detail"]
    assert "이메일과 같은" in signup(client, email="abc12345@test.com", password="abc12345").json()["detail"]


def test_입력값_검증_에러는_한국어_항목별로(client):
    res = signup(client, email="not-an-email", name="   ", phone="abc", role="admin")
    assert res.status_code == 422
    errors = {e["field"]: e["message"] for e in res.json()["errors"]}
    assert errors["email"] == "올바른 이메일 형식이 아닙니다"
    assert errors["name"] == "값을 입력해 주세요"  # 공백만 입력한 이름
    assert errors["phone"] == "형식이 올바르지 않습니다"
    assert errors["role"] == "허용되지 않는 항목입니다"  # 가입할 때 관리자 권한을 요청할 수 없다


def test_빈_연락처는_null로_저장(client):
    assert signup(client, phone="  ").json()["phone"] is None


def test_틀린_비밀번호는_401(client, guardian):
    res = client.post("/auth/login", data={"username": "guardian@test.com", "password": "wrongpass1"})
    assert res.status_code == 401
    # 없는 이메일도 같은 메시지 (가입 여부를 알려주지 않는다)
    res2 = client.post("/auth/login", data={"username": "nobody@test.com", "password": "wrongpass1"})
    assert res2.status_code == 401 and res2.json()["detail"] == res.json()["detail"]


def test_로그인_실패가_반복되면_429(client, guardian):
    for _ in range(settings.login_max_failures):
        assert (
            client.post("/auth/login", data={"username": "guardian@test.com", "password": "wrong1234"}).status_code
            == 401
        )
    res = client.post("/auth/login", data={"username": "guardian@test.com", "password": PASSWORD})
    assert res.status_code == 429  # 잠긴 동안에는 맞는 비밀번호도 거절
    assert "분 후에 다시 시도" in res.json()["detail"]
    assert int(res.headers["Retry-After"]) > 0


def test_로그인_성공하면_실패횟수_초기화(client, guardian):
    for _ in range(settings.login_max_failures - 1):
        client.post("/auth/login", data={"username": "guardian@test.com", "password": "wrong1234"})
    login(client, "guardian@test.com", PASSWORD)
    for _ in range(settings.login_max_failures - 1):
        client.post("/auth/login", data={"username": "guardian@test.com", "password": "wrong1234"})
    # IP 기준 카운터는 성공해도 남는다 → 총 실패가 한도를 넘었으므로 잠김
    assert client.post("/auth/login", data={"username": "guardian@test.com", "password": PASSWORD}).status_code == 429


def test_토큰_없거나_잘못되면_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_다른_비밀키로_만든_토큰은_거절(client, guardian):
    import jwt

    forged = jwt.encode(
        {"sub": "1", "ver": 0, "exp": 9999999999}, "other-secret-key-other-secret-key", algorithm="HS256"
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_내정보_수정(client, guardian):
    res = client.patch("/auth/me", json={"phone": "010-1234-5678"}, headers=guardian)
    assert res.status_code == 200
    assert res.json()["phone"] == "010-1234-5678"
    assert res.json()["name"] == "보호자"
    # 이름을 null로 보내면 거절 (DB 오류 500이 나면 안 된다)
    assert client.patch("/auth/me", json={"name": None}, headers=guardian).status_code == 422


def test_비밀번호_변경하면_이전_토큰은_무효(client, guardian):
    bad = client.post(
        "/auth/me/password", json={"current_password": "wrong", "new_password": "newpass123"}, headers=guardian
    )
    assert bad.status_code == 400
    same = client.post(
        "/auth/me/password", json={"current_password": PASSWORD, "new_password": PASSWORD}, headers=guardian
    )
    assert same.status_code == 400

    ok = client.post(
        "/auth/me/password", json={"current_password": PASSWORD, "new_password": "newpass123"}, headers=guardian
    )
    assert ok.status_code == 200
    new_headers = {"Authorization": f"Bearer {ok.json()['access_token']}"}

    assert client.get("/auth/me", headers=guardian).status_code == 401  # 이전 토큰
    assert client.get("/auth/me", headers=new_headers).status_code == 200  # 새 토큰
    login(client, "guardian@test.com", "newpass123")


def test_비밀번호_변경_시도_제한(client, guardian):
    for _ in range(10):
        client.post(
            "/auth/me/password", json={"current_password": "wrong", "new_password": "newpass123"}, headers=guardian
        )
    res = client.post(
        "/auth/me/password", json={"current_password": PASSWORD, "new_password": "newpass123"}, headers=guardian
    )
    assert res.status_code == 429


def test_회원가입_시도_제한(client):
    for i in range(10):
        signup(client, email=f"user{i}@test.com")
    assert signup(client, email="user99@test.com").status_code == 429
