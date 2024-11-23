import json
import os
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QTabWidget, QWidget, QTableWidget, QTableWidgetItem
from shared_resources import subscribed_instruments  # Import the shared subscribed_instruments set


class RightTable(QWidget):
    cmp_updated = pyqtSignal(float)  # Signal to emit when CMP is updated
    def __init__(self, websocket_thread):
        super().__init__()
        self.websocket_thread = websocket_thread  # Use the centralized WebSocketClient

        self.setup_table()

        # Connect the WebSocket client signal to this table's response handler
        self.websocket_thread.response_received.connect(self.display_response)

        # Dictionary to keep track of row positions for each instrument
        self.instrument_row_mapping = {}

        # Set of instruments for the current strategy
        self.current_strategy_instruments = set()

        # Attribute to store the sum of CMP
        self.cmp_sum = 0.0

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
        self.current_strategy_instruments.clear()  # Clear current strategy instruments
        self.cmp_sum = 0.0  # Reset the CMP sum when clearing the table

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

            # Keep track of instruments for the current strategy
            self.current_strategy_instruments.add(exchange_instrument_id)

            # Send subscription request only if the instrument isn't already subscribed
            if exchange_instrument_id not in subscribed_instruments:
                exchange_segment = row_data[1]  # Assuming Exchange Segment is at index 1
                segment_code = 1 if exchange_segment == "NSECM" else 2  # Adjust segment codes as needed
                self.websocket_thread.send_subscription(segment_code, int(exchange_instrument_id))

                # Mark this instrument as subscribed in the shared set
                subscribed_instruments.add(exchange_instrument_id)

        # Update the CMP sum after adding data
        self.update_cmp_sum()

    def display_response(self, message):
        """Update the CMP and Last Traded Price (Price) based on WebSocket responses."""
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])

                # Update only if the instrument belongs to the current strategy
                if instrument_id in self.current_strategy_instruments:
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

                        # Update the CMP sum after the response
                        self.update_cmp_sum()

                        # Emit the signal with the updated CMP sum
                        self.cmp_updated.emit(self.cmp_sum)
        except json.JSONDecodeError:
            pass  # Ignore JSON decode errors

    def update_cmp_sum(self):
        """Calculate and update the sum of CMP values in the table."""
        total_cmp = 0.0
        for row in range(self.right_table.rowCount()):
            cmp_item = self.right_table.item(row, 13)  # CMP is in column 13
            if cmp_item:
                try:
                    total_cmp += float(cmp_item.text())
                except ValueError:
                    pass  # Skip if the CMP value is not a valid float

        # Store the sum of CMPs
        self.cmp_sum = total_cmp
        print(f"Sum of all CMP values: {self.cmp_sum}")

class RightFrame(QFrame):
    def __init__(self, bottom_left_frame, websocket_thread):
        super().__init__()
        self.bottom_left_frame = bottom_left_frame  # Reference to BottomLeftFrame
        self.websocket_thread = websocket_thread  # Use the centralized WebSocketClient
        self.data_by_strategy = {}  # Dictionary to store data by strategy name
        self.current_strategy = None  # Track the currently selected strategy

        # Set up the layout and load data
        self.setup_right_layout()
        self.load_data_from_file()

        self.right_table_widget.cmp_updated.connect(self.update_current_entry_value_in_blframe)

    def setup_right_layout(self):
        """Set up the layout for the right frame."""
        right_layout = QVBoxLayout()

        # Remove all margins for the right frame layout
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Create a tab widget for navigation in the right frame
        tab_widget = QTabWidget()

        # Initialize the RightTable (existing table in the Table tab)
        self.right_table_widget = RightTable(self.websocket_thread)

        # Create the Trade tab
        trade_tab = QWidget()

        # Add the RightTable in the Table tab
        tab_widget.addTab(self.right_table_widget, "Table")

        # Add a placeholder for the Trade tab (or you can implement it later)
        tab_widget.addTab(trade_tab, "Trade")

        # Add the tab widget to the layout
        right_layout.addWidget(tab_widget)

        # Set the layout for the right frame
        self.setLayout(right_layout)

    def add_data_by_strategy(self, strategy_name, table_data):
        """Store data by strategy name and save it to a JSON file."""
        self.current_strategy = strategy_name  # Set the current strategy
        self.data_by_strategy[strategy_name] = table_data

        # Add strategy name to BottomLeftFrame if not already present
        if not self.bottom_left_frame.is_strategy_present(strategy_name):
            self.bottom_left_frame.add_strategy(strategy_name)

        # Add data to the table
        self.right_table_widget.add_data(table_data)

        # Save the updated data to the JSON file
        self.save_data_to_file()

        # Update the Current Entry Value with the sum of CMP
        cmp_sum = self.right_table_widget.cmp_sum
        self.bottom_left_frame.update_current_entry_value(strategy_name, cmp_sum)



    def update_current_entry_value_in_blframe(self, cmp_sum):
        """Update the Current Entry Value in BottomLeftFrame in real-time."""
        if self.current_strategy:
            self.bottom_left_frame.update_current_entry_value(self.current_strategy, cmp_sum)

    def display_data_by_strategy(self, strategy_name):
        """Display the data for the selected strategy."""
        if strategy_name in self.data_by_strategy:
            self.current_strategy = strategy_name  # Set the current strategy
            table_data = self.data_by_strategy[strategy_name]
            self.right_table_widget.add_data(table_data)
            print(f"Displayed data for strategy: {strategy_name}")

            # Update the Current Entry Value with the sum of CMP
            cmp_sum = self.right_table_widget.cmp_sum
            self.bottom_left_frame.update_current_entry_value(strategy_name, cmp_sum)
        else:
            print(f"No data found for strategy: {strategy_name}")

    def save_data_to_file(self):
        """Save the strategy data to a JSON file."""
        file_path = "strategy_data.json"
        with open(file_path, "w") as json_file:
            json.dump(self.data_by_strategy, json_file, indent=4)
        print("Strategy data saved to JSON file.")

    def load_data_from_file(self):
        """Load the strategy data from a JSON file if it exists."""
        file_path = "strategy_data.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                self.data_by_strategy = json.load(json_file)

            # Add the loaded strategy names to the BottomLeftFrame
            for strategy_name in self.data_by_strategy:
                self.bottom_left_frame.add_strategy(strategy_name)

            print("Strategy data loaded from JSON file.")
        else:
            print("No strategy data file found.")
