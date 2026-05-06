"""Small helpers for reading project configuration from environment files."""

from pathlib import Path


def read_env_file_value(path: Path, key: str) -> str | None:
    """Read one key from a simple .env file without mutating process env."""
    if not path.exists():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()

        name, separator, value = line.partition("=")
        if separator and name.strip() == key:
            return value.strip().strip("\"'")

    return None
