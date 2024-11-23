# price_tab.py
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QHeaderView
from PyQt5.QtCore import pyqtSignal


class PriceTab(QWidget):
    # Signal to request subscription to an instrument
    subscribe_request = pyqtSignal(str, str)

    # Mapping for Exchange Segment codes to display names
    SEGMENT_MAP = {
        "1": "NSECM",
        "2": "NSEFO"
    }
    
    # Reverse mapping for sending subscription requests
    SEGMENT_CODE_MAP = {v: k for k, v in SEGMENT_MAP.items()}

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create the table with columns: Exchange Segment, Instrument ID, LTP, and Status
        self.price_table = QTableWidget()
        self.price_table.setColumnCount(4)  # Update column count to 4
        self.price_table.setHorizontalHeaderLabels(["Exchange Segment", "Exchange Instrument ID", "LTP", "Status"])
        self.price_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.price_table)

        # Input fields for exchange segment and instrument ID
        self.exchange_segment_input = QLineEdit(self)
        self.exchange_segment_input.setPlaceholderText("Enter Exchange Segment (NSECM or NSEFO)")
        layout.addWidget(self.exchange_segment_input)

        self.instrument_id_input = QLineEdit(self)
        self.instrument_id_input.setPlaceholderText("Enter Exchange Instrument ID")
        layout.addWidget(self.instrument_id_input)

        # Submit button to add data to the table
        self.submit_button = QPushButton("Submit", self)  # Renamed button to "Submit"
        self.submit_button.clicked.connect(self.add_data_to_table)
        layout.addWidget(self.submit_button)

        # Set layout for the widget
        self.setLayout(layout)

    def add_data_to_table(self):
        """Add data to the table without sending a subscription request immediately."""
        exchange_segment = self.exchange_segment_input.text().upper()  # Accepts "NSECM" or "NSEFO"
        exchange_instrument_id = self.instrument_id_input.text()

        if exchange_segment in self.SEGMENT_CODE_MAP and exchange_instrument_id:
            # Add data to the table with "Pending Subscription" status
            display_segment = exchange_segment  # Use NSECM or NSEFO as display value
            self.update_price(display_segment, exchange_instrument_id, "Pending LTP...", "Pending Subscription")

            # Send subscription request after data is added to the table
            segment_code = self.SEGMENT_CODE_MAP[exchange_segment]  # Convert to 1 or 2 for the subscription request
            self.subscribe_request.emit(segment_code, exchange_instrument_id)

            # Clear input fields after adding
            self.exchange_segment_input.clear()
            self.instrument_id_input.clear()

    def update_price(self, exchange_segment, exchange_instrument_id, ltp, status):
        """Update the LTP and status for an instrument in the table or add it if it doesn't exist."""
        row_position = self.price_table.rowCount()

        # Check if the instrument already exists in the table
        for row in range(row_position):
            if (self.price_table.item(row, 0) and self.price_table.item(row, 0).text() == exchange_segment and 
                self.price_table.item(row, 1) and self.price_table.item(row, 1).text() == str(exchange_instrument_id)):
                # Update existing LTP and status for the instrument
                self.price_table.setItem(row, 2, QTableWidgetItem(str(ltp)))
                self.price_table.setItem(row, 3, QTableWidgetItem(status))
                return

        # If instrument not in table, add a new row for it
        self.price_table.insertRow(row_position)
        self.price_table.setItem(row_position, 0, QTableWidgetItem(exchange_segment))  # Display NSECM or NSEFO
        self.price_table.setItem(row_position, 1, QTableWidgetItem(str(exchange_instrument_id)))
        self.price_table.setItem(row_position, 2, QTableWidgetItem(str(ltp)))
        self.price_table.setItem(row_position, 3, QTableWidgetItem(status))  # Set the initial status

    def update_ltp_column(self, message):
        """Process WebSocket messages and update the LTP column and status."""
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])
                segment_code = str(message_data["ExchangeSegment"])
                exchange_segment = self.SEGMENT_MAP.get(segment_code, "Unknown")  # Convert code to NSECM/NSEFO

                # Find the row corresponding to the instrument ID
                row_count = self.price_table.rowCount()
                for row in range(row_count):
                    item_id = self.price_table.item(row, 1)  # Assuming column 1 is ExchangeInstrumentID
                    item_segment = self.price_table.item(row, 0)  # Assuming column 0 is ExchangeSegment
                    if item_id and item_segment and item_id.text() == instrument_id and item_segment.text() == exchange_segment:
                        touchline = message_data["Touchline"]

                        # Update the LTP (Last Traded Price)
                        ltp = touchline.get("LastTradedPrice", "0.0")
                        self.price_table.setItem(row, 2, QTableWidgetItem(str(ltp)))

                        # Update Status to "Subscribed"
                        self.price_table.setItem(row, 3, QTableWidgetItem("Subscribed"))
                        break
        except json.JSONDecodeError:
            pass
