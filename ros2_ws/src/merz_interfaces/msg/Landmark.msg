# A landmark in the semantic map.
int64 id
string landmark_class                     # "class" is a Python keyword, so it cannot be the field name
string text                               # room number for room signs, otherwise empty
geometry_msgs/Point position              # metres, in header frame of the LandmarkArray (normally map)
float64[9] covariance                     # position covariance, m^2, row-major x y z
float32 confidence                        # highest detector score seen, 0 to 1
uint32 observation_count
string photo_path                         # empty if no photo was saved
builtin_interfaces/Time first_seen
builtin_interfaces/Time last_seen
