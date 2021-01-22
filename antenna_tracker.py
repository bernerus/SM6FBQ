#!/usr/bin/env python3
from threading import Lock
import time
import RPi.GPIO as GPIO
import smbus2
import pcf8574
import sqlite3
import queue

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import locator.src.maidenhead as mh

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "eventlet"

with open("etc/google_api.txt") as f:
    api_key = f.readline()

app = Flask(__name__, template_folder="./templates")
app.config['SECRET_KEY'] = '!tgilmeh'
app.config['GOOGLEMAPS_API_KEY'] = api_key

socket_io = SocketIO(app, async_mode=async_mode)

thread = None
thread_lock = Lock()

devices_data = {}  # dict to store data of devices
devices_location = {}  # dict to store coordinates of devices

db = sqlite3.connect("/home/pi/SM6FBQ/azel.db")

db.execute("CREATE TABLE IF NOT EXISTS azel_current (id INTEGER PRIMARY KEY AUTOINCREMENT, az int, el int)")
db.execute("CREATE TABLE IF NOT EXISTS config_int (key text PRIMARY KEY , value int)")

msgq = queue.Queue()

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

        self.CCW_BEARING_STOP: int = 162
        self.CW_BEARING_STOP: int = 167

        bearing_range = self.CW_BEARING_STOP - self.CCW_BEARING_STOP + 360

        self.ticks_per_degree = (self.AZ_CW_MECH_STOP - self.AZ_CCW_MECH_STOP)/bearing_range

        self.last_sent_az = None

        self.retriggering = None
        self.rotatiog_cw = None
        self.rotating_ccw = None



        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.AZ_INT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.calibrating = None

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
        self.el = 0
        self.inc = 0
        self.ignore_cw_stops = False
        self.ignore_ccw_stops = False

    def ticks2az(self, ticks):
        az = self.CCW_BEARING_STOP + ticks / self.ticks_per_degree
        if az > 360:
            az -= 360
        if az < 0:
            az += 360
        return int(az)

    def az2ticks(self, az):
        az1 = az - self.CCW_BEARING_STOP
        if az1 < 0:
            az1 += 360
        if az1 > 360:
            az1 -= 360
        return int(self.ticks_per_degree * az1)

    def el_interrupt(self, last, current):
        pass

    def stop_interrupt(self, last, current):

        if not self.p0.bit_read(self.STOP_AZ):
            print("Stop interrupt skipped. timer is cleared")
            return  # Timed is cleared
        if self.p0.bit_read(self.AZ_TIMER) and not self.calibrating and not self.rotating_cw and not self.rotating_ccw:
            print("Stop interrupt skipped. No rotation going on, retrig=%s, cw=%s, ccw=%s, calibrating=%s" % (self.retriggering, self.rotating_cw, self.rotating_ccw, self.calibrating))
            return  # We are not rotating
        print("Azel interrupt, retrig=%s, cw=%s, ccw=%s, calibrating=%s" % (self.retriggering, self.rotating_cw, self.rotating_ccw, self.calibrating))
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

        print("Az set to %d ticks" % self.az)
        self.send_azel()
        if self.calibrating:
            self.calibrating = False
            print("Calibration done")
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

        #            print("Ticks:", self.az)

        self.send_azel()

        self.az_track()

    def az_track(self, target=None):
        if target is not None:
            if self.az2ticks(target) != self.az_target:
                self.az_target = self.az2ticks(target)
                print("Tracking azimuth %d degrees = %d ticks" % (target, self.az_target))

        if self.az_target is not None:
            diff = self.az - self.az_target
            # print("Diff = ", diff)
            if abs(diff) < self.az_hysteresis:
                self.az_stop()
                # self.az_target = None
                return
            if diff < 0:
                if not self.rotating_cw:
                    self.az_cw()
            else:
                if not self.rotating_ccw:
                    self.az_ccw()

    def az_stop(self):
        #print("Stop azimuth rotation")
        self.rotating_ccw = False
        self.rotating_cw = False
        self.p0.byte_write(0xff, ~self.STOP_AZ)
        print("Stopped azimuth rotation")
        time.sleep(0.4)  # Allow mechanics to settle
        ctl.store_az()

    def az_ccw(self):
        #print("Rotate anticlockwise")
        self.rotating_ccw = True
        self.rotating_cw = False
        self.p0.byte_write(0xff, self.STOP_AZ)
        time.sleep(0.1)
        self.p0.byte_write(0xff, ~self.AZ_TIMER)
        print("Rotating anticlockwise")

    def az_cw(self):
        #print("Rotate clockwise")
        self.rotating_cw = True
        self.rotating_ccw = False
        self.p0.byte_write(0xff, self.STOP_AZ)
        time.sleep(0.1)
        self.p0.byte_write(0xFF, ~(self.AZ_TIMER | self.ROTATE_CW))
        print("Rotating clockwise")

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

        current_sense = self.p1.byte_read(0x17)
        # print("Interrupt %s %s" % (self.sense2str(self.last_sense), self.sense2str(current_sense)))

        diff = current_sense ^ self.last_sense

        az_mask = 0x03
        el_mask = 0x04
        stop_mask = 0x10

        if diff & az_mask:
            # print("Dispatching to az_interrupt")
            self.az_interrupt(self.last_sense & az_mask, current_sense & az_mask)
        if diff & el_mask:
            # print("Dispatching to el_interrupt")
            self.el_interrupt(self.last_sense & el_mask, current_sense & el_mask)
        if diff & stop_mask and (current_sense & stop_mask == 0):
            print("Dispatching to stop_interrupt, diff=%x, current_sense=%x, last_sense=%x" % (diff, current_sense, self.last_sense))
            self.stop_interrupt(self.last_sense & stop_mask, current_sense & stop_mask)

        self.last_sense = current_sense

    def retrigger_az_timer(self):
        self.retriggering = True
        self.p0.bit_write("p0", "HIGH")
        self.p0.bit_write("p0", "LOW")
        self.retriggering = False

    def restore_az(self):
        db = sqlite3.connect("/home/pi/SM6FBQ/azel.db")
        cur = db.cursor()
        cur.execute("SELECT az FROM azel_current where ID=0")
        rows = cur.fetchall()
        if rows:
            self.az = rows[0][0]
        else:
            self.az = 0
            cur.execute("INSERT INTO azel_current VALUES(0,0,0)")
            db.commit()
        db.close()

    def store_az(self):
        db = sqlite3.connect("/home/pi/SM6FBQ/azel.db")
        cur = db.cursor()
        cur.execute("UPDATE azel_current set az=? WHERE ID=0", (self.az,))
        db.commit()
        db.close()

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

    def send_azel(self, force=None):
        to_send_az = self.ticks2az(self.az)
        if to_send_az != self.last_sent_az or force:
            print("Queueing azel %d %d" % (to_send_az, self.el))
            msgq.put({"az": to_send_az, "el": self.el})
            self.last_sent_az = to_send_az


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
    ctl.calibrating = True
    ctl.az_ccw()
    print("Awaiting calibration")
    while ctl.calibrating:
        time.sleep(1)

    return "Calibration done, az=%d ticks" % ctl.az


@app.route("/track")
def track():
    target = request.args.get('az')
    new_target = int(target)
    if new_target != ctl.az_target:
        ctl.az_track(int(target))
    return "Tracking azimuth %d degrees" % int(target)


@app.route("/untrack")
def untrack():
    ctl.az_target = None
    ctl.az_stop()
    print("Stopped tracking at az=%d degrees"% ctl.ticks2az(ctl.az))
    return "Stopped tracking"

myqth = "JO67BQ68SL59"

@app.route("/myqth")
def my_qth():
    return myqth


@app.route('/getdata', methods=['GET', 'POST'])
def getdata():
    json_data = requests.get.args('json')
    return json_data
    # you can use this to get request with strings and parse json
    # put data in database or something


@app.route("/", methods=['GET', 'POST'])
def mapview():
    n, s, w, e, lon, lat = mh.to_rect(myqth)

    user_location = (lon, lat)

    rect = {
        "stroke_color": '#0000FF',
        "stroke_opacity": .7,
        "stroke_weight": 1,
        "fill_color": None,
        "fill_opacity": 0,
        "bounds": {
            "north": n,
            "west": w,
            "south": s,
            "east": e,
        },
    }

    circle = {  # draw circle on map (user_location as center)
        'stroke_color': '#0000FF',
        'stroke_opacity': .9,
        'stroke_weight': 5,
        # line(stroke) style
        'fill_color': '#FFFFFF',
        'fill_opacity': .2,
        # fill style
        'center': {  # set circle to user_location
            'lat': user_location[0],
            'lng': user_location[1]
        },
        'radius': 500  # circle size (50 meters)
    }

    return render_template('example.html', async_mode=socket_io.async_mode)


def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')


@socket_io.on('my event')
def handle_my_custom_event(json):
    print('received my event: ' + str(json))
    emit('my response', json, callback=messageReceived)
    ctl.send_azel()

@socket_io.on("track az")
def handle_track_az(json):
    # print('received track_az: ' + str(json))
    # emit('my response', json, callback=messageReceived)
    ctl.az_track(int(json['az']))

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        count += 1
        if not msgq.empty():
            item = msgq.get_nowait()
            # print("Sending azel %d %s" % (count, item))
            socket_io.emit("set_azel", item)
            # print("Sent azel %d %s" % (count, item))
        else:
            socket_io.sleep(0.1)


@socket_io.event
def my_ping():
    emit('my_pong')


@socket_io.event
def connect():
    global thread

    # Clear the queue
    try:
        while not msgq.empty():
            msgq.get_nowait()
    except queue.Empty:
        pass

    ctl.send_azel()
    with thread_lock:
        if thread is None:
            thread = socket_io.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})

@socket_io.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    pass
    ctl = AzElControl(hysteresis=3)
    try:
        ctl.startup()
        socket_io.run(app, host='0.0.0.0', port=8877, log_output=False, debug=False)

    finally:
        ctl.az_stop()
        GPIO.cleanup()  # clean up GPIO on exit