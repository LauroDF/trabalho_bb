from pathlib import Path
from functools import wraps
import sqlite3
import csv
import sqlite3


from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    session,
)

from trabalho_bb.database.database import (
    add_user,
    delete_user_by_rfid,
    list_all_users,
    search_user_by_rfid,
    update_user_data,
)

app = Flask(__name__)
app.json.ensure_ascii = False

USUARIO_ADMIN = "admin"
SENHA_ADMIN = "admin"

app.secret_key = "chave-de-desenvolvimento-trocar-depois"

CSV_PATH = Path(__file__).with_name("logs_acesso.csv")

DB_PATH = (
    Path.home()
    / "OneDrive"
    / "Área de Trabalho"
    / "trabalho_sistema"
    / "acess_control.db"
)


def login_obrigatorio(funcao):
    @wraps(funcao)
    def wrapper(*args, **kwargs):
        if not session.get("autenticado"):
            return jsonify({
                "erro": "Faça login para acessar o sistema."
            }), 401

        return funcao(*args, **kwargs)

    return wrapper

def conectar():
    # Garante que a URI use o formato correto para o SQLite
    uri = DB_PATH.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "banco_existe": DB_PATH.is_file(),
        }
    )


@app.get("/api/schema")
def schema():
    if not DB_PATH.is_file():
        return jsonify({"erro": "Banco não encontrado"}), 404

    try:
        with conectar() as conn:
            tabelas = conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """).fetchall()

            resultado = {}

            for (tabela,) in tabelas:
                colunas = conn.execute(f'PRAGMA table_info("{tabela}")').fetchall()

                resultado[tabela] = [
                    {
                        "nome": coluna[1],
                        "tipo": coluna[2],
                    }
                    for coluna in colunas
                ]

        return jsonify(resultado)

    except sqlite3.Error:
        app.logger.exception("Erro ao consultar o banco")
        return jsonify({"erro": "Falha ao consultar o banco"}), 500


@app.get("/api/pessoas")
def listar_pessoas():
    if not DB_PATH.is_file():
        return jsonify({"erro": "Banco não encontrado"}), 404

    try:
        with conectar() as conn:
            conn.row_factory = sqlite3.Row
            pessoas = conn.execute("""
                SELECT id, nome, rfid, cargo, acesso_sala, status
                FROM pessoas
            """).fetchall()

        return jsonify([dict(pessoa) for pessoa in pessoas])

    except sqlite3.Error:
        app.logger.exception("Erro ao consultar pessoas")
        return jsonify({"erro": "Falha ao consultar pessoas"}), 500


@app.post("/api/logs")
def receber_log():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({"erro": "JSON inválido"}), 400

    campos = [
        "data_hora",
        "tag_uid",
        "nome",
        "evento",
        "resultado",
        "mensagem",
    ]

    if any(campo not in dados for campo in campos):
        return jsonify({"erro": "Campos obrigatórios ausentes"}), 400

    try:
        # Garante que a pasta do arquivo CSV existe antes de tentar abrir
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

        arquivo_novo = not CSV_PATH.exists()

        with CSV_PATH.open("a", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.DictWriter(
                arquivo,
                fieldnames=campos,
                extrasaction="ignore",
            )

            if arquivo_novo or CSV_PATH.stat().st_size == 0:
                escritor.writeheader()

            escritor.writerow({campo: dados[campo] for campo in campos})

        return jsonify({"status": "ok", "salvo": True}), 201

    except OSError:
        app.logger.exception("Erro ao salvar log CSV")
        return jsonify({"erro": "Falha ao salvar CSV"}), 500


@app.route("/")
def index():
    pasta_web = Path(__file__).resolve().parents[1] / "web"
    return send_from_directory(pasta_web, "index.html")


@app.route("/api/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "erro": "Envie usuário e senha em formato JSON."
        }), 400

    usuario = dados.get("usuario")
    senha = dados.get("senha")

    if usuario != USUARIO_ADMIN or senha != SENHA_ADMIN:
        return jsonify({
            "erro": "Usuário ou senha incorretos."
        }), 401

    session.clear()
    session["autenticado"] = True
    session["usuario"] = USUARIO_ADMIN

    return jsonify({
        "mensagem": "Login realizado com sucesso.",
        "usuario": USUARIO_ADMIN,
    }), 200


@app.route("/api/session", methods=["GET"])
def verificar_sessao():
    if session.get("autenticado"):
        return jsonify({
            "autenticado": True,
            "usuario": session.get("usuario"),
        }), 200

    return jsonify({
        "autenticado": False
    }), 200


@app.route("/api/logs", methods=["GET"])
@login_obrigatorio
def consultar_logs():
    caminho_csv = Path(__file__).resolve().parents[1] / "logs_acesso.csv"

    if not caminho_csv.is_file():
        return jsonify({
            "erro": "Arquivo de logs não encontrado.",
            "caminho": str(caminho_csv)
        }), 404

    try:
        with caminho_csv.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as arquivo:
            leitor = csv.DictReader(arquivo)

            colunas = {
                "data_hora",
                "tag_uid",
                "nome",
                "evento",
                "resultado",
                "mensagem"
            }

            if not colunas.issubset(set(leitor.fieldnames or [])):
                return jsonify({
                    "erro": "O CSV não possui as colunas esperadas.",
                    "colunas_encontradas": leitor.fieldnames or []
                }), 400

            logs = list(leitor)

        logs.reverse()

        resposta = jsonify(logs)
        resposta.headers["Cache-Control"] = "no-store"
        return resposta, 200

    except (OSError, UnicodeError, csv.Error):
        return jsonify({
            "erro": "Não foi possível ler o arquivo de logs."
        }), 500


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "mensagem": "Sessão encerrada com sucesso."
    }), 200


@app.route("/api/users", methods=["GET"])
@login_obrigatorio
def list_user():
    pessoas = list_all_users()

    resultado = []

    for user in pessoas:
        resultado.append({
            "id": user[0],
            "nome": user[1],
            "rfid": user[2],
            "cargo": user[3],
            "acesso_sala": user[4],
            "status": user[5],
        })

    return jsonify(resultado)


@app.route("/api/users", methods=["POST"])
@login_obrigatorio
def create_user():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "erro": "Envie os dados em formato JSON."
        }), 400

    campos = ["nome", "rfid", "cargo", "acesso_sala"]

    if any(
        not isinstance(dados.get(campo), str)
        or not dados[campo].strip()
        for campo in campos
    ):
        return jsonify({
            "erro": "Informe nome, RFID, cargo e acesso à sala."
        }), 400

    nome = dados["nome"].strip()
    rfid = dados["rfid"].strip()
    cargo = dados["cargo"].strip()
    acesso_sala = dados["acesso_sala"].strip().lower()
    status = dados.get("status", "ativo")

    if acesso_sala not in ("sim", "nao"):
        return jsonify({
            "erro": "O acesso à sala deve ser 'sim' ou 'nao'."
        }), 400

    if not isinstance(status, str) or status not in ("ativo", "inativo"):
        return jsonify({
            "erro": "O status deve ser 'ativo' ou 'inativo'."
        }), 400

    if add_user(nome, rfid, cargo, acesso_sala, status):
        return jsonify({
            "mensagem": "Colaborador cadastrado com sucesso."
        }), 201

    return jsonify({
        "erro": "Não foi possível cadastrar. Verifique se o RFID já existe."
    }), 409


@app.route("/api/users/rfid/<rfid>", methods=["GET"])
@login_obrigatorio
def get_user_by_rfid(rfid):
    pessoa = search_user_by_rfid(rfid)

    if pessoa is None:
        return jsonify({
            "erro": "Colaborador não encontrado."
        }), 404

    return jsonify({
        "nome": pessoa[0],
        "cargo": pessoa[1],
        "acesso_sala": pessoa[2],
        "status": pessoa[3],
        "rfid": rfid,
    })


@app.route("/api/users/rfid/<rfid>", methods=["DELETE"])
@login_obrigatorio
def remove_user(rfid):
    pessoa = search_user_by_rfid(rfid)

    if pessoa is None:
        return jsonify({
            "erro": "Colaborador não encontrado."
        }), 404

    delete_user_by_rfid(rfid)

    return jsonify({
        "mensagem": "Colaborador excluído com sucesso."
    })


@app.route("/api/users/<id>", methods=["PUT"])
@login_obrigatorio
def update_user(id):
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "erro": "Envie os dados em formato JSON."
        }), 400

    campos_permitidos = {
        "nome": "novo_nome",
        "cargo": "novo_cargo",
        "status": "novo_status",
        "rfid": "novo_rfid",
    }

    if not any(campo in dados for campo in campos_permitidos):
        return jsonify({
            "erro": "Informe pelo menos um campo para atualizar."
        }), 400

    for campo in campos_permitidos:
        if campo in dados:
            if (
                not isinstance(dados[campo], str)
                or not dados[campo].strip()
            ):
                return jsonify({
                    "erro": f"O campo '{campo}' não pode ficar vazio."
                }), 400

            dados[campo] = dados[campo].strip()

    if "status" in dados and dados["status"] not in ("ativo", "inativo"):
        return jsonify({
            "erro": "O status deve ser 'ativo' ou 'inativo'."
        }), 400

    connection = sqlite3.connect("acess_control.db")

    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id FROM pessoas WHERE id = ?",
            (id,),
        )
        pessoa = cursor.fetchone()
    finally:
        connection.close()

    if pessoa is None:
        return jsonify({
            "erro": "Colaborador não encontrado."
        }), 404

    sucesso = update_user_data(
        id,
        novo_nome=dados.get("nome"),
        novo_cargo=dados.get("cargo"),
        novo_status=dados.get("status"),
        novo_rfid=dados.get("rfid"),
    )

    if not sucesso:
        return jsonify({
            "erro": (
                "Não foi possível atualizar. "
                "Verifique se o RFID já está cadastrado."
            )
        }), 409

    return jsonify({
        "mensagem": "Colaborador atualizado com sucesso."
    }), 200


def run():
    app.run(debug=True, use_reloader=False)


if __name__ == "__main__":
    run()