#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
import smbus2
import pcf8574
import sqlite3
import json

from flask import Flask, request, render_template

from flask_googlemaps import GoogleMaps, Map

app = Flask(__name__)

api_key = '<google-api-key>'  # change this to your api key
# get api key from Google API Console (https://console.cloud.google.com/apis/)
GoogleMaps(app, key=api_key)  # set api_key
devices_data = {}  # dict to store data of devices
devices_location = {}  # dict to store coordinates of devices

db = sqlite3.connect("/home/pi/SM6FBQ/azel.db")

db.execute("CREATE TABLE IF NOT EXISTS azel_current (id INTEGER PRIMARY KEY AUTOINCREMENT, az int, el int)")
db.execute("CREATE TABLE IF NOT EXISTS config_int (key text PRIMARY KEY , value int)")


class AzElControl:

    def __init__(self, hysteresis=1, gpio_bus=1):
        self.bus = smbus2.SMBus(gpio_bus)
        self.az_hysteresis = hysteresis
        # Pin names
        self.AZ_TIMER = 1 << 0
        self.STOP_AZ = 1 << 1
        self.ROTATE_CW = 1 << 2
        self.RUN_EL = 1 << 3
        self.EL_UP = 1 << 4

        self.AZ_IND_A = 1 << 0
        self.AZ_IND_B = 1 << 1
        self.EL_PULSE = 1 << 2

        self.AZ_INT = 17

        self.AZ_CCW_MECH_STOP: int = 0
        self.AZ_CW_MECH_STOP: int = 734

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.AZ_INT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.calibrating = False

        self.azz2inc = {0b0000: 0,
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

        self.last_sense = 0xff
        self.az_target = None
        self.az = 0
        self.inc = 0
        self.ignore_cw_stops = False
        self.ignore_ccw_stops = False

    def el_interrupt(self, last, current):
        pass

    def stop_interrupt(self, last, current):

        if not self.p0.bit_read(self.STOP_AZ):
            # print("Stop interrupt skipped. timer is cleared")
            return  # Timed is cleared
        if self.p0.bit_read(self.AZ_TIMER):
            # print("Stop interrupt skipped. No rotation going on")
            return  # We are not rotating
        # time.sleep(1)
        # We ran into a mech stop
        if False:
            if inc == 0:
                # print("Mechanical stop. Unknown dir")
                if not p0.bit_read(ROTATE_CW):
                    # print("Was running clockwise")
                    inc = 1
                else:
                    # print("Was running anticlockwise")
                    inc = -1
            if inc > 0 and not ignore_cw_stops:
                # print("Mechanical stop clockwise")
                self.az = AZ_CW_MECH_STOP
                self.ignore_ccw_stops = True
                # print("Ignoring anticlockwise stops")
            if inc < 0 and not ignore_ccw_stops:
                # print("Mechanical stop anticlockwise")
                self.az = AZ_CCW_MECH_STOP
                self.ignore_cw_stops = True
                # print("Ignoring clockwise stops")
        else:
            if not self.p0.bit_read(self.ROTATE_CW):
                # print("Mechanical stop clockwise")
                self.az = self.AZ_CW_MECH_STOP
                self.ignore_ccw_stops = True
            else:
                # print("Mechanical stop anticlockwise")
                self.az = self.AZ_CCW_MECH_STOP
                self.ignore_cw_stops = True

        print("Az set to", self.az)
        if self.calibrating:
            self.calibrating = False
            self.az_stop()
        else:
            self.az_track()

    def az_interrupt(self, last_az, current_az):

        # print("Azint; %x %x" % (last_az, current_az))
        try:
            inc = self.azz2inc[last_az << 2 | current_az]
        except KeyError:
            print("Key error: index=%s" % bin(last_az << 2 | current_az))
            self.az_track()
            return
        self.az += inc
        if inc:
            if inc > 0:
                ignore_ccw_stops = False
                # print("Enabling ccw stops")
            else:
                ignore_cw_stops = False
                # print("Enabling cw stops")
            self.retrigger_az_timer()

        print(self.az)

        self.az_track()

    def az_track(self, target=None):
        if target is not None:
            self.az_target = target

        if self.az_target is not None:
            diff = self.az - self.az_target
            # print("Diff = ", diff)
            if abs(diff) < self.az_hysteresis:
                self.az_stop()
                return
            if diff < 0:
                self.az_cw()
            else:
                self.az_ccw()

    def az_stop(self):
        print("Stopping azimuth rotation")

        self.p0.byte_write(0xff, ~self.STOP_AZ)
        time.sleep(0.4)     # Allow mechanics to settle
        ctl.store_az()

    def az_ccw(self):
        print("Rotating anticlockwise")
        self.p0.byte_write(0xff, ~self.AZ_TIMER)

    def az_cw(self):
        print("Rotating clockwise")
        self.p0.byte_write(0xFF, ~(self.AZ_TIMER | self.ROTATE_CW))

    def sense2str(self, value):
        x = 1
        ret = ""
        sensebits = {1: "A", 2: "B", 4: "E", 8: "C"}
        while (x < 16):
            if value & x:
                ret += sensebits[x]
            else:
                ret += " "
            x = x << 1
        return ret

    def interrupt_dispatch(self, channel):

        current_sense = self.p1.byte_read(0x0f)
        # print("Interrupt %s %s" % (self.sense2str(self.last_sense), self.sense2str(current_sense)))

        diff = current_sense ^ self.last_sense

        az_mask = 0x03
        el_mask = 0x04
        stop_mask = 0x08

        if diff & az_mask:
            # print("Dispatching to az_interrupt")
            self.az_interrupt(self.last_sense & az_mask, current_sense & az_mask)
        if diff & el_mask:
            # print("Dispatching to el_interrupt")
            self.el_interrupt(self.last_sense & el_mask, current_sense & el_mask)
        if diff & stop_mask and (current_sense & stop_mask == 0):
            # print("Dispatching to stop_interrupt")
            self.stop_interrupt(self.last_sense & stop_mask, current_sense & stop_mask)

        self.last_sense = current_sense

    def retrigger_az_timer(self):
        self.p0.bit_write("p0", "HIGH")
        self.p0.bit_write("p0", "LOW")

    def restore_az(self):
        cur = db.cursor()
        cur.execute("SELECT az FROM azel_current where ID=0")
        rows = cur.fetchall()
        if rows:
            self.az = rows[0][0]
        else:
            self.az = 0
            cur.execute("INSERT INTO azel_current VALUES(0,0,0)")
            db.commit()

    def store_az(self):
        cur = db.cursor()
        cur.execute("UPDATE azel_current set az=? WHERE ID=0", (self.az,))
        db.commit()

    def startup(self):
        self.p0 = pcf8574.PCF(0x20)
        self.p1 = pcf8574.PCF(0x21)

        self.p0.pin_mode("p0", "OUTPUT")
        self.p0.pin_mode("p1", "OUTPUT")
        self.p0.pin_mode("p2", "OUTPUT")

        self.p1.pin_mode("p0", "INPUT")
        self.p1.pin_mode("p1", "INPUT")
        self.p1.pin_mode("p2", "INPUT")
        self.p1.pin_mode("p3", "INPUT")

        # print("Restoring current azimuth")
        self.restore_az()
        # print("Az restored to %d" % self.az)
        self.az_stop()
        # print("Starting interrupt dispatcher")
        GPIO.add_event_detect(self.AZ_INT, GPIO.FALLING, callback=self.interrupt_dispatch)


@app.route('/az')
def get_azimuth():
    return "Az=%d ticks" % ctl.az


@app.route('/calibrate')
def calibrate():
    ctl.calibrating = True
    ctl.az_target = None
    ctl.az_cw()
    time.sleep(1)
    ctl.az_stop()
    ctl.az_ccw()
    print("Awaiting calibration")
    while ctl.calibrating:
        time.sleep(1)
        print("Az is %d" % ctl.az)

    return "Calibration done, az=%d ticks" % ctl.az


@app.route("/track")
def track():
    target = request.args.get('az')
    ctl.az_track(int(target))
    return "Tracking azimuth %d" % int(target)


@app.route("/untrack")
def untrack():
    ctl.az_target = None
    ctl.az_stop()
    return "Stopped tracking"


@app.route('/', methods=["GET"])
def my_map():
    mymap = Map(

                identifier="view-side",

                varname="mymap",

                style="height:720px;width:1100px;margin:0;",  # hardcoded!

                lat=57.702129,  # hardcoded!

                lng=12.139914,  # hardcoded!

                zoom=15,

                markers=[(57.702129, 12.139914)]  # hardcoded!

            )

    return render_template('map.html', mymap=mymap)



@app.route('/getdata', methods=['GET', 'POST'])
def getdata():
    json_data = requests.get.args('json')
    return json_data
    # you can use this to get request with strings and parse json
    # put data in database or something


if __name__ == '__main__':

    ctl = AzElControl()

    try:
        ctl.startup()
        app.run(host='0.0.0.0', port=8877)

    finally:
        ctl.az_stop()
        GPIO.cleanup()  # clean up GPIO on exit
