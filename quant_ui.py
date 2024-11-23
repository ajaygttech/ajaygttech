from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QPushButton,
    QLineEdit, QCheckBox, QGroupBox, QComboBox, QLabel, QGridLayout,
    QTableWidget, QTableWidgetItem,QMessageBox, QHeaderView
)
from PyQt5.QtCore import QTimer, pyqtSignal,Qt
from PyQt5.QtGui import QPixmap
import asyncio
import json
from websocket_client_backend import WebSocketClientBackend
import os
from quant_settings import SettingsWindow
import requests

class Table(QWidget):
    """
    A dedicated class for managing the table that displays order and LTP data.
    """
    subscribe_request = pyqtSignal(str, str)  # Signal to emit subscription requests

    SEGMENT_MAP = {"1": "NSECM", "2": "NSEFO"}
    SEGMENT_CODE_MAP = {v: k for k, v in SEGMENT_MAP.items()}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        """
        Initialize the table layout and settings.
        """
        layout = QVBoxLayout()

        # Create the table
        self.table = QTableWidget(0, 26)
        self.table.setHorizontalHeaderLabels([
            "strategyName", "orderside", "exchangeSegment", "series",
            "exchangeInstrumentID", "tradingSymbol", "orderType",
            "productType", "orderQuantity", "limitPrice", "stopPrice",
            "LTP", "Order Status", "Buy Price", "Buy Qty", "SellQty", 
            "Sell Price", "SL Status", "Target Status", "AppOrderID", 
            "Place Order", "Reason", "Remark", "Action","MTM" ," CallType"
        ])

        # Enable scrollbars
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Allow flexible column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # Allow users to manually resize columns
        header.setStretchLastSection(True)  # Stretch the last column to fill remaining space

        # Enable row selection
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # Select entire rows
        self.table.setSelectionMode(QTableWidget.SingleSelection)  # Allow single row selection (use `MultiSelection` for multiple rows)
        # Add the table to the layout
        layout.addWidget(self.table)
        self.setLayout(layout)

    def add_order(self, strategy_name,order_side,exchange_segment,series ,instrument_id,trading_symbol,order_type,product_Type,order_quantity,limit_price,stop_price,call_type):

        """
        Add a new row to the table for an order.
        
        """
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(strategy_name))
        self.table.setItem(row_position, 1, QTableWidgetItem(order_side))
        self.table.setItem(row_position, 2, QTableWidgetItem(exchange_segment))
        self.table.setItem(row_position, 3, QTableWidgetItem(series))
        self.table.setItem(row_position, 4, QTableWidgetItem(instrument_id))
        self.table.setItem(row_position, 5, QTableWidgetItem(trading_symbol))
        self.table.setItem(row_position, 6, QTableWidgetItem(order_type))
        self.table.setItem(row_position, 7, QTableWidgetItem(product_Type))
        self.table.setItem(row_position, 8, QTableWidgetItem(order_quantity))
        self.table.setItem(row_position, 9, QTableWidgetItem(limit_price))
        self.table.setItem(row_position, 10, QTableWidgetItem(stop_price))
        self.table.setItem(row_position, 11, QTableWidgetItem("0"))  # Default LTP as 0
        self.table.setItem(row_position, 12, QTableWidgetItem(""))
        self.table.setItem(row_position, 13, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 14, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 15, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 16, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 17, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 18, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 19, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 20, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 21, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 22, QTableWidgetItem("N/A"))
        self.table.setItem(row_position, 23, QTableWidgetItem("Active"))
        self.table.setItem(row_position, 24, QTableWidgetItem("0.00"))
        self.table.setItem(row_position, 25, QTableWidgetItem(call_type))
        
        

        

        # Emit subscription request
        segment_code = self.SEGMENT_CODE_MAP.get(exchange_segment, "Unknown")
        self.subscribe_request.emit(segment_code, instrument_id)

        # Use the parent's execution mode
        if self.parent.execution_mode == "Manual":
            self.handle_manual_order(row_position)
        else:
            self.handle_automatic_order(row_position)
            
    def place_order(self, row_position, button=None):
        """
        Handle order placement logic.
        """
        # Retrieve required data from the row
        order_data = {
            "exchangeSegment": self.table.item(row_position, 2).text(),
            "exchangeInstrumentID": self.table.item(row_position, 4).text(),
            "productType": self.table.item(row_position, 7).text(),
            "orderType": self.table.item(row_position, 6).text(),
            "orderSide": self.table.item(row_position, 1).text(),
            "timeInForce": "VALIDITY_DAY",  # Default to "Day"
            "disclosedQuantity": 0,  # Default disclosed quantity
            "orderQuantity": self.table.item(row_position, 8).text(),
            "limitPrice": self.table.item(row_position, 9).text(),
            "stopPrice": self.table.item(row_position, 10).text(),
            "orderUniqueIdentifier": "rattle"  # Default unique identifier
        }
        self.format_order_data(order_data)


        # Place the order via the backend
        order_response = self.parent.backend.place_order(order_data)

        if order_response.get("status") == "success":
            # Update the "AppOrderID" column with OrderID
            order_id = order_response.get("OrderID", "N/A")
            self.table.setItem(row_position, 19, QTableWidgetItem(str(order_id)))  # Column 19 is "AppOrderID"

            # Update the "Order Status" column with OrderStatuses
            order_statuses = ", ".join(order_response.get("OrderStatuses", []))  # Convert list to comma-separated string
            self.table.setItem(row_position, 12, QTableWidgetItem(order_statuses))  # Column 12 is "Order Status"
            
            # Extract the latest status for further processing
            latest_status = order_response.get("OrderStatuses", ["Unknown"])[-1]

            # Log success
            self.parent.text_area.append(f"Order placed successfully: {order_response}")
            
            self.fetch_order_history(order_id, row_position, latest_status)
            
        else:
            # Log failure
            self.parent.text_area.append(f"Failed to place order: {order_response.get('message')}")

        # Hide the button if it exists
        if button:
            button.hide()


    def format_order_data(self, order_data):
        """
        Directly modify the order data to match the app.py backend's expectations.
        """
        # Map exchangeSegment to constants
        segment_map = {"NSEFO": "EXCHANGE_NSEFO", "NSECM": "EXCHANGE_NSECM"}
        order_data["exchangeSegment"] = segment_map.get(order_data["exchangeSegment"], order_data["exchangeSegment"])

        # Map productType to constants
        product_map = {"NRML": "PRODUCT_NRML", "MIS": "PRODUCT_MIS", "CNC": "PRODUCT_CNC"}
        order_data["productType"] = product_map.get(order_data["productType"], order_data["productType"])

        # Map orderType to constants
        order_type_map = {"LIMIT": "ORDER_TYPE_LIMIT", "MARKET": "ORDER_TYPE_MARKET",
                        "STOPLIMIT": "ORDER_TYPE_STOPLIMIT", "STOPMARKET": "ORDER_TYPE_STOPMARKET"}
        order_data["orderType"] = order_type_map.get(order_data["orderType"], order_data["orderType"])

        # Map orderSide to constants
        side_map = {"Buy": "TRANSACTION_TYPE_BUY", "Sell": "TRANSACTION_TYPE_SELL"}
        order_data["orderSide"] = side_map.get(order_data["orderSide"], order_data["orderSide"])

        # Convert numeric fields to correct types
        try:
            order_data["orderQuantity"] = int(order_data["orderQuantity"])
            order_data["limitPrice"] = float(order_data["limitPrice"]) if order_data["limitPrice"] != "None" else 0
            order_data["stopPrice"] = float(order_data["stopPrice"]) if order_data["stopPrice"] != "None" else 0
        except ValueError as e:
            self.parent.text_area.append(f"Error formatting numeric fields: {e}")
            
    def fetch_order_history(self, order_id, row_position, latest_status):
        """Fetch order history and update columns based on order status (Rejected or Filled)."""
        try:
            response = requests.get(f"http://localhost:5000/get_order_history", params={"appOrderID": order_id})
            if response.status_code == 200:
                response_data = response.json()
                if response_data["status"] == "success":
                    order_history = response_data["orderHistory"]

                    # If status is 'Rejected', update only CancelRejectReason
                    if latest_status == "Rejected":
                        cancel_reject_reason = order_history[-1].get("CancelRejectReason", "N/A")
                        self.table.setItem(row_position, 22, QTableWidgetItem(cancel_reject_reason))  # Update Trade History with rejection reason

                    # If status is 'Filled', update Buy/Sell price based on OrderSide
                    elif latest_status in ["Filled", "NewFilled"]:
                        # Update Trade History column with full order history for reference
                        self.table.setItem(row_position, 22, QTableWidgetItem(str(order_history)))
                        
                        # Update Buy/Sell Price column based on OrderSide
                        for entry in order_history:
                            if entry["OrderStatus"] in ["Filled", "NewFilled"]:
                                avg_price = entry.get("OrderAverageTradedPrice", "N/A")
                                if entry["OrderSide"] == "BUY":
                                    self.table.setItem(row_position, 13, QTableWidgetItem(str(avg_price)))  # Buy Price column
                                elif entry["OrderSide"] == "SELL":
                                    self.table.setItem(row_position, 16, QTableWidgetItem(str(avg_price)))  # Sell Price column
                else:
                    print("Failed to fetch order history:", response_data["message"])
            else:
                print("Failed to fetch order history:", response.json())
        except Exception as e:
            print(f"Error fetching order history: {e}")

    def handle_manual_order(self, row_position):
        """
        Add a button for manual order placement.
        """
        button = QPushButton("Place Order")
        button.clicked.connect(lambda: self.place_order(row_position, button))
        self.table.setCellWidget(row_position, 20, button)  # Place button in "Place Order" column
    
    def handle_automatic_order(self, row_position):
        """
        Automatically place an order in automatic mode based on CallType, OrderType, Exchange, Series, and Trading Symbol filters.
        """
        # Retrieve the order details from the table
        call_type = self.table.item(row_position, 25).text()  # Column 25 is CallType
        order_type = self.table.item(row_position, 1).text()  # Column 1 is orderside
        exchange = self.table.item(row_position, 2).text()  # Column 2 is ExchangeSegment
        series = self.table.item(row_position, 3).text()  # Column 3 is Series
        trading_symbol = self.table.item(row_position, 5).text()  # Column 5 is TradingSymbol

        # Retrieve the selected filters from the parent UI
        selected_call_type = self.parent.applied_call_type_label.text()
        selected_order_type = self.parent.applied_order_type_label.text()
        selected_exchange = self.parent.applied_exchange_label.text()
        selected_series = self.parent.applied_series_label.text()
        selected_trading_symbol = self.parent.applied_trading_symbol_label.text()

        # Check if the order matches the selected filters
        call_type_match = selected_call_type == "ALL" or call_type == selected_call_type
        order_type_match = selected_order_type == "ALL" or order_type == selected_order_type
        exchange_match = selected_exchange == "ALL" or exchange == selected_exchange
        series_match = selected_series == "ALL" or series == selected_series
        trading_symbol_match = selected_trading_symbol == "ALL" or trading_symbol == selected_trading_symbol

        if call_type_match and order_type_match and exchange_match and series_match and trading_symbol_match:
            # All filters match, place the order automatically
            self.table.setItem(row_position, 20, QTableWidgetItem("Placing Automatically..."))
            self.place_order(row_position)
        else:
            # If any filter doesn't match, handle as a manual order
            reason = []
            if not call_type_match:
                reason.append(f"CallType mismatch: {call_type} != {selected_call_type}")
            if not order_type_match:
                reason.append(f"OrderType mismatch: {order_type} != {selected_order_type}")
            if not exchange_match:
                reason.append(f"Exchange mismatch: {exchange} != {selected_exchange}")
            if not series_match:
                reason.append(f"Series mismatch: {series} != {selected_series}")
            if not trading_symbol_match:
                reason.append(f"TradingSymbol mismatch: {trading_symbol} != {selected_trading_symbol}")

            reason_text = "; ".join(reason)
            self.table.setItem(row_position, 20, QTableWidgetItem(f"Manual Placement Required: {reason_text}"))
            self.handle_manual_order(row_position)


    
    def update_ltp_column(self, message):
        """
        Process WebSocket messages and update the LTP column for matching rows.
        """
        try:
            message_data = json.loads(message)
            if "Touchline" in message_data and "ExchangeInstrumentID" in message_data:
                instrument_id = str(message_data["ExchangeInstrumentID"])
                ltp = message_data["Touchline"].get("LastTradedPrice", "0.0")

                # Update LTP for all rows with the same instrument
                row_count = self.table.rowCount()
                for row in range(row_count):
                    item_id = self.table.item(row, 4)  # Column 4 is ExchangeInstrumentID
                    if item_id and item_id.text() == instrument_id:
                        self.table.setItem(row, 11, QTableWidgetItem(str(ltp)))  # Update LTP column
        except json.JSONDecodeError:
            if hasattr(self.parent, 'text_area'):
                self.parent.text_area.append("Error: Failed to parse message for LTP update.")
        except Exception as e:
            if hasattr(self.parent, 'text_area'):
                self.parent.text_area.append(f"Error processing LTP update: {e}")




class WebSocketClientUI(QMainWindow):
   
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebSocket Client - Quant UI")

        # Backend setup
        self.backend = WebSocketClientBackend(message_callback=self.update_ui)

        # Define the settings file path
        self.SETTINGS_FILE = "settings.json"  # Path to the JSON file for saving settings
        # UI setup
        self.init_ui()

        self.execution_mode = "Manual"  # Default execution mode
        # Set default execution mode when the main window opens
        self.set_default_execution_mode()
        # Schedule tasks
        QTimer.singleShot(0, self.start_connection)
        QTimer.singleShot(0, self.update_margin_display)
    
    def open_settings_window(self, event):
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Top Section: User Name and Execution Mode
        top_layout = QVBoxLayout()
        
        self.user_name_label = QLabel("Fetching...")
        self.user_name_label.setAlignment(Qt.AlignCenter)
        self.user_name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_layout.addWidget(self.user_name_label)

        # Execution Mode Label with Icon
        execution_mode_layout = QHBoxLayout()

        # Execution Mode Label
        self.execution_mode_label = QLabel("Execution Mode: LIVE")
        self.execution_mode_label.setAlignment(Qt.AlignCenter)
        self.execution_mode_label.setStyleSheet("font-size: 14px; color: green; font-weight: bold;")
        execution_mode_layout.addWidget(self.execution_mode_label)

        # Add icon next to Execution Mode
        self.execution_mode_icon = QLabel(self)
        execution_icon_pixmap = QPixmap("edit.png").scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.execution_mode_icon.setPixmap(execution_icon_pixmap)

        # Connect the click event to open settings window
        self.execution_mode_icon.mousePressEvent = self.open_settings_window
        execution_mode_layout.addWidget(self.execution_mode_icon)

        # Align both in the center
        execution_mode_layout.setAlignment(Qt.AlignCenter)

        # Add the layout to the top layout
        top_layout.addLayout(execution_mode_layout)


        top_widget = QWidget()
        top_widget.setLayout(top_layout)
        main_layout.addWidget(top_widget)

        # Section to display applied settings
        self.applied_settings_widget = QWidget()
        settings_layout = QGridLayout()
    
        # Row 1: General Settings
        settings_layout.addWidget(QLabel("Max Amount:"), 0, 0)
        self.applied_max_amount_label = QLabel("N/A")
        settings_layout.addWidget(self.applied_max_amount_label, 0, 1)

        settings_layout.addWidget(QLabel("Max Profit:"), 0, 2)
        self.applied_max_profit_label = QLabel("N/A")
        settings_layout.addWidget(self.applied_max_profit_label, 0, 3)

        settings_layout.addWidget(QLabel("Max Loss:"), 0, 4)
        self.applied_max_loss_label = QLabel("N/A")
        settings_layout.addWidget(self.applied_max_loss_label, 0, 5)

        settings_layout.addWidget(QLabel("Trade Mode:"), 0, 6)

        self.applied_trade_mode_label = QLabel("LIVE")
        # Set the text color to green
        self.applied_trade_mode_label.setStyleSheet("color: green; font-weight: bold;font-size: 14px;")
        settings_layout.addWidget(self.applied_trade_mode_label, 0, 7)

        settings_layout.addWidget(QLabel("Net Available Margin:"), 0, 8)
        self.applied_net_margin_label = QLabel("N/A")
        settings_layout.addWidget(self.applied_net_margin_label, 0, 9)

        # Row 2: Trade Settings
        settings_layout.addWidget(QLabel("Call Type:"), 1, 0)
        self.applied_call_type_label = QLabel("ALL")
        settings_layout.addWidget(self.applied_call_type_label, 1, 1)

        settings_layout.addWidget(QLabel("Order Type:"), 1, 2)
        self.applied_order_type_label = QLabel("ALL")
        settings_layout.addWidget(self.applied_order_type_label, 1, 3)

        settings_layout.addWidget(QLabel("Exchange:"), 1, 4)
        self.applied_exchange_label = QLabel("ALL")
        settings_layout.addWidget(self.applied_exchange_label, 1, 5)

        settings_layout.addWidget(QLabel("Series:"), 1, 6)
        self.applied_series_label = QLabel("ALL")
        settings_layout.addWidget(self.applied_series_label, 1, 7)

        settings_layout.addWidget(QLabel("Trading Symbol:"), 1, 8)
        self.applied_trading_symbol_label = QLabel("ALL")
        settings_layout.addWidget(self.applied_trading_symbol_label, 1, 9)

        self.applied_settings_widget.setLayout(settings_layout)

        
       # Table Section
        self.table_widget = Table(self)  # Initialize the Table widget
        main_layout.addWidget(self.applied_settings_widget)
        main_layout.addWidget(self.table_widget)  # Add the table widget to the layout


        # Right panel for settings and logs
        right_layout = QVBoxLayout()

        # Manual Mode Label and Settings Icon
        mode_layout = QHBoxLayout()
        # Mode Label
        self.mode_label = QLabel("Statergy Logs")
        self.mode_label.setAlignment(Qt.AlignLeft)
        self.mode_label.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
        mode_layout.addWidget(self.mode_label)

        
       

        # Add settings icon
        self.settings_icon = QLabel(self)
        icon_pixmap = QPixmap("setting.png").scaled(20, 20)
        self.settings_icon.setPixmap(icon_pixmap)
        self.settings_icon.mousePressEvent = self.open_settings_window
        mode_layout.addWidget(self.settings_icon)

        right_layout.addLayout(mode_layout)

        # Add log area
        self.text_area = QTextEdit(self)
        self.text_area.setReadOnly(True)
        right_layout.addWidget(self.text_area)

        
        # Add a standard message input box
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText("Enter your message...")
        right_layout.addWidget(self.message_input)

        # Add a standard send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        right_layout.addWidget(self.send_button)
        # Combine layouts
        full_layout = QHBoxLayout()
        left_container = QWidget()
        left_container.setLayout(main_layout)
        right_container = QWidget()
        right_container.setLayout(right_layout)
        full_layout.addWidget(left_container, 3)
        full_layout.addWidget(right_container, 1)

        container = QWidget()
        container.setLayout(full_layout)
        self.setCentralWidget(container)
        self.load_settings()
    
    def save_settings(self, max_amount, max_profit, max_loss):
        """
        Save the given settings to a JSON file.
        """
        settings = {
            "MaxAmount": max_amount,
            "MaxProfit": max_profit,
            "MaxLoss": max_loss
        }
        try:
            with open(self.SETTINGS_FILE, "w") as file:
                json.dump(settings, file)
            self.text_area.append("Settings saved successfully.")
        except Exception as e:
            self.text_area.append(f"Error saving settings: {e}")
   
    def load_settings(self):
        """
        Load settings from the JSON file. If the file doesn't exist, create it with default settings.
        Send the loaded settings to the server.
        """
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, "r") as file:
                    settings = json.load(file)
            except Exception as e:
                self.text_area.append(f"Error loading settings: {e}")
                settings = self.save_default_settings()
        else:
            self.text_area.append("No settings file found. Using defaults.")
            settings = self.save_default_settings()

        # Update the UI with the loaded settings
        self.applied_max_amount_label.setText(settings.get("MaxAmount", "100000"))
        self.applied_max_profit_label.setText(settings.get("MaxProfit", "10000"))
        self.applied_max_loss_label.setText(settings.get("MaxLoss", "5000"))

        # Send loaded settings to the server
        self.send_loaded_settings_message(settings)

    def send_loaded_settings_message(self, settings):
        """
        Send the loaded settings to the server via the WebSocket backend.
        """
        try:
            message = {
                "System": "LoadedSettings",
                "Settings": settings
            }
            asyncio.create_task(self.backend.send_message(json.dumps(message)))
            self.text_area.append(f"Loaded settings sent to server: {message}")
        except Exception as e:
            self.text_area.append(f"Error sending loaded settings to server: {e}")

    def save_default_settings(self):
        """
        Save default settings to a JSON file.
        """
        default_settings = {
            "MaxAmount": "100000",
            "MaxProfit": "10000",
            "MaxLoss": "5000"
        }
        try:
            with open(self.SETTINGS_FILE, "w") as file:
                json.dump(default_settings, file)
            self.text_area.append("Default settings file created.")
        except Exception as e:
            self.text_area.append(f"Error saving default settings: {e}")
        return default_settings

    def start_connection(self):
        """
        Start the WebSocket connection and fetch the user profile.
        """
        client_name, client_id = self.backend.fetch_profile()
        self.user_name_label.setText(f"{client_name}")
        asyncio.create_task(self.backend.connect())
        
       

    def set_default_execution_mode(self):
        """
        Set the default execution mode when the main window opens.
        """
        mode = "Manual"  # Default mode
        self.execution_mode_label.setText(f"Execution Mode: {mode.upper()}")
        self.execution_mode_label.setStyleSheet("color: blue; font-weight: bold;")
        self.send_execution_mode_message(mode)

      
    def update_execution_mode(self, mode):
        """
        Update the execution mode dynamically.
        """
        self.execution_mode = mode
        self.execution_mode_label.setText(f"Execution Mode: {mode.upper()}")
        if mode.lower() == "manual":
            self.execution_mode_label.setStyleSheet("color: blue; font-weight: bold;")
        else:
            self.execution_mode_label.setStyleSheet("color: red; font-weight: bold;")
        self.text_area.append(f"Execution mode updated to: {mode}")

    def send_execution_mode_message(self, mode):
        """
        Send the execution mode message to the backend.
        """
        mode_message = {"System": "Mode", "Value": mode}
        asyncio.create_task(self.backend.send_message(json.dumps(mode_message)))
        self.text_area.append(f"Execution Mode Set: {mode}")

        
    def send_message(self):
        """
        Send a custom message through the WebSocket backend.
        """
        message = self.message_input.text()
        if message:
            asyncio.create_task(self.backend.send_message(message))
            self.text_area.append(f"You: {message}")
            self.message_input.clear()

    

    def open_settings_window(self, event):
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def update_margin_display(self):
        try:
            margin = self.backend.fetch_margin()
            if margin is not None:
                self.applied_net_margin_label.setText(f"{margin:.2f}")
                margin_update_message = {"System": "MarginUpdate", "NetMarginAvailable": margin}
                asyncio.create_task(self.backend.send_message(json.dumps(margin_update_message)))
                self.text_area.append(f"Net Margin Updated: {margin:.2f}")
            else:
                self.applied_net_margin_label.setText("Error")
        except Exception as e:
            self.text_area.append(f"Error updating margin: {e}")

    def update_ui(self, message):
        """
        Update the UI with new messages.
        """
        try:
            if message.startswith("Server: "):
                message = message[len("Server: "):]

            # Parse JSON if applicable
            parsed_message = json.loads(message) if message.startswith("{") else None

            if parsed_message:
                category = parsed_message.get("category")
                if category == "Ordercall":
                    # Existing logic for Ordercall
                    order_data = parsed_message.get("message", {})
                    strategy_name = order_data.get("strategyName", "Unknown")
                    order_side = order_data.get("orderside", "Unknown")
                    exchange_segment = order_data.get("exchangeSegment", "Unknown")
                    series = order_data.get("series", "Unknown")
                    exchange_instrument_id = order_data.get("exchangeInstrumentID", "Unknown")
                    trading_symbol = order_data.get("tradingSymbol", "Unknown")
                    order_type = order_data.get("orderType", "Unknown")
                    product_Type = order_data.get("productType", "Unknown")
                    order_quantity = str(order_data.get("orderQuantity", "0"))
                    limit_price = str(order_data.get("limitPrice", "0"))
                    stop_price = str(order_data.get("stopPrice", "Unknown"))
                    call_type = order_data.get( "calltype","Unknown")

                    self.table_widget.add_order(
                        strategy_name, order_side, exchange_segment, series,
                        exchange_instrument_id, trading_symbol, order_type,
                        product_Type, order_quantity, limit_price, stop_price,call_type
                    )

                    self.text_area.append(
                        f"Order added: ExchangeSegment={exchange_segment}, InstrumentID={exchange_instrument_id}"
                    )
                    self.update_margin_display()  # Update margin after adding an order

                elif category == "Modification":
                    # Handle Modification category
                    modification_data = parsed_message.get("message", {})
                    self.modify_row_by_strategy_name(modification_data)

                elif category == "chat":
                    # Handle chat messages
                    chat_message = parsed_message.get("message", "No message")
                    self.text_area.append(f"Server Chat: {chat_message}")

                elif category == "ltp_update":
                    # Update LTP column for LTP updates
                    self.update_ltp_column(message)

                elif category == "Cancel":
                    # Handle Cancel category
                    cancel_data = parsed_message.get("message", {})
                    self.cancel_order_by_strategy_name(cancel_data)

                elif category == "Exit":
                    # Handle Exit category
                    exit_data = parsed_message.get("message", {})
                    self.exit_order_by_strategy_name(exit_data)    
                else:
                    # Handle other categories
                    self.text_area.append(f"Server (Parsed): {parsed_message}")
            else:
                # Handle plain text messages
                self.text_area.append(f"Plain Text: {message}")
        except json.JSONDecodeError as e:
            self.text_area.append(f"Error decoding JSON: {message}\n{e}")
        except Exception as e:
            self.text_area.append(f"Error processing message: {message}\n{e}")

    def modify_row_by_strategy_name(self, modification_data):
        """
        Modify a row in the table based on the strategyName.
        """
        strategy_name = modification_data.get("strategyName")
        if not strategy_name:
            self.text_area.append("Error: Modification message missing 'strategyName'.")
            return

        row_count = self.table_widget.table.rowCount()
        for row in range(row_count):
            # Check if the strategyName matches
            item = self.table_widget.table.item(row, 0)  # Assuming strategyName is in column 0
            if item and item.text() == strategy_name:
                # Update the row with new values
                self.table_widget.table.setItem(row, 1, QTableWidgetItem(modification_data.get("orderside", "")))
                self.table_widget.table.setItem(row, 2, QTableWidgetItem(modification_data.get("exchangeSegment", "")))
                self.table_widget.table.setItem(row, 3, QTableWidgetItem(modification_data.get("series", "")))
                self.table_widget.table.setItem(row, 4, QTableWidgetItem(modification_data.get("exchangeInstrumentID", "")))
                self.table_widget.table.setItem(row, 5, QTableWidgetItem(modification_data.get("tradingSymbol", "")))
                self.table_widget.table.setItem(row, 6, QTableWidgetItem(modification_data.get("orderType", "")))
                self.table_widget.table.setItem(row, 7, QTableWidgetItem(modification_data.get("productType", "")))
                self.table_widget.table.setItem(row, 8, QTableWidgetItem(str(modification_data.get("orderQuantity", 0))))
                self.table_widget.table.setItem(row, 9, QTableWidgetItem(str(modification_data.get("limitPrice", 0))))
                self.table_widget.table.setItem(row, 10, QTableWidgetItem(str(modification_data.get("stopPrice", 0))))
                self.table_widget.table.setItem(row, 23, QTableWidgetItem("Modified"))  # Assuming column 23 is "Action"
                self.text_area.append(f"Row updated for strategyName: {strategy_name}")
                return

        # If no matching row is found
        self.text_area.append(f"Error: No row found with strategyName: {strategy_name}")

    def cancel_order_by_strategy_name(self, cancel_data):
        """
        Cancel an order in the table based on the strategyName.
        """
        strategy_name = cancel_data.get("strategyName")
        if not strategy_name:
            self.text_area.append("Error: Cancel message missing 'strategyName'.")
            return

        row_count = self.table_widget.table.rowCount()
        for row in range(row_count):
            # Check if the strategyName matches
            item = self.table_widget.table.item(row, 0)  # Assuming strategyName is in column 0
            if item and item.text() == strategy_name:
                # Update the "Action" column to "Cancelled"
                self.table_widget.table.setItem(row, 23, QTableWidgetItem("Cancelled"))  # Assuming column 23 is "Action"
                self.text_area.append(f"Order cancelled for strategyName: {strategy_name}")
                return

        # If no matching row is found
        self.text_area.append(f"Error: No row found with strategyName: {strategy_name}")

    def exit_order_by_strategy_name(self, exit_data):
        """
        Place an exit order for a specific strategyName and update the Action column to 'Exited'.
        """
        strategy_name = exit_data.get("strategyName")
        if not strategy_name:
            self.text_area.append("Error: Exit message missing 'strategyName'.")
            return

        row_count = self.table_widget.table.rowCount()
        for row in range(row_count):
            # Check if the strategyName matches
            item = self.table_widget.table.item(row, 0)  # Assuming strategyName is in column 0
            if item and item.text() == strategy_name:
                # Retrieve the current order details
                current_side = self.table_widget.table.item(row, 1).text()  # Column 1 is orderside
                exchange_segment = self.table_widget.table.item(row, 2).text()  # Column 2 is exchangeSegment
                instrument_id = self.table_widget.table.item(row, 4).text()  # Column 4 is exchangeInstrumentID
                product_type = self.table_widget.table.item(row, 7).text()  # Column 7 is productType
                order_quantity = self.table_widget.table.item(row, 8).text()  # Column 8 is orderQuantity

                # Map plain text to constants
                side_mapping = {
                    "Buy": "TRANSACTION_TYPE_BUY",
                    "Sell": "TRANSACTION_TYPE_SELL"
                }
                current_side_constant = side_mapping.get(current_side)

                if not current_side_constant:
                    self.text_area.append(f"Error: Unknown order side '{current_side}' for strategyName: {strategy_name}")
                    return

                # Reverse the order side for exit
                exit_side = (
                    "TRANSACTION_TYPE_SELL" if current_side_constant == "TRANSACTION_TYPE_BUY"
                    else "TRANSACTION_TYPE_BUY"
                )

                # Prepare the exit order data
                exit_order_data = {
                    "exchangeSegment": exchange_segment,
                    "exchangeInstrumentID": instrument_id,
                    "productType": product_type,
                    "orderType": "ORDER_TYPE_MARKET",  # Exit with market order
                    "orderSide": exit_side,
                    "timeInForce": "VALIDITY_DAY",
                    "disclosedQuantity": 0,
                    "orderQuantity": order_quantity,
                    "limitPrice": 0,
                    "stopPrice": 0,
                    "orderUniqueIdentifier": "exit_rattle"  # Unique identifier for exit orders
                }

                # Log the exit order data for debugging
                self.text_area.append(f"Exit Order Data: {json.dumps(exit_order_data, indent=2)}")

                # Place the exit order via the backend
                exit_response = self.backend.place_order(exit_order_data)

                if exit_response.get("status") == "success":
                    # Update the "Order Status" column with exit order status
                    order_statuses = ", ".join(exit_response.get("OrderStatuses", []))
                    self.table_widget.table.setItem(row, 12, QTableWidgetItem(order_statuses))  # Column 12 is Order Status

                    # Update the "Action" column to 'Exited'
                    self.table_widget.table.setItem(row, 23, QTableWidgetItem("Exited"))  # Column 23 is Action

                    # Log the exit order details
                    self.text_area.append(f"Exit order placed successfully for strategyName: {strategy_name}. Response: {exit_response}")
                else:
                    # Log failure details
                    self.text_area.append(f"Failed to place exit order for strategyName: {strategy_name}. Error: {exit_response.get('message')}")

                return

        # If no matching row is found
        self.text_area.append(f"Error: No row found with strategyName: {strategy_name}")


                
    async def close_connection(self):
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.log_area.append("Disconnected from WebSocket server")

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    main_window = WebSocketClientUI()
    main_window.show()
    sys.exit(app.exec_()) 