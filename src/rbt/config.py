"""Typed settings for RBT Vector Tiles.

Reads values from:

1. Environment variables (highest precedence).
2. ``config/rbt.conf`` (Bash-style ``KEY=VALUE`` entries; the ``${X:-Y}``
   fallbacks in that file are collapsed using the current environment when
   the file is parsed).
3. Built-in defaults in this module.

The resulting :class:`Settings` object is immutable; mutate via overrides
passed to :func:`load_settings`.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from .paths import config_dir, project_root

_ASSIGNMENT_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved configuration used throughout the CLI."""

    # Database connection
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "rbt"
    database_user: str = "postgres"
    database_password: str = ""

    # Processing
    max_parallel_jobs: int = 4
    retry_count: int = 3
    retry_delay: int = 30
    log_level: str = "INFO"

    # Tile generation
    tile_cache_dir: Path = Path("./output/tiles")
    tile_temp_dir: Path = Path("/tmp/tiles")
    tile_max_zoom: int = 13
    tile_min_zoom: int = 0
    default_projection: str = "3857"

    # Scripting flags
    debug: bool = False
    verbose: bool = False

    # Paths
    project_root: Path = Path(".")
    config_file: Path = Path("config/rbt.conf")
    shared_log_dir: Path = Path("./output/logs")
    shared_temp_dir: Path = Path("./output/temp")

    def psql_conn_string(self, dbname: str | None = None) -> str:
        db = dbname or self.database_name
        parts = [
            f"host={self.database_host}",
            f"port={self.database_port}",
            f"dbname={db}",
            f"user={self.database_user}",
        ]
        if self.database_password:
            parts.append(f"password={self.database_password}")
        return " ".join(parts)

    def ogr_pg_connection(self, dbname: str | None = None) -> str:
        db = dbname or self.database_name
        parts = [
            f"dbname={db}",
            f"host={self.database_host}",
            f"port={self.database_port}",
            f"user={self.database_user}",
        ]
        if self.database_password:
            parts.append(f"password={self.database_password}")
        return "PG:" + " ".join(parts)

    def libpq_env(self) -> dict[str, str]:
        env = {
            "PGHOST": self.database_host,
            "PGPORT": str(self.database_port),
            "PGDATABASE": self.database_name,
            "PGUSER": self.database_user,
        }
        if self.database_password:
            env["PGPASSWORD"] = self.database_password
        return env

    def legacy_pg_env(self) -> dict[str, str]:
        env = {
            "PG_HOST": self.database_host,
            "PG_PORT": str(self.database_port),
            "PG_DATABASE": self.database_name,
            "PG_USR": self.database_user,
        }
        if self.database_password:
            env["PG_PASS"] = self.database_password
        return env


def _parse_conf_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    match = _ASSIGNMENT_RE.match(stripped)
    if not match:
        return None
    key, raw_value = match.group(1), match.group(2).strip()
    raw_value = raw_value.split("#", 1)[0].rstrip()
    if not raw_value:
        return key, ""
    # Strip surrounding quotes
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in ("'", '"'):
        raw_value = raw_value[1:-1]
    return key, _expand_shell_vars(raw_value)


def _expand_shell_vars(value: str) -> str:
    """Evaluate ``${VAR}``, ``${VAR:-default}``, ``${VAR:=default}`` expressions."""

    def resolve(match: re.Match[str]) -> str:
        inner = match.group(1)
        if ":-" in inner:
            name, default = inner.split(":-", 1)
            return os.environ.get(name) or _expand_shell_vars(default)
        if ":=" in inner:
            name, default = inner.split(":=", 1)
            existing = os.environ.get(name)
            if existing is not None and existing != "":
                return existing
            expanded = _expand_shell_vars(default)
            os.environ[name] = expanded
            return expanded
        return os.environ.get(inner, "")

    return re.sub(r"\$\{([^}]+)\}", resolve, value)


def _read_conf(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_conf_line(line)
        if parsed is None:
            continue
        key, value = parsed
        values[key] = value
        # Make the value visible to subsequent ${...} expansions in the same file.
        os.environ.setdefault(key, value)
    return values


def _coerce_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _coerce_int(value: str | int | None, default: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except ValueError:
        return default


def load_settings(overrides: dict[str, str] | None = None) -> Settings:
    """Build a :class:`Settings` instance from env + config file + overrides."""
    root = project_root()
    conf_path = root / "config" / "rbt.conf"
    conf = _read_conf(conf_path)

    def resolve(*keys: str, default: str = "") -> str:
        for key in keys:
            env_value = os.environ.get(key)
            if env_value not in (None, ""):
                return env_value
            conf_value = conf.get(key)
            if conf_value not in (None, ""):
                return conf_value
        return default

    overrides = overrides or {}
    for key, value in overrides.items():
        os.environ[key] = value

    settings = Settings(
        database_host=resolve("DATABASE_HOST", "PG_HOST", default="localhost"),
        database_port=_coerce_int(resolve("DATABASE_PORT", "PG_PORT"), 5432),
        database_name=resolve("DATABASE_NAME", "PG_DATABASE", default="rbt"),
        database_user=resolve("DATABASE_USER", "PG_USR", default="postgres"),
        database_password=resolve("DATABASE_PASSWORD", "PG_PASS", default=""),
        max_parallel_jobs=_coerce_int(resolve("MAX_PARALLEL_JOBS"), 4),
        retry_count=_coerce_int(resolve("RETRY_COUNT"), 3),
        retry_delay=_coerce_int(resolve("RETRY_DELAY"), 30),
        log_level=resolve("LOG_LEVEL", default="INFO"),
        tile_cache_dir=Path(resolve("TILE_CACHE_DIR", default=str(root / "output" / "tiles"))),
        tile_temp_dir=Path(resolve("TILE_TEMP_DIR", default="/tmp/tiles")),
        tile_max_zoom=_coerce_int(resolve("TILE_MAX_ZOOM"), 13),
        tile_min_zoom=_coerce_int(resolve("TILE_MIN_ZOOM"), 0),
        default_projection=resolve("DEFAULT_PROJECTION", default="3857"),
        debug=_coerce_bool(resolve("DEBUG", "SCRIPT_DEBUG"), False),
        verbose=_coerce_bool(resolve("VERBOSE", "SCRIPT_VERBOSE"), False),
        project_root=root,
        config_file=conf_path,
        shared_log_dir=Path(resolve("SHARED_LOG_DIR", default=str(root / "output" / "logs"))),
        shared_temp_dir=Path(resolve("SHARED_TEMP_DIR", default=str(root / "output" / "temp"))),
    )

    # Export resolved values so shelled-out bash scripts inherit them.
    for key, value in settings.libpq_env().items():
        os.environ.setdefault(key, value)
    for key, value in settings.legacy_pg_env().items():
        os.environ.setdefault(key, value)
    os.environ.setdefault("DATABASE_HOST", settings.database_host)
    os.environ.setdefault("DATABASE_PORT", str(settings.database_port))
    os.environ.setdefault("DATABASE_NAME", settings.database_name)
    os.environ.setdefault("DATABASE_USER", settings.database_user)
    if settings.database_password:
        os.environ.setdefault("DATABASE_PASSWORD", settings.database_password)

    return settings


def shell_env_exports(settings: Settings) -> str:
    """Return a bash-safe ``KEY=value`` string for the database connection."""
    pairs: list[str] = []
    for key, value in {**settings.libpq_env(), **settings.legacy_pg_env()}.items():
        pairs.append(f"{key}={shlex.quote(value)}")
    return " ".join(pairs)


__all__ = ["Settings", "load_settings", "shell_env_exports", "config_dir"]
