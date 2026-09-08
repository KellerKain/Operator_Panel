import sys
from PySide6.QtCore import QDateTime, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Operator Panel")
        self.showFullScreen()  # Set the window to fullscreen
        self.setStyleSheet("background-color: white;")

        # 1. Create central container and layouts
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_vbox = QVBoxLayout(central_widget)
        top_hbox = QHBoxLayout()

        # 2. Create the label for time and date
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #000000;"
        )

        # 3. Position label in top-right using spacers and layout alignment
        top_hbox.addStretch()  # Pushes the label to the far right
        top_hbox.addWidget(self.clock_label)
        main_vbox.addLayout(top_hbox)
        main_vbox.addStretch()  # Pushes top layout to the top of the window

        # 4. Set up QTimer to update time every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 1000 milliseconds = 1 second

        # Initial display setup
        self.update_time()

    def update_time(self):
        # Format current date and time
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd  hh:mm:ss AP")
        self.clock_label.setText(current_time)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
