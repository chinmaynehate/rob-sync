import sys
import asyncio
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

def init_robots():
    cmd.mode = 0
    cmd.gaitType = 0
    cmd.speedLevel = 0
    cmd.footRaiseHeight = 0
    cmd.bodyHeight = 0
    cmd.euler = [0, 0, 0]
    cmd.velocity = [0, 0]
    cmd.yawSpeed = 0.0
    cmd.reserve = 0
    udp_robot.SetSend(cmd)
    udp_robot.Send()


def init_receiver():
    udp_robot.Recv()
    udp_robot.SetSend(cmd)
    udp_robot.Send()

def get_current_yaw():
    init_robots()
    init_receiver()
    set_robot_mode(2)
    time.sleep(0.05)
    udp_robot.Recv()  # Receive the latest data from the robot
    udp_robot.GetRecv(state_robot)  # Populate state_robot with the latest data
    return state_robot.imu.rpy[2]  # Return the yaw (rpy[2]) from the IMU

def angle_difference(target_angle, current_angle):
    diff = (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
    return diff

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
        error = angle_difference(set_point, current_yaw)
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
        yawSpeed = max(min(yawSpeed,2.5), -2.5)  # Clamp between -1 and 1

        # Set yaw speed and keep velocity zero (no forward/backward movement)
        cmd.yawSpeed = yawSpeed
        cmd.velocity = [0, 0]

        # Send command to robot
        udp_robot.SetSend(cmd)
        udp_robot.Send()

        print(f"Current Yaw: {current_yaw:.5f} | Error: {error:.5f} | Yaw Speed: {yawSpeed:.5f} | Integral: {integral:.5f} | Derivative: {derivative:.5f}")

        time.sleep(0.1)  # Sleep for a short time before checking again

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
        cmd.mode = 2
        cmd.gaitType = 1
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

def set_robot_mode(mode):
    cmd.mode = mode  # Set the mode (1 for standing, 2 for walking, etc.)
    cmd.velocity = [0, 0]  # No movement
    cmd.yawSpeed = 0.0  # No rotation
    udp_robot.SetSend(cmd)
    udp_robot.Send()

# Command-line argument for the robot name
name = int(sys.argv[1])

# find x,y coord of robot in frame
# returns coordinate 1 indexed and in quadrant 1
def get_robot_position(frame, robot_number):
    for y, row in enumerate(frame):
        for x, value in enumerate(row):
            if int(value) == int(robot_number):
                # translate (x, y) to quadrant 1
                translated_x = x
                translated_y = len(frame) - 1 - y
                return (translated_x + 1, translated_y + 1)
    return None

# might need to switch x and y of cmd.velocity
async def do_drill():
    startTime = time.time()
    set_point = get_current_yaw()
    print("hello from ", name)

    if name == "605" or name == "814":
        # go back
        cmd.mode = 2
        cmd.velocity = [-0.4, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        curr = time.time()  - startTime

        # move for x seconds
        while int(time.time() - startTime) < 1+curr:
            udp_robot.SetSend(cmd)
            udp_robot.Send()
            await asyncio.sleep(0.05)

        # stop and wait for inertia to stop
        init_robots()
        curr = time.time() - startTime
        while int(time.time() - startTime) < 0.9+curr:
            await asyncio.sleep(0.05)

        # begin dance & wait for it to commence
        cmd.mode = 12
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        curr = time.time() - startTime
        while int(time.time() - startTime) < 17.2+curr:
            await asyncio.sleep(0.05)

        init_robots()

        curr = time.time() - startTime

        # apply PID to ensure 180 degree turn
        await apply_pid_controller(set_point + math.pi, K_p=2.5, K_i=0.02, K_d=0.05, threshold=0.05)

        # allow time for rotate
        while int(time.time() - startTime) < 4+curr:
            await asyncio.sleep(0.05)

        init_robots()

         # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        init_robots()
        curr = time.time() - startTime

        # wait for robot to go to 0, 0, 0
        while int(time.time() - startTime) < 0.3+curr:
            await asyncio.sleep(0.05)

        #  # jump yaw twice
        # cmd.mode = 10
        # udp_robot.SetSend(cmd)
        # udp_robot.Send()
        # curr = time.time() - startTime

        # # wait before next jump yaw
        # while int(time.time() - startTime) < 2+curr:
        #     await asyncio.sleep(0.05)

        # init_robots()

        # cmd.mode = 10
        # udp_robot.SetSend(cmd)
        # udp_robot.Send()
        # curr = time.time() - startTime

        # init_robots()
        # curr = time.time() - startTime

        # # wait after jump yaw
        # while int(time.time() - startTime) < 1+curr:
        #     await asyncio.sleep(0.05)

        curr = time.time() - startTime

        # apply PID to ensure 180 degree turn
        await apply_pid_controller(set_point, K_p=2.5, K_i=0.02, K_d=0.05, threshold=0.05)

        # allow time for rotate
        while int(time.time() - startTime) < 4+curr:
            await asyncio.sleep(0.05)

        init_robots()

        # enter pray
        curr = time.time() - startTime
        cmd.mode = 11
        udp_robot.SetSend(cmd)
        udp_robot.Send()

        # wait for pray to finish
        curr = time.time() - startTime
        while int(time.time() - startTime) < 7+curr:
            await asyncio.sleep(0.05)

        # exit pray
        init_robots()
        curr = time.time() - startTime
        while int(time.time() - startTime) < 1+curr:
            await asyncio.sleep(0.05)

        print("do backflip")

        # # backflip
        # cmd.mode = 14
        # udp_robot.SetSend(cmd)
        # udp_robot.Send()

    elif name == "699":
        # go back
        init_robots()
        curr = time.time() - startTime

        # move for x seconds
        while int(time.time() - startTime) < 1+curr:
            udp_robot.SetSend(cmd)
            udp_robot.Send()
            await asyncio.sleep(0.05)

        # stop and wait for inertia to stop
        init_robots()
        curr = time.time() - startTime
        while int(time.time() - startTime) < 0.9+curr:
            await asyncio.sleep(0.05)

        # begin dance & wait for it to commence
        cmd.mode = 12
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        curr = time.time() - startTime
        while int(time.time() - startTime) < 17.2+curr:
            await asyncio.sleep(0.05)

        init_robots()

        curr = time.time() - startTime

        # apply PID to ensure 180 degree turn
        await apply_pid_controller(set_point + math.pi, K_p=2.5, K_i=0.02, K_d=0.05, threshold=0.05)

        # allow time for rotate
        while int(time.time() - startTime) < 4+curr:
            await asyncio.sleep(0.05)

        init_robots()

         # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch up
        cmd.mode = 2
        curr = time.time() - startTime
        cmd.euler = [0, 0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        # pitch down
        curr = time.time() - startTime
        cmd.euler = [0, -0.6, 0]
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        await asyncio.sleep(0.4)

        init_robots()
        curr = time.time() - startTime

        # wait for robot to go to 0, 0, 0
        while int(time.time() - startTime) < 0.3+curr:
            await asyncio.sleep(0.05)

        #  # jump yaw twice
        # cmd.mode = 10
        # udp_robot.SetSend(cmd)
        # udp_robot.Send()
        # curr = time.time() - startTime

        # # wait before next jump yaw
        # while int(time.time() - startTime) < 2+curr:
        #     await asyncio.sleep(0.05)

        # init_robots()

        # cmd.mode = 10
        # udp_robot.SetSend(cmd)
        # udp_robot.Send()
        # curr = time.time() - startTime

        # init_robots()
        # curr = time.time() - startTime

        # # wait after jump yaw
        # while int(time.time() - startTime) < 1+curr:
        #     await asyncio.sleep(0.05)

        curr = time.time() - startTime

        # apply PID to ensure 180 degree turn
        await apply_pid_controller(set_point, K_p=2.5, K_i=0.02, K_d=0.05, threshold=0.05)

        # allow time for rotate
        while int(time.time() - startTime) < 4+curr:
            await asyncio.sleep(0.05)

        init_robots()

        # enter pray
        curr = time.time() - startTime
        cmd.mode = 11
        udp_robot.SetSend(cmd)
        udp_robot.Send()

        # wait for pray to finish
        curr = time.time() - startTime
        while int(time.time() - startTime) < 7+curr:
            await asyncio.sleep(0.05)

        # exit pray
        init_robots()
        curr = time.time() - startTime
        while int(time.time() - startTime) < 1+curr:
            await asyncio.sleep(0.05)

        print("do backflip")

        # # backflip
        # cmd.mode = 14
        # udp_robot.SetSend(cmd)
        # udp_robot.Send()


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
    if len(sys.argv) != 3:
        print("Usage: python client.py <robot_id> <server_ip>")
        print("Example: python client.py 605 192.168.1.100")
        sys.exit(1)

    global name
    name =sys.argv[1]
    server_ip = sys.argv[2]
    uri = f"ws://{server_ip}:8000/ws/{name}"  # Changed from wss:// to ws:// and using local server
    print(f"Connecting to server at: {uri}")

    while True:
        try:
            await websocket_handler(uri)
        except Exception as e:
            print(f"Connection error: {e}")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nClient stopped by user")
        cmd.mode = 0  # Stop the robot when the client is stopped
        udp_robot.SetSend(cmd)
        udp_robot.Send()
        sys.exit(0)
