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

class PIDController:
    def __init__(self, Kp, Ki, Kd, setpoint, min_output, max_output):
        self.Kp = Kp  # Proportional gain
        self.Ki = Ki  # Integral gain
        self.Kd = Kd  # Derivative gain
        self.setpoint = setpoint  # Target yaw (desired yaw)
        self.min_output = min_output  # Minimum output (lower bound for yawSpeed)
        self.max_output = max_output  # Maximum output (upper bound for yawSpeed)
        
        self.previous_error = 0  # Previous error value for derivative calculation
        self.integral = 0  # Accumulated integral error
        
    def calculate(self, current_value):
        # Calculate error
        error = self.setpoint - current_value
        
        # Proportional term
        P = self.Kp * error
        
        # Integral term
        self.integral += error
        I = self.Ki * self.integral
        
        # Derivative term
        D = self.Kd * (error - self.previous_error)
        self.previous_error = error
        
        # PID output
        output = P + I + D
        
        # Clamp the output to the specified bounds (min_output, max_output)
        return max(self.min_output, min(self.max_output, output))

def get_current_yaw():
    udp_robot.Recv()  # Receive the latest data from the robot
    udp_robot.GetRecv(state_robot)  # Populate state_robot with the latest data
    return state_robot.imu.rpy[2]  # Return the yaw (rpy[2]) from the IMU


# Function to adjust the robot's yaw using a PID controller
async def adjust_yaw_with_pid(target_yaw=0.0, Kp=0.6, Ki=0.0, Kd=0.1):
    # Initialize the PID controller
    pid_controller = PIDController(Kp=Kp, Ki=Ki, Kd=Kd, setpoint=target_yaw, min_output=-1.0, max_output=1.0)
    
    # Continuously adjust yaw until error is within the acceptable range
    while True:
        # Get the current yaw (updated within the loop)
        current_yaw = get_current_yaw()
        
        # Calculate the yaw error
        yaw_error = target_yaw - current_yaw
        
        # Check if yaw error is small enough to stop
        if abs(yaw_error) <= 0.01:  # Threshold for yaw error (in radians)
            print(f"Yaw is within the target range: {current_yaw:.2f} radians. Stopping adjustment.")
            break
        
        # Calculate the PID output (desired yawSpeed) based on the current error
        yaw_speed = pid_controller.calculate(current_yaw)
        
        # Apply the calculated yawSpeed while keeping velocity [0, 0] (no forward/backward movement)
        cmd.mode = 2  # Ensure the robot is in walk mode
        cmd.velocity = [0, 0]  # No forward or sideways movement
        cmd.yawSpeed = yaw_speed  # Apply the yawSpeed calculated by the PID controller
        
        # Send the command to the robot
        await send_robot_command()
        
        # Sleep briefly to allow the robot to adjust its yaw
        await asyncio.sleep(0.05)  # Adjust this sleep time if needed for better control

    # Once the yaw is adjusted, stop the yaw movement by setting yawSpeed to 0
    cmd.yawSpeed = 0
    await send_robot_command()

    
    
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
        cmd.velocity = [0.24, 0.166]
        cmd.footRaiseHeight = 0.1
        await move_for_duration(3.7)

# async def perform_triangle_formation():
#     # Get the current Unix time in milliseconds and add 10 seconds (10000 ms)
#     print("Yaw is : ",get_current_yaw())
#     start_time = int((time.time() * 1000))
#     target_time = start_time + 15000
    
#     # Start the triangle formation
#     await create_triangle(2, 1, 0.5, 0.15, "kjhk")
    
#     # Sleep to allow inertia of movement to stop
#     await asyncio.sleep(3)
    
#     # Continuously check if the current time has reached the target time
#     while int((time.time() * 1000)) < target_time:
#         await asyncio.sleep(0.1)  # Wait for a short time before checking again
        
#     # Once the target time is reached, execute the "dance 1" command
#     await process_command("dance 1")
#     print("Yaw is ",get_current_yaw())

async def perform_triangle_formation():
    print("Yaw before formation: ", get_current_yaw())
    
    start_time = int((time.time() * 1000))
    target_time = start_time + 15000
    
    # Start the triangle formation
    await create_triangle(2, 1, 0.5, 0.15, "kjhk")
    
    # Sleep to allow inertia of movement to stop
    await asyncio.sleep(3)
    
    # Continuously check if the current time has reached the target time
    while int((time.time() * 1000)) < target_time:
        await asyncio.sleep(0.1)  # Wait for a short time before checking again
        
    # Once the target time is reached, execute the "dance 1" command
    await process_command("dance 1")
    
    # Print the yaw after the dance
    print("Yaw after dance: ", get_current_yaw())
    
    # Adjust the yaw to correct back to the initial value (0.0 in this case)
    await adjust_yaw_with_pid(target_yaw=0.0)

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
