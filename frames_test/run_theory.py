# simulation of drill movements

import sys
import time
import asyncio
from config3 import frames, frame_info, frame_transition_time

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

            currTime = time.time()

            # if not moving, wait
            if (x_change == 0 and y_change == 0):
                print("cmd.velocity[0][0] until " + str(currTime + frame_transition_time[i] * 1000))
                await move_for_duration(frame_transition_time[i])
                continue

            # calculate speed given frame_transition_time
            v = ((x_change**2 + y_change**2) ** 0.5) / frame_transition_time[i] 

            # x and y speed components
            x_speed = v * (x_change / ((x_change**2 + y_change**2) ** 0.5))
            y_speed = v * (y_change / ((x_change**2 + y_change**2) ** 0.5))

            # simulate move
            print("cmd.velocity[" + str(x_speed) + "][" + str(y_speed) + "] until " + str(currTime + frame_transition_time[i] * 1000))
            await move_for_duration(frame_transition_time[i])

            # simulate wait based on frame_info
            print("waiting until " + str(currTime + frame_info[i][0] * 1000) + " at cmd.velocity[0][0]")
            await move_for_duration(frame_info[i][0])

            # simulate performance at frame
            print("performing mode " + str(frame_info[i][1]))
            print("waiting for mode " + str(frame_info[i][1]) + " to be done")
            await move_for_duration(10) # rough time dance takes
        else:
            print("Robot not found in frame or out of bounds")
            break

# Function to simulate movement for a certain time
async def move_for_duration(duration):
    await asyncio.sleep(duration)

asyncio.run(do_drill())