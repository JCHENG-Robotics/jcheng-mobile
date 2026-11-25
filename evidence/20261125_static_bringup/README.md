# 2026-11-25 — static bring-up (jcheng-mobile)

Status: **partially verified (static); motion unverified.**
Operator: JerichoCheng.
Scope: `/scan`, ICP odometry, slam_toolbox map and Nav2 lifecycle on the robot,
with no base or arm motion.

## Environment

- Pi 5 (8 GB), ROS 2 Humble in the `ArmPiUltra` container, CycloneDDS domain 42.
- LSLIDAR M10 on `/dev/ttyACM0` (`1a86:55d4`, serial `58EB004720`); udev
  `/dev/lslidar_m10`; 460800 8N1.
- Driver `Lslidar/Lslidar_ROS2_driver` `LS-S1_V1.0` v5.2.0, built in
  `/home/ubuntu/lslidar_ws`; mobile package built in `/home/ubuntu/mobile_ws`.
- Nav2 1.1.20 and `rtabmap_odom` 0.23.13 installed in the container.
- No motor bridge was started; no motion command was sent.

## Results

| Check | Result |
|---|---|
| `/scan` | 10.00–10.04 Hz, `frame_id: laser_link`, `angle_increment` 0.006283 rad, `range_min` 0.05, `range_max` 12.0 |
| `/odom` | 10.03–10.10 Hz, `frame_id: odom`, `child_frame_id: base_link`; ICP ratio ~0.72–0.75, std ~3–4 mm |
| `/map` | 0.999 Hz, `frame_id: map`; `map -> odom` present (identity at rest) |
| Nav2 | `controller_server`, `planner_server`, `bt_navigator` active; lifecycle manager active |
| `/cmd_vel` | publishers from controller/behavior/velocity smoother; no base subscriber; no nonzero command |
| host | load ~9, 57 °C, 1.8 GB used; `slam_toolbox` dropped 16 startup scans |

## Caveats

- Static only; no motion, drift or accuracy claim.
- The LiDAR mount pose is the placeholder `(0.12, 0, 0.03, yaw 0)`; the
  footprint is provisional.
- The M10 driver, Nav2 1.1.20 and `diagnostic_updater` 4.0.7 live in the
  stateful robot container; they are not part of this repository and are not
  reproduced by CI.
- `slam_toolbox` dropped scans during startup; the map was published at 1 Hz
  after the TF chain settled.
