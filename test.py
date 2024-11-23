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
        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels(["strategyName", "orderside", "exchangeSegment","series","exchangeInstrumentID","tradingSymbol","orderType","productType","orderQuantity","limitPrice","stopPrice","LTP","NA","NA"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def add_order(self, strategy_name,order_side,exchange_segment,series, exchange_instrument_id,trading_symbol,order_type,product_Type,order_quantity,limit_price,stop_price ):

        """
        Add a new row to the table for an order.
        
        """
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(strategy_name))
        self.table.setItem(row_position, 1, QTableWidgetItem(order_side))
        self.table.setItem(row_position, 2, QTableWidgetItem(exchange_segment))
        self.table.setItem(row_position, 3, QTableWidgetItem(series))
        self.table.setItem(row_position, 4, QTableWidgetItem(exchange_instrument_id))
        self.table.setItem(row_position, 5, QTableWidgetItem(trading_symbol))
        self.table.setItem(row_position, 6, QTableWidgetItem(order_type))
        self.table.setItem(row_position, 7, QTableWidgetItem(product_Type))
        self.table.setItem(row_position, 8, QTableWidgetItem(order_quantity))
        self.table.setItem(row_position, 9, QTableWidgetItem(limit_price))
        self.table.setItem(row_position, 10, QTableWidgetItem(stop_price))
        self.table.setItem(row_position, 11, QTableWidgetItem("0"))  # Default LTP as 0
        self.table.setItem(row_position, 12, QTableWidgetItem("0"))
        self.table.setItem(row_position, 13, QTableWidgetItem("0"))
        

        # Emit subscription request
        segment_code = self.SEGMENT_CODE_MAP.get(exchange_segment, "Unknown")
        self.subscribe_request.emit(segment_code, instrument_id)

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
                row_count = self.table_widget.table.rowCount()
                for row in range(row_count):
                    item_id = self.table_widget.table.item(row, 4)  # Column 1 is Exchange Instrument ID
                    if item_id and item_id.text() == instrument_id:
                        self.table_widget.table.setItem(row, 11, QTableWidgetItem(str(ltp)))  # Update LTP column
                        self.text_area.append(f"LTP Updated: InstrumentID={instrument_id}, LTP={ltp}")
        except json.JSONDecodeError:
            self.text_area.append("Error: Failed to parse message for LTP update.")
        except Exception as e:
            self.text_area.append(f"Error processing LTP update: {e}")



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
                    # Handle Ordercall category
                    order_data = parsed_message.get("message", {})
                   
                    strategy_name = order_data.get("strategyName", "Unknown")
                    order_side = order_data.get("orderside", "Unknown")
                    exchange_segment = order_data.get("exchangeSegment", "Unknown")
                    series = order_data.get("series", "Unknown")
                    exchange_instrument_id = order_data.get("exchangeInstrumentID", "Unknown")

                    trading_symbol = order_data.get("tradingSymbol", "Unknown")
                    order_type = order_data.get("orderType", "Unknown")
                    product_Type = order_data.get("productType", "Unknown")
                    order_quantity = order_data.get("orderQuantity", "Unknown")
                    limit_price = order_data.get("limitPrice", "Unknown")
                    stop_price = order_data.get("stopPrice", "Unknown")
                   

                    self.table_widget.add_order(strategy_name,order_side,exchange_segment,series, exchange_instrument_id,trading_symbol,order_type,product_Type,order_quantity,limit_price,stop_price )

                    self.text_area.append(
                        f"Order added: ExchangeSegment={exchange_segment}, InstrumentID={exchange_instrument_id}"
                    )
                    self.update_margin_display()  # Update margin after adding an order

                elif category == "chat":
                    # Handle chat messages
                    chat_message = parsed_message.get("message", "No message")
                    self.text_area.append(f"Server Chat: {chat_message}")

                elif category == "ltp_update":
                    # Update LTP column for LTP updates
                    self.update_ltp_column(message)

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