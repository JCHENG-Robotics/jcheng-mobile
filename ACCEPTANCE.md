# Acceptance report — jcheng-mobile

> Status: **partially verified (static)** as of 2026-11-25 for v0.1.0.
> Operator: JerichoCheng. Reviewer: pending.
> Scope: the capability contract, the no-hardware boundary, the offline build,
> the launch/URDF configuration, and the 2026-11-25 static hardware bring-up
> (no motion).
> All offline gates pass; the static `/scan`, `/odom` and `/map` gates pass.
> The capability is **not accepted for deployment**: motion, accuracy, lease and
> e-stop gates are unverified. No motion command was sent.

## 1. Gates

| Gate | Command | Level | Result | Evidence |
|---|---|---|---|---|
| Contract tests | `python3 -m pytest -q tests` | L0 | pass (10 tests) | `tests/test_contract.py` |
| No-hardware scan | `python3 -m pytest -q tests/test_no_hardware.py` | L0 | pass | `tests/test_no_hardware.py` |
| ROS build | `colcon build --packages-select jcheng_mobile_bringup` | L0 | pass | CI `mobile-ci` |
| URDF expansion | `xacro .../jcheng_mobile.urdf.xacro` | L0 | pass | CI `mobile-ci` |
| Launch description | `ros2 launch ... --show-args` | L0 | pass | 2026-11-24 offline check |
| M10 driver parameter cross-check | bench package check | L0 | pass | `jcheng-mobile-bench` (predecessor bench) |
| Hardware `/scan` | 2026-11-25 static, Pi 5 | L5 | pass | `evidence/20261125_static_bringup/README.md` |
| Hardware `/odom` + `/map` | 2026-11-25 static, Pi 5 | L5 | pass (static; no accuracy/motion claim) | same evidence |
| Motion / navigation | — | L5 | not run | — |

## 2. Verified claims

| Claim | Level | Evidence |
|---|---|---|
| The manifest declares layer L3, `hardware_access: none`, scope `base`, lease and 500 ms deadman | L0 | `capability.yaml`; `test_contract.py` |
| The contract hash matches interfaces v0.2.0 | L0 | `test_contract.py` |
| No device path, serial/CAN/GPIO access, motor topic or fabricated odometry exists in the package | L0 | `test_no_hardware.py` |
| The package builds and the URDF expands | L0 | CI `mobile-ci` |
| The launch description starts no motor bridge | L0 | `mobile_nav.launch.py` review; no vendor publisher |
| Static `/scan` at 10 Hz, frame `laser_link`, 0.36° spacing | L5 | `evidence/20261125_static_bringup/README.md` |
| Static ICP `/odom` at 10 Hz and `map -> odom`; Nav2 lifecycle active | L5 | same evidence |

## 3. Not verified

| Item | Reason | Risk |
|---|---|---|
| Mount pose and footprint | Values are placeholders (`laser_x=0.12`, `y=0`, `z=0.03`, `yaw=0`) | Odometry, costmaps and TF are wrong before measurement |
| Motion, navigation and drift | Static only; no motion or accuracy run | `/cmd_vel` intent and localization are unproven in motion |
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
- The 2026-11-25 static run used the placeholder LiDAR pose; the reported
  `/odom` and `/map` results validate the graph, not accuracy.
- The M10 driver, Nav2 1.1.20 and `diagnostic_updater` 4.0.7 are installed in
  the stateful robot container; they are not part of this repository.
- The static run measured host load ~9 and 57 °C with the perception stack
  running; CPU headroom is not established for navigation.
- License status is inconsistent with the rest of the ecosystem: this
  repository carries an MIT `LICENSE` from initialization, while the other new
  repositories have none and the review is pending. The file is retained
  pending review ([LICENSE-REVIEW.md](LICENSE-REVIEW.md)); it is not a settled
  ecosystem grant.

## 5. Sign-off

| Role | Name | Date |
|---|---|---|
| Operator | JerichoCheng | 2026-11-25 |
| Reviewer | pending | — |

## 6. Machine-readable report

None. Per-run reports, when produced, must validate against
`jcheng-interfaces/schemas/acceptance-report.v1.schema.json`.
