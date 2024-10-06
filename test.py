from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
from Connect import XTSConnect
from MarketDataSocketClient import MDSocket_io
import sys

# MarketData API Credentials
API_KEY = "145c98468edda965f03394"
API_SECRET = "Brqk551$wa"
source = "WEBAPI"

# Initialise
xt = XTSConnect(API_KEY, API_SECRET, source)

# Login for authorization token
response = xt.marketdata_login()

# Store the token and userid
set_marketDataToken = response['result']['token']
set_muserID = response['result']['userID']
print("Login: ", response)

# Instruments for subscribing
Instruments = [
    {'exchangeSegment': 1, 'exchangeInstrumentID': 26000}
]

class MarketDataThread(QThread):
    new_message = pyqtSignal(str)

    def run(self):
        # Connecting to Marketdata socket
        soc = MDSocket_io(set_marketDataToken, set_muserID)

        # Callback for connection
        def on_connect():
            """Connect from the socket."""
            print('Market Data Socket connected successfully!')

            # Subscribe to instruments
            print('Sending subscription request for Instruments - \n' + str(Instruments))
            response = xt.send_subscription(Instruments, 1501)
            print('Sent Subscription request!')
            print("Subscription response: ", response)

        # Callback on receiving message
        def on_message(data):
            self.new_message.emit(f'I received a message! {data}')

        # Callback for message code 1501 FULL
        def on_message1501_json_full(data):
            self.new_message.emit(f'I received a 1501 Touchline message! {data}')

        # Callback for disconnection
        def on_disconnect():
            print('Market Data Socket disconnected!')

        # Callback for error
        def on_error(data):
            """Error from the socket."""
            print('Market Data Error', data)

        # Assign the callbacks.
        soc.on_connect = on_connect
        soc.on_message = on_message
        soc.on_message1501_json_full = on_message1501_json_full
        soc.on_error = on_error

        # Event listener
        el = soc.get_emitter()
        el.on('connect', on_connect)
        el.on('1501-json-full', on_message1501_json_full)

        # Infinite loop on the main thread. Nothing after this will run.
        # You have to use the pre-defined callbacks to manage subscriptions.
        soc.connect()

class MarketDataWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Start market data thread
        self.market_data_thread = MarketDataThread()
        self.market_data_thread.new_message.connect(self.append_message)
        self.market_data_thread.start()

    def initUI(self):
        self.setWindowTitle('Market Data')
        self.setGeometry(100, 100, 600, 400)

        self.layout = QVBoxLayout()

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

        self.setLayout(self.layout)

    def append_message(self, message):
        self.text_edit.append(message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MarketDataWindow()
    window.show()
    sys.exit(app.exec_())
