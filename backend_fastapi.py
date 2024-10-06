# backend_fastapi.py

from fastapi import FastAPI, WebSocket
from Connect import XTSConnect
from MarketDataSocketClient import MDSocket_io
import threading
import time
import asyncio
import json

# MarketData API Credentials
API_KEY = "145c98468edda965f03394"
API_SECRET = "Brqk551$wa"
source = "WEBAPI"

# Initialise XTSConnect
xt = XTSConnect(API_KEY, API_SECRET, source)

# Login for authorization token
response = xt.marketdata_login()

# Store the token and userid
set_marketDataToken = response['result']['token']
set_muserID = response['result']['userID']
print("Login: ", response)

app = FastAPI()

class MarketDataThread(threading.Thread):
    def __init__(self, websocket, loop):
        super().__init__()
        self.websocket = websocket
        self.loop = loop
        self.soc = None
        self.subscribed_instruments = []  # Store subscribed instruments

    def run(self):
        try:
            self.connect_market_data_socket()
        except Exception as e:
            print(f"Error in market data thread: {e}")

    def connect_market_data_socket(self):
        self.soc = MDSocket_io(set_marketDataToken, set_muserID)

        # Callback for connection
        def on_connect():
            print('Market Data Socket connected successfully!')

            # Send the previously subscribed instruments
            if self.subscribed_instruments:
                self.send_subscription_request(self.subscribed_instruments)

        # Callback on receiving message
        def on_message(data):
            print(f"Received message: {data}")
            asyncio.run_coroutine_threadsafe(self.send_message(f"I received a message! {data}"), self.loop)

        # Callback for message code 1501 FULL
        def on_message1501_json_full(data):
            print(f"Received full message 1501: {data}")
            asyncio.run_coroutine_threadsafe(self.send_message(f"I received a 1501 Touchline message! {data}"), self.loop)

        # Callback for disconnection
        def on_disconnect():
            print('Market Data Socket disconnected! Reconnecting in 5 seconds...')
            time.sleep(5)  # Wait 5 seconds before reconnecting
            self.connect_market_data_socket()  # Attempt to reconnect

        # Callback for error
        def on_error(data):
            print(f"Market Data Error: {data}")

        # Assign the callbacks
        self.soc.on_connect = on_connect
        self.soc.on_message = on_message
        self.soc.on_message1501_json_full = on_message1501_json_full
        self.soc.on_disconnect = on_disconnect
        self.soc.on_error = on_error

        # Start connecting to the market data socket
        print("Starting market data socket connection...")
        self.soc.connect()

    async def send_message(self, message):
        """Send the message back through the WebSocket asynchronously"""
        try:
            print(f"Sending message to WebSocket: {message}")
            await self.websocket.send_text(message)
        except Exception as e:
            print(f"Error sending message: {e}")

    def send_subscription_request(self, instruments):
        """Send the subscription request for the given instruments"""
        print(f'Sending subscription request for Instruments - {instruments}')
        response = xt.send_subscription(instruments, 1501)
        print(f'Sent Subscription request! Subscription response: {response}')
        asyncio.run_coroutine_threadsafe(self.send_message(f"Subscription response: {response}"), self.loop)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    loop = asyncio.get_event_loop()
    market_data_thread = MarketDataThread(websocket, loop)
    market_data_thread.start()

    try:
        print("WebSocket connection open")

        # Listen for messages from the frontend
        while True:
            data = await websocket.receive_text()
            print(f"Received from client: {data}")

            # Handle subscription requests
            try:
                message = json.loads(data)
                if message.get("action") == "subscribe":
                    instruments = message.get("instruments", [])
                    print(f"Subscribing to instruments: {instruments}")

                    # Send the subscription request via the market data thread
                    market_data_thread.subscribed_instruments = instruments
                    market_data_thread.send_subscription_request(instruments)

            except json.JSONDecodeError as e:
                print(f"Error parsing message: {e}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("WebSocket connection closed")
