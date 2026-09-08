import sys
from PySide6.QtWidgets import QApplication, QWidget

# 1. Initialize the application event loop
app = QApplication(sys.argv)

# 2. Create the main window widget
window = QWidget()
window.setWindowTitle("Operator Panel")
window.showFullScreen()  # Set the window to fullscreen
# 3. Render the window on screen
window.show()

# 4. Start the application loop and exit cleanly
sys.exit(app.exec())