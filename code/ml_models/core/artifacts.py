from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import torch


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    return str(value)


def save_artifact(
    directory: Path,
    meta: Dict[str, Any],
    state_dict: Optional[Dict[str, Any]] = None,
    objects: Optional[Dict[str, Any]] = None,
) -> Path:
    directory = Path(directory)
    staging = directory.with_name(directory.name + ".tmp")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    if state_dict is not None:
        torch.save(
            {k: v.detach().cpu() for k, v in state_dict.items()},
            staging / "weights.pt",
        )
    for name, obj in (objects or {}).items():
        joblib.dump(obj, staging / f"{name}.joblib")
    (staging / "meta.json").write_text(
        json.dumps(meta, indent=2, default=_json_default), encoding="utf-8"
    )
    if directory.exists():
        shutil.rmtree(directory)
    directory.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, directory)
    return directory


def load_artifact(
    directory: Path,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Dict[str, Any]]:
    directory = Path(directory)
    meta_path = directory / "meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"No artifact found at {directory}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    weights_path = directory / "weights.pt"
    state = (
        torch.load(weights_path, map_location="cpu", weights_only=True)
        if weights_path.is_file()
        else None
    )
    objects = {p.stem: joblib.load(p) for p in sorted(directory.glob("*.joblib"))}
    return meta, state, objects
