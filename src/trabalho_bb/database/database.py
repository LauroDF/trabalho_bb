import sqlite3
import uuid
from pathlib import Path

def initialize_database():
    connection = sqlite3.connect("../../../data/clients.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cpf TEXT UNIQUE NOT NULL CHECK(length(cpf) == 11),
            password TEXT NOT NULL CHECK(length(password) >= 8)
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
                "admin1234567,"
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
        print("Banco de dados criado e dados inseridos")
    else:
        print("Banco de dados já foi inicializado")

    connection.close()

# def auth_by_rfid(rfid):
#   try:
#     connection = sqlite3.connect("acess_control.db")
#     cursor = connection.cursor()

#     cursor.execute(
#         """
#             SELECT nome, cargo, acesso_sala, status 
#             FROM pessoas 
#             WHERE rfid = ?
#         """,
#         (rfid,),
#     )

#     user = cursor.fetchone()
#     connection.close()

#     if not user:
#       return {
#           "autorizado": False,
#           "mensagem": "Código RFID inválido ou não cadastrado.",
#       }

#     nome, cargo, acesso_sala, status = user

#     if status != "ativo":
#       return {
#           "autorizado": False,
#           "mensagem": f"Acesso negado: {nome}, seu cadastro está inativo.",
#       }

#     if acesso_sala != "sim":
#       return {
#           "autorizado": False,
#           "mensagem": (
#               f"Acesso negado: {nome}, você não tem permissão para entrar na"
#               " sala."
#           ),
#       }

#     return {
#         "autorizado": True,
#         "mensagem": f"Acesso liberado! Bem-vindo(a), {nome} ({cargo}).",
#     }

#   except Exception as e:
#     print(f"Erro ao autenticar: {e}")
#     return {"autorizado": False, "mensagem": "Erro interno no sistema."}

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
