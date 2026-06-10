# Configuration Reference

RBT Vector Tiles uses a centralized configuration file (`config/rbt.conf`) as the single source of truth. Environment variables override values in the file at process start; legacy `PG_*` names are still accepted.

## Resolution order (highest priority first)

1. Environment variables exported at the shell (or passed via `docker-compose`).
2. Values in [`config/rbt.conf`](../config/rbt.conf).
3. Per-script defaults (usually defensive fallbacks in `scripts/lib/config.sh`).

## Sections

### General processing

| Variable | Default | Purpose |
|---|---|---|
| `MAX_PARALLEL_JOBS` | `4` | Default parallelism for import/generation loops. |
| `RETRY_COUNT` | `3` | Retry attempts for network-bound operations. |
| `RETRY_DELAY` | `30` | Seconds between retries. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARN`, `ERROR`. |

### Tile generation

| Variable | Default | Purpose |
|---|---|---|
| `TILE_CACHE_DIR` | `./output/tiles` | Where MBTiles/PBF tiles are written. |
| `TILE_TEMP_DIR` | `/tmp/tiles` | Scratch space for `tippecanoe -t`. Keep on fast storage. |
| `TILE_MAX_ZOOM` | `13` | Maximum zoom level. |
| `TILE_MIN_ZOOM` | `0` | Minimum zoom level. |
| `SUPPORTED_PROJECTIONS` | `"3857 3395 4326"` | Read-only; edited only when adding support. |
| `DEFAULT_PROJECTION` | `3857` | Projection used when `--projection` not provided. |
| `LAYER_TYPES` | `"physical cultural"` | Read-only. |

### Database connection

| Variable | Legacy | Default | Purpose |
|---|---|---|---|
| `DATABASE_HOST` | `PG_HOST` | `localhost` | PostgreSQL host. |
| `DATABASE_PORT` | `PG_PORT` | `5432` | PostgreSQL port. |
| `DATABASE_NAME` | `PG_DATABASE` | `rbt` | Database name. |
| `DATABASE_USER` | `PG_USR` | `postgres` | Database user. |
| `DATABASE_PASSWORD` | `PG_PASS` | *(unset)* | Database password. |

### Database performance tuning

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_WORK_MEM` | `32GB` | Session `work_mem` (ok to lower for small boxes). |
| `DATABASE_MAINTENANCE_WORK_MEM` | `64GB` | `maintenance_work_mem` during index builds. |
| `DATABASE_MAX_PARALLEL_WORKERS` | `8` | Matches `max_parallel_workers_per_gather`. |
| `DATABASE_EFFECTIVE_CACHE_SIZE` | `192GB` | Planner hint; set to ~75% of system RAM. |
| `DATABASE_MAX_CONNECTIONS` | `100` | Used by docs/ops only; set on the server. |
| `DATABASE_CONNECTION_TIMEOUT` | `300` | Client-side psql timeout seconds. |
| `DATABASE_EXTENSIONS` | `"postgis postgis_raster hstore pg_trgm"` | Created during setup. |
| `DATABASE_SCHEMAS` | `"fieldmap mirta naturalearth ourairports rbt geonames overture"` | Expected schemas after setup. |

### OSM import

| Variable | Default | Purpose |
|---|---|---|
| `OSM_LOG_FILE` | `./setup/data-sources/logs/osm_import.log` | Per-run OSM log. |
| `OSM_DATA_DIR` | `/mnt/data` | Planet PBF + diffs landing zone. |
| `OSM_CONFIG_FILE` | `./setup/data-sources/osm/imposm-config.json` | imposm3 config. |
| `OSM_MAPPING_FILE` | `./setup/data-sources/osm/imposm-mapping.yaml` | imposm3 mapping. |
| `OSM_CACHE_DIR` | `/mnt/cache` | imposm3 cache directory. |
| `OSM_DIFF_DIR` | `/mnt/diff` | Downloaded OSC diffs. |
| `OSM_CONNECTION` | `postgis://postgres:postgres@localhost/rbt?prefix=NONE` | imposm3 connection string. |
| `OSM_SRID` | `3857` | SRID of imposm3-imported tables. |
| `ARIA2C_MAX_DOWNLOADS` | `12` | Concurrent aria2c downloads. |
| `ARIA2C_MAX_CONNECTIONS` | `16` | Connections per aria2c download. |
| `ARIA2C_SPLITS` | `9` | aria2c `--split`. |
| `WGET_PARALLEL_JOBS` | `8` | Fallback parallelism when wget is used. |
| `DIFF_START_SEQ` | `713` | Starting diff sequence for bulk backfill. |
| `DIFF_END_SEQ` | `730` | Ending diff sequence for bulk backfill. |
| `OSM_CLEANUP_ON_EXIT` | `true` | Remove temp files on exit. |
| `OSM_VALIDATE_DOWNLOADS` | `true` | Size-check downloaded files. |
| `OSM_HEALTH_CHECK_PORT` | `8080` | HTTP health port. |

### Shared script settings

| Variable | Default | Purpose |
|---|---|---|
| `SHARED_LOG_DIR` | `./output/logs` | Structured log destination. |
| `SHARED_TEMP_DIR` | `./output/temp` | Shared scratch for importers. |
| `SCRIPT_MAX_PARALLEL_JOBS` | `4` | Importer job pool size. |
| `SCRIPT_RETRY_COUNT` | `3` | Retries for importer sub-steps. |
| `SCRIPT_RETRY_DELAY` | `30` | Retry delay seconds. |
| `SCRIPT_CONNECTION_TIMEOUT` | `300` | psql connection timeout. |
| `SCRIPT_PARALLEL_INGESTION` | `false` | Toggle full parallel ingestion. |
| `SCRIPT_DEBUG` | `false` | Verbose tracing. |
| `SCRIPT_VERBOSE` | `false` | Progress bars + extra logs. |
| `SCRIPT_CLEAN_TEMP_FILES` | `false` | Keep temp files for postmortem. |

### Resource limits

| Variable | Default | Purpose |
|---|---|---|
| `DISK_SPACE_REQUIRED_GB` | `100` | Pre-flight check minimum. |
| `MEMORY_REQUIRED_GB` | `16` | Pre-flight check minimum. |
| `HEALTH_CHECK_PORT` | `8080` | Container health endpoint. |
| `HEALTH_CHECK_INTERVAL` | `30` | Health check seconds. |

## Backward compatibility

The legacy `PG_HOST`/`PG_PORT`/`PG_USR`/`PG_PASS`/`PG_DATABASE` variables remain recognized. `scripts/lib/config.sh` resolves them once at script start so that individual scripts only need to source the shared config helper:

```bash
source "${PROJECT_ROOT}/scripts/lib/config.sh"
rbt_config_load   # sets DATABASE_* + exports PG_* for legacy tools
```

## Verifying your configuration

```bash
./tools/validate-environment.sh
```

See [troubleshooting.md](troubleshooting.md) if validation fails.
