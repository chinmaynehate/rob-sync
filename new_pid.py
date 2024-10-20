# integration of yaw pid with triangle and dance.
import asyncio
import websockets
import json
import sys
import time
import math

sys.path.append('../lib/python/arm64')
import robot_interface as sdk

udp_robot = sdk.UDP(0xee, 8080, "192.168.123.161", 8082)
state_robot = sdk.HighState()
cmd = sdk.HighCmd()
udp_robot.InitCmdData(cmd)

async def set_robot_mode(mode):
    cmd.mode = mode  # Set the mode (1 for standing, 2 for walking, etc.)
    cmd.velocity = [0, 0]  # No movement
    cmd.yawSpeed = 0.0  # No rotation
    udp_robot.SetSend(cmd)
    udp_robot.Send()

def get_current_yaw():
    udp_robot.Recv()  # Receive the latest data from the robot
    udp_robot.GetRecv(state_robot)  # Populate state_robot with the latest data
    return state_robot.imu.rpy[2]  # Return the yaw (rpy[2]) from the IMU

# PID controller function
async def apply_pid_controller(set_point, K_p=1.0, K_i=0.01, K_d=0.05, threshold=0.01):
    integral = 0.0  # Initialize the integral term
    previous_error = 0.0  # Initialize the previous error for the derivative term
    previous_time = time.time()
    
    while True:
        current_time = time.time()
        dt = current_time - previous_time
        previous_time = current_time

        # Continuous communication and data fetch
        udp_robot.Recv()
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        time.sleep(0.05)
        # Get the current yaw and calculate error
        current_yaw = get_current_yaw()
        error = set_point - current_yaw
        print("error",error)
        # Stop the loop if the error is within an acceptable range
        if abs(error) < threshold:
            print(f"Aligned to setpoint within threshold: {threshold}")
            break

        # Proportional term
        P_term = K_p * error

        # Integral term accumulation
        integral += error * dt
        I_term = K_i * integral

        # Derivative term (rate of change of error)
        derivative = (error - previous_error) / dt if dt > 0 else 0.0
        D_term = K_d * derivative
        previous_error = error

        # Apply the PID controller logic
        yawSpeed = P_term + I_term + D_term

        # Limit yawSpeed to avoid extreme values
        yawSpeed = max(min(yawSpeed,2.0), -2.0)  # Clamp between -1 and 1
        
        # Set yaw speed and keep velocity zero (no forward/backward movement)
        cmd.yawSpeed = yawSpeed
        cmd.velocity = [0, 0]

        # Send command to robot
        udp_robot.SetSend(cmd)
        udp_robot.Send()

        print(f"Current Yaw: {current_yaw:.5f} | Error: {error:.5f} | Yaw Speed: {yawSpeed:.5f} | Integral: {integral:.5f} | Derivative: {derivative:.5f}")

        time.sleep(0.1)  # Sleep for a short time before checking again

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
async def create_triangle(x, y, d, speed, robot, dir):
    if dir == "forward":
        if name == "605":
            # dont move
            cmd.mode = 2
            cmd.velocity = [0, 0]
            await move_for_duration(3.7)
        elif name == "699":
            cmd.mode = 2
            cmd.gaitType = 1
            cmd.velocity = [0.134, -0.268]
            cmd.footRaiseHeight = 0.1
            await move_for_duration(3.7)

        elif name == "814":
            cmd.mode = 2
            cmd.gaitType = 1
            # cmd.velocity = [0.24, 0.166]
            cmd.velocity = [0.399, 0.265]
            cmd.footRaiseHeight = 0.1
            await move_for_duration(3.7)
    else:
        if name == "605":
            # dont move
            cmd.mode = 2
            cmd.velocity = [0, 0]
            await move_for_duration(3.7)
        elif name == "699":
            cmd.mode = 2
            cmd.gaitType = 1
            cmd.velocity = [-0.134, 0.268]
            cmd.footRaiseHeight = 0.1
            await move_for_duration(3.7)

        elif name == "814":
            cmd.mode = 2
            cmd.gaitType = 1
            # cmd.velocity = [0.24, 0.166]
            cmd.velocity = [-0.399, -0.265]
            cmd.footRaiseHeight = 0.1
            await move_for_duration(3.7)
        

async def perform_triangle_formation():
    # Get the current Unix time in milliseconds and add 10 seconds (10000 ms)
    
    
    udp_robot.Recv()
    udp_robot.SetSend(cmd)
    udp_robot.Send()
    await set_robot_mode(2)
    time.sleep(0.05)
    set_point = get_current_yaw()
    print("set point", set_point)
    
    
    start_time = int((time.time() * 1000))
    target_time = start_time + 8000

    yaw_adjust_time = target_time + 18000
    
    # Start the triangle formation
    await create_triangle(2, 1, 0.5, 0.15, "kjhk", "forward")
    
    # Sleep to allow inertia of movement to stop
    await asyncio.sleep(3)
    
    # Continuously check if the current time has reached the target time
    while int((time.time() * 1000)) < target_time:
        await asyncio.sleep(0.1)  # Wait for a short time before checking again
        
    # Once the target time is reached, execute the "dance 1" command
    #await set_robot_mode(12)
    await process_command("dance 1")

    while int((time.time()*1000)) < yaw_adjust_time:
        await asyncio.sleep(0.1)

    
    await set_robot_mode(2)
    await apply_pid_controller(set_point, K_p=2.0, K_i=0.02, K_d=0.05, threshold=0.01)
    
    await create_triangle(2, 1, 0.5, 0.15, "kjhk", "backward")
    await apply_pid_controller(set_point, K_p=2.0,K_i=0.02, K_d=0.05, threshold = 0.01)

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


