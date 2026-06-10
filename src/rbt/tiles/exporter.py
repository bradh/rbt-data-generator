"""ogr2ogr export helpers."""

from __future__ import annotations

from pathlib import Path

from ..config import Settings
from ..layers import Layer, Projection
from ..logging import get_logger
from ..process import run_with_retry

log = get_logger(__name__)


def export_layer_to_fgb(
    layer: Layer,
    projection: Projection,
    settings: Settings,
    output_dir: Path,
    *,
    dry_run: bool = False,
    log_file: Path | None = None,
) -> Path:
    """Export a Postgres table/view to FlatGeoBuf in the target projection."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fgb = output_dir / f"{layer.output_basename(projection.code)}.fgb"

    if fgb.is_file():
        log.info("ogr2ogr skipped — %s already exists", fgb.name)
        return fgb

    cmd = ["ogr2ogr"]
    if not layer.ogr.spatial_index:
        cmd += ["-lco", "SPATIAL_INDEX=NO"]
    cmd += ["-t_srs", projection.epsg, str(fgb), settings.ogr_pg_connection(), layer.source_table]
    if layer.ogr.skipfailures:
        cmd.append("-skipfailures")

    run_with_retry(
        cmd,
        retries=settings.retry_count,
        delay=settings.retry_delay,
        env=settings.libpq_env(),
        log_file=log_file,
        dry_run=dry_run,
    )
    return fgb
