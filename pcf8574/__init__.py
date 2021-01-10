from pcf8574 import PCF85

LOW = "LOW"
HIGH = "HIGH"


class PCF:

    def __init__(self, address):
        self.address = address
        self.status = True
        self.pin_mode_flags = 0x00
        self.sm_bus_number = 1
        print("Setting up PCF85 address=%d" % address)
        PCF85.setup(address, self.sm_bus_number, self.status)

    def pin_mode(self, pin_name, mode):
        self.pin_mode_flags = PCF85.pin_mode(pin_name, mode, self.pin_mode_flags)
        print("Mode flags on %d is %d" % (self.address, self.pin_mode_flags))

    def bit_read(self, pin_name):
        return PCF85.bit_read(pin_name, self.sm_bus_number, self.address)

    def byte_read(self, pin_mask):
        return PCF85.byte_read(pin_mask, self.sm_bus_number, self.address)

    def bit_write(self, pin_name, value):
        PCF85.bit_write(pin_name, value, self.address, self.pin_mode_flags, self.sm_bus_number)
