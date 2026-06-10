# Troubleshooting

## Database connection fails

```bash
# Check the configuration values being resolved
cat config/rbt.conf | grep -E '^(DATABASE_|PG_)'

# Run the full validator
./tools/validate-environment.sh
```

Common causes:

- `DATABASE_PASSWORD`/`PG_PASS` is unset and the server requires a password.
- The host in `DATABASE_HOST` is unreachable from the container (use the Compose service name, e.g. `postgres`, not `localhost`).
- PostgreSQL client version mismatch — the Dockerfiles install `postgresql-client-17`; older clients may miss features used by PG 17 servers.

## Setup failures (database initialization)

```bash
# Debug mode with verbose logging
DEBUG=true VERBOSE=true ./setup/init-database.sh

# Isolate failing sub-steps
DEBUG=true ./setup/data-sources/reference-data/import-geonames.sh
DEBUG=true ./setup/data-sources/reference-data/import-buildings.sh

# Preserve temp files for inspection
CLEAN_TEMP_FILES=false DEBUG=true ./setup/data-sources/osm/import-osm-data.sh
```

## Tile generation issues

```bash
# Confirm materialized views exist
source config/rbt.conf
psql "host=$DATABASE_HOST dbname=$DATABASE_NAME user=$DATABASE_USER password=$DATABASE_PASSWORD" -c "\dv rbt.*"

# Dry-run a specific layer with verbose logs
./production/generate-tiles.sh --layer-type cultural --building --verbose --dry-run

# Run a single 4326 generator with diagnostic mode
cd production/tile-generation/cultural
DIAGNOSTIC=1 ./generate-cultural-4326.sh --transportation
```

## Missing `postgresql.conf`, `tile-server.json`, or `prometheus.yml`

These files are mounted by `docker-compose.yml` but templated/shipped under [`config/`](../config/). The defaults are safe for single-node operation; tune them before production deployment.

## Tippecanoe or imposm not found

The production Dockerfile builds tippecanoe from the pinned felt/tippecanoe fork and downloads imposm3 0.11.1 with checksum verification. If building locally, ensure:

```bash
./tools/validate-environment.sh
```

reports all required tools.

## Insufficient resources

- Check disk space (`df -h`) and memory (`free -g` / `sysctl hw.memsize`).
- Lower `MAX_PARALLEL_JOBS` in `config/rbt.conf`.
- Set `PARALLEL_INGESTION=false` to reduce peak memory during setup.

## Configuration inspection

```bash
# Verify the resolver loads cleanly
source config/rbt.conf && echo "DATABASE_HOST: $DATABASE_HOST"

# Validate referenced variables exist
grep -E "(DATABASE_|TILE_|OSM_)" config/rbt.conf

# Sanity-check production scripts load the config
./production/generate-tiles.sh --dry-run --verbose
```

## Advanced debugging

```bash
# Schema processing debug mode
DEBUG=true ./setup/data-sources/schemas/physical/process-physical-schemas.sh --water
DEBUG=true ./setup/data-sources/schemas/cultural/process-cultural-schemas.sh --transportation

# Container health monitoring
curl http://localhost:8080/health

# End-to-end performance monitoring
VERBOSE=true PARALLEL_INGESTION=true ./setup/init-database.sh
```
