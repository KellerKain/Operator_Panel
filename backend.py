import json
import sys
import threading
import math
from time import sleep
from statemachine import State, StateChart
from statemachine.exceptions import TransitionNotAllowed
import zmq
import logging

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("backend.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("Backend")

# Global state / hardware handles
IS_PI = False
thermistor_channel = None
hx = None
hx_torque = None


# --- PURE-PYTHON BIT-BANG HX711 CLASS (FOR SECONDARY LOAD CELL) ---
class BitBangHX711:
    """
    Software bit-banging driver for HX711 allowing custom GPIO pin mapping.
    """
    def __init__(self, dout_pin: int, sck_pin: int, gain: int = 128):
        from gpiozero import DigitalInputDevice, DigitalOutputDevice

        self.dout = DigitalInputDevice(dout_pin)
        self.sck = DigitalOutputDevice(sck_pin, initial_value=False)

        # Gain clock pulses: 128 gain = 25 pulses, 32 gain = 26 pulses, 64 gain = 27 pulses
        if gain == 128:
            self.pulses = 25
        elif gain == 32:
            self.pulses = 26
        elif gain == 64:
            self.pulses = 27
        else:
            self.pulses = 25

    def _read(self):
        # Wait for DOUT to go LOW (data ready)
        timeout = 0
        while self.dout.value == 1:
            sleep(0.001)
            timeout += 1
            if timeout > 100:  # Sensor not responding or disconnected
                return None

        count = 0
        for _ in range(24):
            self.sck.on()
            count = (count << 1) | self.dout.value
            self.sck.off()

        # Set gain for next conversion by pulsing SCK extra times
        for _ in range(self.pulses - 24):
            self.sck.on()
            self.sck.off()

        # Convert 24-bit 2's complement signed integer
        if count & 0x800000:
            count -= 0x1000000

        return count


# --- ADS1115 THERMISTOR INITIALIZATION ---
try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    thermistor_channel = AnalogIn(ads, 0)

except (ValueError, RuntimeError, OSError) as i2c_err:
    logger.warning(f"[I2C Warning] ADS1115 unavailable at 0x48 ({i2c_err}). Temperature telemetry will mock 25.0 C.")
    IS_PI = True
except Exception as e:
    logger.warning(f"[HW Warning] General hardware failure on I2C block ({e}).")

# --- PRIMARY HX711 LOAD CELL (PACKING FORCE - HARDWARE SPI0.0) ---
hx = None
try:
    from hx711_gpiozero import HX711

    # Pin 21 (GPIO 9 MISO), Pin 23 (GPIO 11 SCLK)
    hx = HX711(bits=24, channel_gain="A128", max_voltage=3.3)

    TARE_OFFSET = 54686.0
    SCALE_RATIO = 5130.0

    logger.info("[HW Info] Primary HX711 (Packing Force) initialized on SPI0.0.")

except Exception as e:
    logger.warning(f"[HW Warning] Primary HX711 hardware unavailable ({e}). Weight telemetry will mock 0.0 lbs.")
    hx = None

# --- SECONDARY HX711 LOAD CELL (BREAKAWAY TORQUE - BIT-BANG GPIO 5 & 6) ---
hx_torque = None
try:
    # Uses BitBangHX711 on GPIO 5 (Pin 29) DOUT & GPIO 6 (Pin 31) SCK
    hx_torque = BitBangHX711(dout_pin=5, sck_pin=6, gain=128)

    TORQUE_TARE_OFFSET = 0.0
    TORQUE_SCALE_RATIO = 1000.0  # Raw counts per ft-lb

    logger.info("[HW Info] Secondary HX711 (Torque Sensor) initialized via bit-bang on GPIO 5/6.")

except Exception as e:
    logger.warning(f"[HW Warning] Secondary HX711 hardware unavailable ({e}). Torque telemetry will mock 0.0 ft-lb.")
    hx_torque = None


# --- HX711 TARE FUNCTIONS ---
def tare_scale():
    global TARE_OFFSET

    if hx is None:
        logger.error("Cannot tare primary scale: HX711 unavailable")
        return False

    readings = []
    logger.info("Taring primary HX711 scale...")

    for _ in range(20):
        try:
            raw = hx._read()
            if raw is not None:
                readings.append(float(raw))
        except Exception as err:
            logger.error(f"Primary Tare reading failed: {err}")
        sleep(0.1)

    if not readings:
        logger.error("Primary Tare failed: no valid readings")
        return False

    TARE_OFFSET = sum(readings) / len(readings)
    logger.info(f"New Primary Tare Offset: {TARE_OFFSET:.2f}")
    return True


def tare_torque_sensor():
    global TORQUE_TARE_OFFSET

    if hx_torque is None:
        logger.error("Cannot tare torque sensor: Secondary HX711 unavailable")
        return False

    readings = []
    logger.info("Taring secondary HX711 torque sensor...")

    for _ in range(20):
        try:
            raw = hx_torque._read()
            if raw is not None:
                readings.append(float(raw))
        except Exception as err:
            logger.error(f"Torque Tare reading failed: {err}")
        sleep(0.1)

    if not readings:
        logger.error("Torque Tare failed: no valid readings")
        return False

    TORQUE_TARE_OFFSET = sum(readings) / len(readings)
    logger.info(f"New Torque Tare Offset: {TORQUE_TARE_OFFSET:.2f}")
    return True


# --- MOTOR GPIO INITIALIZATION ---
try:
    from gpiozero import OutputDevice

    pin17 = OutputDevice(17, initial_value=False)
    pin22 = OutputDevice(22, initial_value=False)
    pin27 = OutputDevice(27, initial_value=False)

    pin12 = OutputDevice(12, initial_value=False)
    pin16 = OutputDevice(16, initial_value=False)
    pin20 = OutputDevice(20, initial_value=False)

    pin23 = OutputDevice(23, initial_value=False)
    pin24 = OutputDevice(24, initial_value=False)
    pin25 = OutputDevice(25, initial_value=False)

    IS_PI = True
    logger.info("[HW Info] Running on Raspberry Pi 5 hardware GPIO & ADS1115.")

except Exception as e:
    logger.warning(f"[HW Warning] Hardware unavailable ({e}). Using Dummy Mocks.")

    class DummyPin:
        def __init__(self, pin_num):
            self.pin_num = pin_num
        def off(self): pass
        def on(self): pass

    pin17 = DummyPin(17)
    pin22 = DummyPin(22)
    pin27 = DummyPin(27)
    pin12 = DummyPin(12)
    pin16 = DummyPin(16)
    pin20 = DummyPin(20)
    pin23 = DummyPin(23)
    pin24 = DummyPin(24)
    pin25 = DummyPin(25)


# --- SENSOR READER FUNCTIONS ---
def read_weight_lbs():
    if hx is None:
        return None

    try:
        raw_val = hx._read()
        if raw_val is None:
            return None

        weight_lbs = (raw_val - TARE_OFFSET) / SCALE_RATIO
        weight_lbs = weight_lbs - (weight_lbs * 2)
        return round(float(weight_lbs), 3)
    except Exception as err:
        logger.error(f"HX711 Weight Error: {err}")
        return None


def read_breakaway_torque_ftlb():
    """
    Reads raw counts from secondary bit-banged HX711 and calculates torque in ft-lbs.
    """
    if hx_torque is None:
        return None

    try:
        raw_val = hx_torque._read()
        if raw_val is None:
            return None

        torque_ftlb = (raw_val - TORQUE_TARE_OFFSET) / TORQUE_SCALE_RATIO
        return round(float(torque_ftlb), 3)
    except Exception as err:
        logger.error(f"HX711 Torque Error: {err}")
        return None


def read_temperature_celsius():
    if not IS_PI or thermistor_channel is None:
        return 25.0

    try:
        voltage = thermistor_channel.voltage
        v_in = 3.3
        r_divider = 4700.0

        if voltage <= 0 or voltage >= v_in:
            return -999.0

        r_thermistor = r_divider * (v_in - voltage) / voltage
        b_constant = 3950.0
        r_0 = 100000.0
        t_0 = 273.15 + 25.0

        steinhart = (1.0 / t_0) + (1.0 / b_constant) * math.log(r_thermistor / r_0)
        temp_kelvin = 1.0 / steinhart
        return round(temp_kelvin - 273.15, 2)
    except Exception as err:
        logger.error(f"[Thermistor Error] Failed to read sensor: {err}")
        return -999.0


# --- ZMQ TELEMETRY PUBLISHER THREAD ---
def start_telemetry_publisher(state_machine):
    """Publishes live telemetry every 1 second over tcp://127.0.0.1:5556."""
    context = zmq.Context()
    pub_socket = context.socket(zmq.PUB)
    pub_socket.setsockopt(zmq.LINGER, 0)
    pub_socket.bind("tcp://127.0.0.1:5556")
    logger.info("[Backend] Telemetry PUB server running on tcp://127.0.0.1:5556")

    while True:
        try:
            temp_c = read_temperature_celsius()
            temp_f = round((temp_c * 9 / 5) + 32, 2) if temp_c != -999.0 else -999.0

            weight_lb = read_weight_lbs()
            if weight_lb is not None:
                weight_g = round(weight_lb * 453.59237, 2)
                packing_force_n = round(weight_lb * 4.4482216153, 2)
            else:
                weight_lb = -999.0
                weight_g = -999.0
                packing_force_n = -999.0

            # Read breakaway torque (ft-lbs and N-m conversion)
            torque_ftlb = read_breakaway_torque_ftlb()
            if torque_ftlb is not None:
                torque_nm = round(torque_ftlb * 1.3558179483, 3)
            else:
                torque_ftlb = -999.0
                torque_nm = -999.0

            telemetry_data = {
                "temperature_c": temp_c,
                "temperature_f": temp_f,
                "weight_g": weight_g,
                "weight_lb": weight_lb,
                "packing_force_N": packing_force_n,
                "torque_ftlb": torque_ftlb,
                "torque_nm": torque_nm,
                "current_state": state_machine.current_state_value,
                "current_cycle": state_machine.current_cycle,
                "target_cycles": state_machine.target_cycles,
            }
            pub_socket.send_json(telemetry_data)
            logger.info("[Backend] Telemetry data sent")

        except Exception as err:
            logger.error(f"[Telemetry Error] {err}")

        sleep(1.0)


# State Machine Definitions
class SystemStates(StateChart):
    Idle = State(initial=True)
    WearTest = State()
    LeakTest = State()
    TorqueTest = State()
    Depressurized = State()
    Repressurizing = State()

    start_wear = Idle.to(WearTest)
    start_leak = Idle.to(LeakTest)
    start_torque = Idle.to(TorqueTest)
    stop = WearTest.to(Idle) | LeakTest.to(Idle) | TorqueTest.to(Idle)

    depressurize = Idle.to(Depressurized)
    repressurize = Depressurized.to(Repressurizing)
    repressurized_done = Repressurizing.to(Idle)

    def __init__(self):
        super().__init__()
        self.target_cycles = 0
        self.current_cycle = 0
        self.sleep_test_val = 0
        self.is_running = False
        self.test_thread = None

    def on_enter_WearTest(self):
        logger.info(f"[Backend] Starting Wear Test with {self.target_cycles} target cycles...")
        self.is_running = True
        self.current_cycle = 0
        self.test_thread = threading.Thread(target=self._run_wear_cycle_loop, daemon=True)
        self.test_thread.start()

    def _run_wear_cycle_loop(self):
        pin22.on()
        while self.is_running and self.current_cycle < self.target_cycles:
            self.current_cycle += 1
            logger.info(f"[Wear Test] Cycle {self.current_cycle} / {self.target_cycles}")
            current_pulse = 0
            ppc = 9400

            if self.current_cycle % 2 != 0:
                pin27.on()
                sleep(2)
                logger.info(f"[Cycle {self.current_cycle}] PIN 27 set HIGH (3.3V)")
            else:
                pin27.off()
                sleep(2)
                logger.info(f"[Cycle {self.current_cycle}] PIN 27 set LOW (0V)")

            while current_pulse < ppc:
                pin17.on()
                sleep(.0001)
                pin17.off()
                sleep(0.0001)
                current_pulse = 1 + current_pulse

        if self.is_running and self.current_cycle >= self.target_cycles:
            logger.info("[Wear Test] Target cycles reached! Returning to Idle...")
            pin22.off()
            self.stop()

    def on_exit_WearTest(self):
        logger.info("[Backend] Exiting Wear Test...")
        self.is_running = False
        pin17.off()
        pin22.off()

    def on_enter_Idle(self):
        logger.info("[Backend] Entered IDLE state. Safely driving all GPIO LOW.")
        self.is_running = False
        pin17.off()
        pin22.off()
        pin27.off()

    def on_enter_TorqueTest(self):
        logger.info("[Backend] Starting Torque Test...")
        pin17.on()
        pin22.on()
        pin27.on()

    def on_exit_TorqueTest(self):
        logger.info("[Backend] Exiting Torque Test...")
        pin17.off()
        pin22.off()
        pin27.off()

    def on_enter_LeakTest(self):
        logger.info("[Backend] Starting Leak Rate Test...")
        pin17.on()
        pin22.on()
        pin27.on()

    def on_exit_LeakTest(self):
        logger.info("[Backend] Exiting Leak Rate Test...")
        pin17.off()
        pin22.off()
        pin27.off()

    def on_enter_Depressurized(self):
        logger.info("[Backend] System Depressurized. Packing must be repressurized before returning to Idle.")
        pin12.on()
        pin16.on()
        pin20.on()
        pin23.on()
        pin24.on()
        pin25.on()

        sleep(100)

        pin12.off()
        pin16.off()
        pin20.off()
        pin23.off()
        pin24.off()
        pin25.off()

    def on_enter_Repressurizing(self):
        logger.info("[Backend] Repressurizing packing...")
        self.test_thread = threading.Thread(target=self._run_repressurize_routine, daemon=True)
        self.test_thread.start()

    def _run_repressurize_routine(self):
        pin12.on()
        pin16.off()
        pin20.on()
        pin23.on()
        pin24.off()
        pin25.on()
        sleep(2.0)

        pin12.off()
        pin20.off()
        pin23.off()
        pin25.off()

        logger.info("[Backend] Repressurization complete.")
        self.repressurized_done()


def run_backend_zmq_listener(state_machine):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.setsockopt(zmq.LINGER, 0)
    socket.bind("tcp://127.0.0.1:5555")
    logger.info("[Backend] ZeroMQ REP Server online on tcp://127.0.0.1:5555")

    try:
        while True:
            raw_message = socket.recv_string()
            logger.info(f"[ZMQ Received]: {raw_message}")

            command = raw_message
            payload = {}
            if raw_message.startswith("{"):
                try:
                    payload = json.loads(raw_message)
                    command = payload.get("command", "")
                except json.JSONDecodeError:
                    logger.error("[Backend Error] Invalid JSON string received.")

            if "cycles" in payload:
                state_machine.target_cycles = payload["cycles"]

            if "cycle_time" in payload:
                state_machine.sleep_test_val = payload["cycle_time"]

            if "target_pressure" in payload:
                state_machine.target_pressure = payload["target_pressure"]

            if command == "stop" and state_machine.current_state == SystemStates.Idle:
                reply = "ACK: Already in Idle state."
                logger.info(f"[Backend] {reply}")
                socket.send_string(reply)
                continue

            if hasattr(state_machine, command):
                event_method = getattr(state_machine, command)
                try:
                    event_method()
                    reply = f"ACK: State is now '{state_machine.current_state_value}'"
                except TransitionNotAllowed:
                    reply = f"ERR: Cannot transition via '{command}' from state '{state_machine.current_state_value}'."
                    logger.warning(f"[Backend Warning] {reply}")
                except Exception as err:
                    reply = f"ERR: Exception during transition - {err}"
                    logger.error(f"[Backend Exception] {reply}")

                socket.send_string(reply)
            else:
                socket.send_string(f"ERR: Command '{command}' not recognized.")

    except KeyboardInterrupt:
        logger.info("\n[Backend] Shutting down backend server...")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    sm = SystemStates()

    # Tare both load cells before starting telemetry
    if not tare_scale():
        logger.warning("Primary HX711 tare failed; force scale readings are uncalibrated")

    if not tare_torque_sensor():
        logger.warning("Secondary HX711 tare failed; torque readings are uncalibrated")

    # Start telemetry publisher
    telemetry_thread = threading.Thread(
        target=start_telemetry_publisher,
        args=(sm,),
        daemon=True
    )
    telemetry_thread.start()

    # Start ZeroMQ command server
    run_backend_zmq_listener(sm)