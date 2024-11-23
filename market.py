import asyncio
import websockets
import json
from MarketDataSocketClient import MDSocket_io

def start_test(xt_market, market_user_id, market_data_token):
    # Initialize MarketData socket client
    market_data_socket = MDSocket_io(market_data_token, market_user_id)

    # Callback when connected to the market data socket
    def on_connect():
        """Handles connection to the market data socket."""
        print('Market Data Socket connected successfully!')

    # Async function to continuously send messages to WebSocket clients
    async def send_message(websocket, queue):
        while True:
            # Fetch the next message from the queue
            message = await queue.get()

            try:
                # Send the message to the WebSocket client
                await websocket.send(message)
            except websockets.ConnectionClosed:
                print("Connection closed, unable to send message")
                break

    # Function to process incoming messages from the WebSocket client
    async def process_message(websocket, message, queue):
        try:
            data = json.loads(message)
            if data.get('action') == 'subscribe':
                # Extract the exchangeSegment and exchangeInstrumentID from the message
                exchange_segment = int(data.get('exchangeSegment'))
                exchange_instrument_id = int(data.get('exchangeInstrumentID'))

                # Subscribe to the instrument
                instruments = [{'exchangeSegment': exchange_segment, 'exchangeInstrumentID': exchange_instrument_id}]
                print(f"Subscribing to: {instruments}")

                subscription_response = xt_market.send_subscription(instruments, 1502)

                # Prepare the response as JSON
                response_data = {
                    'status': 'subscribed',
                    'instruments': instruments,
                    'subscription_response': subscription_response
                }

                # Send confirmation back to the WebSocket client as JSON
                await queue.put(json.dumps(response_data))
            else:
                await queue.put(json.dumps({"status": "error", "message": "Invalid action specified"}))
        except Exception as e:
            await queue.put(json.dumps({"status": "error", "message": f"Error processing message: {str(e)}"}))

    # Function to handle socket communication and event callbacks
    def handle_socket(queue, websocket, loop):
        """Handles market data socket events and forwards messages to the WebSocket."""
        
        # Callback for receiving 1501 Touchline full data
        def on_message1502_json_full(data):
            # Send the received data to the WebSocket queue
            asyncio.run_coroutine_threadsafe(queue.put(f"{data}"), loop)

        # Assign callbacks for the socket events
        market_data_socket.on_connect = on_connect
        market_data_socket.on_message1502_json_full = on_message1502_json_full

        # Event listener setup
        event_listener = market_data_socket.get_emitter()
        event_listener.on('connect', on_connect)
        event_listener.on('1502-json-full', on_message1502_json_full)

        # Connect to the market data socket (this blocks the thread)
        market_data_socket.connect()

    # Main function to handle WebSocket communication and socket integration
    async def main(websocket, path):
        # Create an asyncio queue to store messages from the market data socket
        queue = asyncio.Queue()

        # Get the current event loop
        loop = asyncio.get_event_loop()

        # Notify the WebSocket client about the connection
        await websocket.send("WebSocket server connected. You can now send subscription requests.")

        # Run the market data socket handler in a separate thread/executor
        loop.run_in_executor(None, handle_socket, queue, websocket, loop)

        # Run the WebSocket message sender concurrently
        send_task = asyncio.create_task(send_message(websocket, queue))

        try:
            # Listen for incoming messages from the WebSocket client
            async for message in websocket:
                await process_message(websocket, message, queue)
        except websockets.ConnectionClosed:
            print("WebSocket connection closed")

        # Wait for the send_message task to finish
        await send_task

    # Function to start the WebSocket server
    async def start_server():
        # Start a WebSocket server on localhost:8765
        async with websockets.serve(main, "localhost", 8766):
            await asyncio.Future()  # Keep the server running indefinitely


    asyncio.run(start_server())
