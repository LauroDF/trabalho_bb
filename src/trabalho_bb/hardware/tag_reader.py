from mfrc522 import SimpleMFRC522

def read_card():

    leitor_rfid = SimpleMFRC522()
    tag, texto = leitor_rfid.read()

    formated_tag = str(tag).strip()

    print(f"\nCartão identificado!")
    print(f"RFID: {formated_tag}")

    return formated_tag