from __future__ import annotations

from datetime import date
from typing import Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.rules_engine.engine import evaluate_user
from backend.rules_engine.features import load_base_dataframe, build_features
from backend.rules_engine.persistence import get_session, Audit
from sqlalchemy import select


router = APIRouter()


class SimulateRequest(BaseModel):
    user_id: str
    eval_date: date = Field(description="Fecha de evaluación ISO (YYYY-MM-DD)", alias="date")
    tenant_id: str = "default"
    debug: bool = False

    model_config = {
        "populate_by_name": True,
        "protected_namespaces": (),
    }


@router.post("/simulate")
def simulate(req: SimulateRequest) -> dict:
    res = evaluate_user(user_id=req.user_id, target_day=req.eval_date, tenant_id=req.tenant_id, debug=req.debug)
    # evaluate_user puede devolver (results, per_rule_debug) si debug=True
    if req.debug:
        events, per_rule_debug = res
    else:
        events = res
        per_rule_debug = []
    resp: dict = {
        "count": len(events),
        "events": [
            {
                "date": str(e.date),
                "tenant_id": e.tenant_id,
                "user_id": e.user_id,
                "rule_id": e.rule_id,
                "category": e.category,
                "severity": e.severity,
                "priority": e.priority,
                "message_id": e.message_id,
                "message_text": e.message_text,
                "locale": e.locale,
                "why": e.why,
            }
            for e in events
        ],
    }
    if req.debug:
        # Devolver auditorías últimas por regla para ese usuario/fecha
        # Si evaluate_user devolvió per_rule_debug, úsalo; si no, leer audits de la BD
        if per_rule_debug:
            resp["debug"] = {"audits": per_rule_debug}
        else:
            audits: list[dict] = []
            with get_session() as session:
                rows = session.scalars(
                    select(Audit).where(Audit.user_id == req.user_id, Audit.date == req.eval_date).order_by(Audit.id.desc())
                ).all()
                seen: set[str] = set()
                for a in rows:
                    rid = a.rule_id or ""
                    if rid in seen:
                        continue
                    seen.add(rid)
                    audits.append(
                        {
                            "rule_id": rid,
                            "fired": bool(a.fired),
                            "why": a.why,
                        }
                    )
            resp["debug"] = {"audits": audits}
    return resp


@router.get("/features")
def features(user_id: str, date: date) -> dict:
    df = load_base_dataframe()
    feats = build_features(df, date, user_id)
    return feats


