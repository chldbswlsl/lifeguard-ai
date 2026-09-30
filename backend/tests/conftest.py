import os

os.environ["DATABASE_URL"] = "sqlite://"  # app import 전에 설정해야 한다

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User, UserRole
from app.security import hash_password


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def signup_and_login(client: TestClient, email: str, password: str = "password123", name: str = "보호자") -> dict:
    res = client.post("/auth/signup", json={"email": email, "password": password, "name": name})
    assert res.status_code == 201, res.text
    return login(client, email, password)


def login(client: TestClient, email: str, password: str) -> dict:
    res = client.post("/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def guardian(client) -> dict:
    return signup_and_login(client, "guardian@test.com")


@pytest.fixture
def other_guardian(client) -> dict:
    return signup_and_login(client, "other@test.com")


@pytest.fixture
def admin(client) -> dict:
    with SessionLocal() as db:
        db.add(User(email="admin@test.com", password_hash=hash_password("adminpass"), name="관리자", role=UserRole.ADMIN))
        db.commit()
    return login(client, "admin@test.com", "adminpass")
