import asyncio
import websockets
import json
import sys

# Function to process commands
async def process_command(command):
    print(f"Processing command: {command}")
    if command == "tilt":
        print("Tilting...")
    elif command == "dance 1":
        print("Performing Dance 1...")
    elif command == "dance 2":
        print("Performing Dance 2...")
    elif command == "forward":
        print("Moving forward...")
    elif command == "backward":
        print("Moving backward...")
    elif command == "left":
        print("Turning left...")
    elif command == "right":
        print("Turning right...")
    elif command == "stop":
        print("Stopping...")
    elif command == "triangle":
        print("Triangle...")
    else:
        print("Unknown command received.")
    await send_robot_command()

# Function to handle received messages
async def handle_message(websocket, message):
    print("Received message:", message)
    
    try:
        data = json.loads(message)
        if "type" in data:
            if data["type"] == "command":
                await process_command(data["command"])
            else:
                print("Unknown type of message received.")
    except json.JSONDecodeError:
        print(f"Non-JSON message received: {message}")

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
