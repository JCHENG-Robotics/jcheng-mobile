# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- Costmap `width`/`height` are integers; the MPPI controller's `model_dt`
  matches the 10 Hz controller period. Found during the 2026-11-25 static
  bring-up.

### Added

- `LICENSE-REVIEW.md`: records the pre-existing MIT `LICENSE`, its origin and
  the pending organization review. The file is retained, not removed
  retroactively.
- Static hardware bring-up evidence (2026-11-25): `/scan` 10 Hz, `/odom` 10 Hz,
  `/map` 1 Hz, `map -> odom`, Nav2 lifecycle active; no motion.
  `evidence/20261125_static_bringup/README.md`.

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
