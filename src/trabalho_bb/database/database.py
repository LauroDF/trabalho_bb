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
            balance REAL
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

def auth_client(rfid_input, password_input):
  try:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
            SELECT id, name, password
            FROM clients 
            WHERE rfid = ?
        """,
        (rfid_input,),
    )

    user = cursor.fetchone()
    connection.close()

    if not user:
      return {
          "Usuário não identificado",
      }

    name, password = user

    if password_input == password:
        print(f"Bem-vindo(a) {name}")
        return True
    else:
       print("Senha incorreta")
       return False

  except Exception as e:
    print(f"Falha ao tentar autenticar o cliente: {e}")
    return False
  
def add_user(nome, rfid, cargo, acesso_sala, status="ativo"):
  try:
    connection = sqlite3.connect("acess_control.db")
    cursor = connection.cursor()

    new_id = str(uuid.uuid4())

    cursor.execute(
        """
            INSERT INTO pessoas (id, nome, rfid, cargo, acesso_sala, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
        (new_id, nome, rfid, cargo, acesso_sala, status),
    )

    connection.commit()
    connection.close()
    print(f"Sucesso: '{nome}' foi cadastrado(a) com o RFID {rfid}.")
    return True

  except sqlite3.IntegrityError:
    print(f"Erro: O cartão RFID '{rfid}' já pertence a outra pessoa cadastrada.")
    return False

def list_all_users():
    connection = sqlite3.connect("acess_control.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id, nome, rfid, cargo, acesso_sala, status FROM pessoas"
    )
    users = cursor.fetchall()

    connection.close()
    return users

def search_user_by_rfid(rfid):
    connection = sqlite3.connect("clients.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT nome, cargo, acesso_sala, status 
        FROM pessoas 
        WHERE rfid = ?
    """,
        (rfid,),
    )

    user = cursor.fetchone()
    connection.close()
    return user

def update_user_data(id, novo_nome=None, novo_cargo=None, novo_status=None, novo_rfid=None):
  try:
    connection = sqlite3.connect("acess_control.db")
    cursor = connection.cursor()

    campos = []
    valores = []

    if novo_nome is not None:
      campos.append("nome = ?")
      valores.append(novo_nome)

    if novo_cargo is not None:
      campos.append("cargo = ?")
      valores.append(novo_cargo)

    if novo_status is not None:
      campos.append("status = ?")
      valores.append(novo_status)

    if novo_rfid is not None:
      campos.append("rfid = ?")
      valores.append(novo_rfid)

    if not campos:
      print("Nenhum dado foi fornecido para atualização.")
      connection.close()
      return False

    valores.append(id)
    sql = f"UPDATE pessoas SET {', '.join(campos)} WHERE id = ?"

    cursor.execute(sql, tuple(valores))
    connection.commit()
    connection.close()
    return True

  except Exception as e:
    print(f"Erro ao atualizar colaborador: {e}")
    return False

def delete_user_by_rfid(rfid):
    connection = sqlite3.connect("acess_control.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM pessoas
        WHERE rfid = ?
    """,
        (rfid,),
    )

    connection.commit()
    connection.close()
    print(f"Pessoa com RFID {rfid} foi removida do sistema.")

if __name__ == "__main__":
    initialize_database()
