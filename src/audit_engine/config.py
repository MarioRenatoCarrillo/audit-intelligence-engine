from __future__ import annotations

import os
from pathlib import Path

import yaml


def resolve_project_root() -> Path:
    """Locate the project resources in local, CI, and container environments."""

    configured_root = os.getenv("AUDIT_ENGINE_ROOT")

    candidates = []

    if configured_root:
        candidates.append(Path(configured_root))

    candidates.extend(
        [
            Path.cwd(),
            Path(__file__).resolve().parents[2],
        ]
    )

    for candidate in candidates:
        resolved = candidate.resolve()

        if (resolved / "config" / "settings.yml").exists():
            return resolved

    raise FileNotFoundError(
        "Could not locate config/settings.yml. "
        "Run the command from the project directory or set "
        "AUDIT_ENGINE_ROOT."
    )


ROOT = resolve_project_root()


def load_settings(path: Path | None = None) -> dict:
    target = path or ROOT / "config" / "settings.yml"

    with target.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)

