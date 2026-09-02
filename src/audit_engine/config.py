from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_settings(path: Path | None = None) -> dict:
    target = path or ROOT / "config" / "settings.yml"
    with target.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)

