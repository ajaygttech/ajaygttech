# trade_book.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView
from PyQt5.QtGui import QColor

class TradeBookDialog(QDialog):
    def __init__(self, trade_data):
        super().__init__()
        self.setWindowTitle("Trade Book")
        self.setGeometry(200, 200, 800, 400)

        # Table setup
        layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(16)  # Updated column count with OrderSide
        self.table.setHorizontalHeaderLabels([
            "ClientID", "ExchangeOrderID", "ExchangeSegment", "OrderCategoryType", "OrderSide", "ProductType",
            "OrderType", "TradingSymbol", "QTY", "OrderAverageTradedPrice",
            "GeneratedBy", "ExecutionID", "ExchangeInstrumentID", "ExchangeTransactTime",
            "OrderGeneratedDateTime", "OrderUniqueIdentifier"
        ])

        # Configure table properties
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)  # Row selection only
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Make table non-editable
        self.table.horizontalHeader().setStretchLastSection(True)  # Make last column stretchable
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Allow column resizing

        # Populate the table with data
        self.populate_table(trade_data)

        # Add table to layout
        layout.addWidget(self.table)

    def populate_table(self, trade_data):
        """Fill table with trade book data and set row color based on OrderSide, showing latest row on top."""
        self.table.setRowCount(len(trade_data))  # Set number of rows

        for row, trade in enumerate(reversed(trade_data)):  # Reverse the order of data
            # Determine row background color based on OrderSide
            order_side = trade.get("OrderSide", "")
            color = QColor(173, 216, 230) if order_side == "BUY" else QColor(255, 182, 193) if order_side == "SELL" else QColor(255, 255, 255)

            # Populate each column and set background color
            self.set_table_item(row, 0, trade.get("ClientID", ""), color)
            self.set_table_item(row, 1, trade.get("ExchangeOrderID", ""), color)
            self.set_table_item(row, 2, trade.get("ExchangeSegment", ""), color)
            self.set_table_item(row, 3, trade.get("OrderCategoryType", ""), color)
            self.set_table_item(row, 4, order_side, color)  # OrderSide column
            self.set_table_item(row, 5, trade.get("ProductType", ""), color)
            self.set_table_item(row, 6, trade.get("OrderType", ""), color)
            self.set_table_item(row, 7, trade.get("TradingSymbol", ""), color)
            self.set_table_item(row, 8, str(trade.get("CumulativeQuantity", "")), color)
            self.set_table_item(row, 9, str(trade.get("OrderAverageTradedPrice", "")), color)
            self.set_table_item(row, 10, trade.get("GeneratedBy", ""), color)
            self.set_table_item(row, 11, trade.get("ExecutionID", ""), color)
            self.set_table_item(row, 12, str(trade.get("ExchangeInstrumentID", "")), color)
            self.set_table_item(row, 13, trade.get("ExchangeTransactTime", ""), color)
            self.set_table_item(row, 14, trade.get("OrderGeneratedDateTime", ""), color)
            self.set_table_item(row, 15, trade.get("OrderUniqueIdentifier", ""), color)


    def set_table_item(self, row, column, text, background_color):
        """Helper method to create a table item with specified text and background color."""
        item = QTableWidgetItem(text)
        item.setBackground(background_color)
        self.table.setItem(row, column, item)
