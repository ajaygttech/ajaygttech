import requests
import asyncio
import websockets


class WebSocketClientBackend:
    def __init__(self, user_name="Fetching...", message_callback=None):
        """
        Initialize the WebSocket client backend.
        :param user_name: Name of the user for identification.
        :param message_callback: Function to call when a message is received.
        """
        self.user_name = user_name  # Initially a placeholder
        self.websocket = None
        self.message_callback = message_callback  # Callback to handle received messages

    async def connect(self):
        """
        Connect to the WebSocket server and fetch the profile data after connecting.
        """
        try:
            # Fetch ClientId before connecting
            client_id = self.fetch_profile()
            if client_id:
                self.user_name = client_id  # Set user_name to ClientId
            
            self.websocket = await websockets.connect("ws://localhost:8083")
            self._update_ui(f"Connected to server as {self.user_name}")
            # Send user name (ClientId) to server
            await self.websocket.send(self.user_name)
            # Start receiving messages
            await self.receive_messages()
        except Exception as e:
            self._update_ui(f"Connection failed: {e}")

    async def receive_messages(self):
        """
        Listen for incoming messages from the server.
        """
        try:
            async for message in self.websocket:
                self._update_ui(f"Server: {message}")
        except websockets.ConnectionClosed:
            self._update_ui("Connection closed")

    async def send_message(self, message):
        """
        Send a message to the WebSocket server.
        """
        if self.websocket and self.websocket.open:
            await self.websocket.send(message)

    async def close_connection(self):
        """
        Close the WebSocket connection.
        """
        if self.websocket and self.websocket.open:
            await self.websocket.close()

    def fetch_profile(self):
        """
        Fetch profile data from the given API URL and return the ClientName and ClientId.
        """
        try:
            response = requests.get("http://127.0.0.1:5000/get_profile")
            response.raise_for_status()
            profile_data = response.json()
            client_name = profile_data.get("profile", {}).get("ClientName", "Unknown")
            client_id = profile_data.get("profile", {}).get("ClientId", "Unknown")
            self._update_ui(f"Fetched Profile: ClientName={client_name}, ClientId={client_id}")
            return client_name, client_id
        except requests.RequestException as e:
            self._update_ui(f"Error fetching profile: {e}")
            return "Unknown", "Unknown"

        
    def place_order(self, order_data):
        """
        Send an order placement request to the Flask server.
        :param order_data: A dictionary containing order details.
        """
        try:
            response = requests.post("http://127.0.0.1:5000/place_order", json=order_data)
            response.raise_for_status()
            order_response = response.json()
            self._update_ui(f"Order placed successfully: {order_response}")
            return order_response
        except requests.RequestException as e:
            self._update_ui(f"Error placing order: {e}")
            return {"status": "error", "message": str(e)}
        
    def fetch_margin(self):
        """
        Fetch margin details from the API and return the netMarginAvailable value.
        """
        try:
            response = requests.get("http://127.0.0.1:5000/get_balance")
            response.raise_for_status()
            balance_data = response.json()

            # Extract netMarginAvailable from the JSON response
            balance_list = balance_data.get("balance", {}).get("BalanceList", [])
            if balance_list:
                net_margin_available = balance_list[0].get("limitObject", {}).get("RMSSubLimits", {}).get("netMarginAvailable")
                self._update_ui(f"Net Margin Available: {net_margin_available}")
                return float(net_margin_available) if net_margin_available is not None else None

        except requests.RequestException as e:
            self._update_ui(f"Error fetching margin: {e}")
        except (KeyError, ValueError, TypeError) as e:
            self._update_ui(f"Error parsing margin data: {e}")
        
        return None




    def _update_ui(self, message):
        """
        Trigger the UI callback with a new message.
        """
        if self.message_callback:
            self.message_callback(message)
