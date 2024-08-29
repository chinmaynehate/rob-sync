import asyncio
import websockets
import json
import sys

# Function to handle received messages
async def handle_message(websocket, message):
    print("Received message:", message)
    
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        # If the message is not JSON, just print it and return
        print(f"Non-JSON message received: {message}")
        return

    if "type" in data:
        print(f"Type: {data['type']}")

        if data["type"] == "tilt":
            print("Tilting...")
        elif data["type"] == "dance 1":
            print("Performing Dance 1...")
        elif data["type"] == "dance 2":
            print("Performing Dance 2...")
        elif data["type"] == "forward":
            print("Moving forward...")
        elif data["type"] == "backward":
            print("Moving backward...")
        elif data["type"] == "left":
            print("Turning left...")
        elif data["type"] == "right":
            print("Turning right...")
        elif data["type"] == "stop":
            print("Stopping...")
        else:
            print("Unknown command received.")

        await send_robot_command()

# Function to send robot command
async def send_robot_command():
    print("Sending the command to the robot")

# WebSocket event handlers
async def on_open(websocket):
    print("Connected to the WebSocket server")
    await websocket.send(json.dumps({"type": "getConnectedClients"}))

async def on_close(websocket, path):
    print("Connection closed")

async def on_error(websocket, error):
    print("Error occurred:", error)

async def websocket_handler(uri, robot_name):
    try:
        async with websockets.connect(uri) as websocket:
            await on_open(websocket)

            while True:
                try:
                    message = await websocket.recv()
                    await handle_message(websocket, message)
                except websockets.ConnectionClosed as e:
                    await on_close(websocket, None)
                    break
    except (websockets.WebSocketException) as e:
        print(f"Error during WebSocket communication: {e}")

async def main():
    if len(sys.argv) != 2:
        print("Error: Name not specified")
        sys.exit(1)

    name = sys.argv[1]
    uri = f"wss://rob-sync-production.up.railway.app/ws/{name}"
    await websocket_handler(uri, name)

if __name__ == "__main__":
    asyncio.run(main())
