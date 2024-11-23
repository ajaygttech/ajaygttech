import asyncio
import websockets
import json
from Connect import XTSConnect
from InteractiveSocketClient import OrderSocket_io

# Path to the JSON file where credentials are saved
CREDENTIALS_FILE = 'credentials.json'


def load_credentials():
    """Load credentials from the JSON file."""
    with open(CREDENTIALS_FILE, 'r') as f:
        return json.load(f)


async def send_message(websocket, path, queue):
    # Send a connection confirmation as soon as the WebSocket connection is made
    await websocket.send("WebSocket connection established. Waiting for updates...")

    while True:
        # Fetch the message from the queue
        message = await queue.get()

        try:
            # Send the message to the WebSocket client, ensure it's awaited
            await websocket.send(message)
        except websockets.ConnectionClosed:
            print("Connection closed, cannot send message")
            break


async def send_direct_message(websocket, message):
    try:
        # Send a message directly through the WebSocket
        await websocket.send(message)
    except websockets.ConnectionClosed:
        print("Connection closed, cannot send direct message")


def handle_socket(queue, websocket, loop):
    # Load Interactive API credentials from JSON file
    credentials = load_credentials()
    order_user_id = credentials['order_user_id']
    order_token = credentials['order_token']
    source = "WEBAPI"

    # Initialize XTSConnect instance with loaded credentials
    xt = XTSConnect("", "", source)  # Keys not needed for session reconnect

    # Connect to the Interactive socket
    soc = OrderSocket_io(order_token, order_user_id)

    # Define the socket callbacks to handle events
    def on_connect():
        # Queue a message via asyncio
        asyncio.run_coroutine_threadsafe(queue.put('Interactive socket connected successfully!'), loop)

    def on_joined(data):
        # Queue the message for processing
        asyncio.run_coroutine_threadsafe(queue.put(f"Interactive socket joined successfully! {data}"), loop)

    def on_order(data):
        # Queue the message
        asyncio.run_coroutine_threadsafe(queue.put(f"Order placed: {data}"), loop)

    def on_trade(data):
        # Queue the message
        asyncio.run_coroutine_threadsafe(queue.put(f"Trade received: {data}"), loop)

    # Assign the callbacks to handle socket events
    soc.on_connect = on_connect
    soc.on_joined = on_joined
    soc.on_order = on_order
    soc.on_trade = on_trade

    # Event listener for additional events
    el = soc.get_emitter()
    el.on('joined', on_joined)
    el.on('order', on_order)
    el.on('trade', on_trade)

    # Connect to the socket (this will block the current thread)
    soc.connect()


async def main(websocket, path):
    # Create an asyncio queue to store messages from the socket
    queue = asyncio.Queue()

    # Get the current event loop
    loop = asyncio.get_event_loop()

    # Notify the WebSocket client
    await websocket.send("WebSocket server connected. Waiting for socket connection...")

    # Run the socket connection in the background (blocking function)
    loop.run_in_executor(None, handle_socket, queue, websocket, loop)

    # Run the WebSocket communication concurrently with the socket handler
    await send_message(websocket, path, queue)


async def start_server():
    async with websockets.serve(main, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(start_server())
