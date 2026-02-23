import json
import pytest

from app.services.exceptions import CacheUnavailable
import redis


class DummyRedis:
    """Простий fake Redis для тестів."""
    def __init__(self, initial=None, fail_get=False, fail_set=False, fail_delete=False):
        self.store = dict(initial or {})
        self.fail_get = fail_get
        self.fail_set = fail_set
        self.fail_delete = fail_delete
        self.set_calls = []
        self.get_calls = []
        self.delete_calls = []

    def get(self, key):
        self.get_calls.append(key)
        if self.fail_get:
            raise redis.RedisError("redis get failed")
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))
        if self.fail_set:
            raise redis.RedisError("redis set failed")
        self.store[key] = value
        return True

    def delete(self, key):
        self.delete_calls.append(key)
        if self.fail_delete:
            raise redis.RedisError("redis delete failed")
        self.store.pop(key, None)
        return 1


class DummyDB:
    """Fake DB, який дозволяє порахувати скільки разів його викликали."""
    def __init__(self, wallet_obj=None, fail=False):
        self.wallet_obj = wallet_obj
        self.fail = fail
        self.calls = 0

    def get(self, model, wallet_id):
        self.calls += 1
        if self.fail:
            raise RuntimeError("DB should not be called")
        return self.wallet_obj


class DummyWallet:
    def __init__(self, wallet_id=1, balance="100.00", user_id=7):
        self.id = wallet_id
        self.balance = balance
        self.user_id = user_id


def test_cache_hit_returns_cached_and_skips_db(monkeypatch):
    """
    Redis доступний, ключ є -> повертаємо дані з кешу, в БД не йдемо.
    """
    from app.services import wallets as wallets_service

    cached = {"id": 1, "balance": "55.00", "user_id": 7}
    r = DummyRedis(initial={ "wallet:1": json.dumps(cached) })

    monkeypatch.setattr(wallets_service, "get_redis", lambda: r)

    db = DummyDB(fail=True)  # якщо звернемось до БД — тест впаде

    data = wallets_service.get_wallet_cached(db, 1)

    assert data == cached
    assert db.calls == 0
    assert r.get_calls == ["wallet:1"]


def test_cache_miss_fetches_db_and_sets_cache(monkeypatch):
    """
    Redis доступний, ключа нема -> читаємо з БД і записуємо в кеш.
    """
    from app.services import wallets as wallets_service

    r = DummyRedis(initial={})  # пустий кеш
    monkeypatch.setattr(wallets_service, "get_redis", lambda: r)

    wallet = DummyWallet(wallet_id=2, balance="100.00", user_id=10)
    db = DummyDB(wallet_obj=wallet)

    data = wallets_service.get_wallet_cached(db, 2)

    assert data["id"] == 2
    assert data["balance"] == "100.00"
    assert data["user_id"] == 10
    assert db.calls == 1

    # перевіряємо, що записали в Redis
    assert r.set_calls, "Expected Redis.set to be called"
    key, value, ex = r.set_calls[0]
    assert key == "wallet:2"
    assert json.loads(value) == {"id": 2, "balance": "100.00", "user_id": 10}
    assert ex is not None  # TTL заданий


def test_redis_unavailable_falls_back_to_db(monkeypatch):
    """
    get_redis() кидає CacheUnavailable -> сервіс не падає, йде в БД.
    """
    from app.services import wallets as wallets_service

    def raise_cache_unavailable():
        raise CacheUnavailable("redis down")

    monkeypatch.setattr(wallets_service, "get_redis", raise_cache_unavailable)

    wallet = DummyWallet(wallet_id=3, balance="77.00", user_id=11)
    db = DummyDB(wallet_obj=wallet)

    data = wallets_service.get_wallet_cached(db, 3)

    assert data == {"id": 3, "balance": "77.00", "user_id": 11}
    assert db.calls == 1


def test_redis_get_error_falls_back_to_db(monkeypatch):
    """
    Redis є, але GET падає -> сервіс не падає, йде в БД.
    """
    from app.services import wallets as wallets_service

    r = DummyRedis(fail_get=True)
    monkeypatch.setattr(wallets_service, "get_redis", lambda: r)

    wallet = DummyWallet(wallet_id=4, balance="12.00", user_id=99)
    db = DummyDB(wallet_obj=wallet)

    data = wallets_service.get_wallet_cached(db, 4)

    assert data == {"id": 4, "balance": "12.00", "user_id": 99}
    assert db.calls == 1


def test_redis_set_error_still_returns_db_data(monkeypatch):
    """
    Redis є, але SET падає -> ми все одно повертаємо дані з БД.
    """
    from app.services import wallets as wallets_service

    r = DummyRedis(fail_set=True)
    monkeypatch.setattr(wallets_service, "get_redis", lambda: r)

    wallet = DummyWallet(wallet_id=5, balance="999.99", user_id=1)
    db = DummyDB(wallet_obj=wallet)

    data = wallets_service.get_wallet_cached(db, 5)

    assert data == {"id": 5, "balance": "999.99", "user_id": 1}
    assert db.calls == 1


def test_invalidate_cache_no_redis_no_crash(monkeypatch):
    """
    invalidate_wallet_cache не повинен падати, якщо Redis нема.
    """
    from app.services import wallets as wallets_service

    monkeypatch.setattr(wallets_service, "get_redis", lambda: None)

    wallets_service.invalidate_wallet_cache(1)


def test_invalidate_cache_redis_delete_error_no_crash(monkeypatch):
    """
    invalidate_wallet_cache не повинен падати, якщо delete в Redis кидає помилку.
    """
    from app.services import wallets as wallets_service

    r = DummyRedis(fail_delete=True)
    monkeypatch.setattr(wallets_service, "get_redis", lambda: r)

    wallets_service.invalidate_wallet_cache(1)
    assert r.delete_calls == ["wallet:1"]
