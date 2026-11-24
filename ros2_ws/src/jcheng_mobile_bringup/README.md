# jcheng_mobile_bringup

ROS 2 Humble bringup for the `jcheng-mobile` capability. It consumes `/scan`
and produces real laser odometry, a map and `/cmd_vel` chassis intent. It does
**not** start the M10 driver, the vendor mecanum node, or any fake odometry.

## Inputs / outputs

| Direction | Topic | Notes |
|---|---|---|
| in | `/scan` | `sensor_msgs/LaserScan`, frame `laser_link`, 10 Hz, from the system/hardware layer |
| out | `/odom` | RTAB-Map ICP laser odometry; TF `odom -> base_link` |
| out | `/map` | slam_toolbox online-async |
| out | `/tf` | `map -> odom -> base_link`, `base_link -> laser_link` |
| out | `/cmd_vel` | Nav2 MPPI Omni chassis intent ≤20 Hz; the system layer applies lease/deadman/e-stop |

## Build

```bash
colcon build --base-paths ros2_ws/src --packages-select jcheng_mobile_bringup
source install/setup.bash
```

Runtime dependencies: `nav2_bringup`, `nav2_mppi_controller`, `slam_toolbox`,
`rtabmap_odom`, `tf2_ros`, `xacro`. The M10 serial driver is not a dependency of
this package.

## Run

```bash
ros2 launch jcheng_mobile_bringup mobile_nav.launch.py \
  laser_x:=0.12 laser_y:=0.0 laser_z:=0.03 laser_yaw:=0.0
```

Arguments:

| Argument | Default | Meaning |
|---|---|---|
| `params_file` | `config/nav2_params.yaml` | Nav2 parameters |
| `slam_params_file` | `config/slam_toolbox.yaml` | slam_toolbox parameters |
| `odom_params_file` | `config/icp_odometry.yaml` | ICP odometry parameters |
| `start_slam` | `true` | Start slam_toolbox |
| `start_nav2` | `true` | Start Nav2 |
| `publish_laser_tf` | `true` | Publish `base_link -> laser_link`; disable if the system owns it |
| `base_frame` / `odom_frame` / `laser_frame` | `base_link` / `odom` / `laser_link` | TF names |
| `laser_x/y/z/yaw/pitch/roll` | `0.12/0/0.03/0/0/0` | **PROVISIONAL** LiDAR pose relative to `base_link` |

No motor bridge is started. `/cmd_vel` is intent only.

## Tests

```bash
python3 -m pytest -q ../../tests
```

The repository-level tests enforce the capability manifest and the
no-hardware boundary (`hardware_access: none`).

## Status

Draft, not hardware-validated. The M10 is not connected, Nav2/RTAB-Map are not
installed in the robot container, and the mount/footprint values are
placeholders. See the repository `README.md` and `docs/INTEGRATION.md`.
