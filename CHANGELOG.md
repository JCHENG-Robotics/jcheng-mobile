# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Nav2 no longer publishes `/cmd_vel`. `mobile_nav.launch.py` wraps the Nav2
  include in a scoped remap group: `controller_server:cmd_vel` and
  `velocity_smoother:cmd_vel` keep the `cmd_vel_nav` hop,
  `velocity_smoother:cmd_vel_smoothed` and the blanket `/cmd_vel` go to the
  internal `/jcheng/nav2/cmd_vel`, so the smoother chain is preserved and no
  raw velocity topic leaves the launch.
- The capability now publishes bounded intent on `/jcheng/intent/base`
  (domain 42) instead of `/cmd_vel`. `capability.yaml` keeps
  `safety.class: motion_source` because the pinned interfaces contract has no
  `intent_source`; the comment records that this is an intent-only over-claim
  to reclassify after v0.3.0 is tagged.
- `mobile_nav.launch.py` sets `ROS_DOMAIN_ID=42` for every child process,
  declares `domain` (default 42) and aborts on any other value. Domain
  isolation is documented as necessary, not as a safety proof.
- The package description, READMEs and Nav2 params comment now describe the
  intent channel instead of `/cmd_vel`.

### Added

- ROS-free `jcheng_mobile_bringup/intent.py`: `Twist` -> `BaseIntent`
  mapping with lease/holder, `command_id`, strictly increasing `seq`,
  monotonic freshness (500 ms), speed limits, duty limit and rate bound.
  Rejections return `None` and never advance state.
- Thin `jcheng_mobile_bringup/intent_node.py`: `lease_id`, `holder`,
  `intent_topic`, `input_topic` and `rate` parameters, explicit
  best-effort/depth-1 QoS, and no publish without a lease or on a domain other
  than 42. The envelope is a provisional `jcheng.mobile.base_intent.v1` JSON
  on `std_msgs/String` until jcheng-interfaces publishes a `BaseIntent`.
- Tests for the intent core, the launch domain/remap boundary and the node's
  static lease/domain/QoS wiring.
- `LICENSE-REVIEW.md`: records the pre-existing MIT `LICENSE`, its origin and
  the pending organization review. The file is retained, not removed
  retroactively.
- Static hardware bring-up evidence (2026-11-25): `/scan` 10 Hz, `/odom` 10 Hz,
  `/map` 1 Hz, `map -> odom`, Nav2 lifecycle active; no motion.
  `evidence/20261125_static_bringup/README.md`.

### Fixed

- Costmap `width`/`height` are integers; the MPPI controller's `model_dt`
  matches the 10 Hz controller period. Found during the 2026-11-25 static
  bring-up.

## [0.1.0] — 2026-11-24

### Added

- Initial contract-compliant mobile capability skeleton.
- Input: `/scan` (LSLIDAR M10, 10 Hz) from the system/hardware layer.
- Outputs: real RTAB-Map ICP laser odometry, slam_toolbox map, Nav2 MPPI Omni
  chassis intent on `/cmd_vel`, and the `map -> odom -> base_link` TF chain.
- `capability.yaml`: layer L3, `hardware_access: none`, scope `base`, lease
  required, 500 ms deadman.
- Contract and no-hardware tests (10 tests) and the Humble `mobile-ci` build,
  xacro and gate workflow.
- The previous bench bringup (M10 serial driver, vendor mecanum node, open-loop
  odometry) moved to `jcheng-mobile-bench`; it is intentionally not part of
  this repository.
