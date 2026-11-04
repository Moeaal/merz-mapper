# merz_description

**Status: IMPLEMENTED - not yet built or tested on hardware.** The sensor poses are placeholders.

The rover's URDF. All numbers are in `config/sensor_poses.yaml`, so measuring the rover needs no XML edits.

## TF tree
```
base_link -> laser
          -> camera_link -> (published by the RealSense driver: optical and IMU frames)
          -> sign_camera -> sign_camera_optical_frame
```
`base_link` lies on the floor at the centre of rotation, so each `z` is a height above the floor.
`odom->base_link` belongs to the EKF and `map->odom` to SLAM Toolbox.

## Check it (on the Jetson or Pi)
```bash
xacro $(ros2 pkg prefix merz_description)/share/merz_description/urdf/merz_rover.urdf.xacro > /tmp/merz.urdf
check_urdf /tmp/merz.urdf
ros2 launch merz_description description.launch.py rviz:=true include_d455_internal_frames:=true
ros2 run tf2_tools view_frames
```

## Unit tests that pass on Windows
`test/test_urdf.py` expands the xacro with the PyPI `xacro` package and checks the frames, the tree shape
and that each pose comes from the YAML. On the Jetson, `check_urdf` must still be run as above.
