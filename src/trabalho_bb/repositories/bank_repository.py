import sqlite3
import uuid
import hashlib
from pathlib import Path

from trabalho_bb.exceptions.exceptions import (
    ClientNotFoundError,
    NoFieldsToBeUpdatedError,
    InsufficientBalanceError, 
    DatabaseError, 
)

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_DIR = ROOT_DIR / "data"
DB_PATH = DB_DIR / "clients.db"

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def initialize_database():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL CHECK(length(cpf) == 11),
                password TEXT NOT NULL CHECK(length(password) >= 8),
                rfid TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0.0
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM clients")
        total_rows = cursor.fetchone()[0]

        if total_rows == 0:
            initial_clients = [
                (
                    str(uuid.uuid4()),
                    "Pedro Silva",
                    "11144477735",
                    hash_password("3443dre3t4t"),
                    "962185903074",
                    578,
                ),
                (
                    str(uuid.uuid4()),
                    "Carlo Edoardo",
                    "52998224059",
                    hash_password("43gds5yge"),
                    "701044494601",
                    2345,
                ),
                (
                    str(uuid.uuid4()),
                    "Miguel Alencar",
                    "12345678908",
                    hash_password("miguel123456"),
                    "632092037175",
                    21,
                ),
                (
                    str(uuid.uuid4()),
                    "Sophia Bonita",
                    "45678901206",
                    hash_password("admin1234567"),
                    "427066982110",
                    95046,
                ),
            ]

            cursor.executemany(
                """
                    INSERT INTO clients (id, name, cpf, password, rfid, balance)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                initial_clients,
            )
            connection.commit()
            print("DB criado e dados inseridos")

        else:
            print("DB já foi inicializado")

    except sqlite3.Error as e:
        print(f"Erro no db ao ser inicializado: {e}")
        raise DatabaseError("Erro interno ao inicializar banco de dados")

    except Exception as e:
        print(f"Erro ao inicializar db: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

def save_account_in_db(name, cpf, hashed_password, rfid, balance):
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        new_id = str(uuid.uuid4())

        cursor.execute(
            """
                INSERT INTO clients (id, name, cpf, password, rfid, balance)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id, name, cpf, hashed_password, rfid, balance),
        )

        connection.commit()
        print(f"{name} foi cadastrado(a) com sucesso")
        return new_id

    except sqlite3.IntegrityError:
        print(f"Erro: Não foi possível criar a conta por uma violação de integridade")
        raise DatabaseError("Erro interno ao criar conta")

    except sqlite3.Error as e:
        print(f"Erro no db ao criar a conta: {e}")
        raise DatabaseError("Erro interno ao criar conta")
    
    except Exception as e:
        print(f"Erro ao criar a conta: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

def update_account_by_id(id, new_name=None, new_cpf=None, new_password=None, new_rfid=None):
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        fields = []
        values = []

        if new_name is not None:
            fields.append("name = ?")
            values.append(new_name)

        if new_cpf is not None:
            fields.append("cpf = ?")
            values.append(new_cpf)

        if new_password is not None:
            fields.append("password = ?")
            values.append(new_password)

        if new_rfid is not None:
            fields.append("rfid = ?")
            values.append(new_rfid)

        if not fields:
            print("Nenhuma informação para ser atualizada")
            raise NoFieldsToBeUpdatedError("Nenhuma informação para ser atualizada")

        values.append(id)
        cursor.execute(
            f"""
                UPDATE clients 
                SET {', '.join(fields)} 
                WHERE id = ?
            """,
            tuple(values)
        )

        connection.commit()

        if cursor.rowcount == 0:
            raise ClientNotFoundError("Cliente não encontrado")
        print(f"Atualização feita com sucesso")

    except (NoFieldsToBeUpdatedError, ClientNotFoundError):
        raise

    except sqlite3.IntegrityError:
        print(f"Erro: Não foi possível atualizar a conta por uma violação de integridade")
        raise DatabaseError("Erro interno ao atualizar conta")

    except sqlite3.Error as e:
        print(f"Erro no db atualizar a conta: {e}")
        raise DatabaseError("Erro interno ao atualizar conta")

    except Exception as e:
        print(f"Erro ao atualizar cliente: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

def get_client_data_by_id(id):
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        cursor.execute(
            """
                SELECT id, name, cpf, rfid, balance
                FROM clients
                WHERE id = ?
            """,
            (id,),
        )

        client_data = cursor.fetchone()

        if not client_data:
            raise ClientNotFoundError("Cliente não encontrado")
        return client_data

    except (ClientNotFoundError):
        raise

    except sqlite3.Error as e:
        print(f"Erro no db atualizar a conta: {e}")
        raise DatabaseError("Erro interno ao atualizar conta")

    except Exception as e:
        print(f"Erro ao atualizar cliente: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

def withdraw_by_id(id, withdraw_amount):
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        cursor.execute(
            """
                SELECT balance
                FROM clients
                WHERE id = ?
            """,
            (id,),
        )

        row = cursor.fetchone()
        if not row:
            raise ClientNotFoundError("Cliente não encontrado")

        current_balance = row[0]
        if current_balance < withdraw_amount:
            raise InsufficientBalanceError("Saldo insuficiente para realizar o saque")

        new_balance = current_balance - withdraw_amount

        cursor.execute(
            """
                UPDATE clients 
                SET balance = ?
                WHERE id = ?
            """,
            (new_balance, id),
        )

        connection.commit()
        print(f"Saque realizado com sucesso")

    except (InsufficientBalanceError, ClientNotFoundError):
        raise

    except sqlite3.Error as e:
        print(f"Erro no db ao realizar o saque: {e}")
        raise DatabaseError("Erro interno ao realizar saque")

    except Exception as e:
        print(f"Erro ao realizar saque: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

def deposit_by_id(id, deposit_amount):
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        cursor.execute(
            """
                SELECT balance
                FROM clients
                WHERE id = ?
            """,
            (id,),
        )

        row = cursor.fetchone()
        if not row:
            raise ClientNotFoundError("Cliente não encontrado")

        current_balance = row[0]
        new_balance = current_balance + deposit_amount

        cursor.execute(
            """
                UPDATE clients 
                SET balance = ?
                WHERE id = ?
            """,
            (new_balance, id),
        )

        connection.commit()
        print(f"Depósito realizado com sucesso")

    except (ClientNotFoundError):
        raise

    except sqlite3.Error as e:
        print(f"Erro no db ao realizar o depósito: {e}")
        raise DatabaseError("Erro interno ao realizar depósito")

    except Exception as e:
        print(f"Erro inesperado ao realizar depósito: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

def search_client_by_rfid(rfid):
    try: 
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        cursor.execute(
            """
                SELECT id, name, cpf, password, balance 
                FROM clients 
                WHERE rfid = ?
            """,
            (rfid,),
        )

        client = cursor.fetchone()

        if not client:
            raise ClientNotFoundError("Cliente não encontrado")
        return client

    except (ClientNotFoundError):
            raise

    except sqlite3.Error as e:
        print(f"Erro no db ao procurar cliente: {e}")
        raise DatabaseError("Erro interno ao procurar cliente")
    
    except Exception as e:
        print(f"Erro ao procurar cliente: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

def delete_account_by_id(id):
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        cursor.execute(
            """
                DELETE FROM clients
                WHERE id = ?
            """,
            (id,),
        )

        connection.commit()

        if cursor.rowcount == 0:
            raise ClientNotFoundError("Cliente não encontrado")
        print(f"Conta excluída com sucesso")

    except (NoFieldsToBeUpdatedError, ClientNotFoundError):
        raise

    except sqlite3.Error as e:
        print(f"Erro no db ao excluir a conta: {e}")
        raise DatabaseError("Erro interno ao deletar conta")

    except Exception as e:
        print(f"Erro ao excluir conta: {e}")
        raise DatabaseError("Ocorreu um erro inesperado no sistema")

    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    initialize_database()
