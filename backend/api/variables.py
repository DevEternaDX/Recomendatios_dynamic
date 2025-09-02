from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from backend.rules_engine.persistence import Variable, get_session


router = APIRouter(prefix="/variables")


class VariableIn(BaseModel):
    key: str
    label: str | None = None
    description: str | None = None
    unit: str | None = None
    type: str = "number"
    allowed_aggregators: list[str] = []
    valid_range: list[float | None] | None = None
    missing_policy: str = "skip"
    decimals: int | None = None
    category: str | None = None
    tenant_id: str = "default"
    examples: list[Any] | None = None


@router.get("")
def list_variables() -> list[dict[str, Any]]:
    with get_session() as session:
        vars = session.scalars(select(Variable).order_by(Variable.key.asc())).all()
        out: list[dict[str, Any]] = []
        for v in vars:
            out.append(
                {
                    "key": v.key,
                    "label": v.label,
                    "description": v.description,
                    "unit": v.unit,
                    "type": v.type,
                    "allowed_aggregators": v.allowed_aggregators,
                    "valid_range": [v.valid_min, v.valid_max],
                    "missing_policy": v.missing_policy,
                    "decimals": v.decimals,
                    "category": v.category,
                    "tenant_id": v.tenant_id,
                    "examples": (v.examples or {}).get("examples"),
                }
            )
        return out


@router.post("")
def upsert_variable(var: VariableIn) -> dict[str, Any]:
    with get_session() as session:
        existing = session.scalar(select(Variable).where(Variable.key == var.key))
        if existing:
            existing.label = var.label
            existing.description = var.description
            existing.unit = var.unit
            existing.type = var.type
            existing.allowed_aggregators = var.allowed_aggregators or []
            if var.valid_range and len(var.valid_range) == 2:
                existing.valid_min = var.valid_range[0]
                existing.valid_max = var.valid_range[1]
            existing.missing_policy = var.missing_policy
            existing.decimals = var.decimals
            existing.category = var.category
            existing.tenant_id = var.tenant_id
            existing.examples = {"examples": var.examples or []}
        else:
            session.add(
                Variable(
                    key=var.key,
                    label=var.label,
                    description=var.description,
                    unit=var.unit,
                    type=var.type,
                    allowed_aggregators=var.allowed_aggregators or [],
                    valid_min=(var.valid_range or [None, None])[0],
                    valid_max=(var.valid_range or [None, None])[1],
                    missing_policy=var.missing_policy,
                    decimals=var.decimals,
                    category=var.category,
                    tenant_id=var.tenant_id,
                    examples={"examples": var.examples or []},
                )
            )
        session.commit()
        return {"key": var.key}


