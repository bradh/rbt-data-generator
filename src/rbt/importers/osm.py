"""OSM importer — currently delegates to setup/data-sources/osm/import-osm-data.sh."""

from __future__ import annotations

from ..bash import delegate
from ..config import Settings


def import_osm(settings: Settings, args: list[str], *, dry_run: bool = False) -> None:
    delegate(
        "setup/data-sources/osm/import-osm-data.sh",
        args,
        settings,
        dry_run=dry_run,
    )


def run_updates(settings: Settings, args: list[str], *, dry_run: bool = False) -> None:
    delegate("production/update-osm.sh", args, settings, dry_run=dry_run)


__all__ = ["import_osm", "run_updates"]
