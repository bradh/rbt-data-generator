# tools/

Ad-hoc utilities and operational aids that run outside the main setup/production pipelines.

| Script | Purpose |
|---|---|
| [validate-environment.sh](validate-environment.sh) | Pre-flight check of env vars, CLI tools, DB connectivity, disk, memory, and project layout. Exits non-zero on any error. |
| [smoke-test.sh](smoke-test.sh) | Fast end-to-end sanity check: environment → extension creation → schema dry run → tile-generation dry run → DB connectivity. |
| [health-check.sh](health-check.sh) | Docker healthcheck script. Returns exit 0 on successful DB round-trip. Honors `DATABASE_HOST`/`DATABASE_PORT`. |
| [overture_building_processing.sh](overture_building_processing.sh) | Downloads Overture buildings from S3 and ingests into PostgreSQL. |
| [duckdb-building-export.sql](duckdb-building-export.sql) | DuckDB alternative for Overture building export, avoiding ogr2ogr for the first pass. |

## Running

All scripts honor `config/rbt.conf` plus legacy `PG_*` env vars:

```bash
./tools/validate-environment.sh
./tools/smoke-test.sh
```

The health check is also exposed via the `HEALTHCHECK` directive in `Dockerfile.production` and via `docker compose exec rbt-tiles ./tools/health-check.sh`.
