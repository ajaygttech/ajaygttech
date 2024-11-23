import json
import asyncio
import websockets
from PyQt5.QtWidgets import QTableWidget, QVBoxLayout, QWidget, QTableWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal


class WebSocketClient(QThread):
    response_received = pyqtSignal(str)  # Signal to update the table with WebSocket messages

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
            print(f"Error connecting to WebSocket: {e}")

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
        # Set up the event loop and start the WebSocket connection
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())


class RightTable(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_table()

        # Initialize WebSocket client
        self.websocket_thread = WebSocketClient()
        self.websocket_thread.response_received.connect(self.display_response)
        self.websocket_thread.start()  # Start the WebSocket connection

        # Set to keep track of subscribed instrument IDs
        self.subscribed_instruments = set()

        # Dictionary to keep track of row positions for each instrument
        self.instrument_row_mapping = {}

    def setup_table(self):
        """Set up the table layout."""
        table_layout = QVBoxLayout()

        # Create the table widget
        self.right_table = QTableWidget()
        self.right_table.setColumnCount(17)  # Set the number of columns
        column_headers = [
            "Action", "Exchange", "Series", "Name", "Expiration", "Strike Price",
            "Option Type", "InstrumentID", "Lot Size", "Tick Size",
            "Freeze Qty", "Price Band High", "Price Band Low", "CMP", "Lot", "Price", "Multiplier"
        ]
        self.right_table.setHorizontalHeaderLabels(column_headers)

        # Add the table to the layout
        table_layout.addWidget(self.right_table)
        self.setLayout(table_layout)

    def clear_table(self):
        """Clear the table contents."""
        self.right_table.clearContents()
        self.right_table.setRowCount(0)

    def add_data(self, table_data):
        """Add data to the table and send subscription requests if needed."""
        self.clear_table()  # Clear the table before adding new data

        for row_data in table_data:
            row_position = self.right_table.rowCount()
            self.right_table.insertRow(row_position)
            exchange_instrument_id = row_data[7]  # Assuming InstrumentID is at index 7

            # Insert the row data into the table
            for col, value in enumerate(row_data):
                self.right_table.setItem(row_position, col, QTableWidgetItem(value))

            # Track the row for the instrument to update CMP and Price later
            self.instrument_row_mapping[exchange_instrument_id] = row_position

            # Send subscription request only if the instrument isn't already subscribed
            if exchange_instrument_id not in self.subscribed_instruments:
                exchange_segment = row_data[1]  # Assuming Exchange Segment is at index 1
                segment_code = 1 if exchange_segment == "NSECM" else 2  # Adjust segment codes as needed
                self.websocket_thread.send_subscription(segment_code, int(exchange_instrument_id))

                # Mark this instrument as subscribed
                self.subscribed_instruments.add(exchange_instrument_id)

    def display_response(self, message):
        """Update the CMP and Last Traded Price (Price) based on WebSocket responses."""
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])
                bid_price = message_data["Touchline"]["BidInfo"].get("Price", "0.0")
                ask_price = message_data["Touchline"]["AskInfo"].get("Price", "0.0")
                last_traded_price = message_data["Touchline"].get("LastTradedPrice", "0.0")

                # Find the row corresponding to the instrument ID
                if instrument_id in self.instrument_row_mapping:
                    row = self.instrument_row_mapping[instrument_id]
                    action = self.right_table.item(row, 0).text()  # Get the action (Buy/Sell)

                    # Update the CMP (Column 13) based on Buy or Sell action
                    if action == "Buy":
                        self.right_table.setItem(row, 13, QTableWidgetItem(str(ask_price)))  # Set Ask Price as CMP
                    elif action == "Sell":
                        self.right_table.setItem(row, 13, QTableWidgetItem(str(bid_price)))  # Set Bid Price as CMP

                    # Update the Last Traded Price (Column 15)
                    self.right_table.setItem(row, 15, QTableWidgetItem(str(last_traded_price)))
        except json.JSONDecodeError:
            pass  # Ignore JSON decode errors
