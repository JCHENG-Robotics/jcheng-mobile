# Integration — jcheng-mobile

## 1. Discovery and boundary

The system reads `capability.yaml` at startup. The manifest declares:

- layer L3, `name: jcheng-mobile`, `version: 0.1.0`;
- `safety.class: motion_source`, `scopes: [base]`, `requires_lease: true`,
  `max_rate_hz: 20`, `deadman_ms: 500`;
- `hardware_access: none`;
- ROS domain 42;
- publishes `/cmd_vel`, `/odom`, `/map`, `/tf`;
- subscribes `/scan`, `/tf`.

`hardware_access: none` is a hard boundary. This repository must never open a
serial/USB/CAN/GPIO device or publish a vendor motor-driver topic. The M10
driver, motor bridge and e-stop belong to the system/hardware layer.

## 2. Required inputs

| Input | Type | Owner | Contract |
|---|---|---|---|
| `/scan` | `sensor_msgs/LaserScan` | system/hardware layer (M10 driver) | frame `laser_link`, 10 Hz, 0.05–12 m, angle_min/max ±π |
| `/tf` | `tf2_msgs/TFMessage` | system + this module | `map -> odom -> base_link`, `base_link -> laser_link` |

This module publishes `base_link -> laser_link` from the measured mount pose by
default. If the system layer already publishes it, launch with
`publish_laser_tf:=false`; duplicate TF publishers are not allowed.

The mount pose is **provisional** until measured. The current defaults are
`laser_x=0.12`, `laser_y=0.0`, `laser_z=0.03`, `laser_yaw=0.0` relative to
`base_link`.

## 3. Outputs

| Output | Type | Consumer | Notes |
|---|---|---|---|
| `/odom` | `nav_msgs/Odometry` + TF `odom -> base_link` | Nav2, system | RTAB-Map ICP laser odometry; real scan matching, not fake wheel odometry |
| `/map` | `nav_msgs/OccupancyGrid` | Nav2, operator | slam_toolbox online-async |
| `/tf` | `tf2_msgs/TFMessage` | system | `map -> odom -> base_link`, `base_link -> laser_link` |
| `/cmd_vel` | `geometry_msgs/Twist` | system/hardware layer | chassis intent only, ≤20 Hz; system applies lease, deadman, e-stop and base limits |

The system/hardware layer must treat `/cmd_vel` as **intent**, not as a motor
command. It applies the control lease, the 500 ms deadman, the base duty cap
(duty 60 ≈ 0.33 m/s) and the physical e-stop/power cutoff.

## 4. Lease and failure semantics

- The capability requires a lease for scope `base`. Without a valid lease it
  must not publish non-zero `/cmd_vel`.
- `deadman_ms: 500`: loss of the intent stream or of the system heartbeat for
  500 ms means zero chassis intent.
- No `/scan` for >1 s: ICP odometry stops updating; Nav2 must stop the base.
- Stale `/odom` (>0.5 s): no motion intent; the system must stop.
- Stale `/map` or missing `map -> odom`: no navigation goal; the system must
  treat the map as no-go, not as free space.
- Missing `base_link -> laser_link`: no scan matching; no motion intent.
- An empty or unknown map is **no-go**, not "drive on".

## 5. Limits

| Limit | Value |
|---|---|
| Max forward speed | 0.25 m/s (Nav2) |
| Max lateral speed | 0.20 m/s (mecanum intent) |
| Max yaw rate | 0.60 rad/s |
| Intent rate | ≤20 Hz (velocity smoother) |
| Deadman | 500 ms |
| Base hardware cap | duty 60 ≈ 0.33 m/s, enforced outside this repo |
| E-stop | none in this repo; system/hardware layer responsibility |

## 6. Out of scope

- LSLIDAR M10 serial driver, udev rules and `/dev/lslidar_m10`.
- Vendor motor controller (`controller/mecanum`) and
  `/ros_robot_controller/set_motor_speeds`.
- Open-loop or otherwise fabricated odometry.
- Wheel encoders and IMU (the base has neither).
- Physical e-stop, brake and bumper.

These live in the system/hardware layer or a bench/ops tool, not in this
capability repository.

## 7. Integration sequence

1. System layer starts the M10 driver and publishes `/scan` in the agreed
   frame. Verify 10 Hz, `angle_increment ≈ 0.00628 rad`, `range_max = 12.0`.
2. Measure and set the LiDAR mount pose; set `publish_laser_tf` according to
   ownership.
3. Start this module with `start_slam:=true start_nav2:=false`; verify
   `/odom` and `map -> odom -> base_link`.
4. Start Nav2 with `start_nav2:=true`; verify `/cmd_vel` is bounded and zero
   when no goal is active.
5. System layer consumes `/cmd_vel` only after lease, deadman and e-stop are
   verified. First motion at 0.1 m/s, wheels off the ground for the command
   path test, then supervised on the floor with the power switch in reach.

## 8. Verification

- `pytest -q tests` (contract + no-hardware scan) is the repository gate.
- CI `mobile-gate` requires the contract job and the Humble ROS build.
- No hardware claim is valid until `/scan`, `/odom`, `/map` and a supervised
  motion run are recorded with the M10 and a measured mount pose.
