import hashlib
import logging
from validate_docbr import CPF
from redis.exceptions import RedisError
from trabalho_bb.cache.redis import delete_client, get_client, post_client
from trabalho_bb.cache.schemas import ClientData

from trabalho_bb.repositories.bank_repository import (
    save_account_in_db,
    update_account_by_id,
    get_client_data_by_id,
    withdraw_by_id,
    deposit_by_id,
    search_client_by_rfid,
    delete_account_by_id,
)

from trabalho_bb.exceptions.exceptions import (
    PasswordNotFoundError,
    IncorrectPasswordError,
    MissingValueError,
    InvalidWithdrawAmountError,
    InvalidDepositAmountError,
    InvalidNameError,
    InvalidCpfError,
    InvalidRfidError
)

logger = logging.getLogger(__name__)

def _client_data_to_dict(client_data):
    return {
        "id": client_data.id,
        "name": client_data.name,
        "cpf": client_data.cpf,
        "rfid": client_data.rfid,
        "balance": client_data.balance,
    }


def _cache_client_data(client_data):
    try:
        post_client(client_data)
    except RedisError:
        logger.warning("Unable to cache client %s", client_data.id, exc_info=True)


def _get_cached_client_data(client_id):
    try:
        return get_client(client_id)
    except RedisError:
        logger.warning("Unable to read cached client %s", client_id, exc_info=True)
        return None


def _delete_cached_client_data(client_id):
    try:
        delete_client(client_id)
    except RedisError:
        logger.warning("Unable to invalidate cached client %s", client_id, exc_info=True)


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_account(name, cpf, password, rfid, balance=0.0):
    if not name:
        raise MissingValueError("Nome não fornecido")
    
    if not cpf:
        raise MissingValueError("Cpf não fornecido")

    if not password:
        raise MissingValueError("Senha não fornecida")
    
    if not rfid:
        raise MissingValueError("Tag não identificada")

    if len(name) < 3 or len(name) > 100:
        raise InvalidNameError("Nome fora dos padrões")

    if len(password) < 8 or len(password) > 128:
        raise IncorrectPasswordError("Senha fora dos padrões")

    cpf_validator = CPF()
    if not cpf_validator.validate(cpf):
        raise InvalidCpfError("Cpf inválido")

    if len(rfid) < 8 or len(rfid) > 15:
        raise InvalidRfidError("Cartão fora dos padrões")

    hashed_password = hash_password(password)
    id = save_account_in_db(name, cpf, hashed_password, rfid, balance)

    account = {
        "id": id,
        "name": name,
        "cpf": cpf,
        "rfid": rfid,
        "balance": balance
    }
    _cache_client_data(ClientData(**account))

    return account

def authenticate_client(rfid, password_input):
        if not rfid:
            raise MissingValueError("Tag não identificada")

        if not password_input:
            raise MissingValueError("Senha não fornecida")

        if len(rfid) < 8 or len(rfid) > 15:
            raise InvalidRfidError("Cartão fora dos padrões")

        if len(password_input) < 8 or len(password_input) > 128:
            raise IncorrectPasswordError("Senha fora dos padrões")

        client_data = search_client_by_rfid(rfid)
        id, name, cpf, password, balance = client_data

        hashed_password = hash_password(password_input)

        if hashed_password != password:
            raise PasswordNotFoundError("Senha incorreta")

        return {
            "id": id,
            "name": name,
            "cpf": cpf,
            "rfid": rfid,
            "balance": balance
        }

def update_client_account(id, name, cpf, password, rfid):
    hashed_password = None

    if len(name) < 3 or len(name) > 100:
        raise InvalidNameError("Nome fora dos padrões")

    if password is not None:
        if len(password) < 8 or len(password) > 128:
            raise IncorrectPasswordError("Senha fora dos padrões")
        hashed_password = hash_password(password)

    cpf_validator = CPF()
    if not cpf_validator.validate(cpf):
        raise InvalidCpfError("Cpf inválido")

    if len(rfid) < 8 or len(rfid) > 15:
        raise InvalidRfidError("Cartão fora dos padrões")

    update_account_by_id(id, name, cpf, hashed_password, rfid)

    client_data = get_client_data_by_id(id)
    cached_client_data = ClientData(*client_data)
    _cache_client_data(cached_client_data)

    return _client_data_to_dict(cached_client_data)

def get_client_data_account(id):
    cached_client_data = _get_cached_client_data(id)
    if cached_client_data is not None:
        return _client_data_to_dict(cached_client_data)

    client_data = ClientData(*get_client_data_by_id(id))
    _cache_client_data(client_data)

    return _client_data_to_dict(client_data)
 
def withdraw_client_account(id, withdraw_amount):
    if withdraw_amount <= 0.0:
        raise InvalidWithdrawAmountError("Valor de saque inválido")

    if withdraw_amount > 10000:
        raise InvalidWithdrawAmountError("Valor de saque maior que o permitido")

    withdraw_by_id(id, withdraw_amount)

    client_data = get_client_data_by_id(id)
    cached_client_data = ClientData(*client_data)
    _cache_client_data(cached_client_data)

    return {
        "balance": cached_client_data.balance
    }

def deposit_client_account(id, deposit_amount):
    if deposit_amount <= 0.0:
        raise InvalidDepositAmountError("Valor de depósito inválido")

    if deposit_amount > 1000000:
        raise InvalidDepositAmountError("Valor de depósito maior que o permitido")

    deposit_by_id(id, deposit_amount)

    client_data = get_client_data_by_id(id)
    cached_client_data = ClientData(*client_data)
    _cache_client_data(cached_client_data)

    return {
        "balance": cached_client_data.balance
    }

def delete_client_account(id):
    delete_account_by_id(id)
    _delete_cached_client_data(id)
    