# A room sign read by OCR from the sign camera. The header is copied from the source image.
# The sign's position is NOT here: position comes from the D455, as the C920 autofocus alters its intrinsics.
std_msgs/Header header
string text           # normalised and validated room code, e.g. "C528"
string raw_text       # exactly what the OCR returned, kept for evaluating O3
string name           # rest of the sign: occupant or room use, e.g. "Dr Eni Oko", "Cleaners"; may be empty
float32 confidence    # OCR score, 0 to 1
Detection detection   # the room_sign bounding box in the sign camera image
