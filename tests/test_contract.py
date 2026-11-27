"""Contract checks for the jcheng-mobile capability manifest."""

from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = yaml.safe_load((ROOT / "capability.yaml").read_text(encoding="utf-8"))

TOP_LEVEL = {
    "schema_version",
    "name",
    "version",
    "contract",
    "safety",
    "hardware_access",
    "runtime",
}
CONTRACT_HASH = (
    "sha256:0b8d72ced7f54d444d6851d8b99a51a78e2bed3f687324f51a15f76557f24b42"
)


def test_top_level_fields():
    assert set(MANIFEST) == TOP_LEVEL


def test_identity_and_version():
    assert MANIFEST["schema_version"] == 1
    assert MANIFEST["name"] == "jcheng-mobile"
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", MANIFEST["version"])
    assert MANIFEST["version"] == (ROOT / "VERSION").read_text().strip()


def test_contract_hash_and_ranges():
    contract = MANIFEST["contract"]
    assert set(contract) == {"interfaces", "contract_hash", "system_api"}
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", contract["contract_hash"])
    assert contract["contract_hash"] == CONTRACT_HASH
    assert contract["interfaces"]
    assert contract["system_api"]


def test_safety_scope_and_lease():
    safety = MANIFEST["safety"]
    assert safety["class"] == "motion_source"
    assert safety["scopes"] == ["base"]
    assert safety["requires_lease"] is True
    assert 1 <= safety["max_rate_hz"] <= 20
    assert 1 <= safety["deadman_ms"] <= 500


def test_hardware_access_is_none():
    assert MANIFEST["hardware_access"] == "none"


def test_runtime_surface():
    runtime = MANIFEST["runtime"]
    assert runtime["ros_domains"] == [42]
    assert set(runtime["publishes"]) == {
        "/jcheng/intent/base", "/odom", "/map", "/tf"}
    assert set(runtime["subscribes"]) == {"/scan", "/tf"}
    forbidden = (
        "/ros_robot_controller",
        "set_motor_speeds",
        "/dev/",
        "/cmd_vel",
    )
    for topic in runtime["publishes"] + runtime["subscribes"]:
        assert not any(token in topic for token in forbidden)


def test_manifest_does_not_publish_the_raw_velocity_topic():
    text = (ROOT / "capability.yaml").read_text(encoding="utf-8")
    assert "/cmd_vel" not in text
    assert "/jcheng/intent/base" in text


def test_package_matches_manifest():
    package_xml = (
        ROOT / "ros2_ws" / "src" / "jcheng_mobile_bringup" / "package.xml"
    ).read_text(encoding="utf-8")
    assert "<name>jcheng_mobile_bringup</name>" in package_xml
    assert f"<version>{MANIFEST['version']}</version>" in package_xml
