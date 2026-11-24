# Changelog

## 0.1.0 — 2026-11-24

- Initial contract-compliant mobile capability skeleton.
- Inputs: `/scan` (LSLIDAR M10, 10 Hz) from the system/hardware layer.
- Outputs: real RTAB-Map ICP laser odometry, slam_toolbox map, Nav2 MPPI Omni
  chassis intent on `/cmd_vel`.
- No hardware access, no motor driver and no fake odometry.
- Not hardware-validated: the M10 is not connected, Nav2/RTAB-Map are not
  installed on the robot, and the mount/footprint values are provisional.
