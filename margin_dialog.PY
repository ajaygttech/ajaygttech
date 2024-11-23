from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QGroupBox, QGridLayout, QScrollArea, QWidget

class MarginDialog(QDialog):
    def __init__(self, margin_data):
        super().__init__()
        self.setWindowTitle("Margin Information")
        self.setGeometry(300, 300, 600, 400)

        # Create a scroll area to hold the main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Container widget for the scrollable content
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)

        # Extract margin details from response
        balance_info = margin_data.get("balance", {}).get("BalanceList", [{}])[0].get("limitObject", {})

        # RMS Sub-Limits
        layout.addWidget(self.create_section("RMS Sub-Limits", balance_info.get("RMSSubLimits", {})))

        # Limits Assigned
        layout.addWidget(self.create_section("Limits Assigned", balance_info.get("limitsAssigned", {})))

        # Margin Available
        layout.addWidget(self.create_section("Margin Available", balance_info.get("marginAvailable", {})))

        # Margin Utilized
        layout.addWidget(self.create_section("Margin Utilized", balance_info.get("marginUtilized", {})))

        # Set container widget as the widget for the scroll area
        scroll_area.setWidget(container_widget)

        # Main layout for the dialog
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def create_section(self, title, data_dict):
        """Create a section with a title and dictionary of key-value pairs."""
        group_box = QGroupBox(title)
        layout = QGridLayout()

        for i, (key, value) in enumerate(data_dict.items()):
            layout.addWidget(QLabel(f"{key}:"), i, 0)
            layout.addWidget(QLabel(str(value) if value is not None else "N/A"), i, 1)

        group_box.setLayout(layout)
        return group_box
