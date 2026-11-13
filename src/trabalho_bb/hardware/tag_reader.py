from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
import time
import threading
from trabalho_bb.exceptions.exceptions import RfidTimeoutError

PIN_RED = 15
PIN_GREEN = 11
PIN_BLUE = 29
PIN_BUZZER = 12

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_RED, GPIO.OUT)
GPIO.setup(PIN_GREEN, GPIO.OUT)
GPIO.setup(PIN_BLUE, GPIO.OUT)
GPIO.setup(PIN_BUZZER, GPIO.OUT)

def light_led_and_buzzer():
    GPIO.output(PIN_RED, GPIO.LOW)
    GPIO.output(PIN_GREEN, GPIO.LOW)
    GPIO.output(PIN_BLUE, GPIO.HIGH)
    GPIO.output(PIN_BUZZER, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(PIN_BUZZER, GPIO.LOW)
    GPIO.output(PIN_RED, GPIO.LOW)
    GPIO.output(PIN_GREEN, GPIO.LOW)
    GPIO.output(PIN_BLUE, GPIO.LOW)

def read_card(timeout=15):
    try:
        rfid_reader = SimpleMFRC522()
        start_time = time.time()

        while True:
            current_time = time.time()
            passed_time = current_time - start_time
    
            if passed_time > timeout:
                raise RfidTimeoutError("Tempo para ler cartão expirado")

            (status, TagType) = rfid_reader.READER.MFRC522_Request(rfid_reader.READER.PICC_REQIDL)

            if status == rfid_reader.READER.MI_OK:
                tag, text = rfid_reader.read()
                rfid = str(tag).strip()

                new_thread = threading.Thread(target=light_led_and_buzzer)
                new_thread.start()

                return {
                    "rfid": rfid
                }

            time.sleep(0.1)

    except (RfidTimeoutError):
        raise

    except Exception as e:
        raise
    