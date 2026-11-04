# One object found in one camera image. Pixel coordinates; (0, 0) is the top-left of the image.
string label          # door, lift, stairs, exit_sign, room_sign
float32 confidence    # detector score, 0 to 1
float32 x_min         # pixels
float32 y_min         # pixels
float32 x_max         # pixels
float32 y_max         # pixels
