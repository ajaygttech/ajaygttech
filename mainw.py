import sys
import asyncio
import requests
import websockets
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QTextEdit, QSplitter, QAction, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import json
import os
import threading
import subprocess

from multileg import MultilegTab
from terminal import TerminalTab
from orderbook_dialog import OrderBookDialog
from trade_book import TradeBookDialog
from WebSocketClient import WebSocketClient
from profile_dialog import ProfileDialog
from margin_dialog import MarginDialog
# from algo import AlgoTab, ResearchAlgo  # Import AlgoTab and ResearchAlgo from algo.py
from datetime import datetime, timedelta
from net_position import NetPositionDialog
from quant_ui import WebSocketClientUI
from qasync import QEventLoop
import market
from Connect import XTSConnect


class OrderBookUpdater(QThread):
    data_fetched = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True

    def run(self):
        """Fetch order book data from the API in a separate thread."""
        while self._is_running:
            try:
                response = requests.get("http://127.0.0.1:5000/order_book")
                response.raise_for_status()
                data = response.json()["data"]
                self.data_fetched.emit(data)
            except requests.RequestException as e:
                print(f"Error fetching order book data: {e}")
            self._is_running = False

    def stop(self):
        """Stop the thread gracefully."""
        self._is_running = False
        self.wait()
class LogWindow(QMainWindow):
    """Window to display stored log messages with timestamps."""

    def __init__(self, log_file_path):
        super().__init__()
        self.setWindowTitle("WebSocket Log")
        self.setGeometry(150, 150, 600, 400)
        
        self.log_file_path = log_file_path
        self.text_display = QTextEdit(self)
        self.text_display.setReadOnly(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.text_display)
        
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Load and display initial log data
        self.load_log_data()

    def load_log_data(self):
        """Load log data from file and display it."""
        if os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'r') as log_file:
                log_data = json.load(log_file)
                self.text_display.clear()
                for entry in log_data:
                    timestamp = entry["timestamp"]
                    message = entry["message"]
                    self.text_display.append(f"{timestamp}: {message}")

    def append_message(self, timestamp, message):
        """Append a message to the log display."""
        self.text_display.append(f"{timestamp}: {message}")

class MainWindow(QMainWindow):
    orderbook_signal = pyqtSignal(dict)

    def __init__(self, market_api_key, market_api_secret, order_user_id, order_token, market_data_token, market_user_id):
        super().__init__()
        # self.xt_market = None
        self.market_api_key = market_api_key
        self.market_api_secret = market_api_secret
        self.order_user_id = order_user_id
        self.order_token = order_token
        self.market_data_token = market_data_token
        self.market_user_id = market_user_id
        self.xt_market = XTSConnect(market_api_key, market_api_secret, source="WEBAPI")
        self.xt_market.token = market_data_token  # Set the token for xt_market
        # Run market data in a separate thread
        self.start_market_thread()

    def start_market_thread(self):
        """Start a separate thread for market data handling."""
        def run_market():
            try:
                market.start_test(self.xt_market, self.market_user_id, self.market_data_token)
                print("market.start_test completed successfully.")
            except Exception as e:
                print(f"Error in market.start_test: {e}")

        market_thread = threading.Thread(target=run_market, daemon=True)
        market_thread.start()

        self.setWindowTitle('Interactive Socket and Orders')
        self.setGeometry(100, 100, 800, 600)
        # Initialize log file
        self.log_file_path = "websocket_log.json"
        self.log_window = LogWindow(self.log_file_path)  # Ensure log_window is initialized here
        
        # Ensure log file exists
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w') as log_file:
                json.dump([], log_file)
        # Set up menu bar
        self.create_menu_bar()
        self.orderbook_dialog = None
        self.orderbook_updater = None

        

        # Main layout with a vertical splitter for tabs and bottom message box
        main_layout = QVBoxLayout()
        splitter = QSplitter(Qt.Vertical)

        # Initialize tab widget for Multileg, Terminal, and Algo tabs
        self.tab_widget = QTabWidget(self)
        self.websocket_client = WebSocketClient()
        self.websocket_client.start()

        # Add Multileg Tab
        self.multileg_tab = MultilegTab(self.websocket_client)
        self.tab_widget.addTab(self.multileg_tab, "Multileg")

        # Add Terminal Tab
        self.terminal_tab = TerminalTab(self.websocket_client)
        self.tab_widget.addTab(self.terminal_tab, "Terminal")

        # # Add Algo Tab
        # algo_client = ResearchAlgo("ws://localhost:8800")
        # self.algo_tab = AlgoTab(algo_client)
        # self.algo_tab.subscribe_request.connect(self.websocket_client.send_subscription)
        # self.websocket_client.response_received.connect(self.algo_tab.update_ltp_column)  # Connect for LTP updates
        # algo_client.start()
        # self.tab_widget.addTab(self.algo_tab, "Algo")

    
        # Add Quant Tab
        self.quant_tab = WebSocketClientUI()
        self.quant_tab.table_widget.subscribe_request.connect(self.websocket_client.send_subscription)
        self.websocket_client.response_received.connect(self.quant_tab.table_widget.update_ltp_column)
        self.tab_widget.addTab(self.quant_tab, "Quant")


        # Set tabs to appear at the bottom
        self.tab_widget.setTabPosition(QTabWidget.South)

        # Add tab widget to the splitter
        splitter.addWidget(self.tab_widget)

        # Add Interactive Socket message display box at the bottom
        self.message_box = QTextEdit(self)
        self.message_box.setReadOnly(True)
        self.message_box.setPlaceholderText("Interactive and Order WebSocket messages will appear here...")
        self.message_box.setFixedHeight(50)
        splitter.addWidget(self.message_box)

        # Add splitter to main layout
        main_layout.addWidget(splitter)

        # Set central widget to main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Start a single WebSocket thread for combined messages
        self.socket_thread = WebSocketThread("ws://localhost:8765")
        self.socket_thread.message_signal.connect(self.display_message)
        self.socket_thread.message_signal.connect(self.refresh_order_book_if_open)
        self.socket_thread.start()

    
    def create_menu_bar(self):
        # Create the menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        # Add "Log" action to File menu
        log_action = QAction("Log", self)
        log_action.triggered.connect(self.show_log_window)
        file_menu.addAction(log_action)

        # Other menu actions (e.g., Open, Save, Exit)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Market menu
        market_menu = menu_bar.addMenu("Market")
        
        # Add actions to Market menu
        market_data_action = QAction("Market Data", self)
        trade_action = QAction("Trade", self)
        trade_action.triggered.connect(self.show_trade_book_dialog)  # Connect the trade action
        orderbook_action = QAction("Orderbook", self)
        profile_action = QAction("Profile", self)
        margin_action = QAction("Margin", self)
        net_position_action = QAction("Net Position", self)
        net_position_action.triggered.connect(self.show_net_position_dialog)
        market_menu.addAction(net_position_action)
        profile_action.triggered.connect(self.show_profile_dialog)
        margin_action.triggered.connect(self.show_margin_dialog)
        orderbook_action.triggered.connect(self.show_orderbook_dialog)

        market_menu.addAction(market_data_action)
        market_menu.addAction(trade_action)
        market_menu.addAction(orderbook_action)
        market_menu.addAction(profile_action)
        market_menu.addAction(margin_action)

    def show_net_position_dialog(self):
        # Check if the dialog instance already exists and is not closed
        if not hasattr(self, 'net_position_dialog') or self.net_position_dialog is None:
            # Pass self.websocket_client to the NetPositionDialog
            self.net_position_dialog = NetPositionDialog(self.websocket_client)
            
            # Connect the WebSocket client's response signal to update LTP in NetPositionDialog
            self.websocket_client.response_received.connect(self.net_position_dialog.update_ltp_column)

        self.net_position_dialog.exec_()

    def show_profile_dialog(self):
        """Fetch and display profile data from the API in a custom dialog."""
        try:
            response = requests.get("http://127.0.0.1:5000/get_profile")
            response.raise_for_status()
            profile_data = response.json()

            profile_dialog = ProfileDialog(profile_data)
            profile_dialog.exec_()

        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Error fetching profile data: {e}")

    def show_margin_dialog(self):
        """Fetch and display margin data from the API in a custom dialog."""
        try:
            response = requests.get("http://127.0.0.1:5000/get_balance")
            response.raise_for_status()
            margin_data = response.json()

            margin_dialog = MarginDialog(margin_data)
            margin_dialog.exec_()

        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Error fetching margin data: {e}")

    def show_orderbook_dialog(self):
        """Show the OrderBookDialog and fetch data to display."""
        try:
            response = requests.get("http://127.0.0.1:5000/order_book")
            response.raise_for_status()
            data = response.json()["data"]

            if self.orderbook_dialog and self.orderbook_dialog.isVisible():
                self.orderbook_dialog.data = data
                self.orderbook_dialog.populate_table()
            else:
                self.orderbook_dialog = OrderBookDialog(data)
                self.orderbook_dialog.show()

        except requests.RequestException as e:
            print(f"Error fetching order book data: {e}")
    def show_trade_book_dialog(self):
        """Fetch trade book data and display it in a dialog."""
        try:
            # Fetch data from the server
            response = requests.get("http://127.0.0.1:5000/trade_book")
            response.raise_for_status()
            trade_data = response.json().get("data", [])

            # Open TradeBookDialog with fetched data
            trade_dialog = TradeBookDialog(trade_data)
            trade_dialog.exec_()

        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Error fetching trade book data: {e}")
            
    def refresh_order_book_if_open(self, message):
        """Start background update if the OrderBookDialog is currently open and the message is relevant."""
        if "Order placed" in message and self.orderbook_dialog and self.orderbook_dialog.isVisible():
            self.orderbook_updater = OrderBookUpdater(self)
            self.orderbook_updater.data_fetched.connect(self.update_order_book_data)
            self.orderbook_updater.start()

    def update_order_book_data(self, data):
        """Update the order book dialog with new data."""
        if self.orderbook_dialog and self.orderbook_dialog.isVisible():
            self.orderbook_dialog.data = data
            self.orderbook_dialog.populate_table()

    def closeEvent(self, event):
        """Override close event to stop threads gracefully."""
        if self.orderbook_updater and self.orderbook_updater.isRunning():
            self.orderbook_updater.stop()
        if self.socket_thread.isRunning():
            self.socket_thread.terminate()
        event.accept()

    def keyPressEvent(self, event):
        """Override key press event to detect F3 and F8 key presses."""
        if event.key() == Qt.Key_F3:
            self.show_orderbook_dialog()  # Existing F3 key handling for order book
        elif event.key() == Qt.Key_F8:
            self.show_trade_book_dialog()  # New F8 key handling for trade book


    def show_log_window(self):
        """Show the log window."""
        self.log_window.show()

    def display_message(self, message):
        self.message_box.append(message)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.save_message_to_log(timestamp, message)
        self.log_window.append_message(timestamp, message)

    def save_message_to_log(self, timestamp, message):
        """Append each message with a timestamp to the JSON log file, keeping only one day's messages."""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r') as log_file:
                    log_data = json.load(log_file)
            else:
                log_data = []

            # Add new message
            log_data.append({"timestamp": timestamp, "message": message})

            # Filter messages to keep only those within the last day
            one_day_ago = datetime.now() - timedelta(days=1)
            log_data = [
                entry for entry in log_data
                if datetime.strptime(entry["timestamp"], '%Y-%m-%d %H:%M:%S') > one_day_ago
            ]

            # Write updated log data back to file
            with open(self.log_file_path, 'w') as log_file:
                json.dump(log_data, log_file, indent=4)
        except Exception as e:
            print(f"Error saving message to log: {e}")
    

class WebSocketThread(QThread):
    message_signal = pyqtSignal(str)

    def __init__(self, uri):
        super().__init__()
        self.uri = uri

    async def connect_to_server(self):
        async with websockets.connect(self.uri) as websocket:
            self.message_signal.emit(f"Connected to WebSocket server at {self.uri}.")
            try:
                while True:
                    message = await websocket.recv()
                    self.message_signal.emit(message)
            except websockets.ConnectionClosed:
                self.message_signal.emit(f"Connection to WebSocket server at {self.uri} closed.")

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect_to_server())

# Main application setup
if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)  # Integrate PyQt and asyncio event loops
    asyncio.set_event_loop(loop)  # Set the qasync loop as the default asyncio loop

    window = MainWindow()
    window.show()

    with loop:  # Start the integrated event loop
        loop.run_forever()