import pytest

from trabalho_bb.exceptions.exceptions import (
    IncorrectPasswordError,
    InvalidCpfError,
    InvalidDepositAmountError,
    InvalidNameError,
    InvalidRfidError,
    InvalidWithdrawAmountError,
    MissingValueError,
    PasswordNotFoundError,
)
from trabalho_bb.services import bank_service as service


@pytest.fixture(autouse=True)
def disable_real_redis(monkeypatch):
    monkeypatch.setattr(service, "post_client", lambda _data: None)
    monkeypatch.setattr(service, "get_client", lambda _client_id: None)
    monkeypatch.setattr(service, "delete_client", lambda _client_id: None)


def test_hash_password_is_sha256():
    assert service.hash_password("abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


@pytest.mark.parametrize(
    "args",
    [
        (None, "52998224725", "senha12345", "123456789012"),
        ("Maria", None, "senha12345", "123456789012"),
        ("Maria", "52998224725", None, "123456789012"),
        ("Maria", "52998224725", "senha12345", None),
    ],
)
def test_create_account_requires_all_fields(args):
    with pytest.raises(MissingValueError):
        service.create_account(*args)


def test_create_account_validates_name(monkeypatch):
    with pytest.raises(InvalidNameError):
        service.create_account("Al", "52998224725", "senha12345", "123456789012")


def test_create_account_validates_password():
    with pytest.raises(IncorrectPasswordError):
        service.create_account("Maria", "52998224725", "123", "123456789012")


def test_create_account_validates_cpf():
    with pytest.raises(InvalidCpfError):
        service.create_account("Maria", "11111111111", "senha12345", "123456789012")


def test_create_account_validates_rfid():
    with pytest.raises(InvalidRfidError):
        service.create_account("Maria", "52998224725", "senha12345", "123")


def test_create_and_authenticate_account(monkeypatch):
    stored = {}

    def save(name, cpf, password_hash, rfid, balance):
        stored.update(
            id="id-teste", name=name, cpf=cpf, password=password_hash,
            rfid=rfid, balance=balance
        )
        return "id-teste"

    monkeypatch.setattr(service, "save_account_in_db", save)
    result = service.create_account(
        "Maria Teste", "52998224725", "senha12345", "123456789012"
    )
    assert result["id"] == "id-teste"
    assert "password" not in result

    monkeypatch.setattr(
        service, "search_client_by_rfid",
        lambda _rfid: (
            stored["id"], stored["name"], stored["cpf"],
            stored["password"], stored["balance"]
        ),
    )
    authenticated = service.authenticate_client("123456789012", "senha12345")
    assert authenticated["name"] == "Maria Teste"


def test_authenticate_rejects_wrong_password(monkeypatch):
    monkeypatch.setattr(
        service, "search_client_by_rfid",
        lambda _rfid: ("id", "Maria", "52998224725",
                       service.hash_password("senha-correta"), 0.0),
    )
    with pytest.raises(PasswordNotFoundError):
        service.authenticate_client("123456789012", "senha-errada")


@pytest.mark.parametrize("amount", [0, -1, 10000.01])
def test_withdraw_rejects_invalid_amount(amount):
    with pytest.raises(InvalidWithdrawAmountError):
        service.withdraw_client_account("id", amount)


@pytest.mark.parametrize("amount", [0, -1, 1000000.01])
def test_deposit_rejects_invalid_amount(amount):
    with pytest.raises(InvalidDepositAmountError):
        service.deposit_client_account("id", amount)


def test_get_client_data_uses_cache_when_available(monkeypatch):
    from trabalho_bb.cache.schemas import ClientData

    cached = ClientData("id", "Maria", "52998224725", "123456789012", 10.0)
    monkeypatch.setattr(service, "get_client", lambda _id: cached)
    monkeypatch.setattr(
        service, "get_client_data_by_id",
        lambda _id: pytest.fail("O banco não deveria ser consultado"),
    )
    result = service.get_client_data_account("id")
    assert result["name"] == "Maria"
    assert result["balance"] == 10.0
