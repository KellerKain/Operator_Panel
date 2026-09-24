import json
from time import sleep
from statemachine import State, StateChart
import zmq

#Mock GPIO setup for non-Pi development vs Live Raspberry Pi 5
try:
  from gpiozero import OutputDevice

  pin17 = OutputDevice(17, initial_value=False)
  pin22 = OutputDevice(22, initial_value=False)
  pin27 = OutputDevice(27, initial_value=False)
  print("[HW Info] Running on Raspberry Pi 5 hardware GPIO.")
except Exception as e:
  print(f"[HW Warning] GPIO unavailable ({e}). Using Dummy Mock Pins.")


  class DummyPin:

    def __init__(self, pin_num):
      self.pin_num = pin_num

    def off(self):
      print(f"[Mock Pin {self.pin_num}] State set to LOW / Ground (0V)")

    def on(self):
      print(f"[Mock Pin {self.pin_num}] State set to HIGH (3.3V)")


  pin17 = DummyPin(17)
  pin22 = DummyPin(22)
  pin27 = DummyPin(27)


#State Machine Definitions
class SystemStates(StateChart):

  # States
  Idle = State(initial=True)
  WearTest = State()
  LeakTest = State()
  TorqueTest = State()

  # Transitions
  start_wear = Idle.to(WearTest)
  start_leak = Idle.to(LeakTest)
  start_torque = Idle.to(TorqueTest)

  # Reset/Stop Transitions (Return to Idle from any active state)
  stop = WearTest.to(Idle) | LeakTest.to(Idle) | TorqueTest.to(Idle)

  #Idle Handler
  def on_enter_Idle(self):
    print("[Backend] Entered IDLE state. Safely driving all GPIO pins LOW.")
    pin17.off()
    pin22.off()
    pin27.off()

  #Wear Handler
  def on_enter_WearTest(self):
    print("[Backend] Starting Wear Test...")
    # Example: Pull pins down or set initial relay outputs
    pin17.off()
    pin22.off()

  def on_exit_WearTest(self):
    print("[Backend] Exiting Wear Test: Shutting down Wear hardware...")
    pin17.off()
    pin22.off()

  #Torque Handler
  def on_enter_TorqueTest(self):
    print("[Backend] Starting Torque Test...")
    pin27.off()

  def on_exit_TorqueTest(self):
    print("[Backend] Exiting Torque Test...")
    pin27.off()

  #Leak Rate Handler
  def on_enter_LeakTest(self):
    print("[Backend] Starting Leak Rate Test...")

  def on_exit_LeakTest(self):
    print("[Backend] Exiting Leak Rate Test...")


# ZMQ Server Listener Loop
def run_backend_zmq_listener(state_machine):
  context = zmq.Context()
  socket = context.socket(zmq.REP)
  socket.bind("tcp://127.0.0.1:5555")
  print("[Backend] ZeroMQ REP Server online on tcp://127.0.0.1:5555")

  while True:
    try:
      raw_message = socket.recv_string()
      print(f"[ZMQ Received]: {raw_message}")

      # Parse incoming string or JSON command
      command = raw_message
      payload = {}
      if raw_message.startswith("{"):
        payload = json.loads(raw_message)
        command = payload.get("command", "")

      # Execute transition if valid
      if hasattr(state_machine, command):
        event_method = getattr(state_machine, command)
        event_method()  # Triggers the state transition & lifecycle callbacks

        reply = f"ACK: State is now '{state_machine.current_state_value}'"
        socket.send_string(reply)
      else:
        socket.send_string(f"ERR: Command '{command}' not recognized.")

    except Exception as e:
      print(f"[ZMQ Server Error]: {e}")
      socket.send_string(f"ERR: Internal exception - {e}")


if __name__ == "__main__":
  sm = SystemStates()
  run_backend_zmq_listener(sm)