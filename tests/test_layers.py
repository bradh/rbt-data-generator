"""Smoke tests for config/layers.yml."""

from __future__ import annotations

from rbt.layers import load_registry


def test_registry_loads() -> None:
    registry = load_registry()
    assert registry.btp_schema_version
    assert "3857" in registry.projections
    assert "3395" in registry.projections
    assert "4326" in registry.projections


def test_known_layer_keys_exist() -> None:
    registry = load_registry()
    for expected in ("building", "highway", "water", "waterway", "landcover"):
        assert expected in registry.layers, f"missing layer {expected!r}"


def test_category_membership() -> None:
    registry = load_registry()
    cultural = registry.categories.get("cultural", {})
    assert "building" in cultural["building"]
    assert "highway" in cultural["transportation"]
    assert "railway" in cultural["transportation"]


def test_filters_reachable() -> None:
    registry = load_registry()
    building = registry.layer("building")
    assert registry.filter_for(building) is not None


def test_physical_layer_projections() -> None:
    registry = load_registry()
    contour = registry.layer("contour")
    assert "4326" not in contour.projections
    assert "3857" in contour.projections


def test_every_layer_has_source_table() -> None:
    registry = load_registry()
    for layer in registry.layers.values():
        assert layer.source_table.startswith("rbt."), (
            f"{layer.key} source_table does not live in rbt schema: {layer.source_table}"
        )
