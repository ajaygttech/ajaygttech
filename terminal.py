import pandas as pd
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget,QDialog,QLabel, QTableWidgetItem, QMessageBox, QAbstractItemView, QFrame, QHBoxLayout, QMenu, QFileDialog
from PyQt5.QtCore import Qt, QPoint,QEvent
from scriptbar import Application  # Import Application from scriptbar.py
from order import PlaceOrderApp  # Import the OrderWindow class
from shared_resources import subscribed_instruments  # Import the shared subscribed_instruments set


class TerminalTab(QWidget):
    def __init__(self, websocket_client, parent=None):
        super().__init__(parent)

        # Initialize WebSocket client
        self.websocket_client = websocket_client
      
        self.websocket_client.response_received.connect(self.update_ltp_column)  # Connect signal to update LTP

        # Start WebSocket client in a separate thread
        self.websocket_client.start()

        # Main layout for the Terminal Tab
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # No margins around the layout
        main_layout.setSpacing(0)  # No spacing between widgets

        # Create a top frame to contain the two parts: left for scriptbar, right blank
        top_frame = QFrame()
        top_frame_layout = QHBoxLayout()
        top_frame_layout.setContentsMargins(0, 0, 0, 0)  # No margins inside the frame
        top_frame_layout.setSpacing(0)  # No spacing between elements in the frame

        # Left top frame for the scriptbar comboboxes
        left_top_frame = QFrame()
        left_top_layout = QVBoxLayout()
        left_top_layout.setContentsMargins(0, 0, 0, 0)

        # Add the Application (scriptbar comboboxes) to the left top frame
        dummy_df = pd.DataFrame()  # Use an empty DataFrame or load your data here
        self.app_widget = Application(dummy_df)  # Instantiate your Application class
        self.app_widget.data_selected.connect(self.update_table)  # Connect signal to update table
        left_top_layout.addWidget(self.app_widget)

        left_top_frame.setLayout(left_top_layout)

        # Right top frame (currently blank)
        right_top_frame = QFrame()

        # Add left and right top frames to the top frame layout
        top_frame_layout.addWidget(left_top_frame)
        top_frame_layout.addWidget(right_top_frame)

        # Set the layout for the top frame
        top_frame.setLayout(top_frame_layout)

        # Add the top frame to the main layout
        main_layout.addWidget(top_frame)

        # Bottom frame (for the table)
        self.table_widget = QTableWidget(0, 34)  # Start with 0 rows, 34 columns
        # Set the column headers in the specified order
        column_headers = [
            "ExchangeSegment", "Series", "ContractExpiration", "StrikePrice", "OptionType", "Name", "BidQty", "Bid Price",
            "Ask Price", "Ask Qty", "LTP", "% Change", "Change Value", "LTQ", "ATP", "Open", "High", "Low", "Close", "InstrumentType",
            "Description", "NameWithSeries", "InstrumentID", "PriceBandHigh", "PriceBandLow", "FreezeQty",
            "TickSize", "LotSize", "Multiplier", "UnderlyingIndexName",
            "ISIN", "displayName", "ExchangeInstrumentID",  "UnderlyingInstrumentId"
        ]
        self.table_widget.setHorizontalHeaderLabels(column_headers)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setSelectionBehavior(self.table_widget.SelectRows)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        # Enable right-click context menu
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

        # Add the table widget to the main layout (bottom section)
        main_layout.addWidget(self.table_widget)

        # Set the layout for the Terminal tab


        self.setLayout(main_layout)
        self.current_key = None
        self.table_widget.installEventFilter(self)

    def eventFilter(self, source, event):
        """Capture key events even when the table is non-editable."""
        if event.type() == QEvent.KeyPress and source is self.table_widget:
            if event.key() == Qt.Key_Plus:  # Plus key pressed for BUY
                self.current_key = Qt.Key_Plus
                self.open_order_window(order_side="BUY")  # Explicitly set BUY
                return True
            elif event.key() == Qt.Key_Minus:  # Minus key pressed for SELL
                self.current_key = Qt.Key_Minus
                self.open_order_window(order_side="SELL")  # Explicitly set SELL
                return True
            elif event.key() == Qt.Key_Delete:  # Delete key pressed to delete selected row
                self.delete_selected_row()
                return True
        return super().eventFilter(source, event)

        
    def open_order_window(self, order_side):
        """Open the order window and pass the selected instrument's details to PlaceOrderApp."""
        selected_row = self.table_widget.currentRow()  # Get the selected row index
        if selected_row < 0:  # If no row is selected, show a warning
            QMessageBox.warning(self, "No selection", "Please select a row first.")
            return

        # Retrieve instrument details from the selected row
        exchange_instrument_id = self.table_widget.item(selected_row, 32).text()  # Assuming column 32 holds ExchangeInstrumentID
        exchange_segment = self.table_widget.item(selected_row, 0).text()  # Assuming column 0 holds ExchangeSegment
        price_band_high = float(self.table_widget.item(selected_row, 23).text())  # Column 24 for PriceBandHigh
        price_band_low = float(self.table_widget.item(selected_row, 24).text())  # Column 25 for PriceBandLow
        freeze_qty = self.table_widget.item(selected_row, 25).text()  # Column 26 for FreezeQty
        tick_size = float(self.table_widget.item(selected_row, 26).text())  # Column 27 for TickSize
        lot_size = int(self.table_widget.item(selected_row, 27).text())  # Column 28 for LotSize
        bid_price = float(self.table_widget.item(selected_row, 7).text())  # Column 7 for Bid Price
        ask_price = float(self.table_widget.item(selected_row, 8).text())  # Column 8 for Ask Price

        # Open the PlaceOrderApp dialog and pass the collected details
        order_window = PlaceOrderApp(
            exchange_instrument_id=exchange_instrument_id,
            order_side=order_side,
            price_band_high=price_band_high,
            price_band_low=price_band_low,
            freeze_qty=freeze_qty,
            tick_size=tick_size,
            lot_size=lot_size,
            bid_price=bid_price,
            ask_price=ask_price,
            exchange_segment=exchange_segment,
            parent=self
        )
        order_window.exec_()  # Show the window as a modal dialog


      

    def delete_selected_row(self):
        """Deletes the currently selected row."""
        selected_row = self.table_widget.currentRow()
        if selected_row >= 0:
            self.table_widget.removeRow(selected_row)
        else:
            QMessageBox.warning(self, "No selection", "Please select a row to delete.")

    def show_context_menu(self, pos: QPoint):
        """Show the right-click context menu."""
        menu = QMenu(self)
        save_action = menu.addAction("Save Market Watch")
        open_action = menu.addAction("Open Market Watch")

        # Connect the actions to their corresponding methods
        save_action.triggered.connect(self.save_market_watch)
        open_action.triggered.connect(self.open_market_watch)

        # Show the context menu at the cursor position
        menu.exec_(self.table_widget.mapToGlobal(pos))

    def save_market_watch(self):
        """Save the market watch data to a JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Market Watch", "", "JSON Files (*.json)")
        if file_path:
            table_data = []
            row_count = self.table_widget.rowCount()
            col_count = self.table_widget.columnCount()

            for row in range(row_count):
                row_data = {}
                for col in range(col_count):
                    item = self.table_widget.item(row, col)
                    row_data[self.table_widget.horizontalHeaderItem(col).text()] = item.text() if item else ""
                table_data.append(row_data)

            with open(file_path, "w") as file:
                json.dump(table_data, file, indent=4)
            QMessageBox.information(self, "Success", "Market Watch saved successfully!")

    def open_market_watch(self):
        """Open and load the market watch data from a JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Market Watch", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, "r") as file:
                table_data = json.load(file)

            self.table_widget.setRowCount(0)  # Clear the table before loading new data
            for row_data in table_data:
                next_row = self.table_widget.rowCount()
                self.table_widget.insertRow(next_row)

                # Add the data to the table and send subscription request
                for col, header in enumerate(self.table_widget.horizontalHeaderItem(i).text() for i in range(self.table_widget.columnCount())):
                    value = row_data.get(header, "")
                    self.table_widget.setItem(next_row, col, QTableWidgetItem(str(value)))

                # Extract the necessary values to send a subscription request
                exchange_segment = row_data.get("ExchangeSegment")
                exchange_instrument_id = row_data.get("ExchangeInstrumentID")

                # Send subscription request for each instrument loaded from file
                if exchange_segment and exchange_instrument_id:
                    self.subscribe_to_instrument(exchange_segment, exchange_instrument_id)

            QMessageBox.information(self, "Success", "Market Watch loaded successfully!")


    def is_duplicate_instrument(self, exchange_instrument_id):
        """Checks if the ExchangeInstrumentID already exists in column 32 of the table."""
        row_count = self.table_widget.rowCount()
        for row in range(row_count):
            item = self.table_widget.item(row, 32)  # Assuming ExchangeInstrumentID is in column 32
            if item and item.text() == exchange_instrument_id:
                return True
        return False

    def update_table(self, data):
        """Update the table by adding the selected data to a new row, replacing NaN with an empty string."""
        exchange_instrument_id = data.get("ExchangeInstrumentID")

        # Check if the ExchangeInstrumentID is already present in the table (column 32)
        if self.is_duplicate_instrument(exchange_instrument_id):
            QMessageBox.warning(self, "Duplicate Entry", f"Instrument ID {exchange_instrument_id} already exists.")
            return

        # Get the next available row (the current row count)
        next_row = self.table_widget.rowCount()

        # Insert a new row at the next available position
        self.table_widget.insertRow(next_row)

        # Add the data to the table, replacing NaN with an empty string
        headers = [self.table_widget.horizontalHeaderItem(i).text() for i in range(self.table_widget.columnCount())]
        for col, header in enumerate(headers):
            if header in data:
                value = data[header]
                if pd.isna(value):  # Check if the value is NaN for **any** column
                    value = ""  # Replace NaN with an empty string
                self.table_widget.setItem(next_row, col, QTableWidgetItem(str(value)))

        # Send WebSocket subscription request for the new row
        exchange_segment = data.get("ExchangeSegment")
        if exchange_segment and exchange_instrument_id:
            self.subscribe_to_instrument(exchange_segment, exchange_instrument_id)

    def subscribe_to_instrument(self, exchange_segment, exchange_instrument_id):
        """Send subscription request for real-time updates via WebSocket only if not already subscribed."""
        if exchange_instrument_id not in subscribed_instruments:
            # Determine the exchange segment code
            segment_code = 1 if exchange_segment == "NSECM" else 2  # Adjust segment codes as per your requirement
            self.websocket_client.send_subscription(segment_code, int(exchange_instrument_id))

            # Add the instrument to the subscribed instruments set
            subscribed_instruments.add(exchange_instrument_id)

    def update_ltp_column(self, message):
        """Update the LTP, ATP, Open, High, Low, Close, BidQty, BidPrice, AskQty, AskPrice, LTQ columns with WebSocket messages."""
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])

                # Find the row corresponding to the instrument ID
                row_count = self.table_widget.rowCount()
                for row in range(row_count):
                    item = self.table_widget.item(row, 32)  # Assuming ExchangeInstrumentID is in column 32
                    if item and item.text() == instrument_id:
                        touchline = message_data["Touchline"]

                        # Update BidQty (Column 6)
                        bid_qty = touchline["BidInfo"].get("Size", "0")
                        self.table_widget.setItem(row, 6, QTableWidgetItem(str(bid_qty)))

                        # Update BidPrice (Column 7)
                        bid_price = touchline["BidInfo"].get("Price", "0.0")
                        self.table_widget.setItem(row, 7, QTableWidgetItem(str(bid_price)))

                        # Update AskPrice (Column 8)
                        ask_price = touchline["AskInfo"].get("Price", "0.0")
                        self.table_widget.setItem(row, 8, QTableWidgetItem(str(ask_price)))

                        # Update AskQty (Column 9)
                        ask_qty = touchline["AskInfo"].get("Size", "0")
                        self.table_widget.setItem(row, 9, QTableWidgetItem(str(ask_qty)))

                        # Update LTP (Column 10)
                        ltp = touchline.get("LastTradedPrice", "0.0")
                        self.table_widget.setItem(row, 10, QTableWidgetItem(str(ltp)))

                        # Update Change % (Column 11)
                        change_percent = touchline.get("PercentChange", "0.0")
                        self.table_widget.setItem(row, 11, QTableWidgetItem(f"{float(change_percent):.2f}"))

                        # Update Change Value (Column 12, calculate as LTP - Close)
                        close_price = touchline.get("Close", "0.0")
                        change_value = float(ltp) - float(close_price)
                        self.table_widget.setItem(row, 12, QTableWidgetItem(f"{change_value:.2f}"))

                        # Update LTQ (Last Traded Quantity) (Column 13)
                        ltq = touchline.get("LastTradedQunatity", "0")
                        self.table_widget.setItem(row, 13, QTableWidgetItem(str(ltq)))

                        # Update ATP (Column 14)
                        atp = touchline.get("AverageTradedPrice", "0.0")
                        self.table_widget.setItem(row, 14, QTableWidgetItem(str(atp)))

                        # Update Open (Column 15)
                        open_price = touchline.get("Open", "0.0")
                        self.table_widget.setItem(row, 15, QTableWidgetItem(str(open_price)))

                        # Update High (Column 16)
                        high_price = touchline.get("High", "0.0")
                        self.table_widget.setItem(row, 16, QTableWidgetItem(str(high_price)))

                        # Update Low (Column 17)
                        low_price = touchline.get("Low", "0.0")
                        self.table_widget.setItem(row, 17, QTableWidgetItem(str(low_price)))

                        # Update Close (Column 18)
                        close_price = touchline.get("Close", "0.0")
                        self.table_widget.setItem(row, 18, QTableWidgetItem(str(close_price)))

                        break
        except json.JSONDecodeError:
            pass  