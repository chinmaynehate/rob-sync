import time
import sys

# Ensure the SDK path is correct for your system
sys.path.append('../lib/python/arm64')
import robot_interface as sdk

# Initialize the UDP connection to the robot
udp_robot = sdk.UDP(0xee, 8080, "192.168.123.161", 8082)  # Replace with your robot's IP if different
state_robot = sdk.HighState()  # Create a HighState object to store the robot's state
cmd = sdk.HighCmd()  # Command object to send commands to the robot
udp_robot.InitCmdData(cmd)  # Initialize the command data

# Function to set the robot's mode
def set_robot_mode(mode):
    cmd.mode = mode  # Set the mode (1 for standing, 2 for walking, etc.)
    cmd.velocity = [0, 0]  # No movement
    cmd.yawSpeed = 0.0  # No rotation
    udp_robot.SetSend(cmd)
    udp_robot.Send()

# Function to get the current yaw of the robot
def get_current_yaw():
    udp_robot.Recv()  # Receive the latest data from the robot
    udp_robot.GetRecv(state_robot)  # Populate the state_robot object with the latest data
    return state_robot.imu.rpy[2]  # Return the yaw (rpy[2]) from the IMU

# Main loop to continuously set mode, read yaw values, and track min/max yaw
def main():
    try:
        # Set the robot to walking mode (mode = 2)
        set_robot_mode(2)
        print("Robot set to walking mode (mode 2).")

        min_yaw = float('inf')  # Set initial min yaw to a very high value
        max_yaw = float('-inf')  # Set initial max yaw to a very low value

        while True:
            udp_robot.Recv()  # Receive the latest data from the robot
            udp_robot.SetSend(cmd)  # Send the latest command to the robot to keep communication alive
            udp_robot.Send()  # Ensure continuous sending of commands to keep the robot in the right state

            # Get the current yaw value
            current_yaw = get_current_yaw()

            # Update min and max yaw values
            min_yaw = min(min_yaw, current_yaw)
            max_yaw = max(max_yaw, current_yaw)

            # Print the current yaw, min yaw, and max yaw
            print(f"Current Yaw: {current_yaw:.5f} radians")
            print(f"Min Yaw: {min_yaw:.5f} radians")
            print(f"Max Yaw: {max_yaw:.5f} radians")

            time.sleep(0.1)  # Sleep for 100ms before printing the next value (adjust as needed)
    except KeyboardInterrupt:
        print("Yaw reading stopped by user.")
        print(f"Final Min Yaw: {min_yaw:.5f} radians")
        print(f"Final Max Yaw: {max_yaw:.5f} radians")

if __name__ == "__main__":
    main()

