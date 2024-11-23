import sys
import requests
import pandas as pd
from PyQt5.QtWidgets import QWidget, QComboBox, QApplication, QVBoxLayout, QHBoxLayout, QCompleter, QLineEdit
from PyQt5.QtCore import Qt, pyqtSignal
from io import StringIO
from datetime import datetime

# Define format_date function
def format_date(date):
    return date.strftime('%d%b%y').upper()

class Application(QWidget):
    data_selected = pyqtSignal(dict)  # Signal to emit selected data row

    def __init__(self, df):
        super().__init__()
        self.masterdf = df
        self.setWindowTitle("Instrument Filter")
        self.setup_ui()
        self.fetch_data()  # Fetch data when the UI is initialized

    def setup_ui(self):
        """Set up the UI elements and layout."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        combobox_layout = QHBoxLayout()
        combobox_layout.setContentsMargins(0, 0, 0, 0)

        # Initialize Comboboxes
        self.exchange_segment_cb = self.create_combobox(combobox_layout, 10, self.on_exchange_segment_change)
        self.series_cb = self.create_combobox(combobox_layout, 10, self.on_series_change)
        self.name_cb = self.create_combobox(combobox_layout, 20, self.on_name_change, enable_completer=True, editable=True)
        self.contract_exp_cb = self.create_combobox(combobox_layout, 10, self.on_contract_exp_change)
        self.strike_price_cb = self.create_combobox(combobox_layout, 12, self.on_strike_price_change)
        self.option_type_cb = self.create_combobox(combobox_layout, 8, self.on_option_type_change)
        self.instrument_id_cb = self.create_combobox(combobox_layout, 10)

        # Set layout
        main_layout.addLayout(combobox_layout)
        self.setLayout(main_layout)

    def fetch_data(self):
        """Fetch master data for NSEFO and NSECM exchange segments."""
        try:
            # Fetch master data for NSEFO
            response = requests.get('http://localhost:5000/fetch_data_nsefo')
            nsefo_data = response.json()
            if nsefo_data['status'] == 'success':
                nsefo_df = pd.read_csv(StringIO(nsefo_data['data']), sep='|', usecols=range(19), header=None, low_memory=False)
                nsefo_df.columns = [
                    "ExchangeSegment", "ExchangeInstrumentID", "InstrumentType", "Name", "Description", 
                    "Series", "NameWithSeries", "InstrumentID", "PriceBandHigh", "PriceBandLow", 
                    "FreezeQty", "TickSize", "LotSize", "Multiplier", "UnderlyingInstrumentId", 
                    "UnderlyingIndexName", "ContractExpiration", "StrikePrice", "OptionType"
                ]
                nsefo_df['ContractExpiration'] = pd.to_datetime(nsefo_df['ContractExpiration'], errors='coerce').apply(lambda x: x.date())
                nsefo_df['OptionType'] = nsefo_df['OptionType'].replace({1: 'Spread', 3: 'CALL', 4: 'PUT'})
                nsefo_df = nsefo_df.dropna(subset=['ContractExpiration'])

                # Exclude rows where 'StrikePrice' contains 'SPD'
                nsefo_df = nsefo_df[~nsefo_df['StrikePrice'].astype(str).str.contains('SPD', na=False)]

            # Fetch master data for NSECM
            response = requests.get('http://localhost:5000/fetch_data_nsecm')
            nsecm_data = response.json()
            if nsecm_data['status'] == 'success':
                nsecm_df = pd.read_csv(StringIO(nsecm_data['data']), sep='|', usecols=range(16), header=None, low_memory=False)
                nsecm_df.columns = [
                    'ExchangeSegment', 'ExchangeInstrumentID', 'InstrumentType', 'Name', 'Description', 'Series', 
                    'NameWithSeries', 'InstrumentID', 'PriceBandHigh', 'PriceBandLow', 'FreezeQty', 'TickSize', 
                    'LotSize', 'Multiplier', 'displayName', 'ISIN'
                ]

            # Combine the data from both NSEFO and NSECM
            self.masterdf = pd.concat([nsefo_df, nsecm_df], ignore_index=True)

            # Populate the first ComboBox with Exchange Segments
            self.update_combobox(self.exchange_segment_cb, self.masterdf['ExchangeSegment'].unique())

        except Exception as e:
            print(f"Error fetching data: {str(e)}")

    def create_combobox(self, layout, width, callback=None, enable_completer=False, editable=False):
        """Create a ComboBox with optional completer and editing capabilities."""
        combobox = QComboBox()
        combobox.setFixedWidth(width * 10)
        if callback:
            combobox.currentIndexChanged.connect(callback)
        if enable_completer:
            completer = QCompleter()
            completer.setCompletionMode(QCompleter.PopupCompletion)
            combobox.setCompleter(completer)
        combobox.setEditable(editable)
        if editable:
            line_edit = combobox.lineEdit()
            line_edit.textChanged.connect(self.convert_text_to_uppercase)
        layout.addWidget(combobox)
        return combobox

    def convert_text_to_uppercase(self, text):
        """Convert entered text to uppercase."""
        sender = self.sender()
        sender.setText(text.upper())

    def update_combobox(self, combobox, values):
        """Update the ComboBox with new values."""
        combobox.clear()
        combobox.addItems(sorted([str(value) for value in values]))
        if len(values) > 0:
            combobox.setCurrentIndex(0)
        if combobox.completer():
            combobox.completer().setModel(combobox.model())

    def clear_combobox(self, combobox):
        """Clear the ComboBox items."""
        combobox.clear()

    # def on_exchange_segment_change(self):
    #     """Handle Exchange Segment change."""
    #     exchange_segment = self.exchange_segment_cb.currentText()
    #     filtered_df = self.masterdf[self.masterdf['ExchangeSegment'] == exchange_segment]
    #     self.update_combobox(self.series_cb, filtered_df['Series'].unique())
    #     self.reset_comboboxes()

    def on_exchange_segment_change(self):
        """Handle Exchange Segment change."""
        # Get the selected exchange segment
        exchange_segment = self.exchange_segment_cb.currentText()

        # Filter data based on the selected Exchange Segment
        filtered_df = self.masterdf[self.masterdf['ExchangeSegment'] == exchange_segment]

        # Reset dependent comboboxes before updating them
        self.reset_comboboxes()

        # Update the Series combobox with available series for the selected exchange segment
        self.update_combobox(self.series_cb, filtered_df['Series'].unique())

        # Set default Series based on Exchange Segment
        if exchange_segment == "NSECM":
            # Default to "EQ" for NSECM
            default_series = "EQ"
        elif exchange_segment == "NSEFO":
            # Default to "OPTIDX" for NSEFO
            default_series = "OPTIDX"
        else:
            default_series = None

        # Set the default series in the Series combobox if it exists in the filtered data
        if default_series and default_series in filtered_df['Series'].unique():
            self.series_cb.setCurrentText(default_series)

        # Trigger the series change logic to update other comboboxes based on the default series selection
        self.on_series_change()

    def on_series_change(self):
        """Handle Series change."""
        series = self.series_cb.currentText()
        exchange_segment = self.exchange_segment_cb.currentText()
        filtered_df = self.masterdf[(self.masterdf['ExchangeSegment'] == exchange_segment) & (self.masterdf['Series'] == series)]
        self.update_combobox(self.name_cb, filtered_df['Name'].unique())

    def on_name_change(self):
        """Handle Name change."""
        exchange_segment = self.exchange_segment_cb.currentText()
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()

        # Filter based on Exchange Segment, Series, and Name
        if exchange_segment == "NSEFO":
            filtered_df = self.masterdf[
                (self.masterdf['ExchangeSegment'] == exchange_segment) &
                (self.masterdf['Series'] == series) &
                (self.masterdf['Name'] == name)
            ]

            # If series is FUTIDX or FUTSTK, disable StrikePrice and OptionType
            if series in ["FUTIDX", "FUTSTK"]:
                # Disable StrikePrice and OptionType ComboBoxes
                self.strike_price_cb.clear()
                self.option_type_cb.clear()
                self.strike_price_cb.setEnabled(False)
                self.option_type_cb.setEnabled(False)

                # Sort Contract Expiry dates in descending order
                sorted_contracts = filtered_df.sort_values(by='ContractExpiration', ascending=False)
                formatted_dates = sorted_contracts['ContractExpiration'].apply(format_date).unique()
                self.update_combobox(self.contract_exp_cb, formatted_dates)

                # Call on_contract_exp_change to update ExchangeInstrumentID
                self.on_contract_exp_change()

            # If the series is OPTIDX or OPTSTK, enable StrikePrice and OptionType
            elif series in ["OPTIDX", "OPTSTK"]:
                # Enable StrikePrice and OptionType ComboBoxes
                self.strike_price_cb.setEnabled(True)
                self.option_type_cb.setEnabled(True)

                # Sort Contract Expiry dates in descending order
                sorted_contracts = filtered_df.sort_values(by='ContractExpiration', ascending=False)
                formatted_dates = sorted_contracts['ContractExpiration'].apply(format_date).unique()
                self.update_combobox(self.contract_exp_cb, formatted_dates)

                # Call on_contract_exp_change to ensure proper updates
                self.on_contract_exp_change()

        elif exchange_segment == "NSECM":
            filtered_df = self.masterdf[
                (self.masterdf['ExchangeSegment'] == exchange_segment) &
                (self.masterdf['Series'] == series) &
                (self.masterdf['Name'] == name)
            ]
            if not filtered_df.empty:
                self.update_exchange_instrument_id(filtered_df)  # Ensure ExchangeInstrumentID is updated
            else:
                self.clear_combobox(self.instrument_id_cb)

    def on_contract_exp_change(self):
        """Handle Contract Expiration change."""
        exchange_segment = self.exchange_segment_cb.currentText()
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = pd.to_datetime(self.contract_exp_cb.currentText(), format='%d%b%y').date()

        if exchange_segment == "NSEFO":
            filtered_df = self.masterdf[
                (self.masterdf['ExchangeSegment'] == exchange_segment) &
                (self.masterdf['Series'] == series) &
                (self.masterdf['Name'] == name) &
                (self.masterdf['ContractExpiration'] == contract_exp)
            ]

            # For FUTIDX and FUTSTK, do not show StrikePrice and OptionType
            if series in ["FUTIDX", "FUTSTK"]:
                self.update_exchange_instrument_id(filtered_df)  # Only update ExchangeInstrumentID

            # For OPTIDX and OPTSTK, show StrikePrice and OptionType
            elif series in ["OPTIDX", "OPTSTK"]:
                self.update_combobox(self.strike_price_cb, sorted(filtered_df['StrikePrice'].unique()))
                self.on_strike_price_change()


    def on_strike_price_change(self):
        """Handle Strike Price change."""
        exchange_segment = self.exchange_segment_cb.currentText()
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = pd.to_datetime(self.contract_exp_cb.currentText(), format='%d%b%y').date()
        strike_price = self.strike_price_cb.currentText()

        if exchange_segment == "NSEFO" and series in ["OPTIDX", "OPTSTK"]:
            filtered_df = self.masterdf[
                (self.masterdf['ExchangeSegment'] == exchange_segment) &
                (self.masterdf['Series'] == series) &
                (self.masterdf['Name'] == name) &
                (self.masterdf['ContractExpiration'] == contract_exp) &
                (self.masterdf['StrikePrice'] == strike_price)
            ]
            self.update_combobox(self.option_type_cb, filtered_df['OptionType'].unique())

    def on_option_type_change(self):
        """Handle Option Type change."""
        exchange_segment = self.exchange_segment_cb.currentText()
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = pd.to_datetime(self.contract_exp_cb.currentText(), format='%d%b%y').date()
        strike_price = self.strike_price_cb.currentText()
        option_type = self.option_type_cb.currentText()

        # Ensure that ExchangeInstrumentID updates based on current selections
        filtered_df = self.masterdf[
            (self.masterdf['ExchangeSegment'] == exchange_segment) &
            (self.masterdf['Series'] == series) &
            (self.masterdf['Name'] == name) &
            (self.masterdf['ContractExpiration'] == contract_exp) &
            (self.masterdf['StrikePrice'] == strike_price) &
            (self.masterdf['OptionType'] == option_type)
        ]
        self.update_exchange_instrument_id(filtered_df)

    def on_option_type_change(self):
        """Handle Option Type change."""
        exchange_segment = self.exchange_segment_cb.currentText()
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = pd.to_datetime(self.contract_exp_cb.currentText(), format='%d%b%y').date()
        strike_price = self.strike_price_cb.currentText()
        option_type = self.option_type_cb.currentText()

        filtered_df = self.masterdf[
            (self.masterdf['ExchangeSegment'] == exchange_segment) &
            (self.masterdf['Series'] == series) &
            (self.masterdf['Name'] == name) &
            (self.masterdf['ContractExpiration'] == contract_exp) &
            (self.masterdf['StrikePrice'] == strike_price) &
            (self.masterdf['OptionType'] == option_type)
        ]
        self.update_exchange_instrument_id(filtered_df)

    def update_exchange_instrument_id(self, filtered_df):
        """Update the ExchangeInstrumentID combobox based on the filtered DataFrame."""
        self.update_combobox(self.instrument_id_cb, filtered_df['ExchangeInstrumentID'].unique())

    def reset_comboboxes(self):
        """Reset all dependent ComboBoxes."""
        self.clear_combobox(self.name_cb)
        self.clear_combobox(self.contract_exp_cb)
        self.clear_combobox(self.strike_price_cb)
        self.clear_combobox(self.option_type_cb)
        self.clear_combobox(self.instrument_id_cb)

    def keyPressEvent(self, event):
        """Handle key events for selection."""
        if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            # Gather selected data from comboboxes
            series = self.series_cb.currentText()
            name = self.name_cb.currentText()
            contract_exp = self.contract_exp_cb.currentText()
            strike_price = self.strike_price_cb.currentText()
            option_type = self.option_type_cb.currentText()
            exchange_instrument_id = self.instrument_id_cb.currentText()

            try:
                # Filter the master data for the selected ExchangeInstrumentID to get actual values
                filtered_df = self.masterdf[self.masterdf['ExchangeInstrumentID'] == int(exchange_instrument_id)]

                if not filtered_df.empty:
                    # Retrieve real values from the filtered dataframe
                    exchange_segment = filtered_df.iloc[0]['ExchangeSegment']
                    instrument_type = filtered_df.iloc[0]['InstrumentType']
                    description = filtered_df.iloc[0]['Description']
                    name_with_series = filtered_df.iloc[0]['NameWithSeries']
                    instrument_id = filtered_df.iloc[0]['InstrumentID']
                    price_band_high = filtered_df.iloc[0]['PriceBandHigh']
                    price_band_low = filtered_df.iloc[0]['PriceBandLow']
                    freeze_qty = filtered_df.iloc[0]['FreezeQty']
                    tick_size = filtered_df.iloc[0]['TickSize']
                    lot_size = filtered_df.iloc[0]['LotSize']
                    multiplier = filtered_df.iloc[0]['Multiplier']
                    underlying_instrument_id = filtered_df.iloc[0]['UnderlyingInstrumentId']
                    underlying_index_name = filtered_df.iloc[0]['UnderlyingIndexName']
                    contract_expiration = filtered_df.iloc[0]['ContractExpiration']
                    display_name = filtered_df.iloc[0]['displayName']
                    isin = filtered_df.iloc[0]['ISIN']
                else:
                    # Default values if no data is found
                    exchange_segment = "N/A"
                    instrument_type = "N/A"
                    description = "N/A"
                    name_with_series = "N/A"
                    instrument_id = "N/A"
                    price_band_high = 0
                    price_band_low = 0
                    freeze_qty = 0
                    tick_size = 0
                    lot_size = 0
                    multiplier = 1
                    underlying_instrument_id = "N/A"
                    underlying_index_name = "N/A"
                    contract_expiration = "0"
                    display_name = "N/A"
                    isin = "N/A"

                # Prepare the selected data to emit (leave missing fields blank)
                selected_data = {
                    "ExchangeSegment": exchange_segment,
                    "Series": series,
                    "StrikePrice": strike_price,
                    "OptionType": option_type,
                    "Name": name,
                    "BidQty": "",  # Blank as no data is available
                    "Bid Price": "",  # Blank as no data is available
                    "Ask Price": "",  # Blank as no data is available
                    "Ask Qty": "",  # Blank as no data is available
                    "LTP": "",  # Blank as no data is available
                    "LTQ": "",  # Blank as no data is available
                    "ATP": "",  # Blank as no data is available
                    "Open": "",  # Blank as no data is available
                    "High": "",  # Blank as no data is available
                    "Low": "",  # Blank as no data is available
                    "Close": "",  # Blank as no data is available
                    "InstrumentType": instrument_type,
                    "Description": description,
                    "NameWithSeries": name_with_series,
                    "InstrumentID": instrument_id,
                    "PriceBandHigh": price_band_high,
                    "PriceBandLow": price_band_low,
                    "FreezeQty": freeze_qty,
                    "TickSize": tick_size,
                    "LotSize": lot_size,
                    "Multiplier": multiplier,
                    "UnderlyingInstrumentId": underlying_instrument_id,
                    "UnderlyingIndexName": underlying_index_name,
                    "ContractExpiration": contract_expiration,
                    "displayName": display_name,
                    "ISIN": isin,
                    "ExchangeInstrumentID": exchange_instrument_id
                }

                print("Selected Data:", selected_data)
                self.data_selected.emit(selected_data)  # Emit the selected data as a dictionary

            except ValueError:
                print("Please enter a valid Exchange Instrument ID.")

# Main Application Entry Point
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Initialize the application with an empty DataFrame for now
    dummy_df = pd.DataFrame()
    window = Application(dummy_df)
    window.show()

    sys.exit(app.exec_())
