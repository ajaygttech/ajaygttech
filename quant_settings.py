from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox, QLabel,
    QLineEdit, QComboBox, QPushButton, QWidget
)
from PyQt5.QtCore import Qt
import asyncio
import os
from PyQt5.QtWidgets import QMessageBox
import json

class SettingsWindow(QMainWindow):
    """
    A child window for displaying and applying general and trade settings.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 500)
        self.parent = parent
        self.init_ui()
        

    

    def init_ui(self):
        # Execution Mode checkboxes
        execution_mode_group = QGroupBox("Execution Mode")
        execution_mode_layout = QHBoxLayout()
        self.manual_checkbox = QCheckBox("Manual")
        self.automatic_checkbox = QCheckBox("Automatic")

       

        # Ensure only one checkbox is checked at a time
        self.manual_checkbox.stateChanged.connect(self.on_manual_selected)
        self.automatic_checkbox.stateChanged.connect(self.on_automatic_selected)

        execution_mode_layout.addWidget(self.manual_checkbox)
        execution_mode_layout.addWidget(self.automatic_checkbox)
        execution_mode_group.setLayout(execution_mode_layout)

        # General Settings group box
        general_settings_group = QGroupBox("General Settings")
        general_settings_layout = QVBoxLayout()

        self.max_amount_input = QLineEdit(self)
        self.max_amount_input.setDisabled(True)  # Disable by default
        general_settings_layout.addWidget(QLabel("Set Max Amount:"))
        general_settings_layout.addWidget(self.max_amount_input)

        self.max_profit_input = QLineEdit(self)
        self.max_profit_input.setDisabled(True)  # Disable by default
        general_settings_layout.addWidget(QLabel("Set Max Profit:"))
        general_settings_layout.addWidget(self.max_profit_input)

        self.max_loss_input = QLineEdit(self)
        self.max_loss_input.setDisabled(True)  # Disable by default
        general_settings_layout.addWidget(QLabel("Set Max Loss:"))
        general_settings_layout.addWidget(self.max_loss_input)

        self.trade_mode_combo = QComboBox()
        self.trade_mode_combo.addItems(["Live"])
        self.trade_mode_combo.setDisabled(True)  # Disable by default
        general_settings_layout.addWidget(QLabel("Trade Mode:"))
        general_settings_layout.addWidget(self.trade_mode_combo)

        self.general_apply_button = QPushButton("Apply Settings")
        self.general_apply_button.setDisabled(True)  # Disable by default
        self.general_apply_button.clicked.connect(self.gen_apply_settings)
        general_settings_layout.addWidget(self.general_apply_button)
        general_settings_group.setLayout(general_settings_layout)

        # Trade Settings group box
        trade_settings_group = QGroupBox("Trade Settings")
        trade_settings_layout = QVBoxLayout()

        self.call_type_combo = QComboBox()
        self.call_type_combo.addItems(["ALL", "Intraday", "Delivery", "POSITIONAL", "HERO ZERO", "OPTION TRADE"])
        self.call_type_combo.setDisabled(True)  # Disable by default
        trade_settings_layout.addWidget(QLabel("Call Type:"))
        trade_settings_layout.addWidget(self.call_type_combo)

        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["ALL", "Buy", "Sell"])
        self.order_type_combo.setDisabled(True)  # Disable by default
        trade_settings_layout.addWidget(QLabel("Order Type:"))
        trade_settings_layout.addWidget(self.order_type_combo)

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["ALL", "NSECM", "NSEFO"])
        self.exchange_combo.setDisabled(True)  # Disable by default
        trade_settings_layout.addWidget(QLabel("Exchange:"))
        trade_settings_layout.addWidget(self.exchange_combo)

        self.series_combo = QComboBox()
        self.series_combo.addItems(["ALL", "OPTIDX", "FUTIDX", "FUTSTK", "OPTSTK", "EQ"])
        self.series_combo.setDisabled(True)  # Disable by default
        trade_settings_layout.addWidget(QLabel("Series:"))
        trade_settings_layout.addWidget(self.series_combo)

        self.trading_symbol_input = QLineEdit(self)
        self.trading_symbol_input.setPlaceholderText("Enter Trading Symbol...")
        self.trading_symbol_input.setDisabled(True)  # Disable by default

        # Ensure input is always in uppercase
        self.trading_symbol_input.textChanged.connect(
            lambda text: self.trading_symbol_input.setText(text.upper())
        )

        trade_settings_layout.addWidget(QLabel("Trading Symbol:"))
        trade_settings_layout.addWidget(self.trading_symbol_input)

        trade_settings_group.setLayout(trade_settings_layout)

        # Apply settings button
        self.set_settings_button = QPushButton("Trade Settings")
        self.set_settings_button.setDisabled(True)  # Disable by default
        self.set_settings_button.clicked.connect(self.apply_trade_settings)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(execution_mode_group)
        main_layout.addWidget(general_settings_group)
        main_layout.addWidget(trade_settings_group)
        main_layout.addWidget(self.set_settings_button)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

   

    def on_manual_selected(self, state):
        if state == Qt.Checked:
            self.automatic_checkbox.setChecked(False)
            self.parent.execution_mode_label.setText("Execution Mode: MANUAL")
            self.parent.execution_mode_label.setStyleSheet("color: blue; font-weight: bold;")
            self.parent.send_execution_mode_message("Manual")
            self.parent.update_execution_mode("Manual")

            # Disable General and Trade Settings
            self.toggle_settings(enabled=False)

    def on_automatic_selected(self, state):
        if state == Qt.Checked:
            # Show a warning message
            warning_message = QMessageBox(self)
            warning_message.setWindowTitle("Warning")
            warning_message.setIcon(QMessageBox.Warning)
            warning_message.setText(
                "<h3 style='color: red;'>Do you want to execute orders automatically?</h3>"
                "<p>Enabling <strong>Automatic Execution Mode</strong> will allow the system to place orders without manual intervention.</p>"
            )
            warning_message.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            warning_message.setDefaultButton(QMessageBox.Cancel)

            response = warning_message.exec_()
            if response == QMessageBox.Ok:
                self.manual_checkbox.setChecked(False)
                self.parent.execution_mode_label.setText("Execution Mode: AUTOMATIC")
                self.parent.execution_mode_label.setStyleSheet("color: red; font-weight: bold;")
                self.parent.send_execution_mode_message("Automatic")
                self.parent.update_execution_mode("Automatic")

                # Enable General and Trade Settings
                self.toggle_settings(enabled=True)
            else:
                self.automatic_checkbox.setChecked(False)
                self.manual_checkbox.setChecked(True)

    def toggle_settings(self, enabled):
        """
        Enable or disable the General and Trade Settings sections.
        """
        self.max_amount_input.setEnabled(enabled)
        self.max_profit_input.setEnabled(enabled)
        self.max_loss_input.setEnabled(enabled)
        self.trade_mode_combo.setEnabled(enabled)
        self.general_apply_button.setEnabled(enabled)

        self.call_type_combo.setEnabled(enabled)
        self.order_type_combo.setEnabled(enabled)
        self.exchange_combo.setEnabled(enabled)
        self.series_combo.setEnabled(enabled)
        self.trading_symbol_input.setEnabled(enabled)
        self.set_settings_button.setEnabled(enabled)
        
    def gen_apply_settings(self):
        """
        Apply settings and update the main window labels.
        """
        max_amount = self.max_amount_input.text()
        max_profit = self.max_profit_input.text()
        max_loss = self.max_loss_input.text()
        trade_mode = self.trade_mode_combo.currentText()

        # Validate inputs
        if not max_amount.isdigit() or not max_profit.isdigit() or not max_loss.isdigit():
            self.parent.text_area.append("Error: General settings must be numeric values.")
            return

        # Update labels in the main window
        self.parent.applied_max_amount_label.setText(max_amount)
        self.parent.applied_max_profit_label.setText(max_profit)
        self.parent.applied_max_loss_label.setText(max_loss)
        self.parent.applied_trade_mode_label.setText(trade_mode)

        # Save settings to JSON
        self.parent.save_settings(max_amount, max_profit, max_loss)

        # Prepare and log settings messages
        general_settings_message = {
            "System": "Settings",
            "MaxAmount": int(max_amount),
            "MaxProfit": int(max_profit),
            "MaxLoss": int(max_loss),
            "TradeMode": trade_mode,
        }

        # Send messages to the backend
        asyncio.create_task(self.parent.backend.send_message(json.dumps(general_settings_message)))

        # Log the applied settings
        self.parent.text_area.append(f"Settings Applied: {general_settings_message}")


       

    def apply_trade_settings(self):
        """
        Apply settings and update the main window labels.
        """
      
        call_type = self.call_type_combo.currentText()
        order_type = self.order_type_combo.currentText()
        exchange = self.exchange_combo.currentText()
        series = self.series_combo.currentText()
        trading_symbol = self.trading_symbol_input.text().strip()

        if not trading_symbol:
            trading_symbol = "ALL"

 

        # Update labels in the main window
       
        self.parent.applied_call_type_label.setText(call_type)
        self.parent.applied_order_type_label.setText(order_type)
        self.parent.applied_exchange_label.setText(exchange)
        self.parent.applied_series_label.setText(series)
        self.parent.applied_trading_symbol_label.setText(trading_symbol)

        
        trade_settings_message = {
            "CallType": call_type,
            "OrderType": order_type,
            "Exchange": exchange,
            "Series": series,
            "TradingSymbol": trading_symbol,
        }

        # Send messages to the backend
  
        asyncio.create_task(self.parent.backend.send_message(json.dumps(trade_settings_message)))

        # Log the applied settings
       
        self.parent.text_area.append(f"Trade Settings Applied: {trade_settings_message}")

        # Close the settings window
        self.close()

    def handle_trade_settings(self):
        """
        Handle the logic for the Trade Settings button.
        """
        self.parent.text_area.append("Trade Settings button clicked!")
        # Additional functionality for Trade Settings can be implemented here.

        pass
