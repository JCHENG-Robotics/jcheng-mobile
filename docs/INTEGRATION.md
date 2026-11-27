# Integration — jcheng-mobile

## 1. Discovery and boundary

The system reads `capability.yaml` at startup. The manifest declares:

- layer L3, `name: jcheng-mobile`, `version: 0.1.0`;
- `safety.class: motion_source`, `scopes: [base]`, `requires_lease: true`,
  `max_rate_hz: 20`, `deadman_ms: 500`;
- `hardware_access: none`;
- ROS domain 42;
- publishes `/jcheng/intent/base`, `/odom`, `/map`, `/tf`;
- subscribes `/scan`, `/tf`.

`hardware_access: none` is a hard boundary. This repository must never open a
serial/USB/CAN/GPIO device or publish a vendor motor-driver topic. The M10
driver, motor bridge and e-stop belong to the system/hardware layer.

### Intent-only authority

This capability is an **intent source**, not a motion authority. It never calls
`ExecuteMotion`, never publishes `/cmd_vel`, and never publishes a vendor
velocity or duty topic. Nav2's velocity is remapped to the internal
`/jcheng/nav2/cmd_vel`, validated, and republished as
`/jcheng/intent/base`. The system layer remains the only origin of motion.

The manifest keeps `class: motion_source` because the pinned interfaces
contract (`capability-manifest.v1`, no `intent_source` value) cannot express an
intent source. `jcheng-interfaces` `main` adds `intent_source` for an untagged
v0.3.0, which is not a pin. Until v0.3.0 is released and the ecosystem lock
moves, read the class as "publishes an intent stream" and not as a grant of
motion authority. The manifest comment records this over-claim. Reclassify to
`intent_source` only after the tag exists.

### Domain 42

`mobile_nav.launch.py` sets `ROS_DOMAIN_ID=42` for every child process and
asserts `domain:=42` before starting any node; any other value aborts the
launch. The intent node also refuses to publish when its process
`ROS_DOMAIN_ID` is not 42.

**Domain isolation is necessary but not sufficient.** A process on domain 42
can still publish a malformed or unauthorised intent. The system layer must
validate every envelope independently: schema, lease, sequence, freshness,
speed and duty. Do not treat domain membership, the source node name or the
presence of a publisher as authorisation.

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

`/jcheng/nav2/cmd_vel` is **not** an external input. It is an internal topic
created by the remap group around the Nav2 include (`geometry_msgs/Twist`,
best-effort, depth 1). Do not subscribe to it from another capability.

## 3. Outputs

| Output | Type | Consumer | Notes |
|---|---|---|---|
| `/jcheng/intent/base` | `std_msgs/String` JSON `jcheng.mobile.base_intent.v1` (provisional) | system intent intake | lease-gated, ≤20 Hz, domain 42, best-effort depth 1 |
| `/jcheng/nav2/cmd_vel` | `geometry_msgs/Twist` | this launch only | Nav2 velocity, never leaves the launch and is not declared in the manifest |
| `/odom` | `nav_msgs/Odometry` + TF `odom -> base_link` | Nav2, system | RTAB-Map ICP laser odometry; real scan matching, not fake wheel odometry |
| `/map` | `nav_msgs/OccupancyGrid` | Nav2, operator | slam_toolbox online-async |
| `/tf` | `tf2_msgs/TFMessage` | system | `map -> odom -> base_link`, `base_link -> laser_link` |

`/cmd_vel` is not an output. Nav2's `controller_server` keeps its internal
`cmd_vel_nav` hop, `velocity_smoother` consumes `cmd_vel_nav`, and both the
smoother output (`cmd_vel_smoothed`) and the behavior server's raw `cmd_vel`
are scoped to `/jcheng/nav2/cmd_vel`.

This topology follows the Humble Nav2 1.1.20 `navigation_launch.py` remaps
(controller `cmd_vel -> cmd_vel_nav`; smoother `cmd_vel -> cmd_vel_nav` and
`cmd_vel_smoothed -> cmd_vel`; behavior server unmapped). A Nav2 upgrade can
change it: re-check the launch remaps and the smoother chain before running on
the robot. The static test pins our strings but cannot detect an upstream
change.

### Provisional envelope

`BaseIntent` is repository-local: the pinned interfaces contract has no such
message and the v0.3.0 addition is untagged. The JSON form is the only wire
format for now and must not be treated as an admitted contract. Example:

```json
{
  "schema": "jcheng.mobile.base_intent.v1",
  "lease_id": "lease-7f3a",
  "holder": "jcheng-mobile",
  "command_id": "lease-7f3a:5c1e9a0b7d21:41",
  "seq": 41,
  "stamp_ns": 123456789012,
  "frame": "base_link",
  "linear": {"x": 0.10, "y": 0.0},
  "angular": {"z": 0.0},
  "duty_limit": 0.60
}
```

| Field | Meaning |
|---|---|
| `lease_id` | Control lease granted by the system; never minted here |
| `holder` | Lease holder name; must match the lease |
| `command_id` | `<lease_id>:<process session>:<seq>`; unique across restarts |
| `seq` | Strictly increasing per process; a restart resets it |
| `stamp_ns` | Monotonic receipt time of the Nav2 sample; local to this node |
| `frame` | `base_link` |
| `linear.x` / `linear.y` | Forward/lateral velocity cap in m/s |
| `angular.z` | Yaw-rate cap in rad/s |
| `duty_limit` | Normalized duty cap in (0, 0.60] |

QoS is explicit on both ends: **best-effort, keep-last, depth 1**. A lost
sample is not retransmitted; the 500 ms deadman is the loss response, because a
retransmitted stale velocity is worse than no velocity.

## 4. Lease and intent semantics

- The node never mints a lease. `lease_id` and `holder` are launch arguments
  with empty defaults; while either is empty the node publishes nothing.
- `seq` must strictly increase. A duplicate or rollback is rejected and does
  not advance state. `command_id` includes a per-process session so the
  system-side dedup key stays unique after a restart.
- `stamp_ns` is the monotonic receipt time. A sample older than 500 ms or dated
  in the future is rejected. Holding the last fresh sample is intentional: the
  stream stops 500 ms after the input stops. The value is local to this node
  (monotonic, not a wall clock); the system must use its own arrival timestamp
  for liveness and must not compare `stamp_ns` across hosts.
- Out-of-limit values are **rejected, not clamped**: `|x| ≤ 0.25 m/s`,
  `|y| ≤ 0.20 m/s`, `|z| ≤ 0.60 rad/s`, `0 < duty_limit ≤ 0.60`, all finite.
  A rejected sample is not published and does not advance `seq`.
- No lease, stale input, sequence rollback, non-finite values or an
  out-of-limit sample means **no intent**. The system's 500 ms deadman then
  produces zero motion.
- The node must be launched with the lease after the system grants it:
  `lease_id:=<id> holder:=<name>`. Granting is an operator action, not a
  side effect of starting the launch.
- The system must still apply its own lease check, deadman, base duty cap and
  stop latch. The envelope limits are early feedback, not authority.

Failure semantics:

- No `/scan` for >1 s: ICP odometry stops updating; Nav2 must stop the base.
- Stale `/odom` (>0.5 s): no motion intent; the system must stop.
- Stale `/map` or missing `map -> odom`: no navigation goal; the system must
  treat the map as no-go, not as free space.
- Missing `base_link -> laser_link`: no scan matching; no motion intent.
- An empty or unknown map is **no-go**, not "drive on".

## 5. Limits

| Limit | Value |
|---|---|
| Max forward speed | 0.25 m/s (Nav2, re-checked by the intent guard) |
| Max lateral speed | 0.20 m/s (mecanum, re-checked) |
| Max yaw rate | 0.60 rad/s (re-checked) |
| Intent rate | ≤20 Hz |
| Deadman | 500 ms |
| Duty limit carried in the intent | 0.60 (duty 60 ≈ 0.33 m/s) |
| Base hardware cap | enforced outside this repo |
| E-stop | none in this repo; system/hardware layer responsibility |

## 6. Out of scope

- LSLIDAR M10 serial driver, udev rules and `/dev/lslidar_m10`.
- Vendor motor controller (`controller/mecanum`) and
  `/ros_robot_controller/set_motor_speeds`.
- Open-loop or otherwise fabricated odometry.
- Wheel encoders and IMU (the base has neither).
- Physical e-stop, brake and bumper.
- Lease issuance and intent arbitration.

These live in the system/hardware layer or a bench/ops tool, not in this
capability repository.

## 7. Integration sequence

1. System layer starts the M10 driver and publishes `/scan` in the agreed
   frame. Verify 10 Hz, `angle_increment ≈ 0.00628 rad`, `range_max = 12.0`.
2. Measure and set the LiDAR mount pose; set `publish_laser_tf` according to
   ownership.
3. Start this module with `start_slam:=true start_nav2:=false`; verify
   `/odom` and `map -> odom -> base_link`.
4. Start Nav2 with `start_nav2:=true`. Verify that `/jcheng/nav2/cmd_vel` is
   bounded, that `cmd_vel_nav` feeds the smoother, and that **no `/cmd_vel`
   publisher exists**.
5. After the system grants the lease, start the intent path with
   `lease_id:=<id> holder:=<name>`; verify `/jcheng/intent/base` at ≤20 Hz with
   an increasing `seq`, a fresh `stamp_ns` and `duty_limit=0.60`.
6. Stop the Nav2 input or the lease and verify that the intent stream stops
   within 500 ms; the system must then report zero motion.
7. The system layer consumes intent only after its own lease, deadman and
   e-stop checks. First motion at 0.1 m/s, wheels off the ground for the
   command-path test, then supervised on the floor with the power switch in
   reach.

## 8. Verification

- `python3 -m pytest -q tests` covers the contract, no-hardware scan, launch
  remaps/domain guard, the ROS-free intent guard and the node's static
  lease/domain/QoS wiring (50 tests at the time of writing).
- CI `mobile-gate` requires the contract job and the Humble ROS build.
- No test in this repository starts DDS, a ROS node or a device; the launch is
  checked statically. Runtime topic behaviour on domain 42 is **unverified**
  until a supervised bench run records it.
- No hardware claim is valid until `/scan`, `/odom`, `/map` and a supervised
  motion run are recorded with the M10 and a measured mount pose.
