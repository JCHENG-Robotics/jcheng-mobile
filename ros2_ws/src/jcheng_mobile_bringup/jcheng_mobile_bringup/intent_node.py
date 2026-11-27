"""Thin ROS 2 wrapper for the base intent guard.

Subscribes to Nav2's scoped velocity topic (``/jcheng/nav2/cmd_vel`` by
default) and publishes the provisional ``jcheng.mobile.base_intent.v1`` JSON
envelope on ``/jcheng/intent/base`` (``std_msgs/String``). All validation lives
in the ROS-free :mod:`jcheng_mobile_bringup.intent`; this node only holds the
latest sample, runs the timer and serializes the envelope.

Safety rules:

* The node never mints a lease. ``lease_id`` and ``holder`` must be supplied
  after the system layer grants a lease; the defaults are empty and the node
  publishes nothing without them.
* The ROS domain is fixed to 42. The launch file sets ``ROS_DOMAIN_ID`` and
  asserts it; the node also refuses to publish on any other domain. Domain
  isolation is not an authorization or safety mechanism by itself: the system
  layer must still validate every envelope.
* QoS is explicit: best-effort, keep-last depth 1 on both ends. Loss is
  handled by the system's 200 ms freshness window / 300 ms deadman (both
  provisional), not by retransmitting stale velocities.
"""

from __future__ import annotations

import json
import os
import time
import uuid

from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from jcheng_mobile_bringup.intent import IntentGuard, IntentLimits, TwistSample

EXPECTED_ROS_DOMAIN = '42'

# Latest-sample-wins: a dropped frame must not be retransmitted after the
# velocity is stale. The system deadman covers loss.
INPUT_QOS = QoSProfile(
    depth=1,
    history=HistoryPolicy.KEEP_LAST,
    reliability=ReliabilityPolicy.BEST_EFFORT,
)
OUTPUT_QOS = QoSProfile(
    depth=1,
    history=HistoryPolicy.KEEP_LAST,
    reliability=ReliabilityPolicy.BEST_EFFORT,
)


class BaseIntentNode(Node):
    def __init__(self) -> None:
        super().__init__('jcheng_base_intent')

        self.declare_parameter('lease_id', '')
        self.declare_parameter('holder', '')
        self.declare_parameter('intent_topic', '/jcheng/intent/base')
        self.declare_parameter('input_topic', '/jcheng/nav2/cmd_vel')
        self.declare_parameter('rate', 20.0)
        self.declare_parameter('duty_limit', 0.60)
        self.declare_parameter('deadman_ms', 500)

        self.lease_id = str(self.get_parameter('lease_id').value or '')
        self.holder = str(self.get_parameter('holder').value or '')
        self.intent_topic = str(self.get_parameter('intent_topic').value)
        self.input_topic = str(self.get_parameter('input_topic').value)
        self.rate = float(self.get_parameter('rate').value)
        self.duty_limit = float(self.get_parameter('duty_limit').value)
        deadman_ms = int(self.get_parameter('deadman_ms').value)

        limits = IntentLimits(deadman_ms=deadman_ms)
        if not 0.0 < self.rate <= limits.max_rate_hz:
            raise ValueError(
                f'rate must be in (0, {limits.max_rate_hz:g}], got {self.rate}')
        if not 0.0 < self.duty_limit <= limits.max_duty:
            raise ValueError(
                f'duty_limit must be in (0, {limits.max_duty}], '
                f'got {self.duty_limit}')
        if not 0 < deadman_ms <= 500:
            raise ValueError(f'deadman_ms must be in (0, 500], got {deadman_ms}')

        self.limits = IntentLimits(
            max_rate_hz=self.rate,
            deadman_ms=deadman_ms,
        )
        self.guard = IntentGuard(self.limits)
        self._latest = None
        self._rejections = 0
        # command_id = <lease_id>:<process session>:<seq>; the session keeps
        # ids unique across restarts, where seq restarts at 0.
        self._session = uuid.uuid4().hex[:12]

        domain = os.environ.get('ROS_DOMAIN_ID', '')
        self._domain_ok = domain == EXPECTED_ROS_DOMAIN
        if not self._domain_ok:
            self.get_logger().error(
                f'ROS_DOMAIN_ID={domain or "<unset>"}; the mobile intent source '
                f'is fixed to domain {EXPECTED_ROS_DOMAIN} and will not publish. '
                'Start it through mobile_nav.launch.py or export '
                f'ROS_DOMAIN_ID={EXPECTED_ROS_DOMAIN}.')
        if not self.lease_id or not self.holder:
            self.get_logger().error(
                'no lease: lease_id and holder are required. The node will not '
                'publish until the system layer grants a lease and the launch '
                'arguments are set. The node never mints a lease.')

        self.subscription = self.create_subscription(
            Twist, self.input_topic, self._on_twist, INPUT_QOS)
        self.publisher = self.create_publisher(
            String, self.intent_topic, OUTPUT_QOS)
        self.create_timer(1.0 / self.rate, self._tick)

        self.get_logger().info(
            f'base intent: in={self.input_topic} out={self.intent_topic} '
            f'rate={self.rate:g} Hz duty_limit={self.duty_limit} '
            f'lease={self.lease_id or "<none>"} holder={self.holder or "<none>"} '
            f'domain={domain or "<unset>"}')

    def _on_twist(self, msg: Twist) -> None:
        self._latest = TwistSample(
            linear_x=float(msg.linear.x),
            linear_y=float(msg.linear.y),
            angular_z=float(msg.angular.z),
            stamp_ns=time.monotonic_ns(),
        )

    def _tick(self) -> None:
        if not self._domain_ok or not self.lease_id or not self.holder:
            return
        if self._latest is None:
            return

        now_ns = time.monotonic_ns()
        seq = self.guard.last_seq + 1
        intent = self.guard.map_twist(
            self._latest,
            lease_id=self.lease_id,
            holder=self.holder,
            command_id=f'{self.lease_id}:{self._session}:{seq}',
            seq=seq,
            now_ns=now_ns,
            duty_limit=self.duty_limit,
        )
        if intent is None:
            self._rejections += 1
            self.get_logger().warning(
                'intent rejected (%d): %s'
                % (self._rejections, '; '.join(self.guard.last_rejection)),
                throttle_duration_sec=5.0)
            return

        msg = String()
        msg.data = json.dumps(
            intent.to_payload(), allow_nan=False, separators=(',', ':'))
        self.publisher.publish(msg)


def main(args=None) -> None:
    import rclpy

    rclpy.init(args=args)
    node = None
    try:
        node = BaseIntentNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
