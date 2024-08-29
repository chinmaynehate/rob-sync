import asyncio
import websockets
import json
import sys

sys.path.append('../lib/python/arm64')
import robot_interface as sdk

udp_robot = sdk.UDP(0xee, 8080, "192.168.123.161", 8082)
state_robot = sdk.HighState()
cmd = sdk.HighCmd()
udp_robot.InitCmdData(cmd)


# Function to handle received messages
async def handle_message(websocket, message):
    print("Received message:", message)
    
    try:
        cmd.mode = 0 
        cmd.gaitType = 0
        cmd.speedLevel = 0
        cmd.footRaiseHeight = 0
        cmd.bodyHeight = 0
        cmd.euler = [0, 0, 0]
        cmd.velocity = [0, 0]
        cmd.yawSpeed = 0.0
        cmd.reserve = 0
        data = json.loads(message)
    except json.JSONDecodeError:
        # If the message is not JSON, just print it and return
        print(f"Non-JSON message received: {message}")
        return

    if "type" in data:
        print(f"Type: {data['type']}")

        if data["type"] == "tilt":
            print("Tilting...")
            cmd.mode = 1
            cmd.euler = [0, 0, -0.3]
        elif data["type"] == "dance 1":
            print("Performing Dance 1...")
            cmd.mode = 12
            cmd.gaitType = 1
            cmd.velocity = [0.0, 0]
        elif data["type"] == "dance 2":
            print("Performing Dance 2...")
            cmd.mode = 13
            cmd.gaitType = 1
            cmd.velocity = [0.0, 0]
        elif data["type"] == "forward":
            print("Moving forward...")
            cmd.mode = 2
            cmd.gaitType = 1
            cmd.velocity = [0.3, 0]
            cmd.footRaiseHeight = 0.1
                
        elif data["type"] == "backward":
            print("Moving backward...")
            cmd.mode = 2
            cmd.gaitType = 1
            cmd.velocity = [-0.3, 0]
            cmd.footRaiseHeight = 0.1
        elif data["type"] == "left":
            print("Turning left...")
            cmd.mode = 2
            cmd.gaitType = 1
            cmd.velocity = [0, 0.3]
            cmd.footRaiseHeight = 0.1
        elif data["type"] == "right":
            print("Turning right...")
            cmd.mode = 2
            cmd.gaitType = 1
            cmd.velocity = [0, -0.3]
            cmd.footRaiseHeight = 0.1
        elif data["type"] == "stop":
            print("Stopping...")
            cmd.mode = 0 
            cmd.gaitType = 0
            cmd.speedLevel = 0
            cmd.footRaiseHeight = 0
            cmd.bodyHeight = 0
            cmd.euler = [0, 0, 0]
            cmd.velocity = [0, 0]
            cmd.yawSpeed = 0.0
            cmd.reserve = 0
        elif data["type"] == "form1":
            if name == "514": 
            cmd.mode = 2
            cmd.gaitType = 1
            cmd.velocity = [-0.3, 0] # backwards
            cmd.footRaiseHeight = 0.1
            elif name == "605": # middle robot
                cmd.mode = 2
                cmd.gaitType = 1
                cmd.velocity = [0.3, 0] # forwards
                cmd.footRaiseHeight = 0.1
            elif name == "699":
                cmd.mode = 2
                cmd.gaitType = 1
                cmd.velocity = [-0.3, 0] # backwards
                cmd.footRaiseHeight = 0.1

            # for 2 seconds
            start_time = time.time()
            while time.time() - start_time < 2:
                udp_robot.SetSend(cmd)
                udp_robot.Send()
                time.sleep(0.05)

            # stop formation
            cmd.mode = 0 
            cmd.gaitType = 0
            cmd.speedLevel = 0
            cmd.footRaiseHeight = 0
            cmd.bodyHeight = 0
            cmd.euler = [0, 0, 0]
            cmd.velocity = [0, 0]
            cmd.yawSpeed = 0.0
            cmd.reserve = 0
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
