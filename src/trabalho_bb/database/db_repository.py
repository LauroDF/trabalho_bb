import sqlite3
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_DIR = ROOT_DIR / "data"
DB_PATH = DB_DIR / "clients.db"

def initialize_database():
    DB_DIR.mkdir(parents=True, exist_ok=True)

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
                "3443dre3t4t",
                "962185903074",
                578,
            ),
            (
                str(uuid.uuid4()),
                "Carlo Edoardo",
                "52998224059",
                "43gds5yge",
                "701044494601",
                2345,
            ),
            (
                str(uuid.uuid4()),
                "Miguel Alencar",
                "12345678908",
                "miguel123456",
                "632092037175",
                21,
            ),
            (
                str(uuid.uuid4()),
                "Sophia Bonita",
                "45678901206",
                "admin1234567",
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

    connection.close()

def auth_client(rfid, password_input):
    try:
        client = search_client_by_rfid(rfid)

        if client == "Usuário não identificado":
           return "Usuário não identificado"

        id, name, cpf, password, balance = client

        if password_input == password:
            print(f"Bem-vindo(a) {name}")
            return True
        else:
            print("Senha incorreta")
            return False

    except sqlite3.Error as e:
        print(f"Erro no db ao autenticar cliente: {e}")
        return False

    except Exception as e:
        print(f"Erro ao autenticar cliente: {e}")
        return False
  
def create_account(name, cpf, password, rfid):
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        new_id = str(uuid.uuid4())

        cursor.execute(
            """
                INSERT INTO pessoas (id, name, cpf, password, rfid)
                VALUES (?, ?, ?, ?, ?)
            """,
            (new_id, name, cpf, password, rfid),
        )

        connection.commit()
        print(f"Sucesso: '{name}' foi cadastrado(a) com o RFID {rfid}")
        return True

    except sqlite3.IntegrityError:
        print(f"Erro: RFID ou cpf já pertence a outro cliente cadastrado")
        return False

    except sqlite3.Error as e:
        print(f"Erro no db ao criar a conta: {e}")
        return False
    
    except Exception as e:
        print(f"Erro ao criar a conta: {e}")
        return False

    finally:
        if connection:
            connection.close()

def list_all_clients():
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        cursor.execute(
            """
                SELECT id, name, cpf, rfid, balance
                FROM clients
            """
        )
        clients = cursor.fetchall()
        return clients

    except sqlite3.Error as e:
        print(f"Erro no db ao listar clientes: {e}")
        return False

    except Exception as e:
        print(f"Erro ao listar clientes: {e}")
        return False

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
            return "Usuário não identificado"
        return client

    except sqlite3.Error as e:
        print(f"Erro no db ao procurar cliente: {e}")
        return False
    
    except Exception as e:
        print(f"Erro ao procurar cliente: {e}")
        return False

    finally:
        if connection:
            connection.close()

def update_client_data(id, new_name=None, new_cpf=None, new_password=None, new_rfid=None):
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
            return False

        values.append(id)
        sql = f"UPDATE clients SET {', '.join(fields)} WHERE id = ?"

        cursor.execute(sql, tuple(values))
        connection.commit()
        return True

    except sqlite3.IntegrityError:
        print(f"Erro: RFID ou cpf já pertence a outro cliente cadastrado")
        return False

    except sqlite3.Error as e:
        print(f"Erro no db atualizar a conta: {e}")
        return False

    except Exception as e:
        print(f"Erro ao atualizar cliente: {e}")
        return False

    finally:
        if connection:
            connection.close()

def delete_user_by_id(id):
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
        print(f"Conta excluída com sucesso")

    except sqlite3.Error as e:
        print(f"Erro no db ao excluir a conta: {e}")
        return False

    except Exception as e:
        print(f"Erro ao deletar cliente: {e}")
        return False

    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    initialize_database()
