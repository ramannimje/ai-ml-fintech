from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


def save_model(path: Path, model: Any, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    path.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_model(path: Path) -> tuple[Any, dict[str, Any]]:
    model = joblib.load(path)
    metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    return model, metadata
