# Performance & Sizing

## System requirements

### Minimum

- 16 cores, 32 GB RAM, ~6 TB SSD
- PostgreSQL 17 with PostGIS 3.5

### Recommended

- 64 cores, 512 GB RAM, 4x 4 TB NVMe SSD
- Dedicated PostgreSQL server tuned with the values in [`config/rbt.conf`](../config/rbt.conf)

## Processing times

Numbers below assume the recommended hardware and `PARALLEL_INGESTION=true`.

### Database initialization (one-time)

| Step | Duration |
|---|---|
| OSM import (download + diffs + imposm3) | 24 – 48 h |
| Reference data (FieldMaps / Natural Earth / etc.) | 2 – 4 h |
| GeoNames data | 1 – 2 h |
| Overture buildings (S3 + ogr2ogr) | 4 – 6 h |
| Schema processing (materialized views, indexes) | 6 – 12 min |
| **Total** | **36 – 72 h** |

### Tile generation

| Scope | Duration |
|---|---|
| All layers, all projections | 6 – 12 h |
| Single projection | 2 – 4 h |
| Specific layers only | 30 min – 2 h |
| OSM continuous updates | Real-time |

## Optimization knobs

- **`TILE_TEMP_DIR`** — point at NVMe. Tippecanoe is extremely I/O-bound during zoom-level materialization.
- **`DATABASE_WORK_MEM` / `DATABASE_MAINTENANCE_WORK_MEM`** — set via `ALTER SYSTEM` on the server so index rebuilds use the full budget.
- **`SCRIPT_PARALLEL_INGESTION=true`** — activates full-fan-out ingestion; doubles peak memory but roughly halves wall time.
- **`MAX_PARALLEL_JOBS`** — default of 4 is conservative; bump to core count minus 2 on a dedicated host.

## Built-in performance features

- **Materialized views** for frequently-accessed spatial queries.
- **GIN trigram indexes** for fuzzy text and pattern matching.
- **Spatial GiST indexes** clustered and VACUUM'd at create time.
- **Transaction-scoped tuning** (`SET LOCAL work_mem`, `min_parallel_index_scan_size`) inside schema SQL.
- **Resume semantics** — generators skip already-produced FlatGeoBuf/MBTiles files.
