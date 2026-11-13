import pytest

from trabalho_bb.exceptions.exceptions import (
    ClientNotFoundError,
    InsufficientBalanceError,
    NoFieldsToBeUpdatedError,
)
from trabalho_bb.repositories import bank_repository as repo


def test_initialize_database_creates_table(database):
    import sqlite3
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clients'"
        ).fetchone()
    assert row is not None


def test_save_and_search_client(database):
    client_id = repo.save_account_in_db(
        "Maria Teste", "52998224725", repo.hash_password("senha12345"),
        "111122223333", 125.0
    )
    result = repo.search_client_by_rfid("111122223333")
    assert result[0] == client_id
    assert result[1] == "Maria Teste"
    assert result[2] == "52998224725"
    assert result[4] == 125.0


def test_get_client_data_by_id(sample_client):
    result = repo.get_client_data_by_id(sample_client["id"])
    assert result[0] == sample_client["id"]
    assert result[1] == "Teste Cliente"
    assert result[4] == 500.0


def test_withdraw_updates_balance(sample_client):
    repo.withdraw_by_id(sample_client["id"], 100.0)
    result = repo.get_client_data_by_id(sample_client["id"])
    assert result[4] == 400.0


def test_deposit_updates_balance(sample_client):
    repo.deposit_by_id(sample_client["id"], 75.0)
    result = repo.get_client_data_by_id(sample_client["id"])
    assert result[4] == 575.0


def test_withdraw_rejects_insufficient_balance(sample_client):
    with pytest.raises(InsufficientBalanceError):
        repo.withdraw_by_id(sample_client["id"], 900.0)


def test_update_account_fields(sample_client):
    repo.update_account_by_id(
        sample_client["id"], new_name="Nome Atualizado", new_rfid="999988887777"
    )
    result = repo.get_client_data_by_id(sample_client["id"])
    assert result[1] == "Nome Atualizado"
    assert result[3] == "999988887777"


def test_update_without_fields_raises(sample_client):
    with pytest.raises(NoFieldsToBeUpdatedError):
        repo.update_account_by_id(sample_client["id"])


def test_delete_account(sample_client):
    repo.delete_account_by_id(sample_client["id"])
    with pytest.raises(ClientNotFoundError):
        repo.get_client_data_by_id(sample_client["id"])


def test_search_unknown_rfid_raises(database):
    with pytest.raises(ClientNotFoundError):
        repo.search_client_by_rfid("000000000000")
