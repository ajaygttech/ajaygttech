import sys
import requests
from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout, QGridLayout, QMessageBox, QComboBox, QLabel, QDoubleSpinBox, QSpinBox, QApplication, QHBoxLayout
from PyQt5.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, QObject
from PyQt5.QtGui import QFont


class OrderSignals(QObject):
    order_summary_signal = pyqtSignal(int, int)


class OrderPlacementTask(QRunnable):
    def __init__(self, order_data, order_number, signals):
        super().__init__()
        self.order_data = order_data
        self.order_number = order_number
        self.signals = signals

    def run(self):
        """Place a single order and emit success or failure."""
        try:
            response = requests.post('http://127.0.0.1:5000/place_order', json=self.order_data)
            if response.status_code == 200:
                self.signals.order_summary_signal.emit(1, 0)  # Success
            else:
                self.signals.order_summary_signal.emit(0, 1)  # Failure
        except Exception:
            self.signals.order_summary_signal.emit(0, 1)  # Failure


class PlaceOrderApp(QDialog):
    def __init__(self, exchange_instrument_id=None, order_side=None,
                 price_band_high=None, price_band_low=None,
                 freeze_qty=None, tick_size=None, lot_size=None,
                 bid_price=None, ask_price=None, exchange_segment=None,
                 parent=None):
        super().__init__(parent)
        self.exchange_instrument_id = exchange_instrument_id
        self.price_band_high = float(price_band_high) if price_band_high else 0.0
        self.price_band_low = float(price_band_low) if price_band_low else 0.0
        self.freeze_qty = int(float(freeze_qty)) if freeze_qty else 1000000
        self.tick_size = float(tick_size) if tick_size else 1.0
        self.lot_size = int(lot_size) if lot_size else 1
        self.bid_price = bid_price
        self.ask_price = ask_price
        self.exchange_segment = exchange_segment
        self.initUI()

        if order_side:
            self.order_side_combo.setCurrentText(order_side)
            self.update_price_based_on_side(order_side)

        # Initialize thread pool and order tracking variables
        self.thread_pool = QThreadPool()
        self.success_orders = 0
        self.failed_orders = 0

    def initUI(self):
        self.setWindowTitle('Place Buy/Sell Order')

        # Advanced/Normal option with "Normal" as the default
        advanced_normal_combo = QComboBox(self)
        advanced_normal_combo.addItems(['Normal', 'Advance'])
        advanced_normal_combo.setCurrentText('Normal')
        advanced_normal_combo.currentIndexChanged.connect(self.toggle_advanced_options)

        # Order Side (BUY/SELL)
        self.order_side_combo = QComboBox(self)
        self.order_side_combo.addItems(['BUY', 'SELL'])
        self.order_side_combo.currentIndexChanged.connect(self.on_order_side_changed)

        # Exchange Segment
        self.exchange_segment_combo = QComboBox(self)
        self.exchange_segment_combo.addItems(['NSECM', 'NSEFO'])
        if self.exchange_segment:
            self.exchange_segment_combo.setCurrentText(self.exchange_segment)

        # Order Type (Market, Limit, SL) with "Limit" as the default
        self.order_type_combo = QComboBox(self)
        self.order_type_combo.addItems(['Limit', 'Market', 'StopLimit','StopMarket'])
        self.order_type_combo.setCurrentText('Limit')
        self.order_type_combo.currentIndexChanged.connect(self.toggle_price_box)

        # Product Type (MIS/NRML) with "NRML" as the default
        self.product_type_combo = QComboBox(self)
        self.product_type_combo.addItems(['NRML', 'MIS','CNC'])
        self.product_type_combo.setCurrentText('NRML')

        # Time in Force (Day/IOC)
        self.time_in_force_combo = QComboBox(self)
        self.time_in_force_combo.addItems(['Day', 'IOC'])

        # Exchange Instrument ID
        self.instrument_input = QLineEdit(self)
        self.instrument_input.setPlaceholderText("Exchange Instrument ID")
        if self.exchange_instrument_id:
            self.instrument_input.setText(self.exchange_instrument_id)
            self.instrument_input.setReadOnly(True)

        # Quantity SpinBox with lot size as the step increment
        self.quantity_input = QSpinBox(self)
        self.quantity_input.setRange(self.lot_size, 1000000)
        self.quantity_input.setSingleStep(self.lot_size)
        self.quantity_input.setPrefix("Qty: ")
        self.quantity_input.setValue(self.lot_size)

        # Freeze Qty label with smaller font
        self.freeze_qty_label = QLabel(f"Freeze Qty: {self.freeze_qty}" if self.freeze_qty else "", self)
        self.freeze_qty_label.setFont(QFont("Arial", 8))

        # Price DoubleSpinBox, flexible for user input
        self.limit_price_input = QDoubleSpinBox(self)
        self.limit_price_input.setRange(0, 1000000)
        self.limit_price_input.setDecimals(2)
        self.limit_price_input.setPrefix("Price: ")
        self.limit_price_input.setSingleStep(self.tick_size)

        # Set initial price box state based on order type
        self.toggle_price_box()

        # Price Band label with smaller font
        self.price_band_label = QLabel(f"Price Band: {self.price_band_low} - {self.price_band_high}", self)
        self.price_band_label.setFont(QFont("Arial", 8))

        # Stop Price input (disabled unless SL is selected)
        self.stop_price_input = QDoubleSpinBox(self)
        self.stop_price_input.setRange(0, 1000000)
        self.stop_price_input.setDecimals(2)
        self.stop_price_input.setPrefix("Stop Price: ")
        self.stop_price_input.setDisabled(True)

        # Disclosed Quantity SpinBox
        self.disclosed_quantity_input = QSpinBox(self)
        self.disclosed_quantity_input.setPrefix("Disc Qty: ")
        self.disclosed_quantity_input.setValue(0)

        # Advanced options: Multiplier, Split Qty, and Split Price, initially hidden
        self.multiplier_input = QSpinBox(self)
        self.multiplier_input.setPrefix("Multiplier: ")
        self.multiplier_input.setRange(1, 1000)
        self.multiplier_input.setValue(1)
        self.multiplier_input.setVisible(False)

        # Split Qty SpinBox with lot size as the step increment
        self.split_qty_input = QSpinBox(self)
        self.split_qty_input.setPrefix("Split Qty: ")
        self.split_qty_input.setRange(0, 1000000)
        self.split_qty_input.setSingleStep(self.lot_size)
        self.split_qty_input.valueChanged.connect(self.toggle_quantity_input)
        self.split_qty_input.setVisible(False)

        # Split Price input
        self.split_price_input = QDoubleSpinBox(self)
        self.split_price_input.setDecimals(2)
        self.split_price_input.setPrefix("Split Price: ")
        self.split_price_input.setVisible(False)

        # Submit and Cancel buttons aligned to the right
        self.submit_button = QPushButton('Submit', self)
        self.submit_button.clicked.connect(self.confirm_order)
        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.close)

        # Layout
        layout = QVBoxLayout()
        form_layout = QGridLayout()
        form_layout.addWidget(advanced_normal_combo, 0, 0)
        form_layout.addWidget(self.order_side_combo, 0, 1)
        form_layout.addWidget(self.exchange_segment_combo, 0, 2)
        form_layout.addWidget(self.order_type_combo, 0, 3)
        form_layout.addWidget(self.product_type_combo, 0, 4)
        form_layout.addWidget(self.time_in_force_combo, 0, 5)
        form_layout.addWidget(self.instrument_input, 0, 6)
        form_layout.addWidget(self.quantity_input, 0, 7)
        form_layout.addWidget(self.limit_price_input, 0, 8)
        form_layout.addWidget(self.stop_price_input, 0, 9)
        form_layout.addWidget(self.disclosed_quantity_input, 0, 10)
        form_layout.addWidget(self.freeze_qty_label, 1, 7)
        form_layout.addWidget(self.price_band_label, 1, 8)
        form_layout.addWidget(self.multiplier_input, 2, 0)
        form_layout.addWidget(self.split_qty_input, 2, 1)
        form_layout.addWidget(self.split_price_input, 2, 2)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Connect the order type combo to control stop price input
        self.order_type_combo.currentIndexChanged.connect(self.toggle_stop_price)

    def toggle_advanced_options(self):
        """Show or hide advanced options based on the selected mode."""
        is_advanced = self.sender().currentText() == 'Advance'
        self.multiplier_input.setVisible(is_advanced)
        self.split_qty_input.setVisible(is_advanced)
        self.split_price_input.setVisible(is_advanced)

    def toggle_quantity_input(self):
        """Enable or disable the Quantity input based on the Split Qty value."""
        if self.split_qty_input.value() > 0:
            self.quantity_input.setDisabled(True)
        else:
            self.quantity_input.setDisabled(False)

    def toggle_price_box(self):
        """Enable or disable the Price input based on the selected Order Type."""
        order_type = self.order_type_combo.currentText()
        if order_type == 'Market' or order_type == 'StopMarket':
            self.limit_price_input.setDisabled(True)
            self.limit_price_input.setValue(0.0)
        else:
            self.limit_price_input.setDisabled(False)
            self.limit_price_input.setRange(self.price_band_low, self.price_band_high)



    def on_order_side_changed(self):
        """Update price field based on the selected order side."""
        order_side = self.order_side_combo.currentText()
        self.update_price_based_on_side(order_side)

    def update_price_based_on_side(self, order_side):
        """Set the price field to ask price if BUY and bid price if SELL."""
        if order_side == 'BUY' and self.ask_price is not None:
            self.limit_price_input.setValue(float(self.ask_price))
        elif order_side == 'SELL' and self.bid_price is not None:
            self.limit_price_input.setValue(float(self.bid_price))

    def toggle_stop_price(self):
        """Enable or disable the Stop Price input based on the Order Type selection."""
        order_type = self.order_type_combo.currentText()
        if order_type in ['StopLimit', 'StopMarket']:
            self.stop_price_input.setDisabled(False)
        else:
            self.stop_price_input.setDisabled(True)
            self.stop_price_input.setValue(0.0)


    def confirm_order(self):
        """Validate order details on submit and ask for confirmation."""
        if self.quantity_input.value() > self.freeze_qty:
            QMessageBox.warning(self, "Invalid Quantity", f"Quantity cannot exceed Freeze Qty ({self.freeze_qty}).")
            return
        
        if self.order_type_combo.currentText() != 'Market' and not (self.price_band_low <= self.limit_price_input.value() <= self.price_band_high):
            QMessageBox.warning(self, "Invalid Price", f"Price must be within Price Band ({self.price_band_low} - {self.price_band_high}).")
            return

        reply = QMessageBox.question(self, 'Confirm Order', "Do you want to confirm the order?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.start_order_placement()

    def start_order_placement(self):
        """Start placing orders using QThreadPool with adjusted prices based on Split Price."""
        order_side = self.order_side_combo.currentText()
        order_side_mapped = 'TRANSACTION_TYPE_BUY' if order_side == 'BUY' else 'TRANSACTION_TYPE_SELL'
        product_type = self.product_type_combo.currentText()
        product_type_mapped = (
            'PRODUCT_MIS' if product_type == 'MIS' else
            'PRODUCT_NRML' if product_type == 'NRML' else
            'PRODUCT_CNC' if product_type == 'CNC' else None
        )

        if product_type_mapped is None:
            raise ValueError(f"Invalid product type: {product_type}")

        # product_type_mapped = 'PRODUCT_MIS' if product_type == 'MIS' else 'PRODUCT_NRML'
        order_type = self.order_type_combo.currentText()
        order_type_mapped = (
            'ORDER_TYPE_MARKET' if order_type == 'Market' 
            else 'ORDER_TYPE_LIMIT' if order_type == 'Limit' 
            else 'ORDER_TYPE_STOPLIMIT' if order_type == 'StopLimit' 
            else 'ORDER_TYPE_STOPMARKET'  # For StopMarket
        )
        exchange_segment = self.exchange_segment_combo.currentText()
        exchange_segment_mapped = 'EXCHANGE_NSECM' if exchange_segment == 'NSECM' else 'EXCHANGE_NSEFO'
        time_in_force = self.time_in_force_combo.currentText()
        time_in_force_mapped = 'VALIDITY_DAY' if time_in_force == 'Day' else 'VALIDITY_IOC'
        
        multiplier = self.multiplier_input.value()
        order_quantity = self.split_qty_input.value() if self.split_qty_input.value() > 0 else self.quantity_input.value()
        base_price = self.limit_price_input.value()
        split_price = self.split_price_input.value()

        # Initialize order signals to track completion
        self.order_signals = OrderSignals()
        self.order_signals.order_summary_signal.connect(self.update_order_summary)

        # Create and add tasks to the thread pool with adjusted prices
        for i in range(multiplier):
            # Adjust the price based on split price for each order if not StopMarket
            if order_type != 'StopMarket':
                if order_side == 'BUY':
                    adjusted_price = base_price - (i * split_price)
                else:  # SELL
                    adjusted_price = base_price + (i * split_price)

                # Ensure the adjusted price remains within price band
                if not (self.price_band_low <= adjusted_price <= self.price_band_high):
                    QMessageBox.warning(self, "Invalid Price", f"Adjusted price out of bounds for order {i+1}")
                    continue
            else:
                # For StopMarket, limit price is always 0
                adjusted_price = 0

            # Prepare order data with adjusted price
            order_data = {
                'exchangeSegment': exchange_segment_mapped,
                'productType': product_type_mapped,
                'orderType': order_type_mapped,
                'orderSide': order_side_mapped,
                'timeInForce': time_in_force_mapped,
                'exchangeInstrumentID': self.instrument_input.text(),
                'orderQuantity': order_quantity,
                'disclosedQuantity': self.disclosed_quantity_input.value(),
                'limitPrice': adjusted_price,  # Set to 0 for StopMarket
                'stopPrice': self.stop_price_input.value() if order_type in ['StopLimit', 'StopMarket'] else '0',
                'orderUniqueIdentifier': f"Rattle-{i+1}"
            }
            print(f"{order_data}")
            order_task = OrderPlacementTask(order_data, i + 1, self.order_signals)
            self.thread_pool.start(order_task)


    def update_order_summary(self, success, failure):
        """Update order counts and show summary when all tasks are complete."""
        self.success_orders += success
        self.failed_orders += failure

        if self.success_orders + self.failed_orders == self.multiplier_input.value():
            QMessageBox.information(self, 'Order Summary', f"Orders placed successfully: {self.success_orders}\nFailed orders: {self.failed_orders}")
            self.close()

# If running standalone, uncomment these lines:
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     window = PlaceOrderApp()
#     window.show()
#     sys.exit(app.exec_())
