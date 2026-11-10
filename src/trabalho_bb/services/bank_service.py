import hashlib
from flask import (
    Flask,
    jsonify,
    request,
)
from trabalho_bb.repositories.bank_repository import (
    create_account,
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

def authenticate_client(rfid, password_input):
        if not rfid:
            raise MissingValueError("Tag não identificada")

        if not password_input:
            raise MissingValueError("Senha não fornecida")

        if len(password_input) < 8 or len(password_input) > 128:
            raise IncorrectPasswordError("Senha não pode ter menos que oito ou mais que 128 caracteres")

        client = search_client_by_rfid(rfid)
        id, name, cpf, password, balance = client

        hashed_password_input = hash_password(password_input)

        if hashed_password_input != password:
            raise PasswordNotFoundError("Senha incorreta")

        return {
            "id": id,
            "name": name,
            "balance": balance
        }

# ENDPOINTS:
# criar usuário, deletar usuário, depositar e sacar
