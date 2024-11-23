import sys
import asyncio
import json
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QApplication, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QCheckBox, QComboBox, QLabel
)
from PyQt5.QtCore import QThread, pyqtSignal
from shared_resources import subscribed_instruments  # Import shared resources

try:
    import websockets
except ImportError:
    print("Please install the websockets library using `pip install websockets`.")
    sys.exit(1)

# WebSocket client class
class ResearchAlgo(QThread):
    message_received = pyqtSignal(str)

    def __init__(self, uri):
        super().__init__()
        self.uri = uri

    async def listen(self):
        """Connect to WebSocket server and listen for messages."""
        try:
            async with websockets.connect(self.uri) as websocket:
                while True:
                    message = await websocket.recv()
                    self.message_received.emit(message)
        except Exception as e:
            print(f"Error in WebSocket connection: {e}")

    def run(self):
        """Start the WebSocket client in a separate thread."""
        asyncio.run(self.listen())

# Main UI class
class AlgoTab(QWidget):
    subscribe_request = pyqtSignal(str, str)

    SEGMENT_MAP = {"1": "NSECM", "2": "NSEFO"}
    SEGMENT_CODE_MAP = {v: k for k, v in SEGMENT_MAP.items()}

    def __init__(self, call_client):
        super().__init__()
        self.client = call_client
        self.automatic_mode = False
        self.selected_call_type = "All"
        self.selected_exchange_segment = "Both"
        self.selected_order_side = "Both"
        self.selected_series = "All"
        self.init_ui()
        self.client.message_received.connect(self.display_message)

    def init_ui(self):
        """Initialize the UI components for displaying WebSocket messages."""
        main_layout = QVBoxLayout()

        # Manual/Automatic Mode Toggle
        mode_switch_layout = QHBoxLayout()
        
        # Manual Mode Checkbox (default selected)
        self.manual_mode_switch = QCheckBox("Manual Mode")
        self.manual_mode_switch.setChecked(True)
        self.manual_mode_switch.stateChanged.connect(self.toggle_manual_mode)
        mode_switch_layout.addWidget(self.manual_mode_switch)

        # Automatic Mode Checkbox
        self.automatic_mode_switch = QCheckBox("Automatic Mode")
        self.automatic_mode_switch.stateChanged.connect(self.toggle_automatic_mode)
        mode_switch_layout.addWidget(self.automatic_mode_switch)

        # Checkboxes and dropdowns for filters
        self.call_type_checkbox = QCheckBox("Call Type")
        self.call_type_checkbox.stateChanged.connect(lambda: self.toggle_dropdown(self.call_type_selector, self.call_type_checkbox))
        mode_switch_layout.addWidget(self.call_type_checkbox)
        
        self.call_type_selector = QComboBox()
        self.call_type_selector.addItems(["All", "Delivery", "Intraday", "BTST", "Positional"])
        self.call_type_selector.currentTextChanged.connect(self.update_call_type)
        mode_switch_layout.addWidget(self.call_type_selector)

        self.exchange_segment_checkbox = QCheckBox("Exchange Segment")
        self.exchange_segment_checkbox.stateChanged.connect(lambda: self.toggle_dropdown(self.exchange_segment_selector, self.exchange_segment_checkbox))
        mode_switch_layout.addWidget(self.exchange_segment_checkbox)

        self.exchange_segment_selector = QComboBox()
        self.exchange_segment_selector.addItems(["Both", "NSECM", "NSEFO"])
        self.exchange_segment_selector.currentTextChanged.connect(self.update_exchange_segment)
        mode_switch_layout.addWidget(self.exchange_segment_selector)

        self.order_side_checkbox = QCheckBox("Order Side")
        self.order_side_checkbox.stateChanged.connect(lambda: self.toggle_dropdown(self.order_side_selector, self.order_side_checkbox))
        mode_switch_layout.addWidget(self.order_side_checkbox)

        self.order_side_selector = QComboBox()
        self.order_side_selector.addItems(["Both", "BUY", "SELL"])
        self.order_side_selector.currentTextChanged.connect(self.update_order_side)
        mode_switch_layout.addWidget(self.order_side_selector)

        self.series_checkbox = QCheckBox("Series")
        self.series_checkbox.stateChanged.connect(lambda: self.toggle_dropdown(self.series_selector, self.series_checkbox))
        mode_switch_layout.addWidget(self.series_checkbox)

        self.series_selector = QComboBox()
        self.series_selector.addItems(["All", "FUTIDX", "FUTSTK", "OPTIDX", "OPTSTK", "EQ", "BE"])
        self.series_selector.currentTextChanged.connect(self.update_series)
        mode_switch_layout.addWidget(self.series_selector)

        main_layout.addLayout(mode_switch_layout)

        # Table Setup
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(23)
        self.price_table.setHorizontalHeaderLabels([
            "Strategy Name", "Call Type", "Trading Symbol", "Exchange Segment", "Product Type",
            "Order Type", "Order Side", "Time In Force", "Exchange Instrument ID",
            "Order Quantity", "Limit Price", "Stop Price", "Target Price", "LTP",
            "MTM", "Order Status", "Trade Status", "Stoploss Status", "Place Order", "OrderID",
            "Buy Price", "Sell Price", "Trade History"  # Added Trade History column
        ])
        
        # Hide specific columns
        self.price_table.setColumnHidden(4, True)
        self.price_table.setColumnHidden(5, True)
        self.price_table.setColumnHidden(7, True)
        self.price_table.setColumnHidden(8, True)

        # Enable row selection and allow user to adjust column widths
        self.price_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.price_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        main_layout.addWidget(self.price_table)
        self.setLayout(main_layout)
        self.setWindowTitle("Algo Trading - Message Display")

        # Initially set all selectors as disabled because Manual Mode is selected by default
        self.enable_selectors(False)

    def toggle_manual_mode(self):
        """Activate Manual Mode, disable Automatic Mode, and disable all selectors."""
        if self.manual_mode_switch.isChecked():
            self.automatic_mode_switch.setChecked(False)
            self.automatic_mode = False
            self.enable_selectors(False)

    def toggle_automatic_mode(self):
        """Activate Automatic Mode, disable Manual Mode, and enable all filter checkboxes."""
        if self.automatic_mode_switch.isChecked():
            self.manual_mode_switch.setChecked(False)
            self.automatic_mode = True
            self.call_type_checkbox.setEnabled(True)
            self.exchange_segment_checkbox.setEnabled(True)
            self.order_side_checkbox.setEnabled(True)
            self.series_checkbox.setEnabled(True)

            # Enable dropdowns based on checkbox state
            self.toggle_dropdown(self.call_type_selector, self.call_type_checkbox)
            self.toggle_dropdown(self.exchange_segment_selector, self.exchange_segment_checkbox)
            self.toggle_dropdown(self.order_side_selector, self.order_side_checkbox)
            self.toggle_dropdown(self.series_selector, self.series_checkbox)
        else:
            # If Automatic Mode is unchecked, disable all selectors and checkboxes
            self.enable_selectors(False)

    def enable_selectors(self, enabled):
        """Enable or disable all selectors and checkboxes."""
        self.call_type_checkbox.setEnabled(enabled)
        self.exchange_segment_checkbox.setEnabled(enabled)
        self.order_side_checkbox.setEnabled(enabled)
        self.series_checkbox.setEnabled(enabled)
        
        # Ensure dropdowns are also disabled if selectors are disabled
        self.call_type_selector.setEnabled(False)
        self.exchange_segment_selector.setEnabled(False)
        self.order_side_selector.setEnabled(False)
        self.series_selector.setEnabled(False)

    def toggle_dropdown(self, dropdown, checkbox):
        """Enable or disable a dropdown based on the associated checkbox."""
        dropdown.setEnabled(checkbox.isChecked())

    def update_call_type(self, call_type):
        """Update the selected call type for automatic mode."""
        self.selected_call_type = call_type
        print("Selected call type:", self.selected_call_type)

    def update_exchange_segment(self, exchange_segment):
        """Update the selected exchange segment for automatic mode."""
        self.selected_exchange_segment = exchange_segment
        print("Selected exchange segment:", self.selected_exchange_segment)

    def update_order_side(self, order_side):
        """Update the selected order side for automatic mode."""
        self.selected_order_side = order_side
        print("Selected order side:", self.selected_order_side)

    def update_series(self, series):
        """Update the selected series for automatic mode."""
        self.selected_series = series
        print("Selected series:", self.selected_series)

    def display_message(self, message):
        """Process incoming WebSocket message, extract relevant fields, and update the table."""
        print("Received message:", message)

        # Check if message starts with "research:" and parse it
        if message.startswith("research:"):
            json_part = message[len("research:"):].strip()
            if not json_part:
                print("Message after 'research:' prefix is empty.")
                return

            try:
                message_data = json.loads(json_part)
                exchange_instrument_id = message_data.get("exchangeInstrumentID")
                
                # Check if instrument is already subscribed
                if exchange_instrument_id not in subscribed_instruments:
                    subscribed_instruments.add(exchange_instrument_id)
                    exchange_segment = message_data.get("exchangeSegment")
                    segment_code = self.SEGMENT_CODE_MAP.get(exchange_segment)
                    if segment_code:
                        self.subscribe_request.emit(segment_code, exchange_instrument_id)

                data = [
                    message_data.get("strategyName", "N/A"),  # Strategy Name
                    message_data.get("callType", "N/A"),
                    message_data.get("tradingSymbol", "N/A"),
                    message_data.get("exchangeSegment", "N/A"),
                    message_data.get("productType", "N/A"),
                    message_data.get("orderType", "N/A"),
                    message_data.get("orderSide", "N/A"),
                    message_data.get("timeInForce", "N/A"),
                    exchange_instrument_id,
                    message_data.get("orderQuantity", "N/A"),
                    message_data.get("limitPrice", "N/A"),
                    message_data.get("stopPrice", "N/A"),
                    message_data.get("targetPrice", "N/A"),
                    "Pending LTP...",  
                    "N/A",             
                    "Pending",         
                    "Pending",         
                    "Active",          
                    "Not Placed",      
                    "",  # Placeholder for OrderID
                    message_data.get("buyPrice", "N/A"),  # Buy Price
                    message_data.get("sellPrice", "N/A"),  # Sell Price
                    ""  # Placeholder for Trade History
                ]

                row = self.add_data_to_table(data)

                # Check if the conditions for automatic placement are met
                if (self.automatic_mode and
                    (self.selected_call_type == "All" or message_data.get("callType") == self.selected_call_type) and
                    (self.selected_exchange_segment == "Both" or message_data.get("exchangeSegment") == self.selected_exchange_segment) and
                    (self.selected_order_side == "Both" or message_data.get("orderSide") == self.selected_order_side) and
                    (self.selected_series == "All" or message_data.get("series") == self.selected_series)):
                    self.place_order(message_data, row)
                else:
                    # Show "Place Order" button for manual placement
                    place_order_btn = QPushButton("Place Order")
                    place_order_btn.clicked.connect(lambda _, r=row, data=message_data: self.manual_place_order(data, r))
                    self.price_table.setCellWidget(row, 18, place_order_btn)

            except json.JSONDecodeError as e:
                print(f"Failed to parse message as JSON: {e}")
        else:
            print("Message does not start with 'research:' prefix.")

    def place_order(self, order_data, row):
        """Place an order by sending a POST request to the Flask server."""
        order_payload = {
            "exchangeSegment": order_data["exchangeSegment"],
            "exchangeInstrumentID": order_data["exchangeInstrumentID"],
            "productType": order_data["productType"],
            "orderType": order_data["orderType"],
            "orderSide": order_data["orderSide"],
            "timeInForce": order_data["timeInForce"],
            "disclosedQuantity": order_data["orderQuantity"],
            "orderQuantity": order_data["orderQuantity"],
            "limitPrice": order_data["limitPrice"],
            "stopPrice": order_data["stopPrice"],
            "orderUniqueIdentifier": "unique_order_id_123"
        }

        try:
            response = requests.post("http://localhost:5000/place_order", json=order_payload)
            if response.status_code == 200:
                response_data = response.json()
                print("Order placed successfully:", response_data)
                if response_data.get("status") == "success":
                    order_id = response_data.get("OrderID")
                    order_statuses = response_data.get("OrderStatuses", [])
                    strategy_name = order_data.get("strategyName", "N/A")
                    self.update_order_in_table(strategy_name, order_id, order_statuses)

                    # Update Place Order column
                    self.price_table.setItem(row, 18, QTableWidgetItem("AutomaticOrder" if self.automatic_mode else "ManualOrder"))

                    # Check if the latest status is 'Rejected' or 'Filled' and fetch order history accordingly
                    latest_status = order_statuses[-1]
                    if "Rejected" in latest_status or "Filled" in latest_status:
                        self.fetch_order_history(order_id, row, latest_status)  # Fetch and process the order history
            else:
                print("Failed to place order:", response.json())
        except Exception as e:
            print(f"Error placing order: {e}")

    def fetch_order_history(self, app_order_id, row, latest_status):
        """Fetch order history and update columns based on order status (Rejected or Filled)."""
        try:
            response = requests.get(f"http://localhost:5000/get_order_history", params={"appOrderID": app_order_id})
            if response.status_code == 200:
                response_data = response.json()
                if response_data["status"] == "success":
                    order_history = response_data["orderHistory"]

                    # If status is 'Rejected', update only CancelRejectReason
                    if latest_status == "Rejected":
                        cancel_reject_reason = order_history[-1].get("CancelRejectReason", "N/A")
                        self.price_table.setItem(row, 22, QTableWidgetItem(cancel_reject_reason))  # Update Trade History with rejection reason

                    # If status is 'Filled', update Buy/Sell price based on OrderSide
                    elif latest_status in ["Filled", "NewFilled"]:
                        # Update Trade History column with full order history for reference
                        self.price_table.setItem(row, 22, QTableWidgetItem(str(order_history)))
                        
                        # Update Buy/Sell Price column based on OrderSide
                        for entry in order_history:
                            if entry["OrderStatus"] in ["Filled", "NewFilled"]:
                                avg_price = entry.get("OrderAverageTradedPrice", "N/A")
                                if entry["OrderSide"] == "BUY":
                                    self.price_table.setItem(row, 20, QTableWidgetItem(str(avg_price)))  # Buy Price column
                                elif entry["OrderSide"] == "SELL":
                                    self.price_table.setItem(row, 21, QTableWidgetItem(str(avg_price)))  # Sell Price column
                else:
                    print("Failed to fetch order history:", response_data["message"])
            else:
                print("Failed to fetch order history:", response.json())
        except Exception as e:
            print(f"Error fetching order history: {e}")


    def manual_place_order(self, order_data, row):
        """Handler for manual order placement when the 'Place Order' button is clicked."""
        self.place_order(order_data, row)
        # Remove the Place Order button after placing the order
        self.price_table.removeCellWidget(row, 18)

    def update_order_in_table(self, strategy_name, order_id, order_statuses):
        """Update the OrderID and OrderStatus columns based on Strategy Name."""
        row_count = self.price_table.rowCount()
        for row in range(row_count):
            item = self.price_table.item(row, 0)  # Column 0 is Strategy Name
            if item and item.text() == strategy_name:
                # Update OrderID
                self.price_table.setItem(row, 19, QTableWidgetItem(str(order_id)))  # Column 19 is OrderID
                # Update Order Status with the latest status
                if order_statuses:
                    latest_status = order_statuses[-1]
                    self.price_table.setItem(row, 15, QTableWidgetItem(latest_status))  # Column 15 is Order Status
                break

    def add_data_to_table(self, data):
        """Add data to the table or update if the strategy already exists."""
        row_position = self.price_table.rowCount()
        for row in range(row_position):
            if self.price_table.item(row, 0) and self.price_table.item(row, 0).text() == data[0]:  # Strategy Name
                for col, value in enumerate(data):
                    self.price_table.setItem(row, col, QTableWidgetItem(str(value)))
                return row
        self.price_table.insertRow(row_position)
        for col, value in enumerate(data):
            self.price_table.setItem(row_position, col, QTableWidgetItem(str(value)))
        return row_position

    def update_ltp_column(self, message):
        """Process WebSocket messages and update the LTP column for matching rows."""
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])
                ltp = message_data["Touchline"].get("LastTradedPrice", "0.0")

                # Update LTP for all rows with the same instrument
                row_count = self.price_table.rowCount()
                for row in range(row_count):
                    item_id = self.price_table.item(row, 8)  # Column 8 is Exchange Instrument ID
                    if item_id and item_id.text() == instrument_id:
                        self.price_table.setItem(row, 13, QTableWidgetItem(str(ltp)))  # Update LTP column
        except json.JSONDecodeError:
            print("Failed to parse message for LTP update.")

# Main code to run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    websocket_uri = "ws://localhost:8800"
    call_client = ResearchAlgo(websocket_uri)
    algo_tab = AlgoTab(call_client)
    call_client.start()
    algo_tab.show()
    sys.exit(app.exec_())
