import json
import requests
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
from shared_resources import subscribed_instruments  # Import the shared set


class NetPositionDialog(QDialog):
    # Mapping for ExchangeSegment names to codes
    EXCHANGE_SEGMENT_MAP = {
        "NSECM": "1",
        "NSEFO": "2"
    }
    
    # Reverse mapping for segment codes to display names
    SEGMENT_MAP = {
        "1": "NSECM",
        "2": "NSEFO"
    }

    def __init__(self, websocket_client):
        super().__init__()
        self.setWindowTitle("Net and Day Position")
        self.resize(800, 600)
        
        # Store reference to the WebSocket client for sending subscription requests
        self.websocket_client = websocket_client

        # Dropdown for selecting position type
        self.selection_box = QComboBox(self)
        self.selection_box.addItems(["Net Position", "Day Position"])
        self.selection_box.currentTextChanged.connect(self.load_positions)

        # Table to display position data
        self.table_widget = QTableWidget(self)
        self.table_widget.setColumnCount(19)
        self.table_widget.setHorizontalHeaderLabels([
            "AccountID", "ExchangeSegment", "ProductType", "TradingSymbol", "BuyAveragePrice", "OpenBuyQuantity",
            "BuyAmount", "OpenSellQuantity", "SellAmount", "SellAveragePrice", "Quantity", "ltp",
            "MTM", "RealizedMTM", "Realize Qty", "Marketlot", "Multiplier", "NetAmount", "ExchangeInstrumentId"
        ])
        
        # Enable selection of entire rows
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Hide the "Realize Qty" column (index 14)
        self.table_widget.hideColumn(14)

        layout = QVBoxLayout()
        layout.addWidget(self.selection_box)
        layout.addWidget(self.table_widget)
        self.setLayout(layout)

        # Initialize totals for the required columns as instance attributes
        self.total_buy_amount = 0.0
        self.total_sell_amount = 0.0
        self.total_mtm = 0.0
        self.total_realized_mtm = 0.0
        self.total_net_amount = 0.0

        # Load default data (Net Position)
        self.load_positions("Net Position")

    def load_positions(self, position_type):
        """Load net or day position data based on selection and display in the table."""
        url = "http://127.0.0.1:5000/net_position" if position_type == "Net Position" else "http://127.0.0.1:5000/day_position"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json().get("data", {})

            # Reset totals each time data is loaded
            self.total_buy_amount = 0.0
            self.total_sell_amount = 0.0
            self.total_mtm = 0.0
            self.total_realized_mtm = 0.0
            self.total_net_amount = 0.0

            if "positionList" in data:
                position_list = data["positionList"]
                self.table_widget.setRowCount(len(position_list) + 1)  # Extra row for totals

                for row, position in enumerate(position_list):
                    def format_decimal(value):
                        return f"{float(value):.2f}"

                    # Calculate Realize Qty and RealizedMTM
                    open_buy_qty = int(position.get("OpenBuyQuantity", 0))
                    open_sell_qty = int(position.get("OpenSellQuantity", 0))
                    realize_qty = min(open_buy_qty, open_sell_qty)
                    
                    buy_avg_price = float(position.get("BuyAveragePrice", 0))
                    sell_avg_price = float(position.get("SellAveragePrice", 0))
                    realized_mtm = (sell_avg_price - buy_avg_price) * realize_qty

                    # Populate each column with data
                    self.table_widget.setItem(row, 0, QTableWidgetItem(str(position.get("AccountID", ""))))
                    self.table_widget.setItem(row, 1, QTableWidgetItem(str(position.get("ExchangeSegment", ""))))
                    self.table_widget.setItem(row, 2, QTableWidgetItem(str(position.get("ProductType", ""))))
                    self.table_widget.setItem(row, 3, QTableWidgetItem(str(position.get("TradingSymbol", ""))))
                    self.table_widget.setItem(row, 4, QTableWidgetItem(format_decimal(buy_avg_price)))
                    self.table_widget.setItem(row, 5, QTableWidgetItem(str(open_buy_qty)))
                    
                    buy_amount = float(position.get("BuyAmount", 0))
                    self.total_buy_amount += buy_amount
                    self.table_widget.setItem(row, 6, QTableWidgetItem(format_decimal(buy_amount)))
                    
                    self.table_widget.setItem(row, 7, QTableWidgetItem(str(open_sell_qty)))
                    
                    sell_amount = float(position.get("SellAmount", 0))
                    self.total_sell_amount += sell_amount
                    self.table_widget.setItem(row, 8, QTableWidgetItem(format_decimal(sell_amount)))
                    
                    self.table_widget.setItem(row, 9, QTableWidgetItem(format_decimal(sell_avg_price)))
                    
                    quantity = int(position.get("Quantity", 0))
                    self.table_widget.setItem(row, 10, QTableWidgetItem(str(quantity)))
                    
                    # Populate the new "ltp" column with a default value
                    self.table_widget.setItem(row, 11, QTableWidgetItem("Pending..."))
                    
                    # Set RealizedMTM and accumulate total
                    self.total_realized_mtm += realized_mtm
                    self.table_widget.setItem(row, 13, QTableWidgetItem(format_decimal(realized_mtm)))
                    self.table_widget.setItem(row, 14, QTableWidgetItem(str(realize_qty)))  # Hidden column
                    
                    self.table_widget.setItem(row, 15, QTableWidgetItem(str(position.get("Marketlot", ""))))
                    self.table_widget.setItem(row, 16, QTableWidgetItem(str(position.get("Multiplier", ""))))
                    
                    net_amount = float(position.get("NetAmount", 0))
                    self.total_net_amount += net_amount
                    self.table_widget.setItem(row, 17, QTableWidgetItem(format_decimal(net_amount)))
                    
                    self.table_widget.setItem(row, 18, QTableWidgetItem(str(position.get("ExchangeInstrumentId", ""))))

                    # Map ExchangeSegment to the correct code and send subscription request
                    exchange_segment_name = position.get("ExchangeSegment", "")
                    exchange_segment_code = self.EXCHANGE_SEGMENT_MAP.get(exchange_segment_name, "")
                    exchange_instrument_id = position.get("ExchangeInstrumentId", "")
                    
                    # Check if instrument is already subscribed
                    if (exchange_segment_code, exchange_instrument_id) not in subscribed_instruments:
                        # Add to subscribed set and send subscription request
                        subscribed_instruments.add((exchange_segment_code, exchange_instrument_id))
                        print(f"Subscribing to ExchangeSegment: {exchange_segment_name} (Code: {exchange_segment_code}), ExchangeInstrumentID: {exchange_instrument_id}")
                        self.websocket_client.send_subscription(exchange_segment_code, exchange_instrument_id)
                    else:
                        print(f"Already subscribed to ExchangeSegment: {exchange_segment_name} (Code: {exchange_segment_code}), ExchangeInstrumentID: {exchange_instrument_id}")

                # Insert totals in the last row of the table
                totals_row = len(position_list)
                self.table_widget.setItem(totals_row, 6, QTableWidgetItem(f"Total: {self.total_buy_amount:.2f}"))
                self.table_widget.setItem(totals_row, 8, QTableWidgetItem(f"Total: {self.total_sell_amount:.2f}"))
                self.table_widget.setItem(totals_row, 12, QTableWidgetItem(f"Total: {self.total_mtm:.2f}"))
                self.table_widget.setItem(totals_row, 13, QTableWidgetItem(f"Total: {self.total_realized_mtm:.2f}"))
                self.table_widget.setItem(totals_row, 17, QTableWidgetItem(f"Total: {self.total_net_amount:.2f}"))

            else:
                QMessageBox.information(self, "No Data", f"No {position_type.lower()} data available.")

        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Error fetching {position_type.lower()} data: {e}")

    def update_ltp_column(self, message):
        """Process WebSocket messages to update the LTP and MTM columns in the net position table for all matching rows."""
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])
                segment_code = str(message_data["ExchangeSegment"])
                exchange_segment = self.SEGMENT_MAP.get(segment_code, "Unknown")  # Convert code to NSECM/NSEFO

                # Extract the LTP from the message
                touchline = message_data["Touchline"]
                ltp = float(touchline.get("LastTradedPrice", 0.0))

                # Iterate over all rows and update each row that matches the instrument ID and segment
                row_count = self.table_widget.rowCount()
                self.total_mtm = 0.0  # Reset total MTM before recalculating
                for row in range(row_count - 1):  # Exclude the last row (totals row)
                    item_id = self.table_widget.item(row, 18)  # Assuming column 18 is ExchangeInstrumentId
                    item_segment = self.table_widget.item(row, 1)  # Assuming column 1 is ExchangeSegment
                    if item_id and item_segment and item_id.text() == instrument_id and item_segment.text() == exchange_segment:
                        # Update the LTP in the table
                        self.table_widget.setItem(row, 11, QTableWidgetItem(f"{ltp:.2f}"))

                        # Calculate MTM based on the quantity and update it in the table
                        quantity = int(self.table_widget.item(row, 10).text())
                        buy_avg_price = float(self.table_widget.item(row, 4).text())
                        sell_avg_price = float(self.table_widget.item(row, 9).text())
                        realized_mtm = float(self.table_widget.item(row, 13).text())

                        if quantity > 0:
                            mtm = (ltp - buy_avg_price) * quantity + realized_mtm
                        else:
                            mtm = (sell_avg_price - ltp) * abs(quantity) + realized_mtm

                        # Update the MTM column and accumulate total MTM
                        self.total_mtm += mtm
                        self.table_widget.setItem(row, 12, QTableWidgetItem(f"{mtm:.2f}"))
                        print(f"Updated LTP and MTM for {instrument_id} in row {row}: LTP = {ltp}, MTM = {mtm}")

                # Update the MTM total in the totals row
                totals_row = row_count - 1
                self.table_widget.setItem(totals_row, 12, QTableWidgetItem(f"Total: {self.total_mtm:.2f}"))

        except json.JSONDecodeError:
            print("Error decoding WebSocket message.")
