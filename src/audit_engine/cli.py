import argparse
import json
from .config import ROOT
from .dashboard import build_dashboard
from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Intelligence Engine")
    parser.add_argument("command", choices=["run", "dashboard", "all"])
    args = parser.parse_args()
    metrics = None
    if args.command in ("run", "all"):
        metrics = run(ROOT)
    if args.command in ("dashboard", "all"):
        build_dashboard(ROOT)
    if metrics:
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

