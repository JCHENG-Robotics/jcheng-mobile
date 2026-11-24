"""Static boundary check: the mobile capability must not touch hardware.

The scan covers the ROS package's code, configs, launch files and URDF. It
deliberately excludes README/docs (which may name the M10) and this test file
(which contains the forbidden tokens for the scan).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ros2_ws" / "src" / "jcheng_mobile_bringup"

TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".xml", ".xacro", ".sh", ".cfg", ".txt"}

FORBIDDEN = (
    "/dev/",
    "serial_port",
    "/ros_robot_controller",
    "set_motor_speeds",
    "open_loop_odom",
    "lslidar_driver",
    "rplidar",
    "socketcan",
    "can0",
    "pigpio",
    "gpio",
    "MotorSpeedControl",
    "MotorsSpeedControl",
    "controller/mecanum",
)


def _package_files():
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        yield path


def test_no_hardware_tokens_in_package():
    problems = []
    for path in _package_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN:
            if token in text:
                problems.append(f"{path.relative_to(ROOT)}: {token}")
    assert not problems, "hardware tokens found:\n" + "\n".join(problems)


def test_bench_and_driver_artifacts_are_absent():
    assert not (PACKAGE / "armpi_mobile_bringup" / "open_loop_odom.py").exists()
    assert not (PACKAGE / "config" / "lslidar_m10.yaml").exists()
    assert not (PACKAGE / "launch" / "bench_nav.launch.py").exists()


def test_launch_has_no_vendor_or_base_driver():
    launch = (PACKAGE / "launch" / "mobile_nav.launch.py").read_text(
        encoding="utf-8"
    )
    for token in ("controller/mecanum", "ros_robot_controller", "lslidar_driver"):
        assert token not in launch
