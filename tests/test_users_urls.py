from datetime import datetime
import app.api.users as users_router  


class DummyUser:
    def __init__(self, id: int, name: str = "Test"):
        self.id = id
        self.name = name
        self.created_at = datetime(2026, 2, 7, 12, 0, 0)


def test_post_users_creates_user(client, monkeypatch):
    def fake_create_user(db, *args, **kwargs):
        return DummyUser(id=1, name="John")


    monkeypatch.setattr(users_router, "create_user", fake_create_user)

    r = client.post("/users", params={"name": "John"})
    assert r.status_code == 200

    data = r.json()
    assert data["id"] == 1
    assert data.get("name") in ("John", None)  
    assert data.get("created_at") is not None


def test_get_user_returns_user(client, monkeypatch):
    def fake_get_user_by_id(db, user_id: int):
        return DummyUser(id=user_id, name="Alice")

    monkeypatch.setattr(users_router, "get_user_by_id", fake_get_user_by_id)

    r = client.get("/users/7")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 7
