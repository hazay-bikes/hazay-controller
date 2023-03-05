from machine import UART, Pin, freq
from utime import sleep_us, time, sleep, sleep_ms
from micropython import const
import os

led = Pin(25, Pin.OUT)

with open("id_version", "r") as f:
    id_version = f.read()


CONTROLLER_ID = "hazay_" + id_version

BLE_MODE_PIN = Pin(15, Pin.IN, Pin.PULL_UP)

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

Name_BLE_Set = bytes("AT+BM" + CONTROLLER_ID + "\r\n", "utf-8")
Name_BLE_Query = b"AT+TM\r\n"
# Query baud rate
Baud_Rate_115200 = b"AT+CT05\r\n"
Baud_Rate_Query = b"AT+QT\r\n"

CMND_Tare = b"HazayCargo-Cmnd: Tare"
CMND_Scale = b"HazayCargo-Cmnd: Scale"


class HX711Exception(Exception):
    pass


class InvalidMode(HX711Exception):
    pass


class DeviceIsNotReady(HX711Exception):
    pass


class HX711(object):
    """
    Micropython driver for Avia Semiconductor's HX711
    24-Bit Analog-to-Digital Converter
    """

    CHANNEL_A_128 = const(1)
    CHANNEL_A_64 = const(3)
    CHANNEL_B_32 = const(2)

    DATA_BITS = const(24)
    MAX_VALUE = const(0x7FFFFF)
    MIN_VALUE = const(0x800000)
    READY_TIMEOUT_SEC = const(5)
    SLEEP_DELAY_USEC = const(80)

    def __init__(self, d_out: int, pd_sck: int, channel: int = CHANNEL_A_128):
        self.d_out_pin = Pin(d_out, Pin.IN)
        self.pd_sck_pin = Pin(pd_sck, Pin.OUT, value=0)
        self.channel = channel

        self.OFFSET = 0
        self.SCALE = 1
        self.UNIT = 1

    def __repr__(self):
        return "HX711 on channel %s, gain=%s" % self.channel

    def _convert_from_twos_complement(self, value: int) -> int:
        """
        Converts a given integer from the two's complement format.
        """
        if value & (1 << (self.DATA_BITS - 1)):
            value -= 1 << self.DATA_BITS
        return value

    def _set_channel(self):
        """
        Input and gain selection is controlled by the
        number of the input PD_SCK pulses
        3 pulses for Channel A with gain 64
        2 pulses for Channel B with gain 32
        1 pulse for Channel A with gain 128
        """
        for i in range(self._channel):
            self.pd_sck_pin.value(1)
            self.pd_sck_pin.value(0)

    def _wait(self):
        """
        If the HX711 is not ready within READY_TIMEOUT_SEC
        the DeviceIsNotReady exception will be thrown.
        """
        t0 = time()
        while not self.is_ready():
            if time() - t0 > self.READY_TIMEOUT_SEC:
                raise DeviceIsNotReady()

    @property
    def channel(self) -> tuple:
        """
        Get current input channel in a form
        of a tuple (Channel, Gain)
        """
        if self._channel == self.CHANNEL_A_128:
            return "A", 128
        if self._channel == self.CHANNEL_A_64:
            return "A", 64
        if self._channel == self.CHANNEL_B_32:
            return "B", 32

    @channel.setter
    def channel(self, value):
        """
        Set input channel
        HX711.CHANNEL_A_128 - Channel A with gain 128
        HX711.CHANNEL_A_64 - Channel A with gain 64
        HX711.CHANNEL_B_32 - Channel B with gain 32
        """
        if value not in (self.CHANNEL_A_128, self.CHANNEL_A_64, self.CHANNEL_B_32):
            raise InvalidMode(
                "Gain should be one of HX711.CHANNEL_A_128, HX711.CHANNEL_A_64, HX711.CHANNEL_B_32"
            )
        else:
            self._channel = value

        if not self.is_ready():
            self._wait()

        for i in range(self.DATA_BITS):
            self.pd_sck_pin.value(1)
            self.pd_sck_pin.value(0)

        self._set_channel()

    def is_ready(self) -> bool:
        """
        When output data is not ready for retrieval,
        digital output pin DOUT is high.
        """
        return self.d_out_pin.value() == 0

    def power_off(self):
        """
        When PD_SCK pin changes from low to high
        and stays at high for longer than 60 us ,
        HX711 enters power down mode.
        """
        self.pd_sck_pin.value(0)
        self.pd_sck_pin.value(1)
        sleep_us(self.SLEEP_DELAY_USEC)

    def power_on(self):
        """
        When PD_SCK returns to low, HX711 will reset
        and enter normal operation mode.
        """
        self.pd_sck_pin.value(0)
        self.channel = self._channel

    def read(self, raw=False):
        """
        Read current value for current channel with current gain.
        if raw is True, the HX711 output will not be converted
        from two's complement format.
        """
        if not self.is_ready():
            self._wait()

        raw_data = 0
        for i in range(self.DATA_BITS):
            self.pd_sck_pin.value(1)
            self.pd_sck_pin.value(0)
            raw_data = raw_data << 1 | self.d_out_pin.value()
        self._set_channel()

        if raw:
            return raw_data
        else:
            return self._convert_from_twos_complement(raw_data)

    def read_average(self, times=3):
        sum = 0
        for i in range(times):
            sum += self.read()
        return sum / times

    def tare(self, times=15, known_tare=None):
        if known_tare:
            offset = known_tare
        else:
            offset = self.read_average(times)
        self.set_offset(offset)
        return offset

    def scale(self, times=15, known_scale=None, known_unit=None):
        if not known_scale:
            scale = self.read_average(times) - self.OFFSET
        else:
            scale = known_scale
        self.set_scale(scale)

        if known_unit:
            self.set_unit(known_unit)

        return scale, known_unit

    def set_scale(self, scale):
        self.SCALE = scale

    def set_unit(self, unit):
        self.UNIT = unit

    def set_offset(self, offset):
        self.OFFSET = offset

    def get_value(self):
        return self.read_average() - self.OFFSET

    def get_units(self):
        return self.get_value() / self.SCALE

    def get_reading_in_unit_grams(self):
        return int(abs(max(driver.get_units() * self.UNIT, 0)))

    def is_tare_saved(self):
        try:
            os.stat("tare")
            return True
        except OSError:
            return False

    def load_saved_tare(self):
        f = open("tare", "r")
        data = f.read()
        f.close()
        return float(data)

    def save_tare(self, offset):
        f = open("tare", "w")
        f.write(str(offset))
        f.close()

    def is_scale_unit_saved(self):
        try:
            os.stat("scale_unit")
            return True
        except OSError:
            return False

    def load_saved_scale_unit(self):
        f = open("scale_unit", "r")
        data = f.read()
        f.close()
        scale, unit = data.split(":")
        return float(scale), int(unit)

    def save_scale_unit(self, scale, unit):
        f = open("scale_unit", "w")
        data = f.write(str(scale) + ":" + str(unit))
        f.close()


def ble_init():
    while BLE_MODE_PIN.value() == 0:
        sleep_ms(50)

    uart.write(Name_BLE_Query)
    sleep_ms(100)
    uart.write(Name_BLE_Set)
    sleep_ms(100)
    uart.write(Baud_Rate_Query)
    sleep_ms(100)
    uart.write(Baud_Rate_115200)
    sleep_ms(100)


freq(160000000)
driver = HX711(d_out=5, pd_sck=4)


# Tare logic
if driver.is_tare_saved():
    offset = driver.load_saved_tare()
    driver.tare(known_tare=offset)
else:
    offset = driver.tare()
    driver.save_tare(offset)
sleep(0.5)


# Scale logic
if not driver.is_scale_unit_saved():
    # initial default values - will be calibrated later by user
    driver.save_scale_unit(scale=33150.00, unit=1556)

# load saved scale and unit
scale, unit = driver.load_saved_scale_unit()
driver.scale(known_scale=scale, known_unit=unit)

uart.init(baudrate=115200, tx=Pin(0), rx=Pin(1))

ble_init()

while True:
    if uart.any():
        uart_data = uart.read()
        # Support for tare
        if uart_data == CMND_Tare:
            offset = driver.tare()
            driver.save_tare(offset)
            sleep_ms(500)
        elif CMND_Scale in uart_data:
            decoded_data = uart_data.decode("utf-8")
            mass_grams = int(decoded_data.split(";")[1].split(":")[1])
            scale, unit = driver.scale(known_unit=mass_grams)
            driver.save_scale_unit(scale=scale, unit=unit)
            sleep_ms(500)

    sleep_ms(100)

    scale_readings_g = str(driver.get_reading_in_unit_grams())

    print(scale_readings_g)

    uart.write(scale_readings_g + ";" + CONTROLLER_ID)

    led.value(1)  # Set led turn on
    sleep_ms(200)
    led.value(0)
    sleep_ms(200)
