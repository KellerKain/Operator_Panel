from statemachine import StateChart, State
import zmq





class SystemStates(StateChart):

    #States
    Idle = State(initial=True)
    WearTest = State()
    LeakTest = State()
    TorqueTest = State()

    #Events
    start_wear = Idle.to(WearTest)
    start_leak = Idle.to(LeakTest)
    start_torque = Idle.to(TorqueTest)

    #Reset Transitions
    stop = WearTest.to(Idle) | LeakTest.to(Idle) | TorqueTest.to(Idle)


def on_enter_WearTest(self):
    print("[Backend] Entering Wear Test: Starting I2C polling thread...")

def on_exit_WearTest(self):
    print("[Backend] Exiting Wear Test: Safely stopping actuators...")

def run_backend_zmq_listener(state_machine):
  context = zmq.Context()
  socket = context.socket(zmq.REP)
  socket.bind("tcp://127.0.0.1:5555")

  while True:
    message = socket.recv_string()
    print(f"[ZMQ Received]: {message}")

    # Map received string commands to state machine events
    if hasattr(state_machine, message):
      event_method = getattr(state_machine, message)
      event_method()  # Trigger the transition
      socket.send_string(f"ACK: Switched to {state_machine.current_state.id}")
    else:
      socket.send_string(f"ERR: Unknown event '{message}'")

if __name__ == "__main__":
  run_backend_zmq_listener(SystemStates())