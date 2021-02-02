import time
import pcf8574
import smbus2

imc = {
    'A': '.-',
    'B': '-...',
    'C': '-.-.',
    'D': '-..',
    'E': '.',
    'F': '..-.',
    'G': '--.',
    'H': '....',
    'I': '..',
    'J': '.---',
    'K': '-.-',
    'L': '.-..',
    'M': '--',
    'N': '-.',
    'O': '---',
    'P': '.--.',
    'Q': '--.-',
    'R': '.-.',
    'S': '...',
    'T': '-',
    'U': '..-',
    'V': '...-',
    'W': '.--',
    'X': '-..-',
    'Y': '-.--',
    'Z': '--..',
    'Å': '.--.-',
    'Ä': '.-.-',
    'Ö': '---.',

    '1': '.----',
    '2': '..---',
    '3': '...--',
    '4': '....-',
    '5': '.....',
    '6': '-....',
    '7': '--...',
    '8': '---..',
    '9': '----.',
    '0': '-----',

    '.': '.-.-.-',
    ',': '--..--',
    '?': '..--..',
    '\'': '.----.',
    '!': '-.-.--',
    '/': '-..-.',
    '(': '-.--.',
    ')': '-.--.-',
    '&': '.-...',
    ':': '---...',
    ';': '-.-.-.',
    '=': '-...-',
    '+': '.-.-.',
    '-': '-....-',
    '_': '..--.-',
    '"': '.-..-.',
    '$': '...-..-',
    '@': '.--.-.'
}


class Morser:

    def __init__(self, verbose=False, gpio_bus=1, speed=None, p0=None):

        if speed is None:
            speed = 80
        self.UNIT_TIME = 6/speed
        self.CW_KEY = "CW_KEY"
        self.unit_time = 6/speed
        self.verbose = verbose
        self.bus = smbus2.SMBus(gpio_bus)
        self.p0 = p0

    def transmit_sentence(self, sentence):
        for (index, word) in enumerate(sentence.split()):
            if index > 0:
                self.wait_between_words()
            self.transmit_word(word)

    def transmit_word(self, word):
        for (index, letter) in enumerate(word):
            if index > 0:
                self.wait_between_letters()
            self.transmit_letter(letter)

    def transmit_letter(self, letter):
        code = imc.get(letter.upper(), '')

        if code != '':

            if self.verbose:
                print('\nProcessing letter "{}" and code "{}"'.format(letter.upper(), code))

            for (index, signal) in enumerate(code):
                if index > 0:
                    self.wait_between_signals()

                if signal == '.':
                    self.transmit_dot()
                else:
                    self.transmit_dash()

        else:
            if self.verbose:
                print('\nInvalid input: {}'.format(letter))

    def transmit_dot(self):
        self.p0.bit_write(self.CW_KEY, "LOW")
        time.sleep(self.UNIT_TIME)

    def transmit_dash(self):
        self.p0.bit_write(self.CW_KEY, "LOW")
        time.sleep(self.UNIT_TIME * 3)

    def wait_between_signals(self):
        self.p0.bit_write(self.CW_KEY, "HIGH")
        time.sleep(self.UNIT_TIME)

    def wait_between_letters(self):
        self.p0.bit_write(self.CW_KEY, "HIGH")
        time.sleep(self.UNIT_TIME * 3)

    def wait_between_words(self):
        self.p0.bit_write(self.CW_KEY, "HIGH")
        time.sleep(self.UNIT_TIME * 7)

    def send_message(self, message, repeat=1):
        count = repeat
        try:
            while count:
                if message != '':
                    if self.verbose:
                        print('\nBegin Transmission')

                    self.transmit_sentence(message)
                    self.p0.bit_write(self.CW_KEY, "HIGH")
                count -= 1
                if count == 0:
                    break
                self.wait_between_words()

            if self.verbose:
                print('\nEnd Transmission')

        finally:
            self.p0.bit_write(self.CW_KEY, "HIGH")

