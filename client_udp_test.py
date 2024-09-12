import asyncio
import websockets
import json
import sys
import time

sys.path.append('../lib/python/arm64')
import robot_interface as sdk

udp_robot = sdk.UDP(0xee, 8080, "192.168.123.161", 8082)
state_robot = sdk.HighState()
cmd = sdk.HighCmd()
udp_robot.InitCmdData(cmd)

# Function to process commands
async def process_command(command):
    print(f"Processing command: {command}")
    if command == "tilt":
        print("Tilting...")
        cmd.mode = 1
        cmd.euler = [0, 0, -0.3]
    elif command == "dance 1":
        print("Performing Dance 1...")
        cmd.mode = 12
        cmd.gaitType = 1
        cmd.velocity = [0.0, 0]
    elif command == "dance 2":
        print("Performing Dance 2...")
        cmd.mode = 13
        cmd.gaitType = 1
        cmd.velocity = [0.0, 0]
    elif command == "forward":
        print("Moving forward...")
        cmd.mode = 2
        cmd.gaitType = 1
        cmd.velocity = [0.3, 0]
        cmd.footRaiseHeight = 0.1
    elif command == "backward":
        print("Moving backward...")
        cmd.mode = 2
        cmd.gaitType = 1
        cmd.velocity = [-0.3, 0]
        cmd.footRaiseHeight = 0.1
    elif command == "left":
        print("Turning left...")
        cmd.mode = 2
        cmd.gaitType = 1
        cmd.velocity = [0, 0.3]
        cmd.footRaiseHeight = 0.1
    elif command == "right":
        print("Turning right...")
        cmd.mode = 2
        cmd.gaitType = 1
        cmd.velocity = [0, -0.3]
        cmd.footRaiseHeight = 0.1
    elif command == "stop":
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
    elif command == "triangle":
        await perform_triangle_formation()
    else:
        print("Unknown command received.")

    await send_robot_command()

# robot: id of robot (last 3)
# speed: an arbitrary speed multipler
# x: y length of triangle
# y: x length of triangle
# d: distance for 514 (middle robot) to move forwards
async def create_triangle(x, y, d, speed, robot):
    if robot == "605":
        x1 = 2*x*speed
        y1 = y*speed
        cmd.mode = 2
        cmd.gaitType = 1
        cmd.velocity = [x1, y1]
        cmd.footRaiseHeight = 0.1
        time = (math.sqrt(4*x**2 + y**2))/(math.sqrt(x1**2 + y1**2))
        await move_for_duration(time)
    elif robot == "699":
        x2 = x*speed
        y2 = y*speed
        cmd.mode = 2
        cmd.gaitType = 1
        cmd.velocity = [x2, -y2]
        cmd.footRaiseHeight = 0.1
        time = (math.sqrt(x**2 + y**2))/(math.sqrt(x2**2 + y2**2))
        await move_for_duration(time)
    elif robot == "514":
        cmd.mode = 2
        cmd.gaitType = 1
        cmd.velocity = [d*speed, 0]
        cmd.footRaiseHeight = 0.1
        await move_for_duration(d/speed)

# Function to perform the triangle formation
async def perform_triangle_formation():
    await create_triangle(2, 1, 0.5, 0.3, "514")
    await create_triangle(2, 1, 0.5, 0.3, "605")
    await create_triangle(2, 1, 0.5, 0.3, "699")
    # if name == "514": 
    #     # Move forward for 3 seconds
    #     cmd.mode = 2
    #     cmd.gaitType = 1
    #     cmd.velocity = [0.3, 0] # Move forward
    #     cmd.footRaiseHeight = 0.1
    #     await move_for_duration(3)
    #     cmd.velocity = [0.0, 0]
    #     # Wait for 2 seconds to synchronize with other robots
    #     await move_for_duration(2)
        
    # elif name == "605": 
    #     # Move forward for 3 seconds
    #     cmd.mode = 2
    #     cmd.gaitType = 1
    #     cmd.velocity = [0.3, 0] # Move forward
    #     cmd.footRaiseHeight = 0.1
    #     await move_for_duration(3)
    #     # Move diagonally to the left
    #     cmd.velocity = [0.3, 0.3] # Move diagonally left
    #     await move_for_duration(2)
        
    # elif name == "699":
    #     # Move forward for 3 seconds
    #     cmd.mode = 2
    #     cmd.gaitType = 1
    #     cmd.velocity = [0.3, 0] # Move forward
    #     cmd.footRaiseHeight = 0.1
    #     await move_for_duration(3)
        
    #     # Move diagonally to the right
    #     cmd.velocity = [0.3, -0.3] # Move diagonally right
    #     await move_for_duration(2)
    
    # Perform two dances (All robots start at the same time)
    for dance_command in ["dance 1", "dance 2"]:
        await process_command(dance_command)
        await asyncio.sleep(3)  # Allow each dance to perform for 3 seconds
    
    # Stop all robots
    await process_command("stop")


# Function to move for a specific duration
async def move_for_duration(seconds):
    start_time = time.time()
    while time.time() - start_time < seconds:
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.05)

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
    udp_robot.SetSend(cmd)
    udp_robot.Send()

# WebSocket event handlers
async def on_open(websocket):
    print("Connected to the WebSocket server")
    await websocket.send(json.dumps({"type": "getConnectedClients"}))

async def on_close(websocket, path):
    print("Connection closed")

async def on_error(websocket, error):
    print("Error occurred:", error)

async def websocket_handler(uri):
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
        print("Usage: client_udp_test.py <client_id>")
        sys.exit(1)

    global name
    name = sys.argv[1]
    uri = f"wss://rob-sync-production.up.railway.app/ws/{name}"
    await websocket_handler(uri)

if __name__ == "__main__":
    asyncio.run(main())
