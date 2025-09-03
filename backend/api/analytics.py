from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func

from backend.rules_engine.persistence import Audit, Rule, get_session


router = APIRouter(prefix="/analytics")


def _daterange(start: date, end: date) -> List[date]:
    days: List[date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur = cur + timedelta(days=1)
    return days


@router.get("/triggers")
def triggers(
    start: date,
    end: date,
    tenant_id: str = "default",
    rule_ids: str | None = None,
) -> Dict[str, Any]:
    if end < start:
        raise HTTPException(status_code=400, detail="end < start")
    ids: List[str] | None = None
    if rule_ids:
        ids = [s.strip() for s in rule_ids.split(",") if s.strip()]

    days = _daterange(start, end)
    day_keys = [d.isoformat() for d in days]

    with get_session() as session:
        stmt = (
            select(Audit.rule_id, Audit.date, func.count(Audit.id))
            .where(
                Audit.tenant_id == tenant_id,
                Audit.fired == True,  # noqa: E712
                Audit.date >= start,
                Audit.date <= end,
            )
            .group_by(Audit.rule_id, Audit.date)
        )
        if ids:
            stmt = stmt.where(Audit.rule_id.in_(ids))
        rows = session.execute(stmt).all()

        # Collect rule_ids present if not provided
        rule_set: List[str] = ids[:] if ids else []
        if not ids:
            seen: set[str] = set()
            for rid, _day, _cnt in rows:
                if rid and rid not in seen:
                    seen.add(rid)
            rule_set = sorted(seen)

        # Build map: (rule_id -> {date_key -> count})
        by_rule: Dict[str, Dict[str, int]] = {rid: {} for rid in rule_set}
        for rid, d, cnt in rows:
            if rid not in by_rule:
                by_rule[rid] = {}
            by_rule[rid][d.isoformat()] = int(cnt)

        series: List[Dict[str, Any]] = []
        for rid in rule_set:
            points = [{"date": k, "count": int(by_rule.get(rid, {}).get(k, 0))} for k in day_keys]
            series.append({"rule_id": rid, "points": points})

        return {"start": start.isoformat(), "end": end.isoformat(), "series": series}


@router.get("/logs")
def logs(
    start: date | None = None,
    end: date | None = None,
    rule_id: str | None = None,
    user: str | None = None,
    action: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    from backend.rules_engine.persistence import ChangeLog, get_session
    from sqlalchemy import and_
    with get_session() as session:
        stmt = select(ChangeLog).order_by(ChangeLog.id.desc()).limit(max(1, min(limit, 1000)))
        conds = []
        if rule_id:
            conds.append((ChangeLog.entity_type == "rule") & (ChangeLog.entity_id == rule_id))
        if user:
            conds.append(ChangeLog.user == user)
        if action:
            conds.append(ChangeLog.action == action)
        if start:
            conds.append(ChangeLog.created_at >= start)
        if end:
            conds.append(ChangeLog.created_at <= end)
        if conds:
            from functools import reduce
            from operator import and_ as op_and
            stmt = stmt.where(reduce(op_and, conds))
        rows = session.scalars(stmt).all()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append({
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "user": r.user,
                "role": r.role,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "before": r.before,
                "after": r.after,
            })
        return out


