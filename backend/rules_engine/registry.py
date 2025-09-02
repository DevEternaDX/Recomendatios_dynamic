from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import BaseModel, Field
import os
import csv

ALLOWED_AGGREGATORS = [
    "current",
    "mean_3d",
    "mean_7d",
    "mean_14d",
    "median_14d",
    "delta_pct_3v14",
    "zscore_28d",
]


class VariableDef(BaseModel):
    key: str
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    type: str = Field(pattern=r"^(number|boolean|category)$", default="number")
    allowed_aggregators: list[str] = Field(default_factory=lambda: ALLOWED_AGGREGATORS[:])
    valid_range: tuple[float | None, float | None] | list[float | None] | None = None
    missing_policy: str = Field(pattern=r"^(skip|zero|fallback\(.+\))$", default="skip")
    decimals: int | None = None
    category: str | None = None
    examples: list[Any] | None = None
    tenant_id: str = "default"


def seed_variables_from_json(path: str) -> None:
    # Called from app startup; defers to persistence for DB insert
    from backend.rules_engine.persistence import seed_variables_from_json as _seed

    _seed(path)


def load_registry_seed() -> list[Dict[str, Any]]:
    with open("backend/seeds/variables_seed.json", "r", encoding="utf-8") as f:
        return json.load(f)


def infer_variables_from_csvs() -> list[Dict[str, Any]]:
    """Lee encabezados de CSV reales y propone definitions de variables básicas.

    Se limita a tipos numéricos obvios y evita duplicados.
    """
    out: list[Dict[str, Any]] = []
    seen: set[str] = set()
    candidates: list[tuple[str, str]] = [
        (os.path.join("data", "patient_daily_data.csv"), ";"),
        (os.path.join("data", "patient_sleep_data.csv"), ";"),
    ]
    for path, sep in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=sep)
                headers = next(reader, [])
        except Exception:
            headers = []
        rename = {
            "patient_id": "user_id",
            "calculation_date": "date",
        }
        for raw in headers:
            key = rename.get(raw, raw)
            if key in {"user_id", "date", "start_date_time", "end_date_time", "device_source", "webhook_date_time", "last_webhook_update_date_time"}:
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "key": key,
                    "type": "number",
                    "allowed_aggregators": ALLOWED_AGGREGATORS[:],
                    "tenant_id": "default",
                }
            )
    return out


