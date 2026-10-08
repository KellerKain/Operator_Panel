import json
import sys
import threading
import logging #not setup yet
from time import sleep
from statemachine import State, StateChart
from statemachine.exceptions import TransitionNotAllowed
import zmq
import logging #allows for log file creation

#Logging Setup
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


# Mock GPIO setup for non-Pi development vs Live Raspberry Pi 5
try:
    from gpiozero import OutputDevice
    # pins for the NEMA 17 Motor
    pin17 = OutputDevice(17, initial_value=False)
    pin22 = OutputDevice(22, initial_value=False)
    pin27 = OutputDevice(27, initial_value=False)

    # Pins for the NEMA 23 Motors
    pin12 = OutputDevice(12, initial_value=False)
    pin16 = OutputDevice(16, initial_value=False)
    pin20 = OutputDevice(20, initial_value=False)

    pin23 = OutputDevice(23, initial_value=False)
    pin24 = OutputDevice(24, initial_value=False)
    pin25 = OutputDevice(25, initial_value=False)

    logger.info("[HW Info] Running on Raspberry Pi 5 hardware GPIO.")
except Exception as e:
    logger.warning(f"[HW Warning] GPIO unavailable ({e}). Using Dummy Mock Pins.")

    class DummyPin:
        def __init__(self, pin_num):
            self.pin_num = pin_num

        def off(self):
            logger.info(f"[Mock Pin {self.pin_num}] State set to LOW / Ground (0V)")

        def on(self):
            logger.info(f"[Mock Pin {self.pin_num}] State set to HIGH (3.3V)")

    pin17 = DummyPin(17)
    pin22 = DummyPin(22)
    pin27 = DummyPin(27)


# State Machine Definitions
class SystemStates(StateChart):
    # States
    Idle = State(initial=True)
    WearTest = State()
    LeakTest = State()
    TorqueTest = State()
    Depressurized = State()
    Repressurizing = State()

    # Test Transitions
    start_wear = Idle.to(WearTest)
    start_leak = Idle.to(LeakTest)
    start_torque = Idle.to(TorqueTest)
    stop = WearTest.to(Idle) | LeakTest.to(Idle) | TorqueTest.to(Idle)

    # Pressure Management Transitions
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

    # Wear Test Lifecycle
    def on_enter_WearTest(self):
        logger.info(
            f"[Backend] Starting Wear Test with {self.target_cycles} target cycles..."
        )
        self.is_running = True
        self.current_cycle = 0

        self.test_thread = threading.Thread(
            target=self._run_wear_cycle_loop, daemon=True
        )
        self.test_thread.start()

    def _run_wear_cycle_loop(self):
        """Background loop executing the hardware cycles."""
        while self.is_running and self.current_cycle < self.target_cycles:
            self.current_cycle += 1
            logger.info(
                f"[Wear Test] Cycle {self.current_cycle} / {self.target_cycles}"
            )

            if self.current_cycle % 2 != 0:
                pin27.on()
                logger.info(f"[Cycle {self.current_cycle}] PIN 27 set HIGH (3.3V)")
            else:
                pin27.off()
                logger.info(f"[Cycle {self.current_cycle}] PIN 27 set LOW (0V)")

            pin17.on()
            sleep(self.sleep_test_val)
            pin17.off()
            sleep(0.1)

        if self.is_running and self.current_cycle >= self.target_cycles:
            logger.info("[Wear Test] Target cycles reached! Returning to Idle...")
            self.stop()

    def on_exit_WearTest(self):
        logger.info("[Backend] Exiting Wear Test...")
        self.is_running = False
        pin17.off()
        pin22.off()

    # Idle Handler
    def on_enter_Idle(self):
        logger.info("[Backend] Entered IDLE state. Safely driving all GPIO LOW.")
        self.is_running = False
        pin17.off()
        pin22.off()
        pin27.off()

    # Torque Handler
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

    # Leak Rate Handler
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

    # Depressurization Handlers
    def on_enter_Depressurized(self):
        logger.info("[Backend] System Depressurized. Packing must be repressurized before returning to Idle.")
        # Execute hardware actions to release pressure here
        pin12.on()
        pin16.on()
        pin20.on()

        pin23.on()
        pin24.on()
        pin25.on()

        sleep(100) #placeholder, When the sensors are set up this will be dynamic based on sensor data

        pin12.off()
        pin16.off()
        pin20.off()

        pin23.off()
        pin24.off()
        pin25.off()


    def on_enter_Repressurizing(self):
        logger.info("[Backend] Repressurizing packing...")
        self.test_thread = threading.Thread(
            target=self._run_repressurize_routine, daemon=True
        )
        self.test_thread.start()

    def _run_repressurize_routine(self):
        """Hardware routine to restore pressure before returning to Idle."""
        pin12.on()
        pin16.off() #Pins 16 and 24 being off reverses the direction
        pin20.on()

        pin23.on()
        pin24.off()
        pin25.on()
        sleep(2.0)  #Placeholder for when can be done dynamically

        pin12.off()
        pin20.off()

        pin23.off()
        pin25.off()

        logger.info("[Backend] Repressurization complete.")
        self.repressurized_done()


# ZMQ Server Listener Loop
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

            # Check if stopping while already in Idle
            if command == "stop" and state_machine.current_state == SystemStates.Idle:
                reply = "ACK: Already in Idle state."
                logger.info(f"[Backend] {reply}")
                socket.send_string(reply)
                continue

            # Execute transition if valid
            if hasattr(state_machine, command):
                event_method = getattr(state_machine, command)
                try:
                    event_method()  # Triggers state transition & callbacks
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
    run_backend_zmq_listener(sm)