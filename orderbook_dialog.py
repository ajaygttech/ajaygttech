# orderbook_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from modify_order_dialog import ModifyOrderDialog  # Import ModifyOrderDialog
import requests
class OrderBookDialog(QDialog):
    def __init__(self, data):
        super().__init__()
        self.setWindowTitle("Order Book")
        self.setGeometry(300, 300, 1000, 400)

        # Main layout for the dialog
        layout = QVBoxLayout()

        # # Add a label
        # label = QLabel("Order Book", self)
        # layout.addWidget(label)

        # Define primary headers to appear first in the order specified
        primary_headers = [
            "ClientID", "ExchangeSegment", "OrderCategoryType", "OrderSide",
            "OrderType", "ProductType", "TradingSymbol", "OrderQuantity", 
            "OrderPrice", "OrderStatus", "OrderStopPrice", "CancelRejectReason"
        ]

        # All possible headers based on the fields in the data
        all_headers = [
            "ApiOrderSource", "AppOrderID", "ApplicationType", "BoEntryOrderId", 
            "BoLegDetails", "CumulativeQuantity", "ExchangeInstrumentID", "ExchangeOrderID", 
            "ExchangeTransactTime", "GeneratedBy", "IsSpread", "LastUpdateDateTime", 
            "LeavesQuantity", "LoginID", "MessageCode", "MessageVersion", 
            "OrderAverageTradedPrice", "OrderDisclosedQuantity", "OrderExpiryDate", 
            "OrderGeneratedDateTime", "OrderLegStatus", "OrderReferenceID", 
            "SequenceNumber", "TimeInForce", "TokenID"
        ]

        # Combine primary headers and remaining headers, ensuring primary_headers come first
        self.headers = primary_headers + [header for header in all_headers if header not in primary_headers]

        # Store data and set the flag to show only "New" orders initially
        self.data = data
        self.show_only_new = True

        # Create the table widget with row and column counts based on data and headers
        self.table = CustomTableWidget(len(data), len(self.headers), self)
        self.table.setHorizontalHeaderLabels(self.headers)

        # Set table properties
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Allow column resizing
        self.table.horizontalHeader().setStretchLastSection(True)  # Stretch the last column to fill remaining space
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # Select entire row on click
        self.table.setSelectionMode(QTableWidget.SingleSelection)  # Allow selecting one row at a time
        self.table.setShowGrid(False)  # Remove the grid lines
        self.table.verticalHeader().setVisible(False)  # Hide row numbers

        # Populate table with filtered data
        self.populate_table()

        # Add table to the layout
        layout.addWidget(self.table)

        # Set layout to the dialog
        self.setLayout(layout)

        # Set context menu policy and connect right-click action
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

    def populate_table(self):
        """Populate the table with data based on current filter settings."""
        self.table.setRowCount(0)  # Clear existing rows

        # Reverse the data to show the latest orders on top
        for order in reversed(self.data):
            order_status = order.get("OrderStatus", "").upper()

            # Filter based on OrderStatus if `show_only_new` is True, allowing both "NEW" and "REPLACED"
            if self.show_only_new and order_status not in {"NEW", "REPLACED"}:
                continue

            # Determine background color based on OrderSide and OrderStatus
            order_side = order.get("OrderSide", "").upper()
            if order_status == "CANCELLED":
                background_color = QColor("gray")
            elif order_status == "REJECTED":
                background_color = QColor("pink")
            elif order_side == "BUY":
                background_color = QColor("blue")
            elif order_side == "SELL":
                background_color = QColor("red")
            else:
                background_color = QColor("white")

            # Add a new row for the current order
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            for col, header in enumerate(self.headers):
                item_text = str(order.get(header, ""))  # Safely get each field value or empty if missing
                item = QTableWidgetItem(item_text)
                item.setBackground(background_color)  # Set background color for the cell based on conditions
                self.table.setItem(row_position, col, item)

    def show_context_menu(self, position):
        """Display a context menu with options to toggle view, modify, and cancel the selected order."""
        menu = QMenu()

        # Toggle action for showing all orders or only "New" orders
        toggle_action = menu.addAction("Show All Orders" if self.show_only_new else "Show Only 'New' Orders")

        # Modify and Cancel actions
        modify_action = menu.addAction("Modify Order")
        cancel_action = menu.addAction("Cancel Order")

        # Execute the menu and determine which action was triggered
        action = menu.exec_(self.table.mapToGlobal(position))
        
        if action == toggle_action:
            self.show_only_new = not self.show_only_new  # Toggle the flag
            self.populate_table()  # Re-populate the table with updated filter setting
        elif action == modify_action:
            self.open_modify_dialog()  # Open the modify dialog for the selected order
        elif action == cancel_action:
            self.cancel_order()  # Attempt to cancel the selected order


    def open_modify_dialog(self):
        """Open the ModifyOrderDialog for the selected row."""
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Selection Error", "No order selected.")
            return

        # Get OrderStatus for the selected row
        order_status = self.table.item(selected_row, self.headers.index("OrderStatus")).text().upper()
        if order_status not in {"NEW", "REPLACED"}:
            QMessageBox.information(self, "Status Error", "Only orders with status 'New' or 'Replaced' can be modified.")
            return

        # Collect order data from the selected row
        order_data = {header: self.table.item(selected_row, self.headers.index(header)).text() for header in self.headers}

        # Open ModifyOrderDialog with the selected order data
        modify_dialog = ModifyOrderDialog(order_data)
        if modify_dialog.exec_() == QDialog.Accepted:
            pass  # Optional: Refresh the table or take further action after modification

    def show_order_details(self):
        """Show order details for the selected row if OrderStatus is 'New' or 'Replaced'."""
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.information(self, "Selection Error", "No order selected.")
            return

        # Get OrderStatus for the selected row
        order_status = self.table.item(selected_row, self.headers.index("OrderStatus")).text().upper()
        if order_status not in {"NEW", "REPLACED"}:
            QMessageBox.information(self, "Status Error", "You can modify only pending or New orders")
            return

        # Collect order data from the selected row
        order_data = {}
        for header in self.headers:
            order_data[header] = self.table.item(selected_row, self.headers.index(header)).text()

        # Open ModifyOrderDialog with the selected order data
        modify_dialog = ModifyOrderDialog(order_data)
        if modify_dialog.exec_() == QDialog.Accepted:
            # You could refresh the table or take action after saving if needed
            pass

    def cancel_order(self):
        """Cancel the selected order after confirmation."""
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Selection Error", "No order selected.")
            return

        # Get the Order ID and Order Status
        order_status = self.table.item(selected_row, self.headers.index("OrderStatus")).text().upper()
        app_order_id = self.table.item(selected_row, self.headers.index("AppOrderID")).text()

        # Check if the order can be canceled
        if order_status not in {"NEW", "REPLACED"}:
            QMessageBox.information(self, "Cancellation Not Allowed", "Only 'New' or 'Replaced' orders can be canceled.")
            return

        # Confirm cancellation
        confirm = QMessageBox.question(self, "Confirm Cancellation", f"Are you sure you want to cancel order {app_order_id}?", 
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            # Here you would typically send a cancellation request to the backend.
            try:
                # Send appOrderID as the key in the payload
                response = requests.post("http://127.0.0.1:5000/cancel_order", json={"appOrderID": app_order_id})
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", f"Order {app_order_id} canceled successfully.")
                    self.populate_table()  # Refresh the table after cancellation
                else:
                    error_message = response.json().get("message", "Failed to cancel order")
                    QMessageBox.warning(self, "Cancellation Failed", f"Failed to cancel order {app_order_id}: {error_message}")
            except requests.RequestException as e:
                QMessageBox.critical(self, "Error", f"Error connecting to server: {e}")



class CustomTableWidget(QTableWidget):
    def __init__(self, rows, columns, parent=None):
        super().__init__(rows, columns, parent)
        self.parent = parent  # Reference to OrderBookDialog

    def keyPressEvent(self, event):
        """Override key press event to detect Shift + F2 or Delete keys."""
        if event.key() == Qt.Key_Delete:
            self.parent.cancel_order()  # Call cancel order on Delete key press
        elif event.key() == Qt.Key_F2 and event.modifiers() & Qt.ShiftModifier:
            self.parent.show_order_details()
        else:
            super().keyPressEvent(event)  # Pass other key events to the default handler