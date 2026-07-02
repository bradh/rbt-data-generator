"""Tests for tippecanoe command construction."""

from __future__ import annotations

from pathlib import Path

from rbt.config import load_settings
from rbt.layers import load_registry
from rbt.tiles.tippecanoe import build_tippecanoe_command


def test_tippecanoe_command_has_required_flags(tmp_path: Path) -> None:
    settings = load_settings()
    registry = load_registry()
    layer = registry.layer("building")

    cmd = build_tippecanoe_command(
        layer=layer,
        settings=settings,
        input_file=tmp_path / "building.fgb",
        output_file=tmp_path / "building.mbtiles",
        registry=registry,
    )

    assert cmd[0] == "tippecanoe"
    assert "-t" in cmd
    assert "-o" in cmd
    assert "-Z" in cmd and str(layer.min_zoom) in cmd
    assert "-z" in cmd and str(layer.max_zoom) in cmd
    assert "-l" in cmd and layer.layer_name in cmd
    # The building layer references the building filter.
    assert "-j" in cmd
    assert str(tmp_path / "building.fgb") in cmd


def test_int_attr_typings() -> None:
    settings = load_settings()
    registry = load_registry()
    layer = registry.layer("airports")

    cmd = build_tippecanoe_command(
        layer=layer,
        settings=settings,
        input_file=Path("in.fgb"),
        output_file=Path("out.mbtiles"),
        registry=registry,
    )
    assert "airport_id:int" in cmd
    assert "-T" in cmd
