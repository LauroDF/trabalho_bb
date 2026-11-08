from RPLCD.i2c import CharLCD
import time

lcd = CharLCD(
    i2c_expander="PCF8574",
    address=0x27,
    port=1,
    cols=16,
    rows=2,
    charmap="A00",
    auto_linebreaks=False,
)

try:
    lcd.clear()
    lcd.write_string("Controle RFID")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("LCD funcionando")
    time.sleep(5)
finally:
    lcd.clear()
    lcd.close()