from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
import time
import threading
from trabalho_bb.exceptions.exceptions import RfidTimeoutError

# PIN_RED = 15
# PIN_GREEN = 11
# PIN_BLUE = 13
# PIN_BUZZER = 12

GPIO.setmode(GPIO.BCM)
# GPIO.setup(PIN_RED, GPIO.OUT)
# GPIO.setup(PIN_GREEN, GPIO.OUT)
# GPIO.setup(PIN_BLUE, GPIO.OUT)
# GPIO.setup(PIN_BUZZER, GPIO.OUT)
GPIO.cleanup()

GPIO.setmode(GPIO.BCM)
# GPIO.setup(PIN_RED, GPIO.OUT)
# GPIO.setup(PIN_GREEN, GPIO.OUT)
# GPIO.setup(PIN_BLUE, GPIO.OUT)
# GPIO.setup(PIN_BUZZER, GPIO.OUT)

def light_led_and_buzzer():
    # GPIO.output(PIN_RED, GPIO.LOW)
    # GPIO.output(PIN_GREEN, GPIO.LOW)
    # GPIO.output(PIN_BLUE, GPIO.HIGH)
    # GPIO.output(PIN_BUZZER, GPIO.HIGH)
    time.sleep(1)
    # GPIO.output(PIN_BUZZER, GPIO.LOW)
    # GPIO.output(PIN_RED, GPIO.LOW)
    # GPIO.output(PIN_GREEN, GPIO.LOW)
    # GPIO.output(PIN_BLUE, GPIO.LOW)

def read_card(timeout=15):
    try:
        rfid_reader = SimpleMFRC522()
        start_time = time.time()

        while True:
            current_time = time.time()
            passed_time = current_time - start_time
    
            if passed_time > timeout:
                raise RfidTimeoutError("Tempo para ler cartão expirado")

            # Utiliza o método nativo do SimpleMFRC522 para leitura não-bloqueante
            id, text = rfid_reader.read_no_block()

            if id is not None:
                rfid = str(id).strip()

                # Dispara o LED e o buzzer em uma thread separada
                new_thread = threading.Thread(target=light_led_and_buzzer)
                new_thread.start()

                return {
                    "rfid": rfid
                }

            time.sleep(0.1)

            
    except (RfidTimeoutError):
        raise

    except Exception as e:
        print(e)
        raise e