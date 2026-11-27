"""Make the ROS package importable for ROS-free unit tests.

The contract job in CI has no ROS installation, so tests may only import
modules that use the standard library (for example ``intent.py``). The ROS
entry point (``intent_node.py``) is checked statically, never imported.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# ament_python layout: the ROS package root holds setup.py, and the importable
# Python package is the nested directory of the same name.
ROS_PACKAGE = ROOT / "ros2_ws" / "src" / "jcheng_mobile_bringup"
if str(ROS_PACKAGE) not in sys.path:
    sys.path.insert(0, str(ROS_PACKAGE))
