#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
import smbus2
import pcf8574

bus = smbus2.SMBus(1)

# Pin names

START_AZ = "p0"
STOP_AZ = "p1"
ROTATE_CCW = "p2"
RUN_EL = "p3"
EL_UP = "p4"

AZ_IND_A = 1
AZ_IND_B = 2
EL_PULSE = "p2"

AZ_INT = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(AZ_INT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

azz2inc = {0b0000: 0,
           0b0001: 1,
           0b0010: -1,
           0b0101: 0,
           0b0111: 1,
           0b0100: -1,
           0b1111: 0,
           0b1110: 1,
           0b1101: -1,
           0b1010: 0,
           0b1000: 1,
           0b1011: -1
           }

last_az = 0
az = 0

def gpio_az_interrupt(channel):
    global az
    global last_az

    current_az = p1.byte_read(AZ_IND_A | AZ_IND_B)
    try:
        inc = azz2inc[last_az << 2 | current_az]
    except KeyError:
        print("Key error: index=%s" % bin(last_az << 2 | current_az))
        return
    az += inc
    last_az = current_az

    if inc != 0:
        pulse_az_enable()
    print(az)

def pulse_az_enable():
    p0.bit_write(START_AZ, "HIGH")
    p0.bit_write(START_AZ, "LOW")

GPIO.add_event_detect(AZ_INT, GPIO.FALLING, callback=gpio_az_interrupt)

p0 = pcf8574.PCF(0x20)
p1 = pcf8574.PCF(0x21)

p0.pin_mode("p0", "OUTPUT")
p0.pin_mode("p1", "OUTPUT")
p0.pin_mode("p2", "OUTPUT")

p1.pin_mode("p0", "INPUT")
p1.pin_mode("p1", "INPUT")

print("Az=%d" % az)


while (1):
    p0.bit_write("p0", pcf8574.LOW)  # Start CW
    p0.bit_write("p2", pcf8574.HIGH)  # Start CCW
    print("Rotate CW")
    p0.bit_write("p1", pcf8574.HIGH)  # Don't stop me now
    print("Start")
    time.sleep(5)
    print("Az=%d" % az)
GPIO.cleanup()  # clean up GPIO on normal exit
