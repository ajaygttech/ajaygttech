import sys
import json
import asyncio
import websockets
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal
from fetch import Application  # Import the Application class from fetch.py

class WebSocketClient(QThread):
    response_received = pyqtSignal(str)  # Signal to update UI with WebSocket messages
    
    def __init__(self, parent=None):
        super(WebSocketClient, self).__init__(parent)
        self.websocket = None
        self.loop = asyncio.new_event_loop()

    async def connect(self):
        try:
            # Connect to the WebSocket server
            async with websockets.connect("ws://localhost:8765") as websocket:
                self.websocket = websocket
                await self.listen_to_messages()
        except Exception as e:
            pass  # Ignore connection errors

    async def listen_to_messages(self):
        # Listen for messages from the WebSocket server
        async for message in self.websocket:
            self.response_received.emit(message)

    def send_subscription(self, exchange_segment, exchange_instrument_id):
        # Send a subscription request to the WebSocket server
        data = {
            'action': 'subscribe',
            'exchangeSegment': exchange_segment,
            'exchangeInstrumentID': exchange_instrument_id
        }
        asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(data)), self.loop)

    def run(self):
        # Start the WebSocket connection in the thread
        self.loop.run_until_complete(self.connect())

class MarketDataWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.websocket_thread = WebSocketClient()
        self.websocket_thread.response_received.connect(self.display_response)
        self.subscribed_instruments = {}  # Dictionary to store rows for each instrument

    def initUI(self):
        self.setWindowTitle("Market Data Subscription")
        self.setGeometry(300, 300, 1000, 600)  # Increase window size to accommodate more columns and the fetch layout

        # Main layout for the MarketDataWindow
        main_layout = QVBoxLayout()

        # Fetch layout (from fetch.py) will be embedded here
        self.fetch_widget = Application()
        self.fetch_widget.data_selected.connect(self.add_data_to_table)

        # Define new table headers
        column_headers = [
            "Action", "Exchange", "Series", "Name", "Expiration", "Strike Price", 
            "Option Type", "InstrumentID", "Lot Size", "Tick Size", 
            "Freeze Qty", "Price Band High", "Price Band Low", "CMP", "Lot", "Price", "Multiplier"
        ]

        # Table to display market data
        self.data_table = QTableWidget(0, len(column_headers))  # Start with 0 rows, and as many columns as headers
        self.data_table.setHorizontalHeaderLabels(column_headers)
        self.data_table.horizontalHeader().setStretchLastSection(True)

        # Add the fetch layout (from fetch.py) and the data table to the main layout
        main_layout.addWidget(self.fetch_widget)
        main_layout.addWidget(self.data_table)

        self.setLayout(main_layout)

        

    def add_data_to_table(self, data):
        """Method to add data to the table from the fetch layout."""
        row_position = self.data_table.rowCount()
        self.data_table.insertRow(row_position)
        self.data_table.setItem(row_position, 0, QTableWidgetItem(data['Action']))
        self.data_table.setItem(row_position, 1, QTableWidgetItem(data['Exchange Segment']))
        self.data_table.setItem(row_position, 2, QTableWidgetItem(data['Series']))
        self.data_table.setItem(row_position, 3, QTableWidgetItem(data['Name']))
        self.data_table.setItem(row_position, 4, QTableWidgetItem(data['Contract Expiration']))
        self.data_table.setItem(row_position, 5, QTableWidgetItem(data['Strike Price']))
        self.data_table.setItem(row_position, 6, QTableWidgetItem(data['Option Type']))
        self.data_table.setItem(row_position, 7, QTableWidgetItem(data['Exchange Instrument ID']))
        self.data_table.setItem(row_position, 8, QTableWidgetItem(str(data['Lot Size'])))
        self.data_table.setItem(row_position, 9, QTableWidgetItem(str(data['Tick Size'])))
        self.data_table.setItem(row_position, 10, QTableWidgetItem(str(data['Freeze Qty'])))
        self.data_table.setItem(row_position, 11, QTableWidgetItem(str(data['Price Band High'])))
        self.data_table.setItem(row_position, 12, QTableWidgetItem(str(data['Price Band Low'])))
        self.data_table.setItem(row_position, 13, QTableWidgetItem("--"))  # Placeholder for CMP (Last Traded Price)

        # Automatically subscribe after adding the data to the table
        exchange_segment = data['Exchange Segment']
        exchange_instrument_id = data['Exchange Instrument ID']
        segment_code = 1 if exchange_segment == "NSECM" else 2  # Adjust segment codes if needed
        self.websocket_thread.send_subscription(segment_code, int(exchange_instrument_id))

    def display_response(self, message):
        # Parse the message and extract the last traded price (CMP)
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])
                # Find the row with the matching instrument ID
                for row in range(self.data_table.rowCount()):
                    if self.data_table.item(row, 7).text() == instrument_id:
                        last_traded_price = message_data["Touchline"].get("LastTradedPrice", "0.0")
                        # Update the row with the last traded price (CMP)
                        self.data_table.setItem(row, 13, QTableWidgetItem(str(last_traded_price)))  # CMP
                        break
        except json.JSONDecodeError:
            pass  # Ignore JSON decode errors

    def start_websocket(self):
        # Start the WebSocket thread
        self.websocket_thread.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MarketDataWindow()
    window.show()

    # Start the WebSocket connection when the window opens
    window.start_websocket()

    sys.exit(app.exec_())
