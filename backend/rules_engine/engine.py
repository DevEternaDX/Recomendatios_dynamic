from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple
import math
from numpy import bool_ as np_bool
from numpy import floating as np_floating
from numpy import integer as np_integer

from backend.config import settings
from backend.rules_engine.dsl import GroupAll, GroupAny, GroupNone, NumericLeaf, RelativeLeaf, RuleModel, VarRef
from backend.rules_engine.features import build_features, load_base_dataframe
from backend.rules_engine.messages import render_message, select_weighted_random
from backend.rules_engine.persistence import Audit, Rule, RuleMessage, get_enabled_rules, get_session


@dataclass
class RecommendationEvent:
    date: date
    tenant_id: str
    user_id: str
    rule_id: str
    category: str | None
    severity: int
    priority: int
    message_id: int | None
    message_text: str
    locale: str
    why: list[dict[str, Any]]


def compare(op: str, left: Any, right: Any) -> bool:
    if left is None:
        return False
    if op == "<":
        return bool(left < right)
    if op == "<=":
        return bool(left <= right)
    if op == ">":
        return bool(left > right)
    if op == ">=":
        return bool(left >= right)
    if op == "==":
        return bool(left == right)
    if op == "between":
        if right is None or len(right) != 2:
            return False
        low, high = right
        if low is None or high is None:
            return False
        return bool(low <= left <= high)
    if op == "in":
        try:
            return bool(left in right)
        except Exception:  # noqa: BLE001
            return False
    return False


def eval_numeric_leaf(node: NumericLeaf, features: Dict[str, Dict[str, Any]], why: list[dict[str, Any]]) -> bool:
    val = features.get(node.var, {}).get(node.agg)
    outcome = compare(node.op, val, node.value)
    why.append(
        {
            "type": "numeric",
            "var": node.var,
            "agg": node.agg,
            "op": node.op,
            "threshold": node.value,
            "observed": val,
            "result": outcome,
        }
    )
    if val is None and node.required:
        # Abort semantics handled by returning False and tagging required
        return False
    return outcome


def eval_relative_leaf(node: RelativeLeaf, features: Dict[str, Dict[str, Any]], why: list[dict[str, Any]]) -> bool:
    left = features.get(node.left.var, {}).get(node.left.agg)
    right = features.get(node.right.var, {}).get(node.right.agg)
    if right is not None and node.right.scale is not None:
        right = right * node.right.scale
    outcome = compare(node.op, left, right)
    why.append(
        {
            "type": "relative",
            "left": {"var": node.left.var, "agg": node.left.agg, "observed": left},
            "op": node.op,
            "right": {"var": node.right.var, "agg": node.right.agg, "scale": node.right.scale, "observed": right},
            "result": outcome,
        }
    )
    if (left is None or right is None) and node.required:
        return False
    return outcome


def eval_node(node: Any, features: Dict[str, Dict[str, Any]], why: list[dict[str, Any]]) -> bool:
    if isinstance(node, NumericLeaf):
        return eval_numeric_leaf(node, features, why)
    if isinstance(node, RelativeLeaf):
        return eval_relative_leaf(node, features, why)
    if isinstance(node, GroupAll):
        return all(eval_node(child, features, why) for child in node.all)
    if isinstance(node, GroupAny):
        return any(eval_node(child, features, why) for child in node.any)
    if isinstance(node, GroupNone):
        return not any(eval_node(child, features, why) for child in node.none)
    # If it's raw dict (not parsed), try best-effort via RuleModel parsing upstream
    return False


def select_message_for_rule(rule: Rule, features: Dict[str, Dict[str, Any]], user_id: str, day: date) -> Tuple[int | None, str, list[str]]:
    # Construir candidatos activos
    candidates = [
        {"id": m.id, "text": m.text, "weight": m.weight}
        for m in rule.messages
        if m.active
    ]
    if not candidates:
        return None, "", []

    # Anti-repetición: excluir variantes usadas en los últimos N días y preferir no vistas
    recent_ids: set[int] = set()
    try:
        days = max(0, int(settings.anti_repeat_days))
    except Exception:
        days = 0
    if days > 0:
        since = day - timedelta(days=days)
        with get_session() as session:
            rows = (
                session.query(Audit.message_id)
                .filter(
                    Audit.user_id == user_id,
                    Audit.rule_id == rule.id,
                    Audit.fired == True,
                    Audit.date >= since,
                    Audit.message_id.isnot(None),
                )
                .all()
            )
            for (mid,) in rows:
                if isinstance(mid, int):
                    recent_ids.add(mid)

    preferred = [c for c in candidates if c.get("id") not in recent_ids]
    pool = preferred if preferred else candidates

    choice = select_weighted_random(pool)
    if not choice:
        return None, "", []
    text, warnings = render_message(choice.get("text", ""), features)
    return int(choice.get("id")), text, warnings


def resolve_conflicts(events: list[RecommendationEvent]) -> list[RecommendationEvent]:
    # Sort by priority desc, severity desc
    events.sort(key=lambda e: (e.priority, e.severity), reverse=True)
    # Apply per-rule max_per_day first (if any)
    per_rule: dict[str, int] = {}
    tmp: list[RecommendationEvent] = []
    for e in events:
        per_rule[e.rule_id] = per_rule.get(e.rule_id, 0)
        tmp.append(e)

    # Deduplicate per category/day if configured
    max_per_category = settings.max_recs_per_category_per_day
    out: list[RecommendationEvent] = []
    per_category: dict[str | None, int] = {}
    for e in tmp:
        if max_per_category > 0:
            if per_category.get(e.category, 0) >= max_per_category:
                continue
        out.append(e)
        per_category[e.category] = per_category.get(e.category, 0) + 1
    # Global cap
    if settings.max_recs_per_day > 0:
        out = out[: settings.max_recs_per_day]
    return out


def enforce_cooldowns(user_id: str, day: date, events: list[RecommendationEvent]) -> list[RecommendationEvent]:
    # Read audits for prior fires
    kept: list[RecommendationEvent] = []
    with get_session() as session:
        for e in events:
            rule = session.get(Rule, e.rule_id)
            if not rule:
                continue
            if rule.cooldown_days and rule.cooldown_days > 0:
                since = day - timedelta(days=rule.cooldown_days)
                q = (
                    session.query(Audit)
                    .filter(
                        Audit.user_id == user_id,
                        Audit.rule_id == rule.id,
                        Audit.fired == True,
                        Audit.date >= since,
                    )
                )
                if session.query(q.exists()).scalar():
                    continue
            kept.append(e)
    return kept


def evaluate_user(user_id: str, target_day: date, tenant_id: str = "default", debug: bool = False) -> list[RecommendationEvent]:
    df = load_base_dataframe()
    feats = build_features(df, target_day, user_id)
    rules = get_enabled_rules(tenant_id)

    results: list[RecommendationEvent] = []
    per_rule_debug: list[dict[str, Any]] = []

    def _jsonable(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _jsonable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_jsonable(v) for v in obj]
        if isinstance(obj, np_bool):
            return bool(obj)
        if isinstance(obj, np_integer):
            try:
                return int(obj)
            except Exception:
                return None
        if isinstance(obj, np_floating):
            try:
                v = float(obj)
                return v if math.isfinite(v) else None
            except Exception:
                return None
        return obj

    for r in rules:
        # Parse logic via DSL model for safety
        try:
            model = RuleModel(
                id=r.id,
                version=r.version,
                enabled=r.enabled,
                tenant_id=r.tenant_id,
                category=r.category or "",
                priority=r.priority,
                severity=r.severity,
                cooldown_days=r.cooldown_days,
                max_per_day=r.max_per_day,
                tags=r.tags or [],
                logic=r.logic,
                messages={
                    "locale": r.locale,
                    "candidates": [
                        {"id": str(m.id), "text": m.text, "weight": m.weight}
                        for m in r.messages
                        if m.active
                    ],
                },
            )
        except Exception as e:
            if debug:
                per_rule_debug.append({
                    "rule_id": r.id,
                    "fired": False,
                    "priority": r.priority,
                    "severity": r.severity,
                    "why": [{"parse_error": str(e)}],
                })
            # Skip invalid rule
            continue

        why: list[dict[str, Any]] = []
        fired = eval_node(model.logic, feats, why)
        msg_id, msg_text, warn = select_message_for_rule(r, feats, user_id, target_day)
        per_rule_debug.append({
            "rule_id": r.id,
            "fired": bool(fired),
            "priority": r.priority,
            "severity": r.severity,
            "why": _jsonable(why + ([{"warnings": warn}] if warn else [])),
            "values": _jsonable(feats),
        })
        if fired:
            results.append(
                RecommendationEvent(
                    date=target_day,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    rule_id=r.id,
                    category=r.category,
                    severity=r.severity,
                    priority=r.priority,
                    message_id=msg_id,
                    message_text=msg_text,
                    locale=r.locale,
                    why=why + ([{"warnings": warn}] if warn else []),
                )
            )

        # Always write audit (incluye values y why aunque no dispare)
        with get_session() as session:
            session.add(
                Audit(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    date=target_day,
                    rule_id=r.id,
                    fired=fired,
                    discarded_reason=None,
                    why=_jsonable({"conditions": why}),
                    values=_jsonable(feats),
                    message_id=msg_id,
                )
            )
            session.commit()

    # Cooldowns and budgets
    # Cooldowns and budgets
    results = enforce_cooldowns(user_id, target_day, results)
    results = resolve_conflicts(results)

    if debug:
        return results, per_rule_debug
    return results


