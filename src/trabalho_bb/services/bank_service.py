import hashlib
from ..hardware.tag_reader import read_card

from trabalho_bb.repositories.bank_repository import (
    save_account_in_db,
    update_account_by_id,
    get_client_data_by_id,
    withdraw_by_id,
    deposit_by_id,
    search_client_by_rfid,
    delete_account_by_id,
)

from ..exceptions.exceptions import (
    PasswordNotFoundError,
    IncorrectPasswordError,
    MissingValueError,
    InvalidWithdrawAmountError,
    InvalidDepositAmountError,
)

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

    if len(password) < 8 or len(password) > 128:
        raise IncorrectPasswordError("Senha não pode ter menos que oito ou mais que 128 caracteres")

    hashed_password = hash_password(password)
    id = save_account_in_db(name, cpf, hashed_password, rfid, balance)

    return {
        "id": id,
        "name": name,
        "cpf": cpf,
        "rfid": rfid,
        "balance": balance
    }

def authenticate_client(rfid, password_input):
        if not rfid:
            raise MissingValueError("Tag não identificada")

        if not password_input:
            raise MissingValueError("Senha não fornecida")

        if len(password_input) < 8 or len(password_input) > 128:
            raise IncorrectPasswordError("Senha não pode ter menos que oito ou mais que 128 caracteres")

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

    if password is not None:
        if len(password) < 8 or len(password) > 128:
            raise IncorrectPasswordError("Senha não pode ter menos que oito ou mais que 128 caracteres")
        hashed_password = hash_password(password)

    update_account_by_id(id, name, cpf, hashed_password, rfid)

    client_data = get_client_data_by_id(id)
    client_id, client_name, client_cpf, client_rfid, client_balance = client_data

    return {
        "id": client_id,
        "name": client_name,
        "cpf": client_cpf,
        "rfid": client_rfid,
        "balance": client_balance
    }

def get_client_data_account(id):
    client_data = get_client_data_by_id(id)

    id, name, cpf, rfid, balance = client_data

    return {
        "id": id,
        "name": name,
        "cpf": cpf,
        "rfid": rfid,
        "balance": balance
    }
 
def withdraw_client_account(id, withdraw_amount):
    if withdraw_amount <= 0.0:
        raise InvalidWithdrawAmountError("Valor de saque inválido")

    if withdraw_amount > 10000:
        raise InvalidWithdrawAmountError("Valor de saque maior que o permitido")

    withdraw_by_id(id, withdraw_amount)

def deposit_client_account(id, deposit_amount):
    if deposit_amount <= 0.0:
        raise InvalidDepositAmountError("Valor de depósito inválido")

    if deposit_amount > 1000000:
        raise InvalidDepositAmountError("Valor de depósito maior que o permitido")

    deposit_by_id(id, deposit_amount)

def delete_client_account(id):
    delete_account_by_id(id)
    