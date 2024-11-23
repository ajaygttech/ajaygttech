import json
import datetime
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QSpacerItem, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt
from fetch import Application  # Import the Application class from fetch.py
from shared_resources import subscribed_instruments  # Import the shared subscribed_instruments set


class TopLeftFrame(QFrame):
    data_submitted = pyqtSignal(list)  # Signal emitted when data is submitted

    def __init__(self, websocket_thread):
        super().__init__()
        self.websocket_thread = websocket_thread  # Use the centralized WebSocketClient
        self.initUI()

        # Connect WebSocketClient to handle responses
        self.websocket_thread.response_received.connect(self.display_response)

    def initUI(self):
        # Main layout for the TopLeftFrame
        main_layout = QVBoxLayout()

        # Fetch layout (from fetch.py) will be embedded here
        self.fetch_widget = Application()
        self.fetch_widget.data_selected.connect(self.add_data_to_table)

        # Define new table headers
        column_headers = [
            "Action", "Exchange", "Series", "Name", "Expiration", "Strike Price", 
            "Option Type", "InstrumentID", "Lot Size", "Tick Size", 
            "Freeze Qty", "Price Band High", "Price Band Low", "CMP", "Lot", "Price"
        ]

        # Table to display market data
        self.top_left_table = QTableWidget(0, len(column_headers))  # Start with 0 rows, and the necessary number of columns
        self.top_left_table.setHorizontalHeaderLabels(column_headers)
        self.top_left_table.horizontalHeader().setStretchLastSection(True)
        self.top_left_table.setSelectionBehavior(QTableWidget.SelectRows)  # Select whole rows
        self.top_left_table.setSelectionMode(QTableWidget.SingleSelection)  # Allow single-row selection only

        # Connect to cellChanged to detect manual updates in the Lot column
        self.top_left_table.cellChanged.connect(self.on_cell_changed)

        # Add the fetch layout (from fetch.py) and the data table to the main layout
        main_layout.addWidget(self.fetch_widget)
        main_layout.addWidget(self.top_left_table)

        # Add labels and buttons in the same row
        self.spread_value_label = QLabel("Spread Value: 0")
        self.net_premium_label = QLabel("Net Premium: 0")

        label_button_layout = QHBoxLayout()
        label_button_layout.addWidget(self.spread_value_label)
        label_button_layout.addWidget(self.net_premium_label)
        label_button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Submit button
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(80)
        self.submit_button.clicked.connect(self.on_submit_clicked)
        label_button_layout.addWidget(self.submit_button)

        # Reset button
        self.reset_button = QPushButton("Reset")
        self.reset_button.setFixedWidth(80)
        self.reset_button.clicked.connect(self.on_reset_clicked)
        label_button_layout.addWidget(self.reset_button)

        main_layout.addLayout(label_button_layout)
        self.setLayout(main_layout)

    def calculate_spread_value(self):
        """Calculate the Spread Value."""
        total_value = 0
        for row in range(self.top_left_table.rowCount()):
            action = self.top_left_table.item(row, 0).text()
            lot = float(self.top_left_table.item(row, 14).text())  # Lot column
            cmp_value = float(self.top_left_table.item(row, 13).text())  # CMP column

            if action == "Buy":
                total_value -= lot * cmp_value  # Debit
            elif action == "Sell":
                total_value += lot * cmp_value  # Credit

        self.spread_value_label.setText(f"Spread Value: {total_value:.2f}")

    def calculate_net_premium(self):
        """Calculate the Net Premium for OPTIDX series."""
        total_premium = 0
        for row in range(self.top_left_table.rowCount()):
            series = self.top_left_table.item(row, 2).text()  # Series column
            if series == "OPTIDX":
                action = self.top_left_table.item(row, 0).text()
                lot_size = float(self.top_left_table.item(row, 8).text())  # Lot Size column
                lot = float(self.top_left_table.item(row, 14).text())  # Lot column
                cmp_value = float(self.top_left_table.item(row, 13).text())  # CMP column

                if action == "Buy":
                    total_premium -= lot * cmp_value * lot_size  # Debit
                elif action == "Sell":
                    total_premium += lot * cmp_value * lot_size  # Credit

        self.net_premium_label.setText(f"Net Premium: {total_premium:.2f}")

    def on_submit_clicked(self):
        """Handle the Submit button click."""
        current_time = datetime.datetime.now().strftime("%d%m%Y%H%M%S")
        strategy_name = f"rattle{current_time}"

        table_data = []
        for row in range(self.top_left_table.rowCount()):
            lot = self.top_left_table.item(row, 8).text()  # Now checking the Lot column
            if lot == '0':
                QMessageBox.warning(self, "Invalid Submission", "Lot cannot be 0.")
                return  # Prevent submission if Lot is 0

            row_data = []
            for col in range(self.top_left_table.columnCount()):
                item = self.top_left_table.item(row, col)
                row_data.append(item.text() if item else '')
            table_data.append(row_data)

        self.data_submitted.emit([strategy_name, table_data])
        self.top_left_table.clearContents()
        self.top_left_table.setRowCount(0)

        # Update Spread Value and Net Premium
        self.calculate_spread_value()
        self.calculate_net_premium()

        print(f"Data submitted for strategy: {strategy_name}")

    def on_reset_clicked(self):
        """Handle the Reset button click."""
        self.top_left_table.clearContents()
        self.top_left_table.setRowCount(0)
        self.spread_value_label.setText("Spread Value: 0")
        self.net_premium_label.setText("Net Premium: 0")

    def add_data_to_table(self, data):
        """Method to add data to the table from the fetch layout."""
        exchange_instrument_id = data['Exchange Instrument ID']

        # Check if the instrument is already in the table
        for row in range(self.top_left_table.rowCount()):
            if self.top_left_table.item(row, 7).text() == exchange_instrument_id:
                QMessageBox.warning(self, "Duplicate Entry", f"Instrument ID {exchange_instrument_id} already exists.")
                return

        row_position = self.top_left_table.rowCount()
        self.top_left_table.insertRow(row_position)

        # Setting the table items with the data, as specified
        self.top_left_table.setItem(row_position, 0, QTableWidgetItem(data.get('Action', '')))
        self.top_left_table.setItem(row_position, 1, QTableWidgetItem(data.get('Exchange Segment', '')))
        self.top_left_table.setItem(row_position, 2, QTableWidgetItem(data.get('Series', '')))
        self.top_left_table.setItem(row_position, 3, QTableWidgetItem(data.get('Name', '')))
        self.top_left_table.setItem(row_position, 4, QTableWidgetItem(data.get('Contract Expiration', '')))
        self.top_left_table.setItem(row_position, 5, QTableWidgetItem(data.get('Strike Price', '')))
        self.top_left_table.setItem(row_position, 6, QTableWidgetItem(data.get('Option Type', '')))
        self.top_left_table.setItem(row_position, 7, QTableWidgetItem(exchange_instrument_id))

        # Set Lot Size, Tick Size, Freeze Qty, Price Band High, Price Band Low
        self.top_left_table.setItem(row_position, 8, QTableWidgetItem(str(data.get('Lot Size', '0'))))  # Lot Size
        self.top_left_table.setItem(row_position, 9, QTableWidgetItem(str(data.get('Tick Size', '0'))))  # Tick Size
        self.top_left_table.setItem(row_position, 10, QTableWidgetItem(str(data.get('Freeze Qty', '0'))))  # Freeze Qty
        self.top_left_table.setItem(row_position, 11, QTableWidgetItem(str(data.get('Price Band High', '0'))))  # Price Band High
        self.top_left_table.setItem(row_position, 12, QTableWidgetItem(str(data.get('Price Band Low', '0'))))  # Price Band Low

        # Placeholder values for CMP, Lot, and Price
        self.top_left_table.setItem(row_position, 13, QTableWidgetItem("0"))  # CMP (Last Traded Price)
        self.top_left_table.setItem(row_position, 14, QTableWidgetItem("0"))  # Lot
        self.top_left_table.setItem(row_position, 15, QTableWidgetItem("0"))  # Price

        # Automatically subscribe after adding the data to the table if not already subscribed
        if exchange_instrument_id not in subscribed_instruments:  # Check if not already subscribed
            exchange_segment = data.get('Exchange Segment', '')
            segment_code = 1 if exchange_segment == "NSECM" else 2  # Adjust segment codes if needed
            self.websocket_thread.send_subscription(segment_code, int(exchange_instrument_id))

            # Add the instrument to the shared subscribed_instruments set
            subscribed_instruments.add(exchange_instrument_id)

        # Recalculate values after adding a row
        self.calculate_spread_value()
        self.calculate_net_premium()

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
                for row in range(self.top_left_table.rowCount()):
                    if self.top_left_table.item(row, 7).text() == instrument_id:
                        action = self.top_left_table.item(row, 0).text()  # Get the action (Buy/Sell)

                        # Update the CMP (Column 13) based on Buy or Sell action
                        if action == "Buy":
                            self.top_left_table.setItem(row, 13, QTableWidgetItem(str(ask_price)))  # Set Ask Price as CMP
                        elif action == "Sell":
                            self.top_left_table.setItem(row, 13, QTableWidgetItem(str(bid_price)))  # Set Bid Price as CMP

                        # Update the Last Traded Price (Column 15)
                        self.top_left_table.setItem(row, 15, QTableWidgetItem(str(last_traded_price)))

                        # Recalculate Spread Value and Net Premium after updating the price
                        self.calculate_spread_value()
                        self.calculate_net_premium()
                        break
        except json.JSONDecodeError:
            pass  # Ignore JSON decode errors

    def on_cell_changed(self, row, column):
        """Handle cell changes, especially for the Lot column."""
        if column == 14:  # Lot column index
            self.calculate_spread_value()
            self.calculate_net_premium()

    def keyPressEvent(self, event):
        """Handle delete key press to remove selected rows."""
        if event.key() == Qt.Key_Delete:
            selected_rows = sorted(set(index.row() for index in self.top_left_table.selectedIndexes()))
            for row in reversed(selected_rows):  # Delete rows from bottom to top to avoid reindexing issues
                self.top_left_table.removeRow(row)
            # Recalculate values after rows are deleted
            self.calculate_spread_value()
            self.calculate_net_premium()
