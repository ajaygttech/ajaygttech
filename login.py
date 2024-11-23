import sys
import asyncio
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFrame, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt
from mainw import MainWindow  # Import your MainWindow class
from qasync import QEventLoop
from Connect import XTSConnect  # Import XTSConnect
import json
import subprocess


class LoginPage(QWidget):
    def __init__(self, server_url, stacked_widget):
        super().__init__()
        self.server_url = server_url
        self.stacked_widget = stacked_widget
       
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(600, 400)
        self.setWindowTitle("Login")

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        self.center_frame = QFrame()
        self.center_frame.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ccc; border-radius: 10px;")
        self.center_frame.setFixedSize(300, 200)

        self.frame_layout = QVBoxLayout()
        self.frame_layout.setAlignment(Qt.AlignCenter)

        self.label_user = QLabel("User Name:")
        self.label_user.setStyleSheet("font-size: 14px;")
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Enter your username")
        self.input_user.setStyleSheet("font-size: 14px; padding: 5px;")
        self.frame_layout.addWidget(self.label_user)
        self.frame_layout.addWidget(self.input_user)

        self.login_button = QPushButton("Login")
        self.login_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; padding: 10px;")
        self.login_button.clicked.connect(self.login)
        self.frame_layout.addWidget(self.login_button)

        self.center_frame.setLayout(self.frame_layout)
        self.layout.addWidget(self.center_frame)
        self.setLayout(self.layout)

    def login(self):
        user_name = self.input_user.text()

        if not user_name.strip():
            QMessageBox.warning(self, "Input Error", "User Name cannot be empty!")
            return

        try:
            # Make a POST request to the Flask server
            response = requests.post(f"{self.server_url}/login", data={"user_name": user_name})
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    # Extract tokens, IDs, and credentials
                    order_user_id = data["order_user_id"]
                    order_token = data["order_token"]
                    market_data_token = data["market_data_token"]
                    market_user_id = data["market_user_id"]
                    market_api_key = data["market_api_key"]
                    market_api_secret = data["market_api_secret"]

                    # Save credentials to a JSON file
                    self.save_credentials(order_user_id, order_token, market_data_token, market_user_id)

                    
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Login successful! Welcome {user_name}!\n\n"
                        f"Order User ID: {order_user_id}\n"
                        f"Market User ID: {market_user_id}",
                    )
                    # Start ordersbackend.py using subprocess
                    self.start_orders_backend(order_user_id, order_token)
                    # Load the main window and pass xt_market along with tokens and IDs
                    self.load_main_window(market_api_key,market_api_secret, order_user_id, order_token, market_data_token, market_user_id)
                else:
                    error_message = data.get("message", "Unknown error occurred")
                    QMessageBox.critical(self, "Login Failed", error_message)
            else:
                error_message = response.json().get("error", "Unknown error occurred")
                QMessageBox.critical(self, "Login Failed", error_message)
        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to server: {e}")
    def save_credentials(self, order_user_id, order_token, market_data_token, market_user_id):
        credentials = {
            "order_user_id": order_user_id,
            "order_token": order_token,
            "market_data_token": market_data_token,
            "market_user_id": market_user_id
        }
        try:
            with open("credentials.json", "w") as file:
                json.dump(credentials, file, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "File Error", f"Failed to save credentials: {e}")

    def start_orders_backend(self, order_user_id, order_token):
        """Starts the ordersbackend.py script using subprocess."""
        try:
            subprocess.Popen(
                [sys.executable, "ordersbackend.py", order_user_id, order_token],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start ordersbackend.py: {e}")

    def load_main_window(self, market_api_key,market_api_secret, order_user_id, order_token, market_data_token, market_user_id):
        # Pass xt_market and credentials to the main window
        self.main_window = MainWindow(market_api_key,market_api_secret, order_user_id, order_token, market_data_token, market_user_id)
        self.stacked_widget.addWidget(self.main_window)
        self.stacked_widget.setCurrentWidget(self.main_window)


class AppWindow(QMainWindow):
    def __init__(self, server_url):
        super().__init__()
        self.setWindowTitle("Application")
        self.setGeometry(100, 100, 800, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_page = LoginPage(server_url, self.stacked_widget)
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.setCurrentWidget(self.login_page)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)  # Integrate PyQt and asyncio event loops
    asyncio.set_event_loop(loop)

    flask_server_url = "http://127.0.0.1:5000"  # URL of the Flask server
    app_window = AppWindow(flask_server_url)
    app_window.show()

    with loop:
        loop.run_forever()
