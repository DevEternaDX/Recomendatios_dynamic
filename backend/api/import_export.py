from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.rules_engine.persistence import seed_rules_from_json


router = APIRouter(prefix="")


class ImportLegacyYamlRequest(BaseModel):
    yaml_text: str


@router.post("/import/legacy-yaml")
def import_legacy_yaml(_: ImportLegacyYamlRequest) -> dict[str, Any]:
    # Placeholder: implementación real en scripts/migrate_yaml_to_json.py
    raise HTTPException(status_code=501, detail="No implementado aún. Usar scripts/migrate_yaml_to_json.py")


@router.get("/export/json")
def export_rules_json() -> list[dict[str, Any]]:
    # Simple export: lee desde seeds si no hay DB persistida
    try:
        with open("backend/seeds/rules_seed.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


