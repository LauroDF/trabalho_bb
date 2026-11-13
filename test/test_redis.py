import json

from trabalho_bb.cache import redis as cache
from trabalho_bb.cache.schemas import ClientData


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.last_set = None

    def set(self, key, value, ex=None):
        self.values[key] = value
        self.last_set = (key, value, ex)

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)

    def close(self):
        pass


def test_post_client_serializes_data(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis_client", fake)
    client = ClientData("1", "Maria", "52998224725", "123456789012", 20.0)

    cache.post_client(client)

    key, value, ttl = fake.last_set
    assert key == "client:1"
    assert json.loads(value)["name"] == "Maria"
    assert ttl == cache.CLIENT_DATA_TTL_SECONDS


def test_get_client_returns_client_data(monkeypatch):
    fake = FakeRedis()
    fake.values["client:1"] = json.dumps({
        "id": "1", "name": "Maria", "cpf": "52998224725",
        "rfid": "123456789012", "balance": 20.0
    })
    monkeypatch.setattr(cache, "redis_client", fake)

    result = cache.get_client("1")
    assert result == ClientData("1", "Maria", "52998224725", "123456789012", 20.0)


def test_get_client_returns_none_when_key_missing(monkeypatch):
    monkeypatch.setattr(cache, "redis_client", FakeRedis())
    assert cache.get_client("inexistente") is None


def test_get_client_removes_invalid_json(monkeypatch):
    fake = FakeRedis()
    fake.values["client:1"] = "{json inválido"
    monkeypatch.setattr(cache, "redis_client", fake)

    assert cache.get_client("1") is None
    assert "client:1" not in fake.values


def test_delete_client_removes_key(monkeypatch):
    fake = FakeRedis()
    fake.values["client:1"] = "{}"
    monkeypatch.setattr(cache, "redis_client", fake)

    cache.delete_client("1")
    assert "client:1" not in fake.values


def test_close_redis_connection(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis_client", fake)
    cache.close_redis_connection()
