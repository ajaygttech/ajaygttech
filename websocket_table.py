# websocket_table.py
import sys
import json
import asyncio
import websockets
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import QThread, pyqtSignal

class WebSocketThread(QThread):
    message_received = pyqtSignal(str)

    def __init__(self, uri):
        super().__init__()
        self.uri = uri

    async def connect_to_websocket(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                self.message_received.emit("Connected to WebSocket server")
                while True:
                    try:
                        message = await websocket.recv()
                        self.message_received.emit(message)
                    except websockets.ConnectionClosed:
                        self.message_received.emit("WebSocket connection closed")
                        break
        except Exception as e:
            self.message_received.emit(f"WebSocket error: {str(e)}")

    def run(self):
        asyncio.run(self.connect_to_websocket())

class WebSocketClient(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the PyQt5 window
        self.setWindowTitle("WebSocket Client - Order Data")
        self.setGeometry(100, 100, 1200, 500)  # Adjusted for more columns

        # Create a layout and a table to display WebSocket messages as rows
        self.layout = QVBoxLayout()

        # Define the column headers
        self.headers = [
            "ClientID", "ExchangeSegment", "TradingSymbol", "OrderSide", "OrderType", "ProductType", 
            "OrderQuantity", "OrderPrice", "OrderStatus", "AppOrderID", "GeneratedBy", 
            "OrderCategoryType", "OrderDisclosedQuantity", "OrderGeneratedDateTime", 
            "ExchangeTransactTime", "TimeInForce", "CancelRejectReason", "OrderUniqueIdentifier"
        ]

        # Create the table and set headers
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)  # Adjust column width to fit content
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)

        # Initialize the WebSocket thread and start it
        self.websocket_thread = WebSocketThread("ws://localhost:8765")
        self.websocket_thread.message_received.connect(self.on_message_received)
        self.websocket_thread.start()

    def extract_json(self, message):
        """Extract JSON part from the WebSocket message."""
        json_start = message.find('{')
        if json_start != -1:
            return message[json_start:].strip()  # Return only the JSON part
        return None

    def on_message_received(self, message):
        """Handle messages received from the WebSocket and display them in the table."""
        print(f"Received message: {message}")  # Debugging: print the message

        # Extract the JSON part from the message
        json_message = self.extract_json(message)
        if json_message:
            try:
                # Attempt to parse the message as JSON
                data = json.loads(json_message)
                if isinstance(data, dict):  # Check if the data is a dictionary
                    # Skip the order if the OrderStatus is "PendingNew"
                    if data.get("OrderStatus") == "PendingNew":
                        print(f"Skipping order with status PendingNew: {data['AppOrderID']}")
                        return

                    # Insert a new row in the table
                    row_position = self.table.rowCount()
                    self.table.insertRow(row_position)

                    # Populate the row with relevant data
                    column_data = [
                        data.get("ClientID", "N/A"),
                        data.get("ExchangeSegment", "N/A"),
                        data.get("TradingSymbol", "N/A"),
                        data.get("OrderSide", "N/A"),
                        data.get("OrderType", "N/A"),
                        data.get("ProductType", "N/A"),
                        str(data.get("OrderQuantity", "N/A")),
                        str(data.get("OrderPrice", "N/A")),
                        data.get("OrderStatus", "N/A"),
                        str(data.get("AppOrderID", "N/A")),
                        data.get("GeneratedBy", "N/A"),
                        data.get("OrderCategoryType", "N/A"),
                        str(data.get("OrderDisclosedQuantity", "N/A")),
                        data.get("OrderGeneratedDateTime", "N/A"),
                        data.get("ExchangeTransactTime", "N/A"),
                        data.get("TimeInForce", "N/A"),
                        data.get("CancelRejectReason", "N/A"),
                        data.get("OrderUniqueIdentifier", "N/A")
                    ]

                    # Add the data into the respective columns
                    for column, value in enumerate(column_data):
                        self.table.setItem(row_position, column, QTableWidgetItem(value))

                    # Ensure the table updates immediately
                    self.table.repaint()

            except json.JSONDecodeError:
                print("Failed to decode JSON:", json_message)
