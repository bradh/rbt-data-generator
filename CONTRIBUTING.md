# Contributing to RBT Vector Tiles

Thanks for your interest in improving the project.

## Development setup

```bash
git clone https://github.com/MJJ203/rbt-data-generator.git
cd rbt-data-generator

# Bash side: lint locally
brew install shellcheck hadolint   # or apt-get install
find setup production tools scripts -name "*.sh" -print0 \
  | xargs -0 shellcheck -x

# SQL side: lint with sqlfluff
pip install sqlfluff
sqlfluff lint setup/data-sources/schemas --dialect postgres

# Python side (experimental CLI)
pip install -e ".[dev]"
pytest
ruff check src tests
```

## Branching and commits

- Branch off `main`; use short, hyphen-separated names (`fix/docker-pg-version`).
- Keep commits focused. Prefer conventional-commit-style prefixes (`fix:`, `feat:`, `docs:`, `refactor:`, `chore:`).
- Run `./tools/smoke-test.sh` (or `docker compose --profile smoke up rbt-smoke`) before opening a PR.

## Pull requests

Before requesting review:

- [ ] `shellcheck` clean on any touched `.sh` file
- [ ] `sqlfluff lint` clean on any touched `.sql` file
- [ ] `hadolint` clean on any touched Dockerfile
- [ ] `pytest` passes if Python code was touched
- [ ] Docs updated (README, `docs/*.md`) for any user-visible change
- [ ] New configuration keys documented in [`docs/configuration.md`](docs/configuration.md)

CI runs the same checks — you can preview them in `.github/workflows/ci.yml`.

## Adding a new tile layer

The recommended path is to edit [`config/layers.yml`](config/layers.yml) — the tile generators are data-driven. Adding a layer means:

1. Add the materialized view / SQL to the appropriate schema file under `setup/data-sources/schemas/`.
2. Add an entry to `config/layers.yml` describing the tippecanoe options and target projections.
3. Run `rbt tiles --layer-type <type> --<your-layer>` or the equivalent Bash command to verify.

## Reporting bugs

Open an issue including:

- Your deployment mode (bare metal vs `docker compose` vs Kubernetes)
- The output of `./tools/validate-environment.sh`
- Relevant lines from `output/logs/`
- Steps to reproduce

## Code of conduct

Be kind, be specific, be technical. Assume good faith.
