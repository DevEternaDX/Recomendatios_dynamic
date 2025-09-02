from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.rules_engine.dsl import RuleModel
from backend.rules_engine.persistence import Rule, RuleMessage, get_session
def _slugify_id(raw: str) -> str:
    # Normaliza IDs: minúsculas, guiones bajos, sin espacios/raros
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    s = (raw or "").strip().lower().replace(" ", "_")
    out = []
    for ch in s:
        out.append(ch if ch in allowed else "_")
    # colapsar múltiples _
    import re as _re
    val = _re.sub(r"_+", "_", "".join(out)).strip("_")
    return val or "rule"


router = APIRouter(prefix="/rules")


class CreateRuleRequest(BaseModel):
    rule: RuleModel


@router.get("")
def list_rules(enabled: bool | None = None, category: str | None = None, q: str | None = None) -> list[dict[str, Any]]:
    with get_session() as session:
        stmt = select(Rule)
        if enabled is not None:
            stmt = stmt.where(Rule.enabled == enabled)
        if category:
            stmt = stmt.where(Rule.category == category)
        rules = session.scalars(stmt.order_by(Rule.priority.desc(), Rule.severity.desc())).all()
        out: list[dict[str, Any]] = []
        for r in rules:
            out.append(
                {
                    "id": r.id,
                    "enabled": r.enabled,
                    "category": r.category,
                    "priority": r.priority,
                    "severity": r.severity,
                    "cooldown_days": r.cooldown_days,
                    "max_per_day": r.max_per_day,
                    "tags": r.tags or [],
                    "locale": r.locale,
                }
            )
        return out


@router.post("")
def create_rule(req: CreateRuleRequest) -> dict[str, Any]:
    rule = req.rule
    # Normalizar ID
    norm_id = _slugify_id(rule.id)
    with get_session() as session:
        if session.get(Rule, norm_id):
            raise HTTPException(status_code=409, detail="Rule id ya existe")
        db_rule = Rule(
            id=norm_id,
            version=rule.version,
            enabled=rule.enabled,
            tenant_id=rule.tenant_id,
            category=rule.category,
            priority=rule.priority,
            severity=rule.severity,
            cooldown_days=rule.cooldown_days,
            max_per_day=rule.max_per_day,
            tags=rule.tags,
            logic=rule.logic.model_dump() if hasattr(rule.logic, "model_dump") else rule.logic,  # type: ignore[arg-type]
            locale=rule.messages.locale,
        )
        session.add(db_rule)
        session.flush()
        for cand in rule.messages.candidates:
            session.add(
                RuleMessage(
                    rule_id=db_rule.id,
                    locale=rule.messages.locale,
                    text=cand.text,
                    weight=cand.weight,
                    active=True,
                )
            )
        session.commit()
        return {"id": db_rule.id}


@router.get("/{rule_id}")
def get_rule(rule_id: str) -> dict[str, Any]:
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        return {
            "id": r.id,
            "version": r.version,
            "enabled": r.enabled,
            "tenant_id": r.tenant_id,
            "category": r.category,
            "priority": r.priority,
            "severity": r.severity,
            "cooldown_days": r.cooldown_days,
            "max_per_day": r.max_per_day,
            "tags": r.tags or [],
            "logic": r.logic,
            "messages": {
                "locale": r.locale,
                "candidates": [
                    {"id": m.id, "text": m.text, "weight": m.weight, "active": m.active}
                    for m in r.messages
                ],
            },
        }


class UpdateRuleRequest(BaseModel):
    enabled: bool | None = None
    tenant_id: str | None = None
    category: str | None = None
    priority: int | None = None
    severity: int | None = None
    cooldown_days: int | None = None
    max_per_day: int | None = None
    tags: list[str] | None = None
    logic: dict | None = None
    messages: dict | None = None


@router.put("/{rule_id}")
def update_rule(rule_id: str, req: UpdateRuleRequest) -> dict[str, Any]:
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        if req.enabled is not None:
            r.enabled = req.enabled
        if req.category is not None:
            r.category = req.category
        if req.tenant_id is not None:
            r.tenant_id = req.tenant_id
        if req.priority is not None:
            r.priority = req.priority
        if req.severity is not None:
            r.severity = req.severity
        if req.cooldown_days is not None:
            r.cooldown_days = req.cooldown_days
        if req.max_per_day is not None:
            r.max_per_day = req.max_per_day
        if req.tags is not None:
            r.tags = req.tags
        if req.logic is not None:
            r.logic = req.logic
        if req.messages is not None:
            # Replace messages for simplicity
            locale = req.messages.get("locale", r.locale)
            r.locale = locale
            # delete existing
            for m in list(r.messages):
                session.delete(m)
            for cand in req.messages.get("candidates", []):
                session.add(
                    RuleMessage(
                        rule_id=r.id,
                        locale=locale,
                        text=cand.get("text", ""),
                        weight=int(cand.get("weight", 1)),
                        active=bool(cand.get("active", True)),
                    )
                )
        session.commit()
        return {"id": r.id}


@router.delete("/{rule_id}")
def delete_rule(rule_id: str) -> dict[str, Any]:
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        # Borrar mensajes primero para evitar problemas de FK en SQLite
        for m in list(r.messages):
            session.delete(m)
        session.delete(r)
        session.commit()
        return {"id": rule_id, "deleted": True}


class EnableRequest(BaseModel):
    enabled: bool


@router.post("/{rule_id}/enable")
def enable_rule(rule_id: str, req: EnableRequest) -> dict[str, Any]:
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        r.enabled = req.enabled
        session.commit()
        return {"id": r.id, "enabled": r.enabled}


class CloneRequest(BaseModel):
    new_id: str


@router.post("/{rule_id}/clone")
def clone_rule(rule_id: str, req: CloneRequest) -> dict[str, Any]:
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        if session.get(Rule, req.new_id):
            raise HTTPException(status_code=409, detail="new_id ya existe")
        clone = Rule(
            id=req.new_id,
            version=r.version,
            enabled=False,
            tenant_id=r.tenant_id,
            category=r.category,
            priority=r.priority,
            severity=r.severity,
            cooldown_days=r.cooldown_days,
            max_per_day=r.max_per_day,
            tags=r.tags,
            logic=r.logic,
            locale=r.locale,
        )
        session.add(clone)
        session.flush()
        for m in r.messages:
            session.add(
                RuleMessage(
                    rule_id=clone.id,
                    locale=m.locale,
                    text=m.text,
                    weight=m.weight,
                    active=m.active,
                )
            )
        session.commit()
        return {"id": clone.id}


