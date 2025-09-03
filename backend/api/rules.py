from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, func

from backend.rules_engine.dsl import RuleModel
from backend.rules_engine.persistence import Rule, RuleMessage, Audit, ChangeLog, get_session
from backend.config import settings
from typing import Optional
import csv
import io
import re

def _slugify_id(raw: str) -> str:
    # Normaliza IDs: minúsculas, guiones bajos, sin espacios/raros
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    s = (raw or "").strip().lower().replace(" ", "_")
    out = []
    for ch in s:
        out.append(ch if ch in allowed else "_")
    # colapsar múltiples _
    val = re.sub(r"_+", "_", "".join(out)).strip("_")
    return val or "rule"


router = APIRouter(prefix="/rules")
def _current_user() -> dict[str, Any]:
    # Placeholder auth: en el futuro usar OAuth/JWT. Si auth_enabled=False, user anónimo
    if not settings.auth_enabled:
        return {"user": "anonymous", "role": "admin"}
    # Extensible: recuperar usuario real de cabeceras/contexto
    return {"user": "unknown", "role": "viewer"}

def _require_role(ctx: dict[str, Any], allowed: tuple[str, ...]) -> None:
    role = str(ctx.get("role", "viewer"))
    if role not in allowed:
        raise HTTPException(status_code=403, detail="Permiso denegado")

def _log_change(session, ctx: dict[str, Any], action: str, entity_type: str, entity_id: str | None, before: Any, after: Any) -> None:
    try:
        session.add(ChangeLog(user=ctx.get("user"), role=ctx.get("role"), action=action, entity_type=entity_type, entity_id=entity_id, before=before, after=after))
        session.flush()
    except Exception:
        pass


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
def create_rule(req: CreateRuleRequest, ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    _require_role(ctx, ("admin", "editor"))
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
        _log_change(session, ctx, "create", "rule", db_rule.id, None, {
            "id": db_rule.id,
            "category": db_rule.category,
        })
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
def update_rule(rule_id: str, req: UpdateRuleRequest, ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    _require_role(ctx, ("admin", "editor"))
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        before = _serialize_rule(r)
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
        _log_change(session, ctx, "update", "rule", r.id, before, _serialize_rule(r))
        session.commit()
        return {"id": r.id}


@router.delete("/all")
def delete_all_rules(ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    """Eliminar TODAS las reglas (solo para testing)."""
    try:
        _require_role(ctx, ("admin",))
        with get_session() as session:
            # Contar reglas antes de eliminar
            total_rules = session.query(Rule).count()
            
            if total_rules == 0:
                return {"deleted": 0, "message": "No hay reglas para eliminar"}
            
            # Eliminar todos los mensajes de reglas primero (por FK constraint)
            deleted_messages = session.query(RuleMessage).delete()
            
            # Eliminar todas las reglas
            deleted_rules = session.query(Rule).delete()
            
            # Log del cambio masivo
            # _log_change(session, ctx, "delete_all", "rules", "ALL", {"total": total_rules}, None)
            
            session.commit()
            
            return {
                "deleted": deleted_rules,
                "deleted_messages": deleted_messages,
                "message": f"Se eliminaron {deleted_rules} reglas y {deleted_messages} mensajes"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    try:
        _require_role(ctx, ("admin",))
        with get_session() as session:
            r = session.get(Rule, rule_id)
            if not r:
                raise HTTPException(status_code=404, detail="Rule no encontrada")
            # before = _serialize_rule(r)
            # Borrar mensajes primero para evitar problemas de FK en SQLite
            for m in list(r.messages):
                session.delete(m)
            session.delete(r)
            # _log_change(session, ctx, "delete", "rule", rule_id, before, None)
            session.commit()
            return {"id": rule_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# --- API granular de variantes ---

class VariantCreateRequest(BaseModel):
    text: str
    weight: int = 1
    active: bool = True
    locale: Optional[str] = None


@router.post("/{rule_id}/variants")
def add_variant(rule_id: str, req: VariantCreateRequest, ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    _require_role(ctx, ("admin", "editor"))
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        locale = req.locale or r.locale
        m = RuleMessage(rule_id=r.id, locale=locale, text=req.text, weight=req.weight, active=req.active)
        session.add(m)
        session.flush()
        _log_change(session, ctx, "create", "variant", rule_id, None, {"message_id": m.id, "text": m.text})
        session.commit()
        return {"message_id": m.id}


class VariantPatchRequest(BaseModel):
    text: Optional[str] = None
    weight: Optional[int] = None
    active: Optional[bool] = None


@router.patch("/{rule_id}/variants/{message_id}")
def patch_variant(rule_id: str, message_id: int, req: VariantPatchRequest, ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    _require_role(ctx, ("admin", "editor"))
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        m = session.get(RuleMessage, message_id)
        if not m or m.rule_id != rule_id:
            raise HTTPException(status_code=404, detail="Variante no encontrada")
        before = {"text": m.text, "weight": m.weight, "active": m.active}
        if req.text is not None:
            m.text = req.text
        if req.weight is not None:
            m.weight = int(req.weight)
        if req.active is not None:
            m.active = bool(req.active)
        _log_change(session, ctx, "update", "variant", rule_id, before, {"text": m.text, "weight": m.weight, "active": m.active})
        session.commit()
        return {"message_id": m.id}


@router.delete("/{rule_id}/variants/{message_id}")
def delete_variant(rule_id: str, message_id: int, ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    _require_role(ctx, ("admin", "editor"))
    with get_session() as session:
        r = session.get(Rule, rule_id)
        if not r:
            raise HTTPException(status_code=404, detail="Rule no encontrada")
        m = session.get(RuleMessage, message_id)
        if not m or m.rule_id != rule_id:
            raise HTTPException(status_code=404, detail="Variante no encontrada")
        before = {"text": m.text, "weight": m.weight, "active": m.active}
        session.delete(m)
        _log_change(session, ctx, "delete", "variant", rule_id, before, None)
        session.commit()
        return {"message_id": message_id, "deleted": True}


# --- Export/Import reglas JSON/YAML y Stats ---

def _serialize_rule(r: Rule) -> dict[str, Any]:
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


@router.get("/export")
def export_rules(format: str = "json") -> Any:
    with get_session() as session:
        rules = session.scalars(select(Rule)).all()
        out = [_serialize_rule(r) for r in rules]
        if format == "json":
            return out
        if format == "yaml":
            try:
                import yaml  # type: ignore
            except Exception:
                raise HTTPException(status_code=500, detail="YAML no disponible: instalar pyyaml")
            return yaml.safe_dump(out, allow_unicode=True)
        raise HTTPException(status_code=400, detail="Formato no soportado")


class ImportRulesRequest(BaseModel):
    data: Any
    format: str = "json"


@router.post("/import")
def import_rules(req: ImportRulesRequest) -> dict[str, Any]:
    # Validación básica y alta usando lógica de create/update
    payload_list: list[dict]
    if req.format == "json":
        if not isinstance(req.data, list):
            raise HTTPException(status_code=400, detail="data debe ser lista")
        payload_list = req.data
    elif req.format == "yaml":
        try:
            import yaml  # type: ignore
        except Exception:
            raise HTTPException(status_code=500, detail="YAML no disponible: instalar pyyaml")
        if isinstance(req.data, str):
            payload_list = yaml.safe_load(req.data)  # type: ignore
        else:
            raise HTTPException(status_code=400, detail="data debe ser string YAML")
        if not isinstance(payload_list, list):
            raise HTTPException(status_code=400, detail="YAML debe contener una lista")
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado")

    created: list[str] = []
    with get_session() as session:
        for item in payload_list:
            try:
                rule_model = RuleModel(**item)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Regla inválida: {e}")
            if session.get(Rule, rule_model.id):
                # actualizar
                r = session.get(Rule, rule_model.id)
                assert r is not None
                r.enabled = rule_model.enabled
                r.tenant_id = rule_model.tenant_id
                r.category = rule_model.category
                r.priority = rule_model.priority
                r.severity = rule_model.severity
                r.cooldown_days = rule_model.cooldown_days
                r.max_per_day = rule_model.max_per_day
                r.tags = rule_model.tags
                r.logic = rule_model.logic.model_dump() if hasattr(rule_model.logic, "model_dump") else rule_model.logic  # type: ignore
                r.locale = rule_model.messages.locale
                # reemplazar mensajes
                for m in list(r.messages):
                    session.delete(m)
                for cand in rule_model.messages.candidates:
                    session.add(
                        RuleMessage(
                            rule_id=r.id,
                            locale=rule_model.messages.locale,
                            text=cand.text,
                            weight=cand.weight,
                            active=True,
                        )
                    )
            else:
                db_rule = Rule(
                    id=rule_model.id,
                    version=rule_model.version,
                    enabled=rule_model.enabled,
                    tenant_id=rule_model.tenant_id,
                    category=rule_model.category,
                    priority=rule_model.priority,
                    severity=rule_model.severity,
                    cooldown_days=rule_model.cooldown_days,
                    max_per_day=rule_model.max_per_day,
                    tags=rule_model.tags,
                    logic=rule_model.logic.model_dump() if hasattr(rule_model.logic, "model_dump") else rule_model.logic,  # type: ignore
                    locale=rule_model.messages.locale,
                )
                session.add(db_rule)
                session.flush()
                for cand in rule_model.messages.candidates:
                    session.add(
                        RuleMessage(
                            rule_id=db_rule.id,
                            locale=rule_model.messages.locale,
                            text=cand.text,
                            weight=cand.weight,
                            active=True,
                        )
                    )
                created.append(db_rule.id)
        session.commit()
    return {"created": created}


class ImportCsvRequest(BaseModel):
    csv_text: str
    tenant_id: str = "default"
    locale: Optional[str] = None
    replace: bool = True
    default_priority: int = 50
    default_severity: int = 1
    enable: bool = False




@router.post("/import_csv")
def import_csv(req: ImportCsvRequest, ctx: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    try:
        _require_role(ctx, ("admin", "editor"))
        # Parse CSV
        f = io.StringIO(req.csv_text)
        sample = req.csv_text[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)

        # Agrupar por base rule id (antes del sufijo _vN)
        grouped: dict[str, list[dict[str, str]]] = {}
        pattern = re.compile(r"^(?P<base>.*?)(?:_v\d+)?$", re.IGNORECASE)
        rows: list[dict[str, str]] = []
        for row in reader:
            mid = (row.get("message_id") or row.get("id") or "").strip()
            cat = (row.get("category") or row.get("categoria") or "").strip()
            text = (row.get("template_text") or row.get("text") or "").strip()
            if not mid or not text:
                continue
            m = pattern.match(mid)
            base = m.group("base") if m else mid
            base_norm = _slugify_id(base)
            rows.append({"base": base_norm, "category": cat, "text": text})
            grouped.setdefault(base_norm, []).append({"category": cat, "text": text})

        created: list[str] = []
        updated: list[str] = []
        if not rows:
            return {"created": created, "updated": updated}

        with get_session() as session:
            for base_id, items in grouped.items():
                r = session.get(Rule, base_id)
                locale = req.locale or settings.default_locale
                if r is None:
                    # Crear regla mínima deshabilitada (o según flag)
                    r = Rule(
                        id=base_id,
                        version=1,
                        enabled=bool(req.enable),
                        tenant_id=req.tenant_id,
                        category=(items[0].get("category") or None),
                        priority=req.default_priority,
                        severity=req.default_severity,
                        cooldown_days=0,
                        max_per_day=0,
                        tags=[],
                        logic={},
                        locale=locale,
                    )
                    session.add(r)
                    session.flush()
                    created.append(base_id)
                    before = None
                else:
                    # before = _serialize_rule(r)
                    # Actualizar metadatos si procede
                    if items[0].get("category"):
                        r.category = items[0].get("category")
                    r.locale = locale

                if req.replace and r.messages:
                    for m in list(r.messages):
                        session.delete(m)
                for it in items:
                    session.add(
                        RuleMessage(
                            rule_id=r.id,
                            locale=locale,
                            text=it["text"],
                            weight=1,
                            active=True,
                        )
                    )
                if base_id not in created:
                    updated.append(base_id)
                # Comentar temporalmente el log de cambios
                # _log_change(session, ctx, "import_csv", "rule", r.id, before, _serialize_rule(r))
            session.commit()
            return {"created": created, "updated": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/{rule_id}/stats")
def rule_stats(rule_id: str) -> dict[str, Any]:
    with get_session() as session:
        total = session.scalar(
            select(func.count(Audit.id)).where(Audit.rule_id == rule_id, Audit.fired == True)
        ) or 0
        per_variant = session.execute(
            select(Audit.message_id, func.count(Audit.id))
            .where(Audit.rule_id == rule_id, Audit.fired == True, Audit.message_id.isnot(None))
            .group_by(Audit.message_id)
        ).all()
        by_message = {int(mid): int(cnt) for (mid, cnt) in per_variant if mid is not None}
        return {"rule_id": rule_id, "fires": int(total), "by_message": by_message}


@router.get("/{rule_id}/changelog")
def rule_changelog(rule_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with get_session() as session:
        rows = session.scalars(
            select(ChangeLog)
            .where(ChangeLog.entity_type == "rule", ChangeLog.entity_id == rule_id)
            .order_by(ChangeLog.id.desc())
            .limit(max(1, min(limit, 200)))
        ).all()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append({
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "user": r.user,
                "role": r.role,
                "action": r.action,
                "before": r.before,
                "after": r.after,
            })
        return out


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


