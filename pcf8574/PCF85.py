from smbus2 import SMBus

INPUT = "INPUT"
OUTPUT = "OUTPUT"
HIGH = "HIGH"
LOW = "LOW"



def setup(PCFAdd, smBus, status):
    if status:
        with SMBus(smBus) as bus:
            bus.write_byte(PCFAdd, 0xFF)
    elif not status:
        with SMBus(smBus) as bus:
            bus.write_byte(PCFAdd, 0x00)


def pin_mode(pin_name, mode, flg):
    return set_mode(pinNameToNum(pin_name), mode, flg)


def set_mode(pin_number, mode, flg):
    if INPUT in mode:
        return clear_bit(flg, pin_number)
    elif OUTPUT in mode:
        return set_bit(flg, pin_number)
    else:
        return flg


def bit_read(pin_name, smbs, addr):
    with SMBus(smbs) as bus:
        b = bus.read_byte(addr)
    return test_bit(b, pinNameToNum(pin_name))

def byte_read(pin_mask, smbs, addr):
    with SMBus(smbs) as bus:
        b = bus.read_byte(addr)
    return b & pin_mask

def byte_write(pin_mask, smbs, addr, value):
    with SMBus(smbs) as bus:
        bus.write_byte(addr, value & pin_mask)


def pinNameToNum(pin):
    if type(pin) is str:
        pn = int(pin.strip().replace("p", "").strip())
        if pn in range(8):
            return pn
        else:
            print("pin name error!")
    else:
        return pin


def test_bit(n, offset):
    mask = 1 << offset
    return (n & mask)


def set_bit(n, offset):
    mask = 1 << offset
    return(n | mask)


def clear_bit(n, offset):
    mask = ~(1 << offset)
    return (n & mask)


def bit_write(pin_name, val, addr, flg, smbs):
    if test_bit(flg, pinNameToNum(pin_name)):
        if HIGH in val:
            write_data(pinNameToNum(pin_name), 1, smbs, flg, addr)
        elif LOW  in val:
            write_data(pinNameToNum(pin_name), 0, smbs, flg, addr)
    else:
        print("You can not Write Input Pin")


def write_data(pin_number, val, smbs, flg, addr):
    if test_bit(flg, pin_number):
        with SMBus(smbs) as bus:
            value_read = bus.read_byte(addr)
        if val == 0 and test_bit(value_read, pin_number):
            with SMBus(smbs) as bus:
                bus.write_byte(addr, clear_bit(value_read, pin_number))
        elif val == 1 and not test_bit(value_read, pin_number):
            with SMBus(smbs) as bus:
                bus.write_byte(addr, set_bit(value_read, pin_number))
