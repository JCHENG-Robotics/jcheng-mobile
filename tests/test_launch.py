"""Static checks for the launch authority boundary.

The launch file cannot be executed in the contract CI job (no ROS), so these
checks read the source. They pin the properties that matter: a fixed domain,
an abort on any other domain, Nav2 wrapped in a remap group, both the raw and
smoothed velocity topics redirected, and the intent node launched.
"""

from pathlib import Path
import re

PACKAGE = (
    Path(__file__).resolve().parents[1]
    / "ros2_ws"
    / "src"
    / "jcheng_mobile_bringup"
)
SOURCE = (PACKAGE / "launch" / "mobile_nav.launch.py").read_text(encoding="utf-8")


def test_domain_is_fixed_to_42_and_asserted():
    assert "FIXED_DOMAIN = 42" in SOURCE
    assert "SetEnvironmentVariable('ROS_DOMAIN_ID', str(FIXED_DOMAIN))" in SOURCE
    assert "'domain'," in SOURCE
    assert "default_value=str(FIXED_DOMAIN)" in SOURCE
    assert "OpaqueFunction(function=_require_fixed_domain)" in SOURCE
    assert "domain != FIXED_DOMAIN" in SOURCE
    assert "raise RuntimeError" in SOURCE


def test_nav2_include_is_inside_a_remap_group():
    group = SOURCE.index("nav2 = GroupAction(")
    include = SOURCE.index("navigation_launch.py", group)
    assert "condition=IfCondition(start_nav2)" in SOURCE[group:include]
    assert "IncludeLaunchDescription(" in SOURCE[group:include]


def test_nav2_velocity_topics_are_redirected_before_the_include():
    group = SOURCE.index("nav2 = GroupAction(")
    include = SOURCE.index("navigation_launch.py", group)
    block = re.sub(r"\s+", " ", SOURCE[group:include])
    assert "SetRemap('controller_server:cmd_vel', 'cmd_vel_nav')" in block
    assert "SetRemap('velocity_smoother:cmd_vel', 'cmd_vel_nav')" in block
    assert ("SetRemap('velocity_smoother:cmd_vel_smoothed', "
            "'/jcheng/nav2/cmd_vel')") in block
    assert "SetRemap('/cmd_vel', '/jcheng/nav2/cmd_vel')" in block
    assert "'/jcheng/nav2/cmd_vel'" in SOURCE


def test_intent_node_is_launched_with_required_parameters():
    assert "executable='intent_node'" in SOURCE
    assert "INTENT_TOPIC = '/jcheng/intent/base'" in SOURCE
    assert "'intent_topic': INTENT_TOPIC" in SOURCE
    assert "'input_topic': NAV2_CMD_VEL" in SOURCE
    assert "ParameterValue(lease_id, value_type=str)" in SOURCE
    assert "ParameterValue(holder, value_type=str)" in SOURCE
    assert "'rate': intent_rate" in SOURCE


def test_lease_arguments_default_to_empty():
    assert "'lease_id', default_value=''" in SOURCE
    assert "'holder', default_value=''" in SOURCE


def test_launch_has_no_vendor_topic():
    for token in (
        "/ros_robot_controller",
        "set_motor_speeds",
        "controller/mecanum",
        "MotorSpeedControl",
    ):
        assert token not in SOURCE
