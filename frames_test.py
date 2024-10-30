#tested implementation of drill logic

import sys
import asyncio
import websockets
import json
import time
import math

frame0 = [[0, 0, 0],  
          [1, 2, 3],  
          [0, 0, 0]]  

frame1 = [[0, 0, 0],
          [0, 2, 0],
          [1, 0, 3]]

frame2 = [[0, 0, 0],
          [1, 0, 3],
          [0, 2, 0]]

frame3 = [[0, 0, 0],  
          [0, 0, 0],  
          [1, 2, 3]] 

frames = [frame0, frame1, frame2, frame3]

# time spent at frame before entering given mode
# [time, mode]
frame_info = [[3, 12], [3, 12], [3, 12], [3, 12]]

# transition time to next frame
frame_transition_time = [3, 3, 3]

sys.path.append('../lib/python/arm64')
import robot_interface as sdk

udp_robot = sdk.UDP(0xee, 8080, "192.168.123.161", 8082)
state_robot = sdk.HighState()
cmd = sdk.HighCmd()
udp_robot.InitCmdData(cmd)
def get_current_yaw():
    udp_robot.Recv()  # Receive the latest data from the robot
    udp_robot.GetRecv(state_robot)  # Populate state_robot with the latest data
    return state_robot.imu.rpy[2]  # Return the yaw (rpy[2]) from the IMU
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

async def set_robot_mode(mode):
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
    for i in range(len(frames) - 1):
        await set_robot_mode(2)
        time.sleep(0.05)
        set_point = get_current_yaw()
# this needs to be called once robot is to it's position
        print(set_point)
        print(i)
        print(name)
        print(frames[i], frames[i+1])
        pos = get_robot_position(frames[i], name)
        target = get_robot_position(frames[i + 1], name)
        print(pos, target)
        if pos and target:
            x_change = target[0] - pos[0]  # Change in x
            y_change = target[1] - pos[1]  # Change in y
            print(y_change, x_change)
            # if not moving, wait
            if (x_change == 0 and y_change == 0):
                # print("cmd.velocity[0][0] for " + str(frame_transition_time[i]) + " seconds")
                cmd.mode = 2
                cmd.velocity = [0, 0]
                while int(time.time() - startTime) < time.time() + frame_transition_time[i]*1000 + frame_info[i][0]*1000:
                    udp_robot.SetSend(cmd)
                    udp_robot.Send()
                    await asyncio.sleep(0.05)
                # await move_for_duration(frame_transition_time[i])
                # await move_for_duration(frame_info[i][0])

                # simulate performance at frame
                print(int(frame_info[i][1]))
                await set_robot_mode(2)
                time.sleep(0.05)
              #  set_point = get_current_yaw()
                cmd.mode =int(frame_info[i][1])

                if (frame_info[i][1] == 13):
                    print("waiting 45")
                    while int(time.time() - startTime) < time.time() + 45*1000:
                        udp_robot.SetSend(cmd)
                        udp_robot.Send()
                        await asyncio.sleep(0.05)
                    # await asyncio.sleep(0.05)
                    await set_robot_mode(2)

                    await apply_pid_controller(set_point, K_p=2.0, K_i=0.02, K_d=0.05, threshold=0.05)
                    while int(time.time() - startTime) < time.time() + 5*1000:
                        udp_robot.SetSend(cmd)
                        udp_robot.Send()
                        await asyncio.sleep(0.05)
                    # call rotate 90 clockwise
                else:
                    print("waiting 20")
                    while int(time.time() - startTime) < time.time() + 19*1000:
                        udp_robot.SetSend(cmd)
                        udp_robot.Send()
                        await asyncio.sleep(0.05)
                    await set_robot_mode(2)
                    await apply_pid_controller(set_point, K_p=2.0, K_i=0.02, K_d=0.05, threshold=0.05)
                    while int(time.time() - startTime) < time.time() + 5*1000:
                        udp_robot.SetSend(cmd)
                        udp_robot.Send()
                        await asyncio.sleep(0.05)
                continue

            # calculate speed given frame_transition_time
            v = ((x_change**2 + y_change**2) ** 0.5) / frame_transition_time[i]

            # x and y speed components
            x_speed = v * (x_change / ((x_change**2 + y_change**2) ** 0.5))
            y_speed = v * (y_change / ((x_change**2 + y_change**2) ** 0.5))
            print(x_speed, y_speed)
            # do move
            cmd.mode = 2
            cmd.velocity = [y_speed, x_speed]
            print(cmd.mode, "should  be moving")
            await move_for_duration(frame_transition_time[i])
            cmd.velocity = [0, 0]

            print("entering before dance pause")
            curr = time.time() - startTime
                # await move_for_duration(20)
            while int(time.time() - startTime) < frame_info[i][0]+curr:
                print(time.time() - startTime,  frame_info[i][0]+curr)
                await asyncio.sleep(0.05)
            print("exiting after dance pause")

            # wait before entering given mode
            # await move_for_duration(frame_info[i][0])

            # enter mode
            print(int(frame_info[i][1]))
            await set_robot_mode(2)
            time.sleep(0.05)
           # set_point = get_current_yaw()
            cmd.mode = int(frame_info[i][1])
            if (frame_info[i][1] == 13):
                print("waiting 45")
                while int(time.time() - startTime) < time.time() + 45*1000:
                    udp_robot.SetSend(cmd)
                    udp_robot.Send()
                    await asyncio.sleep(0.05)
                await set_robot_mode(2)
                await apply_pid_controller(set_point, K_p=2.0, K_i=0.02, K_d=0.05, threshold=0.05)
                while int(time.time() - startTime) < time.time() + 5*1000:
                    udp_robot.SetSend(cmd)
                    udp_robot.Send()
                    await asyncio.sleep(0.05)
                # call rotate 90 clockwise
            else:
                print("waiting 20")
                curr = time.time() - startTime
                # await move_for_duration(20)
                print("entering dance pause")
                while int(time.time() - startTime) < 19+curr:
                    print(time.time() - startTime,  19+curr)
                    await asyncio.sleep(0.05)
                print("exiting dance pause")
                await set_robot_mode(2)
                await apply_pid_controller(set_point, K_p=2.0, K_i=0.02, K_d=0.05, threshold=0.05)
                print("waiting for after rotate move to sync")
                curr = time.time() - startTime
                while int(time.time() - startTime) < curr + 3:
                    print(time.time() - startTime,  3+curr)
                    await asyncio.sleep(0.05)
                print("exiting after rotate move to sync")
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
    if len(sys.argv) != 3:
        print("Usage: python client.py <robot_id> <server_ip>")
        print("Example: python client.py 605 192.168.1.100")
        sys.exit(1)

    global name
    name = sys.argv[1]
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