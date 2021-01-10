#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
import smbus2
import pcf8574

import sqlite3

db = sqlite3.connect("/home/pi/SM6FBQ/azel.db")

db.execute("CREATE TABLE IF NOT EXISTS azel_current (id INTEGER PRIMARY KEY AUTOINCREMENT, az int, el int)")


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

AZ_CCW_MECH_STOP: int = 0
AZ_CW_MECH_STOP: int = 734

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

last_sense = 0xff
az_target=None
az = 0
inc = 0

def el_interrupt(channel, last, current):
    pass

def stop_interrupt(channel, last, current):
    global az
    global inc

    if not p0.bit_read(STOP_AZ):
        return
    # We ran into the mech stop
    if inc == 0:
        print("Mech stop. Unknown dir")
        az_cw()
        time.sleep(2)
        inc = 1
        return
    if inc > 0:
        print("Mech stop clockwise")
        az = AZ_CW_MECH_STOP
    if inc < 0:
        print("Mech stop counterclockwise")
        az = AZ_CCW_MECH_STOP

def az_interrupt(channel, last_az, current_az):
    global az
    global inc

    print("Azint %x %x" % (last_az, current_az))
    try:
        inc = -azz2inc[last_az << 2 | current_az]
    except KeyError:
        print("Key error: index=%s" % bin(last_az << 2 | current_az))
        return
    az += inc
    if inc:
        pulse_az_enable()
    print(az)

    az_track()


def az_track(target=None):
    global az_target
    if target is not None:
        az_target = target

    if az_target is not None:
        diff = az - az_target
        print("Diff = ", diff)
        if abs(diff) < 3:
            az_stop()
            return
        if diff < 0:
            az_cw()
        else:
            az_ccw()

def az_stop():
    print("Stopping azimuth rotation")
    p0.bit_write(STOP_AZ, pcf8574.LOW)  # Stop azimuth rotation

def az_cw():
    print("Rotating clockwise")
    p0.bit_write(START_AZ, pcf8574.LOW)  # Start CW
    p0.bit_write(STOP_AZ, pcf8574.HIGH)  # Don't stop azimuth rotation

def az_ccw():
    print("Rotating anticlockwise")
    p0.bit_write(ROTATE_CCW, pcf8574.LOW)
    p0.bit_write(START_AZ, pcf8574.LOW)  # Start CCW
    p0.bit_write(STOP_AZ, pcf8574.HIGH)   # Don't stop azimuth rotation


def interrupt_dispatch(channel):
    global last_sense
    global current_sense

    current_sense = p1.byte_read(0xff)
    # print("Interrupt %x %x" %(last_sense, current_sense))

    diff = current_sense ^ last_sense

    az_mask = 0x03
    el_mask = 0x04
    stop_mask = 0x08

    if diff & az_mask:
        az_interrupt(channel, last_sense & az_mask, current_sense & az_mask)
    if diff & el_mask:
        el_interrupt(channel,  last_sense & el_mask, current_sense & el_mask)
    if diff & stop_mask:
        stop_interrupt(channel, last_sense & stop_mask, current_sense & stop_mask)

    last_sense = current_sense


def pulse_az_enable():
    p0.bit_write(START_AZ, "HIGH")
    p0.bit_write(START_AZ, "LOW")

GPIO.add_event_detect(AZ_INT, GPIO.FALLING, callback=interrupt_dispatch)

def restore_az():
    global az
    cur = db.cursor()
    cur.execute("SELECT az FROM azel_current where ID=0")
    rows = cur.fetchall()
    if rows:
        az = rows[0][0]
    else:
        az = 0
        cur.execute("INSERT INTO azel_current VALUES(0,0,0)")
        db.commit()

def store_az():
    global az
    cur = db.cursor()
    cur.execute("UPDATE azel_current set az=? WHERE ID=0", (az,))
    db.commit()



p0 = pcf8574.PCF(0x20)
p1 = pcf8574.PCF(0x21)

p0.pin_mode("p0", "OUTPUT")
p0.pin_mode("p1", "OUTPUT")
p0.pin_mode("p2", "OUTPUT")

p1.pin_mode("p0", "INPUT")
p1.pin_mode("p1", "INPUT")
p1.pin_mode("p2", "INPUT")
p1.pin_mode("p3", "INPUT")


restore_az()


print("Az=%d" % az)

try:
    az_track(target=78)

    while(1):
        time.sleep(10)
finally:
    store_az()
    GPIO.cleanup()  # clean up GPIO on normal exit
