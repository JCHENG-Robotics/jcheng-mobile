# jcheng_mobile_bringup

ROS 2 Humble bringup for the `jcheng-mobile` capability. It consumes `/scan`
and produces real laser odometry, a map and a lease-gated base intent
envelope. Nav2 velocity is remapped off `/cmd_vel`; the package does **not**
start the M10 driver, the vendor mecanum node, or any fake odometry.

## Inputs / outputs

| Direction | Topic | Notes |
|---|---|---|
| in | `/scan` | `sensor_msgs/LaserScan`, frame `laser_link`, 10 Hz, from the system/hardware layer |
| out | `/jcheng/intent/base` | `std_msgs/String` JSON `jcheng.mobile.base_intent.v1` (provisional), lease-gated, ≤20 Hz |
| out | `/odom` | RTAB-Map ICP laser odometry; TF `odom -> base_link` |
| out | `/map` | slam_toolbox online-async |
| out | `/tf` | `map -> odom -> base_link`, `base_link -> laser_link` |
| in (internal) | `/jcheng/nav2/cmd_vel` | Nav2 velocity after the remap group; the intent node validates it |
| — | `/cmd_vel` | **never published**; the Nav2 include is wrapped in a scoped remap group |

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
  laser_x:=0.12 laser_y:=0.0 laser_z:=0.03 laser_yaw:=0.0 \
  lease_id:=<granted-lease> holder:=jcheng-mobile
```

Arguments:

| Argument | Default | Meaning |
|---|---|---|
| `domain` | `42` | ROS domain; any other value aborts the launch |
| `params_file` | `config/nav2_params.yaml` | Nav2 parameters |
| `slam_params_file` | `config/slam_toolbox.yaml` | slam_toolbox parameters |
| `odom_params_file` | `config/icp_odometry.yaml` | ICP odometry parameters |
| `start_slam` | `true` | Start slam_toolbox |
| `start_nav2` | `true` | Start Nav2 |
| `start_intent` | `true` | Start the intent node (publishes nothing without a lease) |
| `lease_id` | empty | Lease granted by the system layer; required for intent |
| `holder` | empty | Lease holder; required for intent |
| `intent_rate` | `20.0` | Intent publish rate in Hz (≤20) |
| `duty_limit` | `0.60` | Normalized duty cap carried in the intent |
| `publish_laser_tf` | `true` | Publish `base_link -> laser_link`; disable if the system owns it |
| `base_frame` / `odom_frame` / `laser_frame` | `base_link` / `odom` / `laser_link` | TF names |
| `laser_x/y/z/yaw/pitch/roll` | `0.12/0/0.03/0/0/0` | **PROVISIONAL** LiDAR pose relative to `base_link` |

No motor bridge is started. `/jcheng/intent/base` is intent only; the system
layer applies its own lease, deadman, e-stop and limits. Domain 42 is
necessary, not a safety proof. The envelope is provisional and test-only, not
a `jcheng-interfaces` contract: its `stamp_ns` is the mobile host's
`time.monotonic_ns()` at receipt, so the system intake can compare it with its
own monotonic clock only on the same host. The implemented system values are
200 ms freshness and a 300 ms deadman, both provisional; the domain guard and
Nav2 remaps are static/unverified on hardware.

## Tests

```bash
python3 -m pytest -q ../../tests
```

The repository-level tests enforce the capability manifest, the no-hardware
boundary (`hardware_access: none`), the launch domain/remap guard and the
ROS-free intent guard.

## Status

Draft, not hardware-validated. The M10 is not connected, Nav2/RTAB-Map are not
installed in the robot container, and the mount/footprint values are
placeholders. The intent boundary has not been run on a robot. See the
repository `README.md` and `docs/INTEGRATION.md`.
