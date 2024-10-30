# config file is the same for all robots
# starting position of robot (where you placed them)
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
frame_info = [[1, 12], [1, 12], [1, 12], [1, 12]]

# transition time to next frame
frame_transition_time = [3, 3, 3]
