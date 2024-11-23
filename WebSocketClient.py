import json
import asyncio
import websockets
from PyQt5.QtCore import QThread, pyqtSignal

class WebSocketClient(QThread):
    response_received = pyqtSignal(str)  # Signal to update both tables with WebSocket messages

    def __init__(self, parent=None):
        super(WebSocketClient, self).__init__(parent)
        self.websocket = None
        self.loop = asyncio.new_event_loop()

    async def connect(self):
        try:
            async with websockets.connect("ws://localhost:8766") as websocket:
                self.websocket = websocket
                await self.listen_to_messages()
        except Exception as e:
            print(f"Error connecting to WebSocket: {e}")

    async def listen_to_messages(self):
        async for message in self.websocket:
            self.response_received.emit(message)

    def send_subscription(self, exchange_segment, exchange_instrument_id):
        data = {
            'action': 'subscribe',
            'exchangeSegment': exchange_segment,
            'exchangeInstrumentID': exchange_instrument_id
        }
        asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps(data)), self.loop)

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())
