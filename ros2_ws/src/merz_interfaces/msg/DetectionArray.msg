# All detections in one image. header.stamp and header.frame_id are copied from that image, so depth
# and TF can be looked up at the moment the image was taken, not when the detector finished.
std_msgs/Header header
Detection[] detections
