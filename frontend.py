# frontend.py

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLineEdit, QLabel, QComboBox
from PyQt5.QtCore import QUrl
from PyQt5.QtWebSockets import QWebSocket
import json
import sys

class MarketDataWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Setup WebSocket
        self.socket = QWebSocket()
        self.socket.error.connect(self.on_error)
        self.socket.textMessageReceived.connect(self.on_message)

        # Connect to FastAPI WebSocket server
        self.socket.open(QUrl("ws://localhost:8000/ws"))

    def initUI(self):
        self.setWindowTitle('Market Data')
        self.setGeometry(100, 100, 600, 400)

        self.layout = QVBoxLayout()

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

        # Exchange selection
        self.exchange_label = QLabel("Select Exchange:", self)
        self.layout.addWidget(self.exchange_label)

        self.exchange_cb = QComboBox(self)
        self.exchange_cb.addItems(["NSE", "BSE", "MCX", "NSEFO"])  # Example exchanges
        self.layout.addWidget(self.exchange_cb)

        # Exchange Instrument ID input
        self.instrument_label = QLabel("Enter Exchange Instrument ID:", self)
        self.layout.addWidget(self.instrument_label)

        self.instrument_input = QLineEdit(self)
        self.layout.addWidget(self.instrument_input)

        # Subscribe button
        self.subscribe_button = QPushButton('Subscribe', self)
        self.subscribe_button.clicked.connect(self.send_subscription_request)
        self.layout.addWidget(self.subscribe_button)

        self.setLayout(self.layout)

    def on_message(self, message):
        # Handle incoming message from WebSocket
        print(f"Received WebSocket message: {message}")
        self.text_edit.append(f"Market Data: {message}")

    def on_error(self, error):
        print(f"WebSocket Error: {error}")

    def send_subscription_request(self):
        # Get the selected exchange and instrument ID
        exchange = self.exchange_cb.currentText()
        instrument_id = self.instrument_input.text()

        # Map exchanges to segment IDs (example mapping)
        exchange_segment_mapping = {
            "NSE": 1,
            "BSE": 2,
            "MCX": 3,
            "NSEFO": 4
        }

        # Get the segment ID from the selected exchange
        exchange_segment_id = exchange_segment_mapping.get(exchange, 1)  # Default to 1 if not found

        # Create a subscription request message
        instruments = [{'exchangeSegment': exchange_segment_id, 'exchangeInstrumentID': int(instrument_id)}]
        message = {
            "action": "subscribe",
            "instruments": instruments
        }

        # Send the subscription request to the backend
        print(f"Sending subscription request for instruments: {instruments}")
        self.socket.sendTextMessage(json.dumps(message))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MarketDataWindow()
    window.show()
    sys.exit(app.exec_())
