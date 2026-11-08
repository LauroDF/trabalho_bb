
import requests

API_URL = "http://10.1.25.56:5000/api/pessoas"
TIMEOUT = 3

from datetime import datetime


API_LOGS_URL = "http://10.1.25.56:5000/api/logs"

def buscar_pessoa_por_tag(uid: str) -> dict | None:
    resposta = requests.get(API_URL, timeout=TIMEOUT)
    resposta.raise_for_status()

    pessoas = resposta.json()

    for pessoa in pessoas:
        if str(pessoa.get("rfid", "")).strip() == str(uid).strip():
            return pessoa

    return None


def pessoa_tem_acesso(pessoa: dict) -> bool:
    status = str(pessoa.get("status", "")).strip().lower()
    acesso = str(pessoa.get("acesso_sala", "")).strip().lower()

    return status == "ativo" and acesso == "sim"


def enviar_log_remoto(
    tag_uid: str,
    nome: str,
    evento: str,
    resultado: str,
    mensagem: str,
) -> bool:
    dados = {
        "data_hora": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "tag_uid": str(tag_uid),
        "nome": nome,
        "evento": evento,
        "resultado": resultado,
        "mensagem": mensagem,
    }

    try:
        resposta = requests.post(
            API_LOGS_URL,
            json=dados,
            timeout=3,
        )
        resposta.raise_for_status()
        return True

    except requests.RequestException as erro:
        print(f"Aviso: não foi possível enviar o log remoto: {erro}")
        return False
