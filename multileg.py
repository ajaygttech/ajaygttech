from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PyQt5.QtCore import Qt
from tlframe import TopLeftFrame  # Import TopLeftFrame
from lbframe import BottomLeftFrame  # Import BottomLeftFrame
from rframe import RightFrame  # Import RightFrame

class MultilegTab(QWidget):
    def __init__(self, websocket_client):
        super().__init__()

        # Use the WebSocketClient passed from mainw.py
        self.websocket_thread = websocket_client

        # Set up the layout for the MultilegTab
        self.setup_multileg_layout()

        # Connect signals after the frames are initialized
        self.top_left_frame.data_submitted.connect(self.handle_data_submission)
        self.bottom_left_frame.strategy_selected.connect(self.display_strategy_data)

    def setup_multileg_layout(self):
        """Set up the layout for the Multileg tab with three frames and no margins."""
        multileg_layout = QVBoxLayout()

        # Set margins to 0 for the multileg_tab layout
        multileg_layout.setContentsMargins(0, 0, 0, 0)  # No margins on any side

        # Create a QSplitter to hold two horizontal frames on the left and one vertical frame on the right
        splitter_main = QSplitter(Qt.Horizontal)  # Main splitter dividing left and right

        # Create a left splitter for two vertical frames on the left side
        splitter_left = QSplitter(Qt.Vertical)

        # Frame 1 (TopLeftFrame) from tlframe.py, pass the WebSocketClient to TopLeftFrame
        self.top_left_frame = TopLeftFrame(self.websocket_thread)

        # Frame 2 (BottomLeftFrame) from lbframe.py
        self.bottom_left_frame = BottomLeftFrame()

        # Add the top-left and bottom-left frames to the left splitter
        splitter_left.addWidget(self.top_left_frame)
        splitter_left.addWidget(self.bottom_left_frame)

        # Pass bottom_left_frame and WebSocketClient to RightFrame
        self.right_frame = RightFrame(self.bottom_left_frame, self.websocket_thread)

        # Add the left splitter and the right frame to the main splitter
        splitter_main.addWidget(splitter_left)
        splitter_main.addWidget(self.right_frame)

        # Add the splitter to the multileg layout
        multileg_layout.addWidget(splitter_main)

        # Set the layout for MultilegTab
        self.setLayout(multileg_layout)

    def handle_data_submission(self, data):
        """Handle the data submission from TopLeftFrame."""
        strategy_name, table_data = data

        # Pass the data to RightFrame
        self.right_frame.add_data_by_strategy(strategy_name, table_data)

        # Add strategy name to BottomLeftFrame
        self.bottom_left_frame.add_strategy(strategy_name)

        # After adding data, update Current Entry Value with the sum of CMP from RightFrame
        cmp_sum = self.right_frame.right_table_widget.cmp_sum  # Get the sum of CMP from RightFrame
        self.bottom_left_frame.update_current_entry_value(strategy_name, cmp_sum)

    def display_strategy_data(self, strategy_name):
        """Display the selected strategy's data in RightFrame."""
        print(f"Displaying data for strategy: {strategy_name}")
        self.right_frame.display_data_by_strategy(strategy_name)

        # After displaying data, update Current Entry Value with the sum of CMP from RightFrame
        cmp_sum = self.right_frame.right_table_widget.cmp_sum  # Get the sum of CMP from RightFrame
        self.bottom_left_frame.update_current_entry_value(strategy_name, cmp_sum)
