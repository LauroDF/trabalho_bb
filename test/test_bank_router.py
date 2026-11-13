import pytest


def test_home_endpoint(app_client):
    response = app_client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {"message": "API funcionando"}


def test_register_account_success(app_client, monkeypatch):
    from trabalho_bb.routers import bank_router

    monkeypatch.setattr(
        bank_router, "create_account",
        lambda name, cpf, password, rfid: {
            "id": "id-1", "name": name, "cpf": cpf,
            "rfid": rfid, "balance": 0.0
        },
    )
    response = app_client.post("/api/clients", json={
        "name": "Maria", "cpf": "52998224725",
        "password": "senha12345", "rfid": "123456789012"
    })
    assert response.status_code == 201
    assert response.get_json()["success"] is True


def test_register_account_missing_body(app_client):
    response = app_client.post("/api/clients", json={})
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_login_success(app_client, monkeypatch):
    from trabalho_bb.routers import bank_router

    monkeypatch.setattr(
        bank_router, "authenticate_client",
        lambda rfid, password: {"id": "id-1", "rfid": rfid}
    )
    response = app_client.post("/api/auth", json={
        "rfid": "123456789012", "password": "senha12345"
    })
    assert response.status_code == 200
    assert response.get_json()["data"]["id"] == "id-1"


def test_get_client_success(app_client, monkeypatch):
    from trabalho_bb.routers import bank_router

    monkeypatch.setattr(
        bank_router, "get_client_data_account",
        lambda client_id: {"id": client_id, "name": "Maria"}
    )
    response = app_client.get("/api/clients/id-1")
    assert response.status_code == 200
    assert response.get_json()["data"]["name"] == "Maria"


def test_delete_client_success(app_client, monkeypatch):
    from trabalho_bb.routers import bank_router

    monkeypatch.setattr(bank_router, "delete_client_account", lambda _id: None)
    response = app_client.delete("/api/clients/id-1")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_rfid_timeout_returns_408(app_client, monkeypatch):
    from trabalho_bb.routers import bank_router
    from trabalho_bb.exceptions.exceptions import RfidTimeoutError

    def timeout():
        raise RfidTimeoutError("Tempo esgotado")

    monkeypatch.setattr(bank_router, "read_card", timeout)
    response = app_client.get("/api/rfid")
    assert response.status_code == 408
