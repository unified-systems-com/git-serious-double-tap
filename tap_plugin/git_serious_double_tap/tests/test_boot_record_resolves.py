"""The in-package composition record cold-resolves and pins what it says it pins.

Mirrors git-serious's own record test (the two-mains model): the plugin's suite loads the
record against the live registries in plugin CI running on core main. Registry-only: the
resolve preflight mutates nothing. Requires the composition's plugin set installed.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from tap.jsonfiles import load_json_file
from tap_boot.orchestrator import check_profile
from tap_boot.profile import _SCHEMA_PATH, _parse

_PKG_ROOT = Path(__file__).resolve().parent.parent
_RECORD = _PKG_ROOT / "boot" / "git_serious_double_tap.boot.json"
_TOML = _PKG_ROOT / "tap-plugin.toml"
_NAME = "git_serious_double_tap"

# The /double-tap page this plugin seeds (grift/home.grift.json); the record pins it as the root.
_HOME_PAGE_ID = "01a081d1-f90f-76ff-b882-491af67b9d4b"


def _canonical_digest(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-8"))
    canon = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def test_record_ships_and_matches_declared_digest():
    assert _RECORD.is_file(), f"in-package boot record missing at {_RECORD}"
    declared = {
        r["name"]: r["sha256"] for r in tomllib.loads(_TOML.read_text()).get("boot", {}).get("records", [])
    }
    assert _NAME in declared, "tap-plugin.toml must enumerate the record under [[boot.records]]"
    actual = _canonical_digest(_RECORD.read_bytes())
    assert actual == declared[_NAME], (
        f"declared sha256 {declared[_NAME]} != actual {actual} — regenerate with scripts/boot-record-hash --refresh"
    )


def test_record_cold_resolves_schema_coherence_and_collector_keys():
    data = load_json_file(_RECORD, schema=_SCHEMA_PATH)
    profile = _parse(_NAME, data)
    check_profile(profile)  # raises BootError on any unresolvable step


def test_record_composes_git_serious_then_this_plugin_and_pins_the_landing():
    """Install and seed order (git_serious before the instance plugin, whose edges target its
    panels) and the operator's landing decision (req-web-page-landing-15) ride the record."""
    data = json.loads(_RECORD.read_text())
    install = [p["slug"] for p in data["install"]["plugins"]]
    assert install.index("git_serious") < install.index(_NAME)
    seeds = [s["plugin"] for s in data["population"]["steps"] if s["type"] == "seed-plugin"]
    assert seeds.index("git_serious") < seeds.index(_NAME)
    assert data["web"] == {"landing_entity_id": _HOME_PAGE_ID, "landing_slug": "/double-tap"}
    home = json.loads((_PKG_ROOT / "grift" / "home.grift.json").read_text())
    page_ids = {
        n["entity"]["entity_id"]
        for b in home["batches"]
        for n in b["nodes"]
        if n["entity"]["entity_type"] == "page" and n["node"]["slug"] == "/double-tap"
    }
    assert page_ids == {_HOME_PAGE_ID}, "the record must pin the page this plugin seeds at /double-tap"
    self_source = next(p for p in data["install"]["plugins"] if p["slug"] == _NAME)["source"]
    assert self_source["type"] == "git"
    if "DEV-PHASE" in data["description"]:
        assert not self_source["rev"].startswith("v")
    else:
        assert self_source["rev"].startswith("v"), "self-reference must pin an immutable tag"
    assert data.get("required_secrets"), "required_secrets must ride the record"
