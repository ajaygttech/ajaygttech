from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot  # Correct imports for QObject and signals
import requests

class ModifyOrderDialog(QDialog):
    def __init__(self, order_data):
        super().__init__()
        self.setWindowTitle("Modify Order")
        self.setGeometry(400, 400, 600, 200)

        # Thread pool for handling asynchronous tasks
        self.thread_pool = QThreadPool()

        # Main layout for the dialog
        main_layout = QVBoxLayout()

        # Horizontal layout to arrange fields in a single row
        fields_layout = QHBoxLayout()

        # Define fields we want to modify and map to order data keys
        self.fields = {
            "AppOrderID": QLineEdit(),
            "ProductType": QLineEdit(),
            "OrderType": QLineEdit(),
            "OrderQuantity": QLineEdit(),
            "LimitPrice": QLineEdit(),         # Maps to OrderPrice
            "StopPrice": QLineEdit(),          # Maps to OrderStopPrice
            "DisclosedQuantity": QLineEdit(),  # Maps to OrderDisclosedQuantity
            "TimeInForce": QLineEdit()
        }

        # Labels for each field
        labels = {
            "AppOrderID": "App Order ID",
            "ProductType": "Product Type",
            "OrderType": "Order Type",
            "OrderQuantity": "Order Quantity",
            "LimitPrice": "Limit Price",
            "StopPrice": "Stop Price",
            "DisclosedQuantity": "Disclosed Quantity",
            "TimeInForce": "Time In Force"
        }

        # Map fields to keys in order_data
        field_mappings = {
            "AppOrderID": "AppOrderID",
            "ProductType": "ProductType",
            "OrderType": "OrderType",
            "OrderQuantity": "OrderQuantity",
            "LimitPrice": "OrderPrice",
            "StopPrice": "OrderStopPrice",
            "DisclosedQuantity": "OrderDisclosedQuantity",
            "TimeInForce": "TimeInForce"
        }

        # Populate fields with data and arrange labels above the boxes
        for field, widget in self.fields.items():
            field_layout = QVBoxLayout()
            mapped_key = field_mappings.get(field, "")
            widget.setText(str(order_data.get(mapped_key, "")))  # Set initial text from order_data

            # Add label and field to the field layout
            field_layout.addWidget(QLabel(labels[field]))
            field_layout.addWidget(widget)
            fields_layout.addLayout(field_layout)

        main_layout.addLayout(fields_layout)

        # Buttons layout aligned to the right
        button_layout = QHBoxLayout()
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))  # Spacer to push buttons to the right
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedSize(80, 30)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedSize(80, 30)

        # Connect buttons to actions
        self.submit_button.clicked.connect(self.start_order_modification)
        self.cancel_button.clicked.connect(self.reject)

        # Add buttons to the layout
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        # Set the main layout for the dialog
        self.setLayout(main_layout)

    @pyqtSlot()
    def start_order_modification(self):
        """Initiate the order modification process asynchronously."""
        updated_order_data = {
            "appOrderID": self.fields["AppOrderID"].text(),
            "productType": self.fields["ProductType"].text(),
            "orderType": self.fields["OrderType"].text(),
            "orderQuantity": self.fields["OrderQuantity"].text(),
            "limitPrice": self.fields["LimitPrice"].text(),
            "stopPrice": self.fields["StopPrice"].text(),
            "disclosedQuantity": self.fields["DisclosedQuantity"].text(),
            "timeInForce": self.fields["TimeInForce"].text(),
            "orderUniqueIdentifier": "unique_123"  # Example unique identifier
        }

        # Check if AppOrderID is provided
        if not updated_order_data["appOrderID"]:
            QMessageBox.warning(self, "Error", "Order ID is missing.")
            return

        # Create and run the task in a separate thread
        task = OrderModificationTask(updated_order_data)
        task.signals.finished.connect(lambda success, response_data: self.on_modification_complete(success, response_data))
        self.thread_pool.start(task)

    @pyqtSlot(bool, object)
    def on_modification_complete(self, success, response_data):
        """Handle the completion of the modification request."""
        if success:
            QMessageBox.information(self, "Success", "Order modification successful.")
        else:
            QMessageBox.warning(self, "Failed", f"Order modification failed: {response_data}")
        self.accept()  # Close the dialog


class OrderModificationTask(QRunnable):
    """Task to handle the order modification in a separate thread."""
    def __init__(self, order_data):
        super().__init__()
        self.order_data = order_data
        self.signals = OrderModificationSignals()

    @pyqtSlot()
    def run(self):
        """Execute the HTTP request in the background."""
        try:
            response = requests.post("http://localhost:5000/modify_order", json=self.order_data)
            if response.status_code == 200:
                self.signals.finished.emit(True, response.json())
            else:
                self.signals.finished.emit(False, response.json())
        except requests.exceptions.RequestException as e:
            self.signals.finished.emit(False, str(e))


class OrderModificationSignals(QObject):
    """Defines signals for communicating task completion."""
    finished = pyqtSignal(bool, object)
