"""ROS-free base intent tests: mapping, limits, freshness, sequence, lease."""

import json
import math

import pytest

from jcheng_mobile_bringup.intent import (
    SCHEMA,
    BaseIntent,
    IntentGuard,
    IntentLimits,
    TwistSample,
)

NOW = 10_000_000_000
PERIOD_NS = 50_000_000


def _twist(**overrides) -> TwistSample:
    base = dict(
        linear_x=0.10,
        linear_y=0.0,
        angular_z=0.0,
        stamp_ns=NOW - 10_000_000,
    )
    base.update(overrides)
    return TwistSample(**base)


def _map(guard: IntentGuard, twist=None, **overrides):
    kwargs = dict(
        lease_id="lease-1",
        holder="nav2",
        command_id="lease-1:0",
        seq=0,
        now_ns=NOW,
        duty_limit=0.60,
    )
    kwargs.update(overrides)
    return guard.map_twist(_twist() if twist is None else twist, **kwargs)


def test_maps_a_bounded_twist():
    guard = IntentGuard()
    intent = _map(guard, _twist(linear_x=0.1, linear_y=-0.05, angular_z=0.2))
    assert isinstance(intent, BaseIntent)
    assert intent.lease_id == "lease-1"
    assert intent.holder == "nav2"
    assert intent.command_id == "lease-1:0"
    assert intent.seq == 0
    assert intent.linear_x == 0.1
    assert intent.linear_y == -0.05
    assert intent.angular_z == 0.2
    assert intent.duty_limit == 0.60
    assert intent.schema == SCHEMA
    assert intent.frame == "base_link"
    assert not intent.is_stop


def test_payload_is_strict_json():
    intent = _map(IntentGuard())
    payload = intent.to_payload()
    assert payload["schema"] == SCHEMA
    assert payload["linear"] == {"x": 0.1, "y": 0.0}
    assert payload["angular"] == {"z": 0.0}
    assert set(payload) == {
        "schema", "lease_id", "holder", "command_id", "seq", "stamp_ns",
        "frame", "linear", "angular", "duty_limit",
    }
    encoded = json.dumps(payload, allow_nan=False, separators=(",", ":"))
    assert json.loads(encoded) == payload


def test_zero_twist_is_an_accepted_stop():
    guard = IntentGuard()
    intent = _map(guard, _twist(linear_x=0.0, linear_y=0.0, angular_z=0.0))
    assert intent is not None
    assert intent.is_stop


@pytest.mark.parametrize("field", ["lease_id", "holder", "command_id"])
def test_identity_fields_are_required(field):
    guard = IntentGuard()
    assert _map(guard, **{field: ""}) is None
    assert guard.last_rejection
    assert guard.last_seq == -1


@pytest.mark.parametrize(
    "field,reason_token,value",
    [
        ("linear_x", "linear.x", 0.26),
        ("linear_y", "linear.y", 0.21),
        ("angular_z", "angular.z", 0.61),
    ],
)
def test_speed_limits_are_rejected_not_clamped(field, reason_token, value):
    guard = IntentGuard()
    assert _map(guard, _twist(**{field: value})) is None
    assert any(reason_token in reason for reason in guard.last_rejection)
    assert guard.last_seq == -1


@pytest.mark.parametrize(
    "field,value",
    [
        ("linear_x", float("nan")),
        ("linear_y", float("inf")),
        ("angular_z", float("-inf")),
    ],
)
def test_non_finite_values_are_rejected(field, value):
    guard = IntentGuard()
    assert _map(guard, _twist(**{field: value})) is None
    assert any("finite" in reason for reason in guard.last_rejection)


def test_stale_input_is_rejected():
    guard = IntentGuard()
    stale = _twist(stamp_ns=NOW - 500_000_001)
    assert _map(guard, stale) is None
    assert any("older than" in reason for reason in guard.last_rejection)


def test_future_input_is_rejected():
    guard = IntentGuard()
    assert _map(guard, _twist(stamp_ns=NOW + 1)) is None
    assert any("future" in reason for reason in guard.last_rejection)


def test_input_at_the_deadman_edge_is_accepted():
    guard = IntentGuard()
    assert _map(guard, _twist(stamp_ns=NOW - 500_000_000)) is not None


def test_sequence_must_strictly_increase():
    guard = IntentGuard()
    assert _map(guard, seq=3) is not None
    assert _map(guard, seq=3, now_ns=NOW + PERIOD_NS) is None
    assert any("seq must increase" in reason for reason in guard.last_rejection)
    assert _map(guard, seq=2, now_ns=NOW + 2 * PERIOD_NS) is None
    assert _map(guard, seq=4, now_ns=NOW + 3 * PERIOD_NS) is not None


def test_rejection_does_not_advance_state():
    guard = IntentGuard()
    assert _map(guard, _twist(linear_x=9.0)) is None
    assert guard.last_seq == -1
    assert guard.last_accepted_ns is None


def test_rate_bound_is_enforced():
    guard = IntentGuard()
    assert _map(guard, seq=0) is not None
    assert _map(guard, seq=1, now_ns=NOW + 10_000_000) is None
    assert any("Hz" in reason for reason in guard.last_rejection)
    assert _map(guard, seq=2, now_ns=NOW + PERIOD_NS) is not None


@pytest.mark.parametrize("duty", [0.0, -0.1, 0.61, math.nan])
def test_duty_limit_is_bounded(duty):
    guard = IntentGuard()
    assert _map(guard, duty_limit=duty) is None
    assert guard.last_rejection


def test_default_duty_limit_comes_from_the_contract():
    guard = IntentGuard()
    intent = _map(guard, duty_limit=None)
    assert intent is not None
    assert intent.duty_limit == IntentLimits().max_duty == 0.60


def test_custom_limits_are_applied():
    guard = IntentGuard(IntentLimits(max_forward_m_s=0.05))
    assert _map(guard, _twist(linear_x=0.10)) is None
    assert any("linear.x" in reason for reason in guard.last_rejection)
