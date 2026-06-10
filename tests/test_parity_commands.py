"""Command-level parity between the Python tile engine and the deprecated bash
generators.

The deprecated scripts under ``production/tile-generation/`` are the ground
truth until the real-data runbook (``docs/parity-runbook.md``) signs off the
native output. These tests catch *command* drift between ``config/layers.yml``
(what the Python engine dispatches) and the hardcoded tippecanoe invocations in
the bash scripts, without needing tile data:

1. The bash tippecanoe argv is captured by sourcing the generator and stubbing
   ``tippecanoe`` (the generator guards ``main`` behind a BASH_SOURCE check, so
   sourcing only defines its functions). This needs bash but no database.
2. ``production/generate-tiles.sh --dry-run`` is exercised for dispatch parity,
   but only when a database is reachable — the script runs ``psql SELECT 1``
   before honouring ``--dry-run``.
3. A pure-Python golden test pins ``build_tippecanoe_command`` output so drift
   is caught even where bash is unavailable.

Tippecanoe options are compared as *sets*: every option here is an independent
flag (or a ``flag value`` pair normalized to one token), so ordering carries no
meaning and tippecanoe treats any order identically. What matters — and what
these tests assert — is which options are present and with which values.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from rbt.config import Settings
from rbt.layers import LayerRegistry, load_registry
from rbt.tiles.tippecanoe import build_tippecanoe_command

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATE_TILES = REPO_ROOT / "production" / "generate-tiles.sh"
PHYSICAL_GENERATOR = (
    REPO_ROOT / "production" / "tile-generation" / "physical" / "generate-physical-3857-3395.sh"
)

# The deprecated bash path is scheduled for deletion after the parity runbook
# passes (docs/parity-runbook.md §4); once it is gone this module self-retires.
pytestmark = pytest.mark.skipif(
    not GENERATE_TILES.is_file() or shutil.which("bash") is None,
    reason="deprecated bash generators removed or bash unavailable",
)

# Connection env captured at import time: the autouse ``_clean_env_and_caches``
# fixture scrubs PG*/DATABASE_* from os.environ before each test, but the bash
# scripts must see the real credentials (e.g. the CI job env) to reach a DB.
_ORIG_DB_ENV: dict[str, str] = {
    key: value
    for key, value in os.environ.items()
    if key.startswith(("PG", "DATABASE_"))
}


def _settings(**overrides: Any) -> Settings:
    """Settings for a dummy DB: real credentials when present, localhost defaults."""
    return Settings(
        database_host=_ORIG_DB_ENV.get("PG_HOST", "localhost"),
        database_port=int(_ORIG_DB_ENV.get("PG_PORT", "5432")),
        database_name=_ORIG_DB_ENV.get("PG_DATABASE", "rbt"),
        database_user=_ORIG_DB_ENV.get("PG_USR", "postgres"),
        database_password=_ORIG_DB_ENV.get("PG_PASS", ""),
        project_root=REPO_ROOT,
        **overrides,
    )


def _registry() -> LayerRegistry:
    # Explicit path: independent of RBT_PROJECT_ROOT (scrubbed by the autouse
    # fixture) and of any fake_repo used elsewhere in the test session.
    return load_registry(REPO_ROOT / "config" / "layers.yml")


@lru_cache(maxsize=1)
def _database_reachable() -> bool:
    """Mirror generate-tiles.sh's pre-flight: ``psql <conn> -c 'SELECT 1'``."""
    settings = _settings()
    conn = settings.psql_conn_string() + " connect_timeout=5"
    try:
        result = subprocess.run(
            ["psql", conn, "-X", "-c", "SELECT 1"],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


# ---------------------------------------------------------------------------
# tippecanoe argv parsing
# ---------------------------------------------------------------------------

# Short flags that consume the next token. Everything else is a standalone
# option; value-carrying flags that are pure tuning knobs (-M, -r) are folded
# into the option set as a single "flag value" token.
_VALUE_FLAGS = frozenset({"-t", "-o", "-Z", "-z", "-n", "-l", "-s", "-j", "-T", "-M", "-r"})
_OPTION_VALUE_FLAGS = frozenset({"-M", "-r"})


@dataclass(frozen=True)
class TippecanoeInvocation:
    """The comparable surface of one tippecanoe command line."""

    min_zoom: int
    max_zoom: int
    layer_name: str
    display_name: str
    source_srs: str
    filter_expr: Any  # parsed -j JSON, or None
    attr_casts: frozenset[str]  # -T column:type pairs
    options: frozenset[str]
    output_name: str  # basename only — directories are environment-specific
    input_name: str


def parse_tippecanoe_argv(argv: list[str]) -> TippecanoeInvocation:
    assert argv and argv[0] == "tippecanoe", argv
    values: dict[str, str] = {}
    attr_casts: set[str] = set()
    options: set[str] = set()
    positional: list[str] = []

    i = 1
    while i < len(argv):
        token = argv[i]
        if token in _VALUE_FLAGS:
            value = argv[i + 1]
            i += 2
            if token == "-T":
                attr_casts.add(value)
            elif token in _OPTION_VALUE_FLAGS:
                options.add(f"{token} {value}")
            else:
                values[token] = value
        elif token.startswith("-"):
            options.add(token)
            i += 1
        else:
            positional.append(token)
            i += 1

    assert len(positional) == 1, f"expected exactly one input file, got {positional}"
    filter_json = values.get("-j")
    return TippecanoeInvocation(
        # tippecanoe defaults -Z to 0, so an absent -Z and an explicit "-Z 0"
        # are the same command.
        min_zoom=int(values.get("-Z", "0")),
        max_zoom=int(values["-z"]),
        layer_name=values["-l"],
        display_name=values["-n"],
        source_srs=values["-s"],
        filter_expr=json.loads(filter_json) if filter_json else None,
        attr_casts=frozenset(attr_casts),
        options=frozenset(options),
        output_name=Path(values["-o"]).name,
        input_name=Path(positional[0]).name,
    )


# ---------------------------------------------------------------------------
# Bash ground truth capture
# ---------------------------------------------------------------------------

# The generator only runs main() when executed, so sourcing it gives direct
# access to generate_water() with its hardcoded tippecanoe invocation — the
# bash dry-run (generate-tiles.sh) never echoes tippecanoe lines, it only
# echoes the sub-script dispatch. Stubbing tippecanoe captures the exact argv
# the bash path would execute, one token per line (no shell re-quoting).
_CAPTURE_SCRIPT = """\
set -eo pipefail
cd "$RBT_PARITY_REPO_ROOT"
source production/tile-generation/physical/generate-physical-3857-3395.sh
PROJECTION_CODE="$RBT_PARITY_PROJECTION"
configure_projection
OUTPUT_DIR="$RBT_PARITY_WORK_DIR/out"
TEMP_DIR="$RBT_PARITY_WORK_DIR/tmp"
mkdir -p "$OUTPUT_DIR"
# A pre-existing NDJSON short-circuits the ogr2ogr/tippecanoe-json-tool steps,
# so no database or GDAL is needed to reach the tippecanoe call.
touch "$OUTPUT_DIR/water_${PROJECTION_CODE}.ndjson"
tippecanoe() { printf '%s\\n' tippecanoe "$@" > "$RBT_PARITY_CAPTURE_FILE"; }
generate_water
"""


def _capture_bash_water_argv(tmp_path: Path, projection_code: str) -> list[str]:
    capture_file = tmp_path / "tippecanoe-argv.txt"
    env = {
        **os.environ,
        **_settings().subprocess_env(),
        "RBT_PARITY_REPO_ROOT": str(REPO_ROOT),
        "RBT_PARITY_PROJECTION": projection_code,
        "RBT_PARITY_WORK_DIR": str(tmp_path),
        "RBT_PARITY_CAPTURE_FILE": str(capture_file),
    }
    result = subprocess.run(
        ["bash", "-c", _CAPTURE_SCRIPT],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"bash capture failed:\n{result.stdout}\n{result.stderr}"
    assert capture_file.is_file(), "stubbed tippecanoe was never invoked"
    return capture_file.read_text(encoding="utf-8").splitlines()


def _native_water_invocation(tmp_path: Path, projection_code: str) -> TippecanoeInvocation:
    registry = _registry()
    layer = registry.layer("water")
    projection = registry.projections[projection_code]
    basename = layer.output_basename(projection.code)
    cmd = build_tippecanoe_command(
        layer=layer,
        projection=projection,
        settings=_settings(tile_temp_dir=tmp_path / "tmp"),
        input_file=tmp_path / "out" / f"{basename}.fgb",
        output_file=tmp_path / "out" / f"{basename}.mbtiles",
        registry=registry,
    )
    return parse_tippecanoe_argv(cmd)


# ---------------------------------------------------------------------------
# Known divergence between config/layers.yml and the bash ground truth
# ---------------------------------------------------------------------------
# These two sets pin REAL, currently-shipping drift for the water layer; they
# are an exact symmetric difference, not an allowance. If either side changes
# — a flag is added to config/layers.yml or removed from generate_water() —
# the parity test fails and the change must be reconciled deliberately:
# shrink these sets toward empty (the goal before the bash path is deleted,
# see docs/parity-runbook.md) rather than growing them.
#
# Reported drift (bash generate_water() vs the water entry in layers.yml):
#   * bash passes feature/perf tuning the registry lacks:
#       -M 200000, -X, --detect-longitude-wraparound, --reorder, --coalesce
#   * the registry adds an option bash never passed for water:
#       --no-simplification-of-shared-nodes
BASH_ONLY_WATER_OPTIONS = frozenset(
    {
        "-M 200000",
        "-X",
        "--detect-longitude-wraparound",
        "--reorder",
        "--coalesce",
    }
)
NATIVE_ONLY_WATER_OPTIONS = frozenset({"--no-simplification-of-shared-nodes"})


@pytest.mark.parametrize("projection_code", ["3857", "3395"])
def test_water_tippecanoe_invariants_match_bash(tmp_path: Path, projection_code: str) -> None:
    """Zooms, layer naming, source SRS, filter, and -T casts must agree."""
    bash = parse_tippecanoe_argv(_capture_bash_water_argv(tmp_path, projection_code))
    native = _native_water_invocation(tmp_path, projection_code)

    assert (bash.min_zoom, bash.max_zoom) == (native.min_zoom, native.max_zoom)
    assert bash.layer_name == native.layer_name == "water"
    assert bash.display_name == native.display_name == "water"
    # Both backends feed tippecanoe data already reprojected by ogr2ogr and
    # declare the source as EPSG:3857 (see the comment in build_tippecanoe_command).
    assert bash.source_srs == native.source_srs == "EPSG:3857"
    assert "-P" in bash.options and "-P" in native.options
    # -j filters compare as parsed JSON, not as strings (whitespace-insensitive).
    assert bash.filter_expr == native.filter_expr
    assert bash.attr_casts == native.attr_casts
    assert bash.output_name == native.output_name == f"water_{projection_code}.mbtiles"
    # Input basenames intentionally differ (bash: GeoJSON→NDJSON, native:
    # FlatGeoBuf) — that is a pipeline difference covered by the runbook's
    # real-data comparison, not an option drift.


@pytest.mark.parametrize("projection_code", ["3857", "3395"])
def test_water_option_set_drift_is_exactly_the_known_set(
    tmp_path: Path, projection_code: str
) -> None:
    """The option sets differ by EXACTLY the pinned, reported divergence.

    Asserting the symmetric difference (instead of ignoring the known flags)
    keeps the test honest: any new flag on either side, or any reconciliation
    of the existing drift, changes the difference and fails here.
    """
    bash = parse_tippecanoe_argv(_capture_bash_water_argv(tmp_path, projection_code))
    native = _native_water_invocation(tmp_path, projection_code)

    assert bash.options - native.options == BASH_ONLY_WATER_OPTIONS, (
        "bash-only tippecanoe options changed — update config/layers.yml (preferred) "
        "or the pinned drift set, and re-run docs/parity-runbook.md"
    )
    assert native.options - bash.options == NATIVE_ONLY_WATER_OPTIONS, (
        "native-only tippecanoe options changed — update config/layers.yml (preferred) "
        "or the pinned drift set, and re-run docs/parity-runbook.md"
    )


@pytest.mark.skipif(
    not _database_reachable(),
    reason="generate-tiles.sh runs `psql SELECT 1` before honouring --dry-run; "
    "no database reachable with the current PG_* environment",
)
def test_generate_tiles_dry_run_dispatches_water(tmp_path: Path) -> None:
    """`generate-tiles.sh --dry-run` routes --water to the physical 3857 generator."""
    settings = _settings()
    env = {
        **os.environ,
        **settings.subprocess_env(),
        # Keep the run from writing logs/tiles into the working tree.
        "SHARED_LOG_DIR": str(tmp_path / "logs"),
        "TILE_CACHE_DIR": str(tmp_path / "tiles"),
        "TILE_TEMP_DIR": str(tmp_path / "tmp"),
    }
    result = subprocess.run(
        [
            "bash",
            str(GENERATE_TILES),
            "--layer-type",
            "physical",
            "--projection",
            "3857",
            "--water",
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output

    dry_run_lines = [line for line in output.splitlines() if "[DRY RUN] Would execute:" in line]
    assert len(dry_run_lines) == 1, output
    dispatch = dry_run_lines[0]
    assert "generate-physical-3857-3395.sh" in dispatch
    assert "--projection 3857" in dispatch
    assert "--water" in dispatch
    # tile-join/BTIS default on in both the bash wrapper and `rbt tiles`.
    assert "--tile-join" in dispatch
    assert "--add-btis" in dispatch
    assert "generate-cultural" not in output


def test_native_water_command_matches_frozen_golden(tmp_path: Path) -> None:
    """Golden pin of the native water command from the REAL registry.

    Purpose: the bash-vs-native tests above need bash; this pure-Python canary
    runs everywhere and freezes what `rbt tiles --water` would hand to
    tippecanoe for EPSG:3857. If it fails, the water entry in config/layers.yml
    (or build_tippecanoe_command) changed: verify the change is intentional,
    update this golden list, and keep BASH_ONLY/NATIVE_ONLY_WATER_OPTIONS
    above in sync with the new reality.
    """
    registry = _registry()
    layer = registry.layer("water")
    input_file = tmp_path / "water_3857.fgb"
    output_file = tmp_path / "water_3857.mbtiles"
    cmd = build_tippecanoe_command(
        layer=layer,
        projection=registry.projections["3857"],
        settings=_settings(tile_temp_dir=Path("/tmp/tiles")),
        input_file=input_file,
        output_file=output_file,
        registry=registry,
    )

    golden = [
        "tippecanoe",
        "-t",
        "/tmp/tiles",
        "-o",
        str(output_file),
        "-P",
        "-s",
        "EPSG:3857",
        "-Z",
        "0",
        "-z",
        "13",
        "-n",
        "water",
        "-l",
        "water",
        "--no-progress-indicator",
        "--single-precision",
        "--extra-detail=13",
        "--drop-smallest-as-needed",
        "--simplify-only-low-zooms",
        "--no-simplification-of-shared-nodes",
        "--no-tiny-polygon-reduction-at-maximum-zoom",
        str(input_file),
    ]
    assert cmd == golden
