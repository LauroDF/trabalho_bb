import hashlib
from flask import (
    Flask,
    jsonify,
    request,
)
from trabalho_bb.repositories.bank_repository import (
    save_account_in_db,
    authenticate_client,
    update_client_data,
    withdraw,
    deposit,
    search_client_by_rfid,
    list_all_clients,
    delete_user_by_id,
)

from ..exceptions.exceptions import (
    ClientNotFoundError,
    PasswordNotFoundError,
    IncorrectPasswordError,
    NoFieldsToBeUpdated,
    InsufficientBalanceError, 
    DatabaseError, 
    MissingValueError,
)
from ..hardware.tag_reader import read_card

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

    hashed_password = hash_password(password)
    id = save_account_in_db(name, cpf, hashed_password, rfid, balance)

    return {
        "id": id,
        "name": name,
        "balance": balance
    }

def authenticate_client(rfid, password_input):
        if not rfid:
            raise MissingValueError("Tag não identificada")

        if not password_input:
            raise MissingValueError("Senha não fornecida")

        if len(password_input) < 8 or len(password_input) > 128:
            raise IncorrectPasswordError("Senha não pode ter menos que oito ou mais que 128 caracteres")

        client = search_client_by_rfid(rfid)
        id, name, cpf, password, balance = client

        hashed_password = hash_password(password_input)

        if hashed_password != password:
            raise PasswordNotFoundError("Senha incorreta")

        return {
            "id": id,
            "name": name,
            "balance": balance
        }

# ENDPOINTS:
# deletar usuário, atualizar conta, depositar e sacar
