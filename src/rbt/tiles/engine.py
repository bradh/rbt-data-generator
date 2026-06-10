"""High-level tile generation engine.

Reads the layer registry at ``config/layers.yml`` and dispatches ogr2ogr +
tippecanoe for every requested layer, projection, and category. This is the
Python replacement for ``production/tile-generation/*/generate-*-3857-3395.sh``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..config import Settings
from ..layers import Layer, LayerRegistry, Projection, load_registry
from ..logging import get_logger
from .btis import apply_btis_metadata
from .exporter import export_layer_to_fgb
from .tile_join import join_layers
from .tippecanoe import run_tippecanoe

log = get_logger(__name__)


@dataclass(slots=True)
class TileJob:
    layer_type: str
    projection: Projection
    layers: list[Layer]
    output_dir: Path
    tile_join: bool = True
    add_btis: bool = True


@dataclass(slots=True)
class TileResult:
    layer: Layer
    projection: Projection
    mbtiles: Path
    fgb: Path
    skipped: bool = False


@dataclass(slots=True)
class TileEngine:
    settings: Settings
    registry: LayerRegistry = field(default_factory=load_registry)
    dry_run: bool = False

    def output_dir_for(self, layer_type: str, projection: Projection) -> Path:
        root = self.settings.tile_cache_dir
        return root / layer_type / projection.code

    def resolve_layers(
        self,
        layer_type: str,
        *,
        categories: list[str] | None = None,
        layer_keys: list[str] | None = None,
    ) -> list[Layer]:
        if not categories and not layer_keys:
            return self.registry.layers_for_type(layer_type)

        selected: dict[str, Layer] = {}
        for cat in categories or []:
            for layer in self.registry.layers_for_category(layer_type, cat):
                selected[layer.key] = layer
        for key in layer_keys or []:
            layer = self.registry.layer(key)
            if layer.layer_type != layer_type:
                log.warning(
                    "layer %r is type %r, skipping under --layer-type %r",
                    key,
                    layer.layer_type,
                    layer_type,
                )
                continue
            selected[layer.key] = layer
        return list(selected.values())

    def generate(self, job: TileJob) -> list[TileResult]:
        results: list[TileResult] = []
        job.output_dir.mkdir(parents=True, exist_ok=True)

        for layer in job.layers:
            if job.projection.code not in layer.projections:
                log.info(
                    "skipping %s: not configured for EPSG:%s",
                    layer.key,
                    job.projection.code,
                )
                continue
            results.append(self._generate_single(layer, job.projection, job.output_dir))

        if job.tile_join and len(results) > 1:
            merged = job.output_dir / f"{job.layer_type}_{job.projection.code}.mbtiles"
            join_layers(
                (r.mbtiles for r in results),
                merged,
                dry_run=self.dry_run,
                log_file=job.output_dir / f"merge_{job.projection.code}.log",
            )
            if job.add_btis and not self.dry_run:
                apply_btis_metadata(
                    merged, job.projection, self.registry.btp_schema_version
                )
        elif job.add_btis and len(results) == 1 and not self.dry_run:
            apply_btis_metadata(
                results[0].mbtiles,
                job.projection,
                self.registry.btp_schema_version,
            )

        return results

    def _generate_single(
        self, layer: Layer, projection: Projection, output_dir: Path
    ) -> TileResult:
        log_file = output_dir / f"{layer.output_basename(projection.code)}.log"
        fgb = export_layer_to_fgb(
            layer,
            projection,
            self.settings,
            output_dir,
            dry_run=self.dry_run,
            log_file=log_file,
        )
        mbtiles = run_tippecanoe(
            layer,
            projection,
            self.settings,
            fgb,
            output_dir,
            self.registry,
            dry_run=self.dry_run,
            log_file=log_file,
        )
        return TileResult(layer=layer, projection=projection, mbtiles=mbtiles, fgb=fgb)


def generate_layer(
    layer_key: str,
    projection_code: str,
    settings: Settings,
    *,
    dry_run: bool = False,
) -> TileResult:
    """Convenience helper for generating a single layer/projection pair."""
    registry = load_registry()
    layer = registry.layer(layer_key)
    projection = registry.projections[projection_code]
    engine = TileEngine(settings=settings, registry=registry, dry_run=dry_run)
    output_dir = engine.output_dir_for(layer.layer_type, projection)
    return engine._generate_single(layer, projection, output_dir)  # noqa: SLF001


__all__ = ["TileEngine", "TileJob", "TileResult", "generate_layer"]
