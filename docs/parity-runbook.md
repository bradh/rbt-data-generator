# Tile Output Parity Runbook

The Python tile engine (`rbt tiles`, the default) replaces the deprecated bash
generators under `production/tile-generation/`. Before the bash scripts are
deleted, run this one-time comparison **against a populated database** to
confirm the native output matches. CI already verifies command-level parity on
every PR; this runbook verifies the actual tile output, which requires real
data.

!!! note "Why not byte-for-byte hashes?"
    Tippecanoe output is not byte-stable across runs (internal ordering and
    timestamps vary), so this runbook compares *content*: metadata rows,
    per-zoom tile counts, and decoded layer statistics.

## Prerequisites

- A database populated via `rbt setup --all` (or the legacy
  bash setup) with the `rbt.*` views in place.
- `tippecanoe-decode` and `sqlite3` on PATH.
- Roughly 30–60 minutes and a few GB of scratch space.

## 1. Generate both outputs

Pick the representative subset below (covers polygons, points, zoom-variant
blends, and every projection backend):

```bash
# Native engine → output/tiles/...
rbt tiles --layer-type physical --projection 3857 --water --no-tile-join
rbt tiles --layer-type physical --projection 3395 --water --no-tile-join
rbt tiles --layer-type cultural --projection 3857 --building --aeroway --no-tile-join
rbt tiles --layer-type physical --projection 4326 --water

# Deprecated bash path → same layout, separate directory
TILE_CACHE_DIR=./output/tiles-bash rbt tiles --mode bash \
  --layer-type physical --projection 3857 --water --no-tile-join
TILE_CACHE_DIR=./output/tiles-bash rbt tiles --mode bash \
  --layer-type physical --projection 3395 --water --no-tile-join
TILE_CACHE_DIR=./output/tiles-bash rbt tiles --mode bash \
  --layer-type cultural --projection 3857 --building --aeroway --no-tile-join
TILE_CACHE_DIR=./output/tiles-bash rbt tiles --mode bash \
  --layer-type physical --projection 4326 --water
```

## 2. Compare MBTiles (3857 / 3395)

For each pair of `.mbtiles` files (e.g. `water_3857.mbtiles`):

```bash
NATIVE=output/tiles/physical/3857/water_3857.mbtiles
BASH=output/tiles-bash/physical/3857/water_3857.mbtiles

# a) Metadata — should match except generator/timestamps
sqlite3 "$NATIVE" "SELECT name, value FROM metadata WHERE name NOT IN
  ('generator', 'generator_options') ORDER BY name" > /tmp/native-meta.txt
sqlite3 "$BASH"   "SELECT name, value FROM metadata WHERE name NOT IN
  ('generator', 'generator_options') ORDER BY name" > /tmp/bash-meta.txt
diff /tmp/native-meta.txt /tmp/bash-meta.txt

# b) Tile counts per zoom — should match exactly
sqlite3 "$NATIVE" "SELECT zoom_level, COUNT(*) FROM tiles GROUP BY 1 ORDER BY 1" \
  > /tmp/native-counts.txt
sqlite3 "$BASH"   "SELECT zoom_level, COUNT(*) FROM tiles GROUP BY 1 ORDER BY 1" \
  > /tmp/bash-counts.txt
diff /tmp/native-counts.txt /tmp/bash-counts.txt

# c) Layer statistics — layer names, feature counts, attribute lists
tippecanoe-decode --stats "$NATIVE" | python3 -m json.tool > /tmp/native-stats.json
tippecanoe-decode --stats "$BASH"   | python3 -m json.tool > /tmp/bash-stats.json
diff /tmp/native-stats.json /tmp/bash-stats.json
```

**Pass criteria:** (a) and (b) identical; (c) identical except floating-point
jitter in simplification statistics.

## 3. Compare 4326 tile directories

```bash
NATIVE=output/tiles/physical/4326/physical_tiles
BASH=output/tiles-bash/physical/4326/physical_tiles

# Tile counts per zoom level
for d in "$NATIVE" "$BASH"; do
  echo "== $d"; find "$d" -name '*.pbf' | awk -F/ '{print $(NF-2)}' | sort | uniq -c
done

# Metadata (ignore the created timestamp)
python3 - "$NATIVE/metadata.json" "$BASH/metadata.json" <<'EOF'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
for d in (a, b): d.pop("created", None)
print("MATCH" if a == b else "DIFF")
EOF
```

**Pass criteria:** per-zoom `.pbf` counts match; metadata matches modulo the
`created` timestamp. Note the bash cultural 4326 script had a table-selection
bug (undefined `*_TABLES` variables), so cultural 4326 differences where the
*native* output contains **more** layers are expected and correct.

## 4. After the runbook passes

Open a follow-up PR that removes:

- `production/tile-generation/` (all four generators)
- `production/generate-tiles.sh`
- the `--mode` option and `bash.generate_tiles_bash` in `src/rbt/`
- the "deprecated bash path" step in `.github/workflows/ci.yml`
- this runbook's escape-hatch references in the docs

Record the parity results (the diff outputs above) in the PR description.
