import math
import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

import requests

from .api_remota import (
    buscar_pessoa_por_tag,
    pessoa_tem_acesso,
    enviar_log_remoto,
)

from datetime import datetime

from .database import (
    buscar_colaborador_por_tag,
    inicializar_banco,
    registrar_evento,
)

# Pinos BCM do Raspberry Pi
LED_VERMELHO = 17
LED_VERDE = 27
LED_AZUL = 23  # Pino físico 16; alterado para evitar conflito com o RFID
BUZZER = 18

GPIO.setmode(GPIO.BCM)

GPIO.setup(LED_VERMELHO, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LED_VERDE, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LED_AZUL, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(BUZZER, GPIO.OUT, initial=GPIO.LOW)

# PWM permite variar o brilho do LED
pwm_vermelho = GPIO.PWM(LED_VERMELHO, 100)
pwm_verde = GPIO.PWM(LED_VERDE, 100)
pwm_azul = GPIO.PWM(LED_AZUL, 100)

pwm_vermelho.start(0)
pwm_verde.start(0)
pwm_azul.start(0)


def definir_led(vermelho=0, verde=0, azul=0):
    pwm_vermelho.ChangeDutyCycle(vermelho)
    pwm_verde.ChangeDutyCycle(verde)
    pwm_azul.ChangeDutyCycle(azul)


def desligar_led():
    definir_led(0, 0, 0)


def bip(duracao=0.15):
    GPIO.output(BUZZER, GPIO.HIGH)
    time.sleep(duracao)
    GPIO.output(BUZZER, GPIO.LOW)


def sinal_autorizado():
    definir_led(0, 100, 0)
    bip(0.15)
    time.sleep(1.85)
    desligar_led()


def sinal_sem_acesso():
    definir_led(100, 20, 0)
    bip(0.15)
    time.sleep(0.2)
    bip(0.15)
    time.sleep(1.5)
    desligar_led()


def sinal_invasao():
    inicio = time.monotonic()
    proximo_bip = inicio

    while time.monotonic() - inicio < 5:
        tempo = time.monotonic() - inicio

        # Varia o brilho do vermelho suavemente, de 0 a 100%.
        brilho = 50 * (1 + math.sin(2 * math.pi * tempo * 1.2))
        definir_led(vermelho=brilho)

        # Bips rápidos durante o alerta.
        agora = time.monotonic()
        if agora >= proximo_bip:
            GPIO.output(BUZZER, GPIO.HIGH)
            time.sleep(0.07)
            GPIO.output(BUZZER, GPIO.LOW)
            proximo_bip = time.monotonic() + 0.13

        time.sleep(0.02)

    desligar_led()
    GPIO.output(BUZZER, GPIO.LOW)


# Tags identificadas como invasoras para testes.
# Elas não são cadastradas como colaboradores no banco.
TAGS_INVASORAS = {
    "426096719348": "Invasor Sombra",
    "427389875583": "Invasor Fantasma",
    "358803442058": "Invasor Espectro",
}


# Estado temporário da sessão
DENTRO_DA_SALA = set()
ENTRADAS_HOJE = {}


def processar_tag(tag):
    tag_uid = str(tag).strip()
    funcionario = buscar_colaborador_por_tag(tag_uid)

    print("\n" + "=" * 40)

    # Tags suspeitas reservadas para testes.
    if tag_uid in TAGS_INVASORAS:
        print("ALERTA: TAG SUSPEITA (TESTE)!")
        print(f"ID da tag: {tag_uid}")
        print("Acesso negado.")
        sinal_invasao()

        registrar_evento(tag_uid, None, "TENTATIVA_INVASAO", "NEGADO")

        enviado = enviar_log_remoto(
            tag_uid,
            "Tag suspeita (teste)",
            "TENTATIVA_INVASAO",
            "NEGADO",
            "Tag identificada como suspeita durante teste.",
        )

        print("Log remoto enviado." if enviado else "Falha ao enviar log remoto.")
        return

    # Consulta a API do PC da Gabi.
    try:
        pessoa = buscar_pessoa_por_tag(tag_uid)

    except (requests.RequestException, ValueError) as erro:
        print("ACESSO NEGADO: não foi possível consultar o servidor.")
        print(f"Motivo: {erro}")
        sinal_sem_acesso()

        # O sistema permanece fechado se a API estiver indisponível.
        registrar_evento(
            tag_uid,
            funcionario["id"] if funcionario else None,
            "ACESSO_NEGADO",
            "NEGADO",
        )

        enviar_log_remoto(
            tag_uid,
            "Pessoa não identificada",
            "TENTATIVA_INVASAO",
            "NEGADO",
            "Tag não encontrada no cadastro remoto.",
        )

        return

    # A tag não existe no cadastro remoto.
    if pessoa is None:
        print("ALERTA: TAG DESCONHECIDA!")
        print(f"ID da tag: {tag_uid}")
        print("Acesso negado.")
        sinal_invasao()

        registrar_evento(tag_uid, None, "TENTATIVA_INVASAO", "NEGADO")

        enviar_log_remoto(
            tag_uid,
            "Pessoa não identificada",
            "TENTATIVA_INVASAO",
            "NEGADO",
            "Tag não encontrada no cadastro remoto.",
        )

        return

    nome = pessoa.get("nome", "Pessoa não identificada")

    # O banco remoto é a fonte da autorização.

    if not pessoa_tem_acesso(pessoa):
        print(f"Pessoa: {nome}")

        if str(pessoa.get("status", "")).strip().lower() != "ativo":
            mensagem = "Acesso negado: cadastro inativo."
        else:
            mensagem = "Acesso negado: sem permissão para a sala."

        print(mensagem)
        sinal_sem_acesso()

        registrar_evento(
            tag_uid,
            funcionario["id"] if funcionario else None,
            "ACESSO_NEGADO",
            "NEGADO",
        )

        enviado = enviar_log_remoto(
            tag_uid,
            nome,
            "ACESSO_NEGADO",
            "NEGADO",
            mensagem,
        )

        print("Log remoto enviado." if enviado else "Falha ao enviar log remoto.")
        return

    # Pessoa ativa e autorizada pelo banco remoto.
    hoje = datetime.now().astimezone().date()
    primeiro_acesso = ENTRADAS_HOJE.get(tag_uid) != hoje

    if tag_uid not in DENTRO_DA_SALA:
        DENTRO_DA_SALA.add(tag_uid)
        ENTRADAS_HOJE[tag_uid] = hoje

        if primeiro_acesso:
            print(f"Bem-vindo, {nome}!")
        else:
            print(f"Bem-vindo de volta, {nome}!")

        print("Acesso autorizado.")
        sinal_autorizado()

        registrar_evento(
            tag_uid,
            funcionario["id"] if funcionario else None,
            "ENTRADA",
            "AUTORIZADO",
        )

        enviar_log_remoto(
            tag_uid,
            nome,
            "ENTRADA",
            "AUTORIZADO",
            f"Acesso autorizado para {nome}.",
        )

    else:
        DENTRO_DA_SALA.remove(tag_uid)

        print(f"Até logo, {nome}!")
        print("Saída registrada.")
        sinal_autorizado()

        registrar_evento(
            tag_uid,
            funcionario["id"] if funcionario else None,
            "SAIDA",
            "AUTORIZADO",
        )

        enviar_log_remoto(
            tag_uid,
            nome,
            "SAIDA",
            "AUTORIZADO",
            f"Saída registrada para {nome}.",
        )


def main():
    inicializar_banco()
    print("Banco SQLite inicializado.")
    leitor_rfid = SimpleMFRC522()

    print("Sistema de controle de acesso iniciado.")
    print("Aproxime um cartão ou tag RFID.")
    print("Pressione Ctrl+C para encerrar.")

    try:
        while True:
            tag, texto = leitor_rfid.read()
            processar_tag(tag)
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nEncerrando o sistema...")

    finally:
        desligar_led()

        pwm_vermelho.stop()
        pwm_verde.stop()
        pwm_azul.stop()

        GPIO.output(BUZZER, GPIO.LOW)
        GPIO.cleanup()

        print("GPIOs liberados.")

def run():
    main()