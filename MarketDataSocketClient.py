import socketio
import os
import configparser
from datetime import datetime

class MDSocket_io(socketio.Client):
    """A Socket.IO client implementation."""

    def __init__(self, token, userID, reconnection=False, reconnection_attempts=0, reconnection_delay=1,
                 reconnection_delay_max=50000, randomization_factor=0.5, logger=False, binary=False, json=None,
                 **kwargs):
        self.sid = socketio.Client(logger=False, engineio_logger=False, ssl_verify=False)
        self.eventlistener = self.sid

        # Attach all the event handlers
        self.sid.on('connect', self.on_connect)
        self.sid.on('message', self.on_message)
        self.sid.on('1501-json-full', self.on_message1501_json_full)
        self.sid.on('1501-json-partial', self.on_message1501_json_partial)
        self.sid.on('1502-json-full', self.on_message1502_json_full)
        self.sid.on('1502-json-partial', self.on_message1502_json_partial)
        self.sid.on('1505-json-full', self.on_message1505_json_full)
        self.sid.on('1505-json-partial', self.on_message1505_json_partial)
        self.sid.on('1507-json-full', self.on_message1507_json_full)
        self.sid.on('1510-json-full', self.on_message1510_json_full)
        self.sid.on('1510-json-partial', self.on_message1510_json_partial)
        self.sid.on('1512-json-full', self.on_message1512_json_full)
        self.sid.on('1512-json-partial', self.on_message1512_json_partial)
        self.sid.on('disconnect', self.on_disconnect)

        # Load root URL from the config file
        currDirMain = os.getcwd()
        configParser = configparser.ConfigParser()
        configFilePath = os.path.join(currDirMain, 'config.ini')
        configParser.read(configFilePath)

        self.port = configParser.get('root_url', 'root')
        self.userID = userID
        publishFormat = 'JSON'
        self.broadcastMode = configParser.get('root_url', 'broadcastMode')
        self.token = token

        # Form the WebSocket connection URL
        port = f'{self.port}/?token='
        self.connection_url = (
            port + token + '&userID=' + self.userID +
            '&publishFormat=' + publishFormat + '&broadcastMode=' + self.broadcastMode
        )

    def connect(self, headers={}, transports=['websocket'], namespaces=None, socketio_path='/apimarketdata/socket.io'):
        """Connect to a Socket.IO server with forced WebSocket transport."""
        url = self.connection_url
        
        # Ensure only WebSocket transport is used
        print(f"Attempting connection to: {url} with WebSocket transport")
        self.sid.connect(url, headers=headers, transports=transports, namespaces=namespaces, socketio_path=socketio_path)
        self.sid.wait()  # Wait indefinitely for messages

    def on_connect(self):
        """Handle successful connection event."""
        print('Market Data Socket connected successfully!')

    def on_message(self, data):
        """Handle receiving a generic message."""
        print(f'Received message: {data}')

    def on_message1501_json_full(self, data):
        """Handle 1501 full message."""
        print(f'Received 1501 Full Level1,Touchline message: {data}')

    def on_message1502_json_full(self, data):
        """Handle 1502 full message."""
        print(f'Received 1502 Market depth full message: {data}')

    def on_message1507_json_full(self, data):
        """Handle 1507 full message."""
        print(f'Received 1507 MarketStatus full message: {data}')

    def on_message1512_json_full(self, data):
        """Handle 1512 full message."""
        print(f'Received 1512 LTP full message: {data}')

    def on_message1505_json_full(self, data):
        """Handle 1505 full message."""
        print(f'Received 1505 Candle data full message: {data}')

    def on_message1510_json_full(self, data):
        """Handle 1510 full message."""
        print(f'Received 1510 Open interest full message: {data}')

    def on_message1501_json_partial(self, data):
        """Handle 1501 partial message."""
        now = datetime.now()
        print(f'{now.strftime("%H:%M:%S")} - Received 1501 Partial Touchline message: {data}')

    def on_message1502_json_partial(self, data):
        """Handle 1502 partial message."""
        print(f'Received 1502 Market depth partial message: {data}')
    
    def on_message1512_json_partial(self, data):
        """Handle 1512 partial message."""
        print(f'Received 1512 LTP partial message: {data}')

    def on_message1505_json_partial(self, data):
        """Handle 1505 partial message."""
        print(f'Received 1505 Candle data partial message: {data}')

    def on_message1510_json_partial(self, data):
        """Handle 1510 partial message."""
        print(f'Received 1510 Open interest partial message: {data}')

    def on_disconnect(self):
        """Handle disconnect event."""
        print('Market Data Socket disconnected!')

    def on_error(self, data):
        """Handle error event."""
        print(f'Market Data Error: {data}')

    def get_emitter(self):
        """Get the event listener for attaching more event handlers."""
        return self.eventlistener
