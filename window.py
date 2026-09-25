import sys
from PySide6.QtCore import QDateTime, QTimer, Qt
from PySide6.QtGui import QColor, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
import pyqtgraph as pg
import zmq


#Circular Red Stop Button Class
class StopButton(QPushButton):

  def __init__(self, parent=None, x=0, y=0, size=60):
    super().__init__("STOP", parent)
    self.setGeometry(x, y, size, size)
    self.setCursor(Qt.PointingHandCursor)

    # Circular red styling using border-radius
    self.setStyleSheet(f"""
            QPushButton {{
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #a71d2a;
                border-radius: {size // 2}px;
            }}
            QPushButton:hover {{
                background-color: #bd2130;
                border-color: #8b101c;
            }}
            QPushButton:pressed {{
                background-color: #7d101a;
            }}
        """)

    # Shadow effect
    shadow = QGraphicsDropShadowEffect(self)
    shadow.setBlurRadius(15)
    shadow.setXOffset(0)
    shadow.setYOffset(4)
    shadow.setColor(QColor(0, 0, 0, 100))
    self.setGraphicsEffect(shadow)


#Tests Window
class TestsWindow(QMainWindow):

  def __init__(self, on_test_start=None):
    super().__init__()
    self.on_test_start = on_test_start

    # Initialize ZeroMQ Client Socket (REQ/REP pattern)
    self.zmq_context = zmq.Context()
    self.zmq_socket = self.zmq_context.socket(zmq.REQ)
    self.zmq_socket.setsockopt(zmq.RCVTIMEO, 1000)
    self.zmq_socket.setsockopt(zmq.LINGER, 0)
    try:
      self.zmq_socket.connect("tcp://127.0.0.1:5555")
    except Exception as e:
      print(f"[ZMQ Error] Failed to connect: {e}")

    self.central_widget = QWidget()
    self.setCentralWidget(self.central_widget)
    self.setWindowTitle("Tests")
    self.resize(500, 700)

    # Sidebar Navigation Buttons
    Wear_btn = QPushButton("Wear Test")
    Torque_btn = QPushButton("Torque Test")
    leak_btn = QPushButton("Leak Rate Test")

    # Layout Setup
    main_layout = QHBoxLayout(self.central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # Sidebar Frame
    self.sidebar_frame = QFrame()
    self.sidebar_frame.setObjectName("SidebarFrame")

    sidebar_layout = QVBoxLayout(self.sidebar_frame)
    sidebar_layout.setContentsMargins(15, 15, 15, 15)
    sidebar_layout.addWidget(Wear_btn, alignment=Qt.AlignCenter)
    sidebar_layout.addWidget(Torque_btn, alignment=Qt.AlignCenter)
    sidebar_layout.addWidget(leak_btn, alignment=Qt.AlignCenter)
    sidebar_layout.addStretch()
    self.sidebar_frame.setFixedWidth(200)

    self.sidebar_frame.setStyleSheet("""
            QFrame#SidebarFrame {
                background-color: #f8f9fa;
                border: none;
            }
            QPushButton {
                min-width: 150px;
                padding: 10px;
                font-size: 14px;
            }
        """)

    shadow = QGraphicsDropShadowEffect(self.sidebar_frame)
    shadow.setBlurRadius(20)
    shadow.setXOffset(5)
    shadow.setYOffset(0)
    shadow.setColor(QColor(0, 0, 0, 80))
    self.sidebar_frame.setGraphicsEffect(shadow)

    # Stacked Widget Pages
    self.stacked_widget = QStackedWidget()

    # Wear page
    self.page_wear = QWidget()
    wear_layout = QVBoxLayout(self.page_wear)
    self.wear_cycles = WearCycles()
    wear_layout.addWidget(self.wear_cycles)

    # Wear Test Start Button
    start_wear_btn = QPushButton("Start Wear Test")
    start_wear_btn.setStyleSheet(
        "background-color: #808080; color: white; font-weight: bold;"
    )
    start_wear_btn.clicked.connect(
        lambda: self.send_zmq_command("start_wear", "Wear Test")
    )
    wear_layout.addStretch()
    wear_layout.addWidget(start_wear_btn)

    # Torque Page
    self.page_torque = QWidget()
    torque_layout = QVBoxLayout(self.page_torque)
    torque_layout.addWidget(
        QLabel(
            "Test settings for Torque page",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
    )

    # Torque Test Start Button
    start_torque_btn = QPushButton("Start Torque Test")
    start_torque_btn.setStyleSheet(
        "background-color: #808080; color: white; font-weight: bold;"
    )
    start_torque_btn.clicked.connect(
        lambda: self.send_zmq_command("start_torque", "Torque Test")
    )
    torque_layout.addStretch()
    torque_layout.addWidget(start_torque_btn)

    # Leak Page
    self.page_leak = QWidget()
    leak_layout = QVBoxLayout(self.page_leak)
    leak_layout.addWidget(
        QLabel(
            "Test settings for Leak page",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
    )

    # Leak Test Start Button
    start_leak_btn = QPushButton("Start Leak Test")
    start_leak_btn.setStyleSheet(
        "background-color: #808080; color: white; font-weight: bold;"
    )
    start_leak_btn.clicked.connect(
        lambda: self.send_zmq_command("start_leak", "Leak Test")
    )
    leak_layout.addStretch()
    leak_layout.addWidget(start_leak_btn)

    # Add pages to the stacked widget
    self.stacked_widget.addWidget(self.page_wear)  # index 0
    self.stacked_widget.addWidget(self.page_torque)  # index 1
    self.stacked_widget.addWidget(self.page_leak)  # index 2

    # Sidebar Navigation Logic
    Wear_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
    Torque_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
    leak_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))

    # Assemble Main Layout
    main_layout.addWidget(self.sidebar_frame)
    main_layout.addWidget(self.stacked_widget)

  # --- ZeroMQ Helper Method ---
  def send_zmq_command(self, command: str, display_name: str):
    """Sends a state transition event string to the backend state machine."""
    print(f"[Frontend] Sending command to backend: '{command}'")
    try:
      self.zmq_socket.send_string(command)
      reply = self.zmq_socket.recv_string()
      print(f"[Backend Reply]: {reply}")
      if self.on_test_start:
        self.on_test_start(display_name)
    except zmq.Again:
      print(
          "[ZMQ Warning] Backend response timed out. Is the backend running?"
      )
    except Exception as e:
      print(f"[ZMQ Error]: {e}")
    finally:
      self.close()

  def closeEvent(self, event):
    """Clean up ZeroMQ socket on window closure."""
    self.zmq_socket.close()
    self.zmq_context.term()
    super().closeEvent(event)


#Full MainWindow Class
class MainWindow(QMainWindow):

  def __init__(self):
    super().__init__()
    self.tests_window = None
    self.setWindowTitle("Operator Panel - Fixed Position Graph")

    #ZeroMQ Socket Setup for MainWindow (REQ pattern to send STOP command)
    self.zmq_context = zmq.Context()
    self.zmq_socket = self.zmq_context.socket(zmq.REQ)
    self.zmq_socket.setsockopt(zmq.RCVTIMEO, 1000)
    self.zmq_socket.setsockopt(zmq.LINGER, 0)
    try:
      self.zmq_socket.connect("tcp://127.0.0.1:5555")
    except Exception as e:
      print(f"[ZMQ Error] MainWindow failed to connect: {e}")

    pg.setConfigOption("background", "w")
    pg.setConfigOption("foreground", "k")

    #Main Central Widget
    self.central_widget = QWidget()
    self.setCentralWidget(self.central_widget)

    # Info Widgets
    self.test_info = CurrentTestInfo(
        "---",
        100,
        10000,
        parent=self.central_widget,
        x=800,
        y=120,
        width=220,
        height=120,
    )
    self.temp_info = TemperatureInfo(
        parent=self.central_widget, x=800, y=50, width=220, height=60
    )

    #Add Circular Red Stop Button
    # Positioned at x=880, y=260 (centered horizontally below CurrentTestInfo)
    self.stop_btn = StopButton(
        parent=self.central_widget, x=840, y=260, size=140
    )
    self.stop_btn.clicked.connect(self.stop_current_test)

    #Add PyQtGraph PlotWidget as direct child (No Layout)
    self.graph_widget = pg.PlotWidget(self.central_widget)
    self.graph_widget.setTitle(
        "Live System Telemetry", color="k", size="12pt"
    )
    self.graph_widget.showGrid(x=True, y=True, alpha=0.3)

    # Configurable plot line
    pen = pg.mkPen(color=(220, 50, 50), width=2)
    self.data_line = self.graph_widget.plot([], [], pen=pen)

    # Graph Positioning
    self.graph_x = 260
    self.graph_y = 50
    self.graph_width = 500
    self.graph_height = 350

    self.graph_widget.setGeometry(
        self.graph_x, self.graph_y, self.graph_width, self.graph_height
    )

    #Sidebar Setup
    self.sidebar_frame = QFrame(self.central_widget)
    self.sidebar_frame.setObjectName("SidebarFrame")
    self.sidebar_frame.setFixedWidth(220)
    self.sidebar_frame.setStyleSheet("""
            QFrame#SidebarFrame {
                background-color: #f8f9fa;
                border: none;
            }
            QPushButton {
                min-width: 150px;
                padding: 10px;
                font-size: 14px;
            }
        """)

    shadow = QGraphicsDropShadowEffect(self.sidebar_frame)
    shadow.setBlurRadius(20)
    shadow.setXOffset(5)
    shadow.setYOffset(0)
    shadow.setColor(QColor(0, 0, 0, 80))
    self.sidebar_frame.setGraphicsEffect(shadow)

    # Button Setup
    Home_btn = QPushButton("Home")
    Tests_btn = QPushButton("Tests")

    # Button Functionality
    Tests_btn.clicked.connect(self.open_tests_window)

    # Sidebar and button placement
    sidebar_layout = QVBoxLayout(self.sidebar_frame)
    sidebar_layout.setContentsMargins(15, 15, 15, 15)
    sidebar_layout.addStretch()
    sidebar_layout.addWidget(Home_btn, alignment=Qt.AlignCenter)
    sidebar_layout.addWidget(Tests_btn, alignment=Qt.AlignCenter)
    sidebar_layout.addWidget(
        QPushButton("Settings"), alignment=Qt.AlignCenter
    )
    sidebar_layout.addStretch()

    self.clock_label = QLabel()
    self.clock_label.setAlignment(Qt.AlignCenter)
    self.clock_label.setStyleSheet(
        "font-size: 14px; font-weight: bold; color: #000000;"
    )
    sidebar_layout.addWidget(self.clock_label, alignment=Qt.AlignCenter)
    sidebar_layout.addStretch()

    self.showFullScreen()

    # Keep sidebar rendered on top layer
    self.sidebar_frame.raise_()

  def stop_current_test(self):
    """Sends the 'stop' command to the backend ZMQ state machine and updates the UI info label."""
    print("[Frontend] Emergency Stop Pressed! Sending 'stop' to backend...")
    try:
      self.zmq_socket.send_string("stop")
      reply = self.zmq_socket.recv_string()
      print(f"[Backend Reply]: {reply}")

      # Update UI to reflect that test is idle / stopped
      self.test_info.update_test_info(test_name="Stopped")

    except zmq.Again:
      print(
          "[ZMQ Warning] Stop command timed out. Is backend running?"
      )
    except Exception as e:
      print(f"[ZMQ Error]: {e}")

  def set_graph_geometry(self, x, y, width, height):
    """Helper function to update graph position and size dynamically via code."""
    self.graph_x = x
    self.graph_y = y
    self.graph_width = width
    self.graph_height = height
    self.graph_widget.setGeometry(x, y, width, height)

  def resizeEvent(self, event: QResizeEvent):
    super().resizeEvent(event)
    if hasattr(self, "sidebar_frame"):
      self.sidebar_frame.setGeometry(
          0, 0, self.sidebar_frame.width(), self.height()
      )

  def open_tests_window(self):
    if self.tests_window is None:
      self.tests_window = TestsWindow(on_test_start=self.handle_test_start)

    self.tests_window.show()
    self.tests_window.activateWindow()

  def handle_test_start(self, test_name):
    # Update label on MainWindow UI
    self.test_info.update_test_info(test_name=test_name)

  def closeEvent(self, event):
    """Clean up ZMQ connection on app exit."""
    self.zmq_socket.close()
    self.zmq_context.term()
    super().closeEvent(event)


#Helper Component Classes
class WearCycles(QWidget):

  def __init__(self):
    super().__init__()
    layout = QVBoxLayout()

    self.cycle_number = QSpinBox()
    self.label = QLabel("Number of Cycles:")

    self.cycle_number.setRange(0, 1_000_000)
    self.cycle_number.setValue(10_000)
    self.cycle_number.setSingleStep(500)

    layout.addWidget(self.label)
    layout.addWidget(self.cycle_number)
    self.setLayout(layout)


class CurrentTestInfo(QFrame):

  def __init__(
      self,
      current_test_name,
      cycle_number_live,
      cycle_number_total,
      parent=None,
      x=0,
      y=0,
      width=200,
      height=100,
  ):
    super().__init__(parent)
    self.setGeometry(x, y, width, height)

    layout = QVBoxLayout()

    self.current_test = QLabel(f"Current Test: {current_test_name}")
    self.current_cycle_num = QLabel(
        f"Current Cycle Number: \n {cycle_number_live}"
    )
    self.total_cycles = QLabel(f"Total Cycle Number: \n {cycle_number_total}")

    layout.addWidget(self.current_test)
    layout.addWidget(self.current_cycle_num)
    layout.addWidget(self.total_cycles)

    self.setLayout(layout)

    self.setFrameShape(QFrame.Box)
    self.setLineWidth(2)
    self.setStyleSheet("""
            CurrentTestInfo {
                background-color: #000000;
                border: 2px solid #333333;
                border-radius: 6px;
            }
            QLabel {
                color: #ffffff;
            }
        """)

  def update_test_info(
      self, test_name=None, cycle_live=None, cycle_total=None
  ):
    if test_name is not None:
      self.current_test.setText(f"Current Test: {test_name}")
    if cycle_live is not None:
      self.current_cycle_num.setText(f"Current Cycle Number:\n{cycle_live}")
    if cycle_total is not None:
      self.total_cycles.setText(f"Total Cycle Number:\n{cycle_total}")


class TemperatureInfo(QFrame):

  def __init__(self, parent=None, temp=0, x=200, y=0, width=200, height=100):
    super().__init__(parent)
    self.setGeometry(x, y, width, height)

    layout = QVBoxLayout()

    self.temperature_label = QLabel(f"Temperature: {self.find_temp(temp)} C")

    layout.addWidget(self.temperature_label)

    self.setLayout(layout)

    self.setFrameShape(QFrame.Box)
    self.setLineWidth(2)
    self.setStyleSheet("""
            TemperatureInfo {
                background-color: #000000;
                border: 2px solid #333333;
                border-radius: 6px;
            }
            QLabel {
                color: #ffffff;
            }
        """)

  def find_temp(self, sensor_input):
    if sensor_input == 0:
      return "--"
    else:
      return sensor_input


if __name__ == "__main__":
  app = QApplication(sys.argv)
  window = MainWindow()
  window.show()
  sys.exit(app.exec())