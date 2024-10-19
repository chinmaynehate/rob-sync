# this only on yaw and not integrated with the triangle and dance.
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

# PID controller function
def apply_pid_controller(set_point, K_p=1.0, K_i=0.01, K_d=0.05, threshold=0.01):
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

# Main function to initiate the PID controller
def main():
    try:
        while True:
            # Continuous communication to ensure robot stays active
            udp_robot.Recv()
            udp_robot.SetSend(cmd)
            udp_robot.Send()

            # Set the robot to walking mode (mode = 2)
            set_robot_mode(2)
            print("Robot set to walking mode (mode 2).")
            time.sleep(0.05)
            # Capture the initial yaw as the set point
            set_point = get_current_yaw()
            print(f"Initial Yaw (Set Point): {set_point:.5f} radians")

            # Simulate a delay or action (like rotating the robot)
            print("Simulating a movement...")
            time.sleep(10)  # Adjust the time if needed to simulate movement

            # Apply the PID controller to bring the robot back to the initial yaw
            apply_pid_controller(set_point, K_p=2.0, K_i=0.02, K_d=0.05, threshold=0.01)

            # Optionally, break the loop if you want to stop after one cycle
            break

    except KeyboardInterrupt:
        print("PID control stopped by user.")

if __name__ == "__main__":
    main()

