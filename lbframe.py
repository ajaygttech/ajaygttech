from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
from PyQt5.QtCore import pyqtSignal

class BottomLeftFrame(QWidget):
    # Signal to emit when a strategy is selected
    strategy_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Set up the layout and table for the bottom-left frame
        self.setup_bottom_left_layout()

        # Connect table selection change to strategy selection handler
        self.bottom_left_table.itemSelectionChanged.connect(self.on_strategy_selected)

    def on_strategy_selected(self):
        """Emit the selected strategy name when a row is selected."""
        selected_items = self.bottom_left_table.selectedItems()
        if selected_items:
            strategy_name = selected_items[0].text()  # Assuming strategy name is in the first column
            self.strategy_selected.emit(strategy_name)

    def add_strategy(self, strategy_name):
        """Add a strategy name to the bottom-left table if not already present."""
        if not self.is_strategy_present(strategy_name):
            row_position = self.bottom_left_table.rowCount()
            self.bottom_left_table.insertRow(row_position)
            self.bottom_left_table.setItem(row_position, 0, QTableWidgetItem(strategy_name))

            print(f"Strategy {strategy_name} added to BottomLeftFrame.")

    def is_strategy_present(self, strategy_name):
        """Check if a strategy is already present in the bottom-left table."""
        for row in range(self.bottom_left_table.rowCount()):
            item = self.bottom_left_table.item(row, 0)
            if item and item.text() == strategy_name:
                return True
        return False

    def update_current_entry_value(self, strategy_name, cmp_sum):
        """Update the Current Entry Value for the given strategy."""
        for row in range(self.bottom_left_table.rowCount()):
            item = self.bottom_left_table.item(row, 0)  # Strategy name is in the first column
            if item and item.text() == strategy_name:
                # Update the Current Entry Value (Column 1) with the CMP sum
                self.bottom_left_table.setItem(row, 1, QTableWidgetItem(str(cmp_sum)))
                print(f"Updated Current Entry Value for {strategy_name} with CMP sum: {cmp_sum}")
                break

    def setup_bottom_left_layout(self):
        """Set up the layout for the bottom-left frame."""
        bottom_left_layout = QVBoxLayout()

        # Remove margins for bottom-left layout
        bottom_left_layout.setContentsMargins(0, 0, 0, 0)  # No margins in the bottom-left frame

        # Create the table widget for bottom-left frame
        self.bottom_left_table = QTableWidget()
        self.bottom_left_table.setColumnCount(9)  # Set the number of columns

        # Set column headers
        column_headers = [
            "Strategy Name", "Current Entry Value", "Entry Value", "Current Exit Value", 
            "Exit Value", "Running Status", "Multiply", "Traded Round", "MTM"
        ]
        self.bottom_left_table.setHorizontalHeaderLabels(column_headers)

        # Add the table to the bottom-left layout
        bottom_left_layout.addWidget(self.bottom_left_table)

        # Add buttons below the table, aligned to the right
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Push buttons to the right

        # Create the buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.exit_button = QPushButton("Exit")
        self.exit_all_button = QPushButton("Exit All")

        # Add buttons to the horizontal layout
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.exit_button)
        button_layout.addWidget(self.exit_all_button)

        # Add the button layout to the bottom-left layout (below the table)
        bottom_left_layout.addLayout(button_layout)

        # Set the layout to the widget
        self.setLayout(bottom_left_layout)
