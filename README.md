# jcheng-mobile

[简体中文](README.zh-CN.md) | **English**

> **STATUS: EXPERIMENTAL / STATIC BRING-UP PARTIALLY VERIFIED (2026-11-25);
> motion unverified.** This is the L3 mobile-base
> capability for the JCHENG ecosystem. It consumes a 2D LiDAR scan, estimates
> real laser odometry, maps, and publishes chassis intent. It does **not** open
> devices, drive motors, or fabricate odometry.
> English canonical; see [README.zh-CN.md](README.zh-CN.md) for the Chinese translation.

## Scope and boundary

| Item | This repository |
|---|---|
| Layer | L3 capability (`capability.yaml`: `hardware_access: none`) |
| Inputs | `/scan` (LSLIDAR M10, 10 Hz, frame `laser_link`) from the system/hardware layer |
| Outputs | `/odom` (RTAB-Map ICP laser odometry), `/map` (slam_toolbox), `/tf`, `/cmd_vel` chassis intent |
| Motion authority | `motion_source`, scope `base`, lease required, 500 ms deadman |
| Not in scope | M10 serial/device driver, motor bridge, e-stop, wheel odometry (the base has no encoders) |
| Forbidden | motor-driver topics, fake odometry, `/dev/*`, serial/CAN/GPIO access |

The system/hardware layer owns the M10 driver and the motor bridge. This
repository consumes `/scan` and produces intent; it never publishes
`/ros_robot_controller/*` or opens a serial port. The static scan in
`tests/test_no_hardware.py` enforces this boundary.

## Layout

```text
jcheng-mobile/
├── capability.yaml                 # admission manifest
├── docs/INTEGRATION.md             # discovery, lease, topics, failure semantics
├── tests/test_contract.py          # manifest contract checks
├── tests/test_no_hardware.py       # static no-hardware scan
├── VERSION
├── CHANGELOG.md
├── LICENSE
└── ros2_ws/src/jcheng_mobile_bringup/
    ├── launch/mobile_nav.launch.py # ICP odom + SLAM + Nav2; no hardware drivers
    ├── config/nav2_params.yaml     # MPPI Omni, costmaps, velocity smoother
    ├── config/slam_toolbox.yaml    # online-async mapping
    ├── config/icp_odometry.yaml    # real laser odometry, /scan -> /odom
    └── urdf/jcheng_mobile.urdf.xacro
```

## Requirements

- ROS 2 Humble.
- `ros-humble-nav2-bringup`, `ros-humble-nav2-mppi-controller`,
  `ros-humble-slam-toolbox`, `ros-humble-rtabmap-odom` installed in the target
  environment.
- A `/scan` publisher owned by the system/hardware layer. The M10 driver is
  not part of this repository.
- Measured LiDAR mount pose and chassis footprint before any real navigation.
  The values in the URDF/launch/Nav2 configs are **provisional**.

## Build and run

```bash
colcon build --base-paths ros2_ws/src --packages-select jcheng_mobile_bringup
source install/setup.bash

ros2 launch jcheng_mobile_bringup mobile_nav.launch.py \
  laser_x:=0.12 laser_y:=0.0 laser_z:=0.03 laser_yaw:=0.0
```

If the system layer already publishes `base_link -> laser_link`, pass
`publish_laser_tf:=false` to avoid duplicate TF. Use `start_slam:=false` or
`start_nav2:=false` for staged checks.

The launch starts no motor bridge. `/cmd_vel` is chassis intent; the system
layer must apply its lease, deadman, e-stop and base limits before any motor
moves.

## Tests

```bash
python3 -m pytest -q tests
```

- `test_contract.py` validates the capability manifest fields, the contract
  hash shape, scope/lease/deadman, domain 42 and the topic surface.
- `test_no_hardware.py` rejects device paths, serial/CAN/GPIO access, motor
  driver topics, the vendor mecanum node and the bench open-loop odometry.

## Validation status

- Offline: YAML parse, `py_compile`, `colcon build`, `xacro` expansion, launch
  description generation, and M10 driver parameter cross-check (in the
  predecessor bench package) passed on 2026-11-24.
- **Static bring-up partially verified (2026-11-25, Pi 5 Humble, no motion):**
  M10 `/scan` 10 Hz, RTAB-Map ICP `/odom` 10 Hz, slam_toolbox `/map` 1 Hz,
  `map -> odom`, and Nav2 `controller_server` / `planner_server` /
  `bt_navigator` active. `/cmd_vel` had publishers but no base subscriber; no
  motor bridge was started.
- **Motion unverified.** No base or arm motion; no accuracy claim. The LiDAR
  mount and footprint are still placeholders, and the driver/Nav2 packages live
  in the stateful robot container.
- Evidence:
  [evidence/20261125_static_bringup/README.md](evidence/20261125_static_bringup/README.md).

Full report: [ACCEPTANCE.md](ACCEPTANCE.md).

## Related

- `JCHENG-Robotics/jcheng-interfaces` — contract schema and hash.
- `JCHENG-Robotics/jcheng-system` — safety, authority, motion, hardware bridge.
- `JCHENG-Robotics/jcheng-ops` — operations and watchdogs.
- `docs/INTEGRATION.md` — discovery, lease and failure semantics.

## License

This repository contains an MIT `LICENSE` added at initialization. That
predates the organization license-review policy: the other new repositories
(`jcheng-interfaces`, `jcheng-system`, `jcheng-perception`, `jcheng-ops`,
`.github`) have no `LICENSE`, and the review is pending. The file is **retained
pending review**; see [LICENSE-REVIEW.md](LICENSE-REVIEW.md). The inconsistency
is recorded in
[`JCHENG-Robotics/.github/ACCEPTANCE.md`](https://github.com/JCHENG-Robotics/.github/blob/main/ACCEPTANCE.md).
Do not treat this file as the organization-wide licensing decision.
