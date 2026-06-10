# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Shared Bash helper `scripts/lib/config.sh` resolving `DATABASE_*` / legacy `PG_*` variables exactly once.
- Declarative layer registry at `config/layers.yml` consumed by both the Bash and Python generators.
- Python CLI package `rbt` under `src/rbt/` (typer-based) exposing `rbt tiles`, `rbt osm`, `rbt setup`, and `rbt generate` commands.
- GitHub Actions CI running `shellcheck`, `hadolint`, `sqlfluff`, and the smoke test against a PostGIS service container.
- MkDocs build workflow that publishes documentation to GitHub Pages.
- Standard project files: `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `.dockerignore`.
- Configuration templates shipped under `config/`: `postgresql.conf`, `tile-server.json`, `prometheus.yml`.
- Documentation split: `docs/configuration.md`, `docs/troubleshooting.md`, `docs/performance.md`.

### Changed
- Pinned PostgreSQL 17 + PostGIS 3.5 across `docker-compose.yml` and both Dockerfiles (previously 15/14/17 mix).
- Rewrote `Dockerfile.production` as multi-stage (shared tippecanoe + imposm builder stages) and removed `Dockerfile.setup` in favor of a single image with a configurable entrypoint.
- `tippecanoe` now built from `felt/tippecanoe` (maintained fork) pinned to a release tag with checksum verification.
- `imposm3` download verified via `sha256sum`.
- Collapsed `process-cultural-schemas.sh` and `process-physical-schemas.sh` into a single data-driven dispatcher.
- `add_btis_metadata` now issues one `sqlite3` transaction instead of seven.
- Health check (`tools/health-check.sh`) honors `DATABASE_HOST`/`DATABASE_PORT` and no longer hardcodes port 5432.
- `TILE_TEMP_DIR` default reconciled across `config/rbt.conf` and scripts (`/tmp/tiles`).
- Logging unified: all shell scripts now source `scripts/lib/logging.sh` instead of reimplementing ANSI color codes.

### Removed
- Deprecated `version: '3.8'` line from `docker-compose.yml`.
- Duplicated per-script logging/config prelude blocks (~400 LOC of bash).
- `Dockerfile.setup` (merged into a single multi-stage Dockerfile).

### Fixed
- `docker-compose.yml` no longer mounts nonexistent files — templates are shipped under `config/`.
- README and compose now agree on PostgreSQL version.
