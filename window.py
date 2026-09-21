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


# Logic for the tests window button
class TestsWindow(QMainWindow):

  def __init__(self):
    super().__init__()

    self.central_widget = QWidget()
    self.setCentralWidget(self.central_widget)
    self.setWindowTitle("Tests")
    self.resize(500, 700)

    # Creates button elements for the Various tests
    Wear_btn = QPushButton("Wear Test")
    Torque_btn = QPushButton("Torque Test")
    leak_btn = QPushButton("Leak Rate Test")

    # Creates a main horizontal layout for central_widget
    main_layout = QHBoxLayout(self.central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # Creates the sidebar frame
    self.sidebar_frame = QFrame()
    self.sidebar_frame.setObjectName("SidebarFrame")

    # Creates Buttons on Sidebar
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

    # Page Creation for Tests window
    self.stacked_widget = QStackedWidget()
    # Wear Page
    self.page_wear = QWidget()
    wear_layout = QVBoxLayout(self.page_wear)
    self.wear_cycles = WearCycles()
    wear_layout.addWidget(self.wear_cycles)
    wear_layout.addStretch()
    # Torque Page
    self.page_torque = QWidget()
    torque_layout = QVBoxLayout(self.page_torque)
    torque_layout.addWidget(
        QLabel(
            "test Label for torque page", alignment=Qt.AlignmentFlag.AlignCenter
        )
    )

    # Add pages to the stack
    self.stacked_widget.addWidget(self.page_wear)  # index 0
    self.stacked_widget.addWidget(self.page_torque)  # index 1

    # Button Logic
    Wear_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
    Torque_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

    # Makes Layouts Visible
    main_layout.addWidget(self.sidebar_frame)
    main_layout.addWidget(self.stacked_widget)
    main_layout.addStretch()


class MainWindow(QMainWindow):

  def __init__(self):
    super().__init__()
    self.tests_window = None
    self.setWindowTitle("Operator Panel - Fixed Position Graph")

    pg.setConfigOption("background", "w")
    pg.setConfigOption("foreground", "k")

    # 1. Main Central Widget
    self.central_widget = QWidget()
    self.setCentralWidget(self.central_widget)

    # --- CHANGED: Instantiation & Positioning of CurrentTestInfo ---
    self.test_info = CurrentTestInfo(
        100, 10000, parent=self.central_widget, x=260, y=420, width=220, height=120
    )

    # 2. Add PyQtGraph PlotWidget as direct child (No Layout)
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

    # 3. Sidebar Setup
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
      self.tests_window = TestsWindow()

    self.tests_window.show()
    self.tests_window.activateWindow()


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


# Change QWidget to QFrame in the class definition
class CurrentTestInfo(QFrame):

  def __init__(
      self,
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

    self.current_cycle_num = QLabel(
        f"Current Cycle Number: \n {cycle_number_live}"
    )
    self.total_cycles = QLabel(f"Total Cycle Number: \n {cycle_number_total}")

    layout.addWidget(self.current_cycle_num)
    layout.addWidget(self.total_cycles)

    self.setLayout(layout)

    # Apply frame border style directly using QFrame attributes or CSS
    self.setFrameShape(QFrame.Box)
    self.setLineWidth(2)
    self.setStyleSheet("""
            CurrentTestInfo {
                background-color: #000000;
                border: 2px solid #333333;
                border-radius: 6px;
            }
        """)

if __name__ == "__main__":
  app = QApplication(sys.argv)
  window = MainWindow()
  window.show()
  sys.exit(app.exec())