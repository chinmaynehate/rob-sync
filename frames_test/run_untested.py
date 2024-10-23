# untested implementation of drill logic

import sys
import asyncio
from config3 import frames, frame_info, frame_transition_time
import websockets
import json
import time
import math

sys.path.append('../lib/python/arm64')
import robot_interface as sdk

udp_robot = sdk.UDP(0xee, 8080, "192.168.123.161", 8082)
state_robot = sdk.HighState()
cmd = sdk.HighCmd()
udp_robot.InitCmdData(cmd)

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
        await do_drill()
    else:
        print("Unknown command received.")

    await send_robot_command()

async def move_for_duration(seconds):
    start_time = time.time()
    while time.time() - start_time < seconds:
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.05)

# Command-line argument for the robot name
name = int(sys.argv[1])

# find x,y coord of robot in frame
# returns coordinate 1 indexed and in quadrant 1
def get_robot_position(frame, robot_number):
    for y, row in enumerate(frame):
        for x, value in enumerate(row):
            if value == robot_number:
                # translate (x, y) to quadrant 1
                translated_x = x
                translated_y = len(frame) - 1 - y
                return (translated_x + 1, translated_y + 1)
    return None

# might need to switch x and y of cmd.velocity
async def do_drill():
    for i in range(len(frames) - 1):
        pos = get_robot_position(frames[i], name)
        target = get_robot_position(frames[i + 1], name)

        if pos and target:
            x_change = target[0] - pos[0]  # Change in x
            y_change = target[1] - pos[1]  # Change in y

            # if not moving, wait
            if (x_change == 0 and y_change == 0):
                # print("cmd.velocity[0][0] for " + str(frame_transition_time[i]) + " seconds")
                cmd.velocity = [0, 0]
                await move_for_duration(frame_transition_time[i])
                await move_for_duration(frame_info[i][0])

                # simulate performance at frame
                cmd.mode = frame_info[i][1]
                continue

            # calculate speed given frame_transition_time
            v = ((x_change**2 + y_change**2) ** 0.5) / frame_transition_time[i] 

            # x and y speed components
            x_speed = v * (x_change / ((x_change**2 + y_change**2) ** 0.5))
            y_speed = v * (y_change / ((x_change**2 + y_change**2) ** 0.5))

            # do move
            cmd.velocity = [x_speed, y_speed]
            await move_for_duration(frame_transition_time[i])
            cmd.velocity = [0, 0]

            # wait before entering given mode
            await move_for_duration(frame_info[i][0])

            # enter mode
            cmd.mode = frame_info[i][1]

        else:
            print("Robot not found in frame or out of bounds")
            break


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