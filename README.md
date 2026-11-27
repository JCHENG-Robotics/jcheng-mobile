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
| Outputs | `/jcheng/intent/base` (lease-gated base intent, JSON envelope), `/odom` (RTAB-Map ICP laser odometry), `/map` (slam_toolbox), `/tf` |
| Motion authority | intent source (declared `motion_source` until interfaces v0.3.0), scope `base`, lease required; system-side freshness 200 ms / deadman 300 ms (provisional), liveness same-host only |
| Not in scope | M10 serial/device driver, motor bridge, e-stop, wheel odometry (the base has no encoders) |
| Forbidden | `/cmd_vel`, motor-driver topics, fake odometry, `/dev/*`, serial/CAN/GPIO access |

The system/hardware layer owns the M10 driver and the motor bridge. This
repository consumes `/scan` and produces intent; it never publishes
`/ros_robot_controller/*` or opens a serial port. Nav2 velocity is remapped to
the internal `/jcheng/nav2/cmd_vel`, validated by the intent node and
republished on `/jcheng/intent/base`; `/cmd_vel` is never published. The static
scan in `tests/test_no_hardware.py` enforces the device boundary.

`/jcheng/intent/base` is a provisional, **test-only** envelope, not a
`jcheng-interfaces` contract; it stays provisional until the
`base-intent-and-lease-holder` proposal is accepted and tagged. Its `stamp_ns`
is the mobile host's `time.monotonic_ns()` at receipt: the system intake may
compare it with its own monotonic clock **only when both run on the same
host**. The implemented system values are 200 ms freshness and a 300 ms
deadman, both provisional and system-side; the domain-42 guard and Nav2 remaps
remain static/unverified on hardware.

## Layout

```text
jcheng-mobile/
├── capability.yaml                 # admission manifest
├── docs/INTEGRATION.md             # discovery, lease, topics, failure semantics
├── tests/test_contract.py          # manifest contract checks
├── tests/test_no_hardware.py       # static no-hardware scan
├── tests/test_launch.py            # domain guard and Nav2 remap checks
├── tests/test_intent.py            # ROS-free intent mapping/guard
├── tests/test_intent_node.py       # node lease/domain/QoS wiring
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
  laser_x:=0.12 laser_y:=0.0 laser_z:=0.03 laser_yaw:=0.0 \
  lease_id:=<granted-lease> holder:=jcheng-mobile
```

If the system layer already publishes `base_link -> laser_link`, pass
`publish_laser_tf:=false` to avoid duplicate TF. Use `start_slam:=false` or
`start_nav2:=false` for staged checks. `domain` is fixed to 42: the launch sets
`ROS_DOMAIN_ID=42` and aborts on any other value.

The launch starts no motor bridge and publishes no `/cmd_vel`. It publishes
`/jcheng/intent/base` only while a lease is supplied and Nav2 input is fresh;
the system layer must apply its own lease, deadman, e-stop and base limits
before any motor moves. Domain 42 is necessary but is not a safety proof, and
the remap topology is static/unverified on hardware.

## Tests

```bash
python3 -m pytest -q tests
```

- `test_contract.py` validates the capability manifest fields, the contract
  hash shape, scope/lease/deadman, domain 42 and the topic surface (no
  `/cmd_vel`).
- `test_no_hardware.py` rejects device paths, serial/CAN/GPIO access, motor
  driver topics, the vendor mecanum node and the bench open-loop odometry.
- `test_launch.py` pins the domain guard and the scoped Nav2 remaps.
- `test_intent.py` covers mapping, limits, freshness, sequence and lease
  rejection without ROS.
- `test_intent_node.py` pins the node's lease/domain/QoS wiring statically.

## Validation status

- Offline: YAML parse, `py_compile`, `colcon build`, `xacro` expansion, launch
  description generation, and M10 driver parameter cross-check (in the
  predecessor bench package) passed on 2026-11-24.
- **Static bring-up partially verified (2026-11-25, Pi 5 Humble, no motion):**
  M10 `/scan` 10 Hz, RTAB-Map ICP `/odom` 10 Hz, slam_toolbox `/map` 1 Hz,
  `map -> odom`, and Nav2 `controller_server` / `planner_server` /
  `bt_navigator` active. At that time `/cmd_vel` had publishers but no base
  subscriber; the 2026-11-27 intent change removes that surface, but it has not
  been re-run on the robot.
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
