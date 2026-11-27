"""Static checks for the thin ROS intent node.

The node is not imported (rclpy and a DDS graph are outside the contract CI
job). The checks pin the lease/domain guards, the explicit QoS choice and the
topic wiring. Behaviour is covered by the ROS-free ``intent.py`` tests.
"""

from pathlib import Path

PACKAGE = (
    Path(__file__).resolve().parents[1]
    / "ros2_ws"
    / "src"
    / "jcheng_mobile_bringup"
)
NODE = (PACKAGE / "jcheng_mobile_bringup" / "intent_node.py").read_text(
    encoding="utf-8"
)
CORE = (PACKAGE / "jcheng_mobile_bringup" / "intent.py").read_text(
    encoding="utf-8"
)


def test_required_parameters_are_declared():
    for name in ("lease_id", "holder", "intent_topic", "input_topic", "rate"):
        assert f"declare_parameter('{name}'" in NODE


def test_node_has_no_default_lease_and_refuses_to_publish():
    assert "declare_parameter('lease_id', '')" in NODE
    assert "declare_parameter('holder', '')" in NODE
    assert "if not self._domain_ok or not self.lease_id or not self.holder:" in NODE
    assert "will not publish" in NODE
    assert "never mints a lease" in NODE


def test_domain_is_asserted_in_the_node_too():
    assert "EXPECTED_ROS_DOMAIN = '42'" in NODE
    assert "os.environ.get('ROS_DOMAIN_ID', '')" in NODE


def test_qos_choice_is_explicit():
    # Both directions are best-effort/depth-1: stale retransmission is worse
    # than a lost sample, and the system deadman covers loss.
    assert "ReliabilityPolicy.BEST_EFFORT" in NODE
    assert "HistoryPolicy.KEEP_LAST" in NODE
    assert "depth=1" in NODE
    assert "OUTPUT_QOS" in NODE
    assert "INPUT_QOS" in NODE


def test_topics_are_wired_through_the_ros_free_core():
    assert "'intent_topic', '/jcheng/intent/base'" in NODE
    assert "'input_topic', '/jcheng/nav2/cmd_vel'" in NODE
    assert "String, self.intent_topic, OUTPUT_QOS" in NODE
    assert "Twist, self.input_topic, self._on_twist, INPUT_QOS" in NODE
    assert "from jcheng_mobile_bringup.intent import" in NODE


def test_command_id_stays_unique_across_restarts():
    # seq restarts at 0 on every process; the session id must keep the
    # command id unique for the system-side deduplication.
    assert "self._session = uuid.uuid4().hex[:12]" in NODE
    assert "command_id=f'{self.lease_id}:{self._session}:{seq}'" in NODE


def test_node_never_publishes_a_raw_velocity_topic():
    assert "'/cmd_vel'" not in NODE
    assert "create_publisher(\n            Twist" not in NODE


def test_core_has_no_ros_import():
    assert "import rclpy" not in CORE
    assert "from geometry_msgs" not in CORE
    assert "from std_msgs" not in CORE


def test_no_vendor_topic_in_the_node_or_core():
    for text in (NODE, CORE):
        for token in (
            "/ros_robot_controller",
            "set_motor_speeds",
            "controller/mecanum",
            "MotorSpeedControl",
        ):
            assert token not in text
