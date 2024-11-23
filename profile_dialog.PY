from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QGroupBox, QGridLayout, QScrollArea, QWidget

class ProfileDialog(QDialog):
    def __init__(self, profile_data):
        super().__init__()
        self.setWindowTitle("Client Profile")
        self.setGeometry(300, 300, 500, 400)

        # Create a scroll area to hold the main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Container widget for the scrollable content
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)

        # Client Information
        client_info = profile_data.get("profile", {})
        layout.addWidget(self.create_section("Client Information", {
            "Client ID": client_info.get("ClientId"),
            "Client Name": client_info.get("ClientName"),
            "PAN": client_info.get("PAN"),
            "Mobile No": client_info.get("MobileNo"),
            "Email ID": client_info.get("EmailId"),
            "Demat Account": client_info.get("DematAccountNumber"),
            "Office Address": client_info.get("OfficeAddress"),
            "Residential Address": client_info.get("ResidentialAddress"),
        }))

        # Client Bank Info
        if client_info.get("ClientBankInfoList"):
            bank_info = client_info["ClientBankInfoList"][0]
            layout.addWidget(self.create_section("Bank Information", {
                "Account Number": bank_info.get("AccountNumber"),
                "Bank Name": bank_info.get("BankName"),
                "Bank Branch": bank_info.get("BankBranchName"),
                "City": bank_info.get("BankCity"),
                "Pincode": bank_info.get("BankCityPincode"),
                "IFSC Code": bank_info.get("BankIFSCCode"),
            }))

        # Client Exchange Details
        exchange_details = client_info.get("ClientExchangeDetailsList", {})
        layout.addWidget(self.create_section("Exchange Details", {
            "BSECM Enabled": str(exchange_details.get("BSECM", {}).get("Enabled")),
            "NSECM Enabled": str(exchange_details.get("NSECM", {}).get("Enabled")),
            "BSEFO Enabled": str(exchange_details.get("BSEFO", {}).get("Enabled")),
            "NSEFO Enabled": str(exchange_details.get("NSEFO", {}).get("Enabled")),
        }))

        # Other Client Preferences
        layout.addWidget(self.create_section("Client Preferences", {
            "Auto Square-off": str(client_info.get("IncludeInAutoSquareoff")),
            "Auto Square-off Blocked": str(client_info.get("IncludeInAutoSquareoffBlocked")),
            "Is Investor Client": str(client_info.get("IsInvestorClient")),
            "POA Enabled": str(client_info.get("IsPOAEnabled")),
            "Pro Client": str(client_info.get("IsProClient")),
        }))

        # Set the container widget as the widget for the scroll area
        scroll_area.setWidget(container_widget)

        # Main layout for the dialog
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def create_section(self, title, info_dict):
        """Create a section with a title and a dictionary of key-value pairs."""
        group_box = QGroupBox(title)
        layout = QGridLayout()

        for i, (key, value) in enumerate(info_dict.items()):
            layout.addWidget(QLabel(f"{key}:"), i, 0)
            layout.addWidget(QLabel(str(value) if value is not None else "N/A"), i, 1)

        group_box.setLayout(layout)
        return group_box
