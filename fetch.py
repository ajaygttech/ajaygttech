import sys
import pandas as pd
import requests
from PyQt5.QtWidgets import QWidget, QComboBox, QVBoxLayout, QHBoxLayout, QCompleter, QPushButton, QApplication, QTableWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from io import StringIO
from datetime import datetime

# Define format_date function
def format_date(date):
    return date.strftime('%d%b%y').upper()

class Application(QWidget):
    data_selected = pyqtSignal(dict)  # Signal to emit selected data row as a dictionary

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instrument Filter")
        self.masterdf = self.fetch_data() 

        # Check if the master data is empty
        if self.masterdf.empty:
            print("Master data is empty. Unable to proceed.")
            return

        # Layouts
        main_layout = QVBoxLayout()
        combobox_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 0, 10, 10)

        # Action combobox for selecting Buy or Sell
        self.action_cb = self.create_combobox(combobox_layout, 10)
        self.update_combobox(self.action_cb, ["Buy", "Sell"])  # Buy/Sell options

        # Create comboboxes and layout for other fields
        self.series_cb = self.create_combobox(combobox_layout, 6, self.on_series_change)
        self.name_cb = self.create_combobox(combobox_layout, 10, self.on_name_change, enable_completer=True, editable=True)
        self.contract_exp_cb = self.create_combobox(combobox_layout, 7, self.on_contract_exp_change)
        self.strike_price_cb = self.create_combobox(combobox_layout, 7, self.on_strike_price_change)
        self.option_type_cb = self.create_combobox(combobox_layout, 5, self.on_option_type_change)

        # Instrument ID combobox
        self.instrument_id_cb = self.create_combobox(combobox_layout, 10)

        # Add button in the combobox row
        self.add_button = QPushButton("Add")
        self.add_button.setFixedWidth(80)
        self.add_button.clicked.connect(self.on_add_button_clicked)
        combobox_layout.addWidget(self.add_button)

        # Load initial data into the first combobox
        self.update_combobox(self.series_cb, self.masterdf['Series'].unique())  # Populate the Series combobox
        self.update_combobox(self.name_cb, self.masterdf['Name'].unique())  # Populate the Name combobox

        # Trigger default selection after window loads
        self.series_cb.setCurrentIndex(0)
        self.on_series_change()

        # Set layout
        main_layout.addLayout(combobox_layout)
        self.setLayout(main_layout)

    def fetch_data(self):
        """Fetch master data from Flask server."""
        try:
            response = requests.get('http://localhost:5000/fetch_data')
            data = response.json()

            if data['status'] == 'success':
                # Read the master data into a DataFrame
                master_data = data['data']
                df = pd.read_csv(StringIO(master_data), sep='|', usecols=range(19), header=None, low_memory=False)
                df.columns = [
                    "ExchangeSegment", "ExchangeInstrumentID", "InstrumentType", "Name", "Description", 
                    "Series", "NameWithSeries", "InstrumentID", "PriceBandHigh", "PriceBandLow", 
                    "FreezeQty", "TickSize", "LotSize", "Multiplier", "UnderlyingInstrumentId", 
                    "UnderlyingIndexName", "ContractExpiration", "StrikePrice", "OptionType"
                ]
                df['ContractExpiration'] = pd.to_datetime(df['ContractExpiration'], errors='coerce').apply(lambda x: x.date())
                df['OptionType'] = df['OptionType'].replace({1: 'Spread', 3: 'CALL', 4: 'PUT'})
                df = df.dropna(subset=['ContractExpiration'])

                # Filter for Series OPTIDX and FUTIDX and exclude rows containing SPD in StrikePrice
                df = df[
                    (df['Series'].isin(['OPTIDX', 'FUTIDX'])) & 
                    (~df['StrikePrice'].str.contains('SPD', na=False))
                ]
                return df
            else:
                print("Error fetching master data:", data['message'])
                return pd.DataFrame()
        except Exception as e:
            print("Exception fetching master data:", str(e))
            return pd.DataFrame()

    def create_combobox(self, layout, width, callback=None, enable_completer=False, editable=False):
        combobox = QComboBox()
        combobox.setFixedWidth(width * 10)
        if callback:
            combobox.currentIndexChanged.connect(callback)
        if enable_completer and editable:
            completer = QCompleter()
            completer.setCompletionMode(QCompleter.PopupCompletion)
            combobox.setCompleter(completer)
        combobox.setEditable(editable)  # Allow editing if specified
        if editable:
            line_edit = combobox.lineEdit()
            line_edit.textChanged.connect(self.convert_text_to_uppercase)  # Convert text to uppercase
        layout.addWidget(combobox)
        return combobox

    def convert_text_to_uppercase(self, text):
        sender = self.sender()
        sender.setText(text.upper())  # Convert text to uppercase

    def update_combobox(self, combobox, values):
        combobox.blockSignals(True)  # Block signals to prevent unnecessary triggering
        combobox.clear()
        combobox.addItems([str(value) for value in values])  # Add values in the provided order
        if len(values) > 0:
            combobox.setCurrentIndex(0)  # Set the first item as the default selection
        combobox.blockSignals(False)  # Unblock signals

    def on_series_change(self):
        """Handle changes in the series combobox."""
        series = self.series_cb.currentText()
        filtered_df = self.masterdf[self.masterdf['Series'] == series]
        
        # Update Name combobox
        self.update_combobox(self.name_cb, filtered_df['Name'].unique())
        
        # Trigger name change based on default value
        self.name_cb.setCurrentIndex(0)
        self.on_name_change()

    def on_name_change(self):
        """Handle changes in the name combobox."""
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        
        # Filter DataFrame based on series and name
        filtered_df = self.masterdf[(self.masterdf['Series'] == series) & (self.masterdf['Name'] == name)]
        
        # Sort Contract Expiration in descending order (latest date first)
        sorted_contracts = filtered_df.sort_values(by='ContractExpiration', ascending=True)
        
        # Format the sorted contract expiration dates
        formatted_dates = sorted_contracts['ContractExpiration'].apply(format_date).unique()
        
        # Update Contract Expiration combobox
        self.update_combobox(self.contract_exp_cb, formatted_dates)
        
        # Trigger contract expiration change based on default value
        self.contract_exp_cb.setCurrentIndex(0)
        self.on_contract_exp_change()

    def on_contract_exp_change(self):
        """Handle changes in the contract expiration combobox."""
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = self.contract_exp_cb.currentText()
        
        # Filter DataFrame based on series, name, and contract expiration
        filtered_df = self.masterdf[
            (self.masterdf['Series'] == series) & 
            (self.masterdf['Name'] == name) & 
            (self.masterdf['ContractExpiration'].apply(format_date) == contract_exp)
        ]
        
        # If series is 'FUTIDX', clear the Strike Price and Option Type combobox
        if series == 'FUTIDX':
            self.strike_price_cb.clear()
            self.option_type_cb.clear()
            self.update_instrument_id_cb(filtered_df)
        else:
            # Update Strike Price combobox
            self.update_combobox(self.strike_price_cb, filtered_df['StrikePrice'].unique())
            self.strike_price_cb.setCurrentIndex(0)
            self.on_strike_price_change()

    def on_strike_price_change(self):
        """Handle changes in the strike price combobox."""
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = self.contract_exp_cb.currentText()
        strike_price = self.strike_price_cb.currentText()
        
        # Filter DataFrame based on series, name, contract expiration, and strike price
        filtered_df = self.masterdf[
            (self.masterdf['Series'] == series) & 
            (self.masterdf['Name'] == name) & 
            (self.masterdf['ContractExpiration'].apply(format_date) == contract_exp) &
            (self.masterdf['StrikePrice'] == strike_price)
        ]
        
        # Update Option Type combobox if the series is not FUTIDX
        if series != 'FUTIDX':
            self.update_combobox(self.option_type_cb, filtered_df['OptionType'].unique())
            self.option_type_cb.setCurrentIndex(0)
            self.on_option_type_change()

    def on_option_type_change(self):
        """Handle changes in the option type combobox."""
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = self.contract_exp_cb.currentText()
        strike_price = self.strike_price_cb.currentText()
        option_type = self.option_type_cb.currentText()

        # Filter DataFrame based on series, name, contract expiration, strike price, and option type
        filtered_df = self.masterdf[
            (self.masterdf['Series'] == series) & 
            (self.masterdf['Name'] == name) & 
            (self.masterdf['ContractExpiration'].apply(format_date) == contract_exp) &
            (self.masterdf['StrikePrice'] == strike_price) &
            (self.masterdf['OptionType'] == option_type)
        ]
        
        self.update_instrument_id_cb(filtered_df)

    def update_instrument_id_cb(self, filtered_df):
        """Update the Exchange Instrument ID combobox based on selected values."""
        self.update_combobox(self.instrument_id_cb, filtered_df['ExchangeInstrumentID'].unique())

    def on_add_button_clicked(self):
        """Handle Add button click."""
        series = self.series_cb.currentText()
        name = self.name_cb.currentText()
        contract_exp = self.contract_exp_cb.currentText()
        strike_price = self.strike_price_cb.currentText()
        option_type = self.option_type_cb.currentText()
        exchange_instrument_id = self.instrument_id_cb.currentText()
        
        # Filter the master data for the selected instrument ID to get actual values
        filtered_df = self.masterdf[self.masterdf['ExchangeInstrumentID'] == int(exchange_instrument_id)]
        
        if not filtered_df.empty:
            # Retrieve real values from the filtered dataframe
            lot_size = filtered_df.iloc[0]['LotSize']
            tick_size = filtered_df.iloc[0]['TickSize']
            freeze_qty = filtered_df.iloc[0]['FreezeQty']
            price_band_high = filtered_df.iloc[0]['PriceBandHigh']
            price_band_low = filtered_df.iloc[0]['PriceBandLow']
        else:
            lot_size = 100  # Default value if no data is found
            tick_size = 0.05  # Default value if no data is found
            freeze_qty = 1000  # Default value if no data is found
            price_band_high = 5000  # Default value if no data is found
            price_band_low = 1000  # Default value if no data is found

        selected_data = {
            'Action': self.action_cb.currentText(),  # Buy/Sell action
            'Exchange Segment': 'NSEFO',  # Adding the Exchange value
            'Series': series,
            'Name': name,
            'Contract Expiration': contract_exp,
            'Strike Price': strike_price,
            'Option Type': option_type,
            'Exchange Instrument ID': exchange_instrument_id,
            'Lot Size': lot_size,
            'Tick Size': tick_size,
            'Freeze Qty': freeze_qty,
            'Price Band High': price_band_high,
            'Price Band Low': price_band_low
        }

        print("Selected Data:", selected_data)
        self.data_selected.emit(selected_data)  # Emit the signal to send data to another widget

