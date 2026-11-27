"""ROS-free base intent mapping and guard for jcheng-mobile.

The mobile capability does not drive motors and does not publish `/cmd_vel`
to the system/hardware layer. It converts Nav2's bounded velocity into a
``BaseIntent`` envelope that the system layer may accept as *intent* after its
own lease, deadman and limit checks.

`BaseIntent` is a repository-local envelope, schema
``jcheng.mobile.base_intent.v1``. jcheng-interfaces does not publish a
``BaseIntent`` message yet (v0.2.0 is the pin, v0.3.0 is untagged), so the
on-wire form is the JSON object built by :meth:`BaseIntent.to_payload` on a
``std_msgs/String``. It is provisional and must not be treated as an admitted
cross-repository contract until jcheng-interfaces adds one.

Safety properties enforced here:

* a non-empty ``lease_id`` and ``holder`` are required, otherwise no intent;
* ``seq`` must strictly increase;
* ``stamp_ns`` must be fresh (inside the deadman window) and not in the future;
* the velocity envelope is rejected, not clamped, when it exceeds a limit;
* ``duty_limit`` is a normalized cap inside the declared base duty cap;
* the accepted rate is bounded.

Rejection returns ``None`` so a caller does not publish. Rejection never
advances the sequence or rate state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

SCHEMA = "jcheng.mobile.base_intent.v1"

# Mirrors docs/INTEGRATION.md, capability.yaml and config/nav2_params.yaml.
MAX_FORWARD_M_S = 0.25
MAX_LATERAL_M_S = 0.20
MAX_YAW_RAD_S = 0.60
MAX_RATE_HZ = 20.0
DEADMAN_MS = 500
# duty 60 is the declared base hardware cap (about 0.33 m/s). The intent
# carries a normalized cap, never a raw duty; the system layer still clamps.
MAX_DUTY = 0.60

FRAME = "base_link"


@dataclass(frozen=True)
class IntentLimits:
    """Bounds applied by the guard; all values come from the mobile contract."""

    max_forward_m_s: float = MAX_FORWARD_M_S
    max_lateral_m_s: float = MAX_LATERAL_M_S
    max_yaw_rad_s: float = MAX_YAW_RAD_S
    max_rate_hz: float = MAX_RATE_HZ
    deadman_ms: int = DEADMAN_MS
    max_duty: float = MAX_DUTY


@dataclass(frozen=True)
class TwistSample:
    """ROS-free mirror of the velocity fields plus the receipt timestamp.

    ``stamp_ns`` is filled by the ROS node from a monotonic clock at receipt;
    Nav2's ``geometry_msgs/Twist`` has no header, so there is no source stamp.
    """

    linear_x: float = 0.0
    linear_y: float = 0.0
    angular_z: float = 0.0
    stamp_ns: int = 0


@dataclass(frozen=True)
class BaseIntent:
    """Bounded chassis intent, not a motor command."""

    lease_id: str
    holder: str
    command_id: str
    seq: int
    stamp_ns: int
    linear_x: float
    linear_y: float
    angular_z: float
    duty_limit: float
    schema: str = SCHEMA
    frame: str = FRAME

    @property
    def is_stop(self) -> bool:
        return (
            self.linear_x == 0.0
            and self.linear_y == 0.0
            and self.angular_z == 0.0
        )

    def to_payload(self) -> dict[str, object]:
        """Return the provisional JSON envelope (no NaN/inf values)."""
        return {
            "schema": self.schema,
            "lease_id": self.lease_id,
            "holder": self.holder,
            "command_id": self.command_id,
            "seq": self.seq,
            "stamp_ns": self.stamp_ns,
            "frame": self.frame,
            "linear": {"x": self.linear_x, "y": self.linear_y},
            "angular": {"z": self.angular_z},
            "duty_limit": self.duty_limit,
        }


class IntentGuard:
    """Stateful validator that maps one Twist sample to at most one intent.

    A single instance belongs to one lease holder. ``map_twist`` returns
    ``None`` and records the reasons in ``last_rejection`` when the sample must
    not be published.
    """

    def __init__(self, limits: IntentLimits | None = None) -> None:
        self.limits = limits if limits is not None else IntentLimits()
        self.last_seq = -1
        self.last_accepted_ns: int | None = None
        self.last_rejection: tuple[str, ...] = ()

    def _reject(self, reasons: list[str]) -> None:
        self.last_rejection = tuple(reasons)

    def map_twist(
        self,
        twist: TwistSample,
        *,
        lease_id: str,
        holder: str,
        command_id: str,
        seq: int,
        now_ns: int,
        duty_limit: float | None = None,
    ) -> BaseIntent | None:
        """Validate and map; return ``None`` when the sample is rejected."""
        limits = self.limits
        duty = limits.max_duty if duty_limit is None else float(duty_limit)
        problems: list[str] = []

        if not lease_id:
            problems.append("lease_id is required")
        if not holder:
            problems.append("holder is required")
        if not command_id:
            problems.append("command_id is required")

        values = (twist.linear_x, twist.linear_y, twist.angular_z, duty)
        if not all(math.isfinite(value) for value in values):
            problems.append("intent values must be finite")
        else:
            if abs(twist.linear_x) > limits.max_forward_m_s:
                problems.append(
                    f"linear.x exceeds {limits.max_forward_m_s} m/s")
            if abs(twist.linear_y) > limits.max_lateral_m_s:
                problems.append(
                    f"linear.y exceeds {limits.max_lateral_m_s} m/s")
            if abs(twist.angular_z) > limits.max_yaw_rad_s:
                problems.append(
                    f"angular.z exceeds {limits.max_yaw_rad_s} rad/s")
            if not 0.0 < duty <= limits.max_duty:
                problems.append(
                    f"duty_limit must be in (0, {limits.max_duty}]")

        age_ns = now_ns - twist.stamp_ns
        if age_ns < 0:
            problems.append("input timestamp is in the future")
        elif age_ns > limits.deadman_ms * 1_000_000:
            problems.append(
                f"input is older than {limits.deadman_ms} ms")

        if seq <= self.last_seq:
            problems.append(
                f"seq must increase: {seq} <= {self.last_seq}")

        if self.last_accepted_ns is not None:
            minimum_ns = int(1_000_000_000 / limits.max_rate_hz)
            if now_ns - self.last_accepted_ns < minimum_ns:
                problems.append(
                    f"intent exceeds the {limits.max_rate_hz:g} Hz bound")

        if problems:
            self._reject(problems)
            return None

        self.last_rejection = ()
        self.last_seq = seq
        self.last_accepted_ns = now_ns
        return BaseIntent(
            lease_id=lease_id,
            holder=holder,
            command_id=command_id,
            seq=seq,
            stamp_ns=twist.stamp_ns,
            linear_x=float(twist.linear_x),
            linear_y=float(twist.linear_y),
            angular_z=float(twist.angular_z),
            duty_limit=duty,
        )
