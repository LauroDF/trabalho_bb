import importlib
import sys
import types

import pytest

from trabalho_bb.repositories import bank_repository


@pytest.fixture
def database(tmp_path, monkeypatch):
    """Banco isolado por teste; nunca usa trabalho_bb/data/clients.db."""
    db_path = tmp_path / "clients_test.db"
    monkeypatch.setattr(bank_repository, "DB_PATH", db_path)
    monkeypatch.setattr(bank_repository, "DB_DIR", tmp_path)
    bank_repository.initialize_database()
    return db_path


@pytest.fixture
def sample_client(database):
    client_id = bank_repository.save_account_in_db(
        name="Teste Cliente",
        cpf="52998224725",
        hashed_password=bank_repository.hash_password("senha12345"),
        rfid="123456789012",
        balance=500.0,
    )
    return {
        "id": client_id,
        "name": "Teste Cliente",
        "cpf": "52998224725",
        "rfid": "123456789012",
        "balance": 500.0,
    }


@pytest.fixture
def app_client(monkeypatch):
    """
    Importa o router sem inicializar GPIO/RFID real.
    O hardware é substituído por um módulo falso antes do import.
    """
    fake_hardware = types.ModuleType("trabalho_bb.hardware.tag_reader")
    fake_hardware.read_card = lambda: {"rfid": "123456789012"}
    monkeypatch.setitem(sys.modules, "trabalho_bb.hardware.tag_reader", fake_hardware)

    sys.modules.pop("trabalho_bb.routers.bank_router", None)
    router = importlib.import_module("trabalho_bb.routers.bank_router")
    router.app.config.update(TESTING=True)
    yield router.app.test_client()
    sys.modules.pop("trabalho_bb.routers.bank_router", None)
