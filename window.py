import sys
from PySide6.QtCore import QDateTime, QTimer, Qt
from PySide6.QtGui import QColor, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import pyqtgraph as pg

#Logic for the tests window button
class TestsWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.setWindowTitle("Tests")
        self.resize(500, 700)

        # 1. Create a main horizontal layout for central_widget
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 2. Create the sidebar frame
        self.sidebar_frame = QFrame()  # No need to manually pass parent when adding to layout
        self.sidebar_frame.setObjectName("SidebarFrame")

        # Note: Increase width or decrease button min-width to prevent overflow
        self.sidebar_frame.setFixedWidth(150)

        self.sidebar_frame.setStyleSheet(
            """
            QFrame#SidebarFrame {
                background-color: #f8f9fa;
                border: none;
            }
            QPushButton {
                min-width: 150px;
                padding: 10px;
                font-size: 14px;
            }
        """
        )

        shadow = QGraphicsDropShadowEffect(self.sidebar_frame)
        shadow.setBlurRadius(20)
        shadow.setXOffset(5)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.sidebar_frame.setGraphicsEffect(shadow)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.addStretch()

        # 3. Add sidebar frame and a stretch area for main content to main_layout
        main_layout.addWidget(self.sidebar_frame)
        main_layout.addStretch()  # Pushes sidebar to the left and takes remaining space


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        #Different the Tests_Window
        self.tests_window = None
        self.setWindowTitle("Operator Panel - Fixed Position Graph")

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        # 1. Main Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 2. Add PyQtGraph PlotWidget as direct child (No Layout)
        self.graph_widget = pg.PlotWidget(self.central_widget)
        self.graph_widget.setTitle("Live System Telemetry", color="k", size="12pt")
        self.graph_widget.showGrid(x=True, y=True, alpha=0.3)

        # Configurable plot line
        pen = pg.mkPen(color=(220, 50, 50), width=2)
        self.data_line = self.graph_widget.plot([], [], pen=pen)

        #Graph Positioning
        self.graph_x = 260  # Horizontal offset from left edge
        self.graph_y = 50  # Vertical offset from top edge
        self.graph_width = 500  # Graph width in pixels
        self.graph_height = 350  # Graph height in pixels

        # Apply positioning and sizing coordinates
        self.graph_widget.setGeometry(
            self.graph_x, self.graph_y, self.graph_width, self.graph_height
        )
        # =========================================================

        # 3. Sidebar Setup
        self.sidebar_frame = QFrame(self.central_widget)
        self.sidebar_frame.setObjectName("SidebarFrame")
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_frame.setStyleSheet(
            """
            QFrame#SidebarFrame {
                background-color: #f8f9fa;
                border: none;
            }
            QPushButton {
                min-width: 150px;
                padding: 10px;
                font-size: 14px;
            }
        """
        )

        shadow = QGraphicsDropShadowEffect(self.sidebar_frame)
        shadow.setBlurRadius(20)
        shadow.setXOffset(5)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.sidebar_frame.setGraphicsEffect(shadow)

        #Button Setup
        Home_btn = QPushButton("Home")
        Tests_btn = QPushButton("Tests")


        #Button Functionality
        Tests_btn.clicked.connect(self.open_tests_window)

        #Sidebar and button placement
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
        self.tests_window.activateWindow()  # Bring window to front if already openHome_btn

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())