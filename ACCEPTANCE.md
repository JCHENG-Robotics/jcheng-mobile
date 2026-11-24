# Acceptance report — jcheng-mobile

> Status: **inconclusive** as of 2026-11-24 for v0.1.0.
> Operator: JerichoCheng. Reviewer: pending.
> Scope: the capability contract, the no-hardware boundary, the offline build
> and the launch/URDF configuration.
> All offline gates pass; every hardware gate has not run, so the capability is
> not accepted for deployment.
> **Not hardware-validated.** No `/scan`, `/odom`, `/map` or motion claim is
> evidence-backed. No motion command was sent.

## 1. Gates

| Gate | Command | Level | Result | Evidence |
|---|---|---|---|---|
| Contract tests | `python3 -m pytest -q tests` | L0 | pass (10 tests) | `tests/test_contract.py` |
| No-hardware scan | `python3 -m pytest -q tests/test_no_hardware.py` | L0 | pass | `tests/test_no_hardware.py` |
| ROS build | `colcon build --packages-select jcheng_mobile_bringup` | L0 | pass | CI `mobile-ci` |
| URDF expansion | `xacro .../jcheng_mobile.urdf.xacro` | L0 | pass | CI `mobile-ci` |
| Launch description | `ros2 launch ... --show-args` | L0 | pass | 2026-11-24 offline check |
| M10 driver parameter cross-check | bench package check | L0 | pass | `jcheng-mobile-bench` (predecessor bench) |
| Hardware `/scan`, `/odom`, `/map` | — | L5 | not run | — |

## 2. Verified claims

| Claim | Level | Evidence |
|---|---|---|
| The manifest declares layer L3, `hardware_access: none`, scope `base`, lease and 500 ms deadman | L0 | `capability.yaml`; `test_contract.py` |
| The contract hash matches interfaces v0.1.0 | L0 | `test_contract.py` |
| No device path, serial/CAN/GPIO access, motor topic or fabricated odometry exists in the package | L0 | `test_no_hardware.py` |
| The package builds and the URDF expands | L0 | CI `mobile-ci` |
| The launch description starts no motor bridge | L0 | `mobile_nav.launch.py` review; no vendor publisher |

## 3. Not verified

| Item | Reason | Risk |
|---|---|---|
| `/scan` input | M10 driver and serial device are not in this repository; the robot container has no driver running | ICP odometry has no input |
| Mount pose and footprint | Values are placeholders (`laser_x=0.12`, `y=0`, `z=0.03`, `yaw=0`) | Odometry, costmaps and TF are wrong before measurement |
| Nav2 / RTAB-Map / slam_toolbox installation | Not installed in the robot container | Launch cannot run on the robot |
| `/odom` accuracy and drift | Not measured | Navigation would trust unbounded drift |
| `/map` correctness | Not measured | An unknown or empty map must be treated as no-go |
| Lease, deadman and base limits at runtime | No system-layer integration run | `/cmd_vel` is unproven as intent |
| Physical e-stop and motor bridge | Outside this repository | No safety-rated stop |

## 4. Limitations

- The base has no wheel encoders or IMU; odometry is laser-based and fails
  without `/scan`.
- An empty or unknown map is no-go, not free space.
- No hardware e-stop, brake or bumper exists in this repository or the base
  platform.
- The mount and footprint values must be measured before any navigation
  attempt.
- License status is inconsistent with the rest of the ecosystem: this
  repository carries an MIT `LICENSE` from initialization, while the other new
  repositories have none and the review is pending. The file is retained
  pending review ([LICENSE-REVIEW.md](LICENSE-REVIEW.md)); it is not a settled
  ecosystem grant.

## 5. Sign-off

| Role | Name | Date |
|---|---|---|
| Operator | JerichoCheng | 2026-11-24 |
| Reviewer | pending | — |

## 6. Machine-readable report

None. Per-run reports, when produced, must validate against
`jcheng-interfaces/schemas/acceptance-report.v1.schema.json`.
