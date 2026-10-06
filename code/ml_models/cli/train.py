from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from ml_models.config import MODEL_TYPES, PROFILES
from ml_models.serving.service import ModelService


def _load_records(path: str) -> Any:
    p = Path(path)
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return pd.read_csv(p).to_dict("records")


def _parse_data(items: list) -> Dict[str, Any]:
    datasets: Dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--data expects TYPE=PATH, got '{item}'")
        model_type, path = item.split("=", 1)
        if model_type not in MODEL_TYPES:
            raise SystemExit(f"Unknown model type '{model_type}'")
        datasets[model_type] = _load_records(path)
    return datasets


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description="Train Fluxion ML models")
    parser.add_argument("--model-dir", default="models")
    parser.add_argument("--models", nargs="*", choices=MODEL_TYPES)
    parser.add_argument("--profile", default="full", choices=sorted(PROFILES))
    parser.add_argument("--data", nargs="*", metavar="TYPE=PATH")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    service = ModelService(args.model_dir)
    summary = service.train(
        args.models, args.profile, _parse_data(args.data), args.seed
    )
    service.shutdown()
    json.dump(summary, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
