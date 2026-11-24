# jcheng-mobile roadmap

> Status: **v0.1.0** as of 2026-11-24. The capability contract and offline
> stack are complete; hardware validation has not started.

## Current state

| Item | State | Evidence |
|---|---|---|
| Contract-compliant skeleton and manifest | Complete (2026-11-24) | `capability.yaml`; `tests/test_contract.py` |
| No-hardware boundary scan | Complete | `tests/test_no_hardware.py` |
| ICP odometry, SLAM and Nav2 configuration | Complete, offline | `ros2_ws/src/jcheng_mobile_bringup/` |
| Build, xacro and launch description | Complete, offline | 2026-11-24 validation |
| M10 `/scan` integration | Not started | Robot has no M10 driver in this repository |
| Mount pose and footprint measurement | Not started | Placeholder values |
| Navigation on hardware | Not started | — |
| Motion through `jcheng-system` lease/deadman | Not started | Integration contract documented only |

## Milestones

| Milestone | Scope | State | Exit criterion | Evidence |
|---|---|---|---|---|
| M0 | Contract-compliant skeleton | Complete (2026-11-24) | Contract and no-hardware tests pass | `tests/` |
| M1 | Offline build and configuration | Complete (2026-11-24) | `colcon build`, `xacro`, launch description pass | CI `mobile-ci` |
| M2 | Hardware input validation | Not started | `/scan` at 10 Hz, calibrated mount pose, no duplicate TF | — |
| M3 | Mapping and localization on hardware | Not started | `/odom` and `/map` update; map matches the room | — |
| M4 | Supervised navigation through the system boundary | Not started | Lease, deadman, e-stop and base limits enforced; supervised run | — |

## Next

1. **M2 — connect the M10 through the system layer.** Measure the LiDAR mount
   pose (`laser_x/y/z/yaw`) and the chassis footprint, then replace the
   provisional URDF/Nav2 values. Prerequisites: the system/hardware layer owns
   the driver and `/scan`.
2. **M3 — validate odometry and mapping.** Confirm ICP odometry does not drift
   unbounded in a short supervised run and that `map -> odom -> base_link`
   stays consistent.
3. **M4 — supervised navigation.** Route `/cmd_vel` through the system lease,
   500 ms deadman and base limits; the physical e-stop remains outside this
   repository.

## Out of scope

- The LSLIDAR M10 serial driver, udev rules and `/dev/lslidar_m10`.
- The vendor motor controller and `/ros_robot_controller/set_motor_speeds`.
- Open-loop or fabricated odometry; the base has no wheel encoders or IMU.
- The physical e-stop, brake and bumper.

## Dependencies

- `jcheng-interfaces` `>=0.1,<0.2`, contract hash
  `sha256:0b8d72ced7f54d444d6851d8b99a51a78e2bed3f687324f51a15f76557f24b42`.
- `jcheng-system` `>=0.1,<0.2` for the lease, deadman and base authority.
- Every hardware run requires separate, explicit operator authorization.
