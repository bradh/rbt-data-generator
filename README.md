# RBT Vector Tiles

An open-source system for generating multi-projection Mapbox Vector Tiles from authoritative geospatial data sources (OpenStreetMap, Natural Earth, GeoNames, Overture Maps, FieldMaps).

## Highlights

- **Multi-projection**: Web Mercator (3857), World Mercator (3395), Geographic (4326)
- **Two-phase pipeline**: one-time database initialization + continuous OSM updates and on-demand tile generation
- **Modular**: physical and cultural layers processed independently with granular per-layer flags
- **Container-native**: PostGIS + imposm3 + tippecanoe orchestrated via Docker Compose
- **CI/CD ready**: transaction-based SQL, idempotent importers, resume-safe generators
- **Two interchangeable CLIs**: the original Bash scripts under `setup/` and `production/`, or the newer Python `rbt` CLI

## Quick start

```bash
git clone https://github.com/MJJ203/rbt-data-generator.git
cd rbt-data-generator

# 1. Configure
cp env.example .env        # edit database credentials
vi config/rbt.conf         # or edit the centralized config directly

# 2. Validate environment
./tools/validate-environment.sh

# 3. One-time database initialization (several hours)
./setup/init-database.sh

# 4. Start continuous operations
nohup ./production/update-osm.sh run > osm-updates.log 2>&1 &
./production/generate-tiles.sh --all
```

### Docker Compose

```bash
# One-time setup
docker compose --profile setup up rbt-setup

# Continuous OSM updates + tile generation
docker compose --profile production up -d

# Optional tile server
docker compose --profile production --profile serve up -d
```

### Python CLI (experimental)

```bash
pip install -e .
rbt --help
rbt tiles --layer-type physical --projection 3857
```

See [getting-started.md](docs/getting-started.md) for the guided walkthrough.

## Prerequisites

- PostgreSQL 17 with PostGIS 3.5
- GDAL/OGR 3.11+ with MVT and FlatGeoBuf drivers
- imposm3 0.11.1+
- tippecanoe (felt/tippecanoe fork recommended)
- Minimum 16 GB RAM, 100 GB disk; see [performance.md](docs/performance.md) for full sizing.

## Project layout

```
rbt-data-generator/
├── config/                        # Centralized configuration (rbt.conf)
├── setup/                         # One-time database initialization
│   ├── init-database.sh
│   └── data-sources/
│       ├── osm/                   # imposm3 import
│       ├── reference-data/        # FieldMaps, Natural Earth, GeoNames, Overture
│       └── schemas/               # PL/pgSQL schema processing
├── production/                    # Continuous operations
│   ├── generate-tiles.sh          # Tile generation orchestrator (Bash)
│   ├── update-osm.sh              # OSM continuous updates
│   └── tile-generation/           # Per-projection tile generators
├── scripts/lib/                   # Shared Bash helpers (logging, config)
├── src/rbt/                       # Python CLI (typer-based)
├── tools/                         # Validation, smoke test, health check
├── docs/                          # MkDocs-buildable documentation
└── output/                        # Generated tiles, logs, metrics
```

## Documentation

- [Getting Started](docs/getting-started.md) — end-to-end walkthrough
- [Architecture](docs/architecture.md) — system design and data flow
- [Configuration Reference](docs/configuration.md) — every variable in `rbt.conf`
- [Performance & Sizing](docs/performance.md) — hardware expectations and tuning
- [Troubleshooting](docs/troubleshooting.md) — common issues
- [Physical Layers](docs/physical-layers.md) / [Cultural Layers](docs/cultural-layers.md)
- [Database Initialization](docs/database-initialization.md)
- [OSM Import Pipeline](docs/osm-import.md)
- [DuckDB Buildings Export](docs/duckdb-buildings.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and security disclosures follow [SECURITY.md](SECURITY.md). Release notes live in [CHANGELOG.md](CHANGELOG.md).

## License

GPL-3.0 — see [LICENSE](LICENSE).
