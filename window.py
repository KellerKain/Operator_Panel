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


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Operator Panel")

        # 1. Main Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Background Content Area
        self.background_layout = QHBoxLayout(self.central_widget)
        self.background_layout.setContentsMargins(0, 0, 0, 0)

        bg_content = QLabel("Main Content / Dashboard View")
        bg_content.setAlignment(Qt.AlignCenter)
        bg_content.setStyleSheet("font-size: 24px; background-color: #ffffff;")
        self.background_layout.addWidget(bg_content)

        # 2. Sidebar Frame (Floating Overlay)
        self.sidebar_frame = QFrame(self.central_widget)
        self.sidebar_frame.setObjectName("SidebarFrame")
        self.sidebar_frame.setFixedWidth(220)
        self.sidebar_frame.setStyleSheet(
            """
            QFrame#SidebarFrame {
                background-color: #f8f9fa;
                border: none;
            }
        """
        )

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self.sidebar_frame)
        shadow.setBlurRadius(20)
        shadow.setXOffset(5)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.sidebar_frame.setGraphicsEffect(shadow)

        # Sidebar Layout
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)

        sidebar_layout.addStretch()

        btn_home = QPushButton("Tests")
        btn_settings = QPushButton("Settings")
        btn_history = QPushButton("History")
        sidebar_layout.addWidget(btn_home)
        sidebar_layout.addWidget(btn_history)
        sidebar_layout.addWidget(btn_settings)

        sidebar_layout.addStretch()

        # Clock Label
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #000000; background: transparent;"
        )
        sidebar_layout.addWidget(self.clock_label)

        # Timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        # Call showFullScreen after layout setup is finished
        self.showFullScreen()
        self.sidebar_frame.raise_()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if hasattr(self, "sidebar_frame"):
            # Measure full window height directly
            self.sidebar_frame.setGeometry(
                0, 0, self.sidebar_frame.width(), self.height()
            )

    def update_time(self):
        current_time = QDateTime.currentDateTime().toString(
            "hh:mm:ss AP\nyyyy-MM-dd"
        )
        self.clock_label.setText(current_time)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())