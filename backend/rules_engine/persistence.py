from __future__ import annotations

import json
from datetime import datetime, date as _Date
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    create_engine,
    select,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, selectinload

from backend.config import settings


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


metadata_obj = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata_obj


engine = create_engine(settings.database_url, echo=False, future=True)


class Variable(Base):
    __tablename__ = "variables"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    label: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    unit: Mapped[Optional[str]]
    type: Mapped[str] = mapped_column(String(20))
    allowed_aggregators: Mapped[dict[str, Any]] = mapped_column(JSON)
    valid_min: Mapped[Optional[float]]
    valid_max: Mapped[Optional[float]]
    missing_policy: Mapped[str] = mapped_column(String(50), default="skip")
    decimals: Mapped[Optional[int]]
    category: Mapped[Optional[str]]
    tenant_id: Mapped[str] = mapped_column(String(50), default="default", index=True)
    examples: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[int] = mapped_column(default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(50), default="default", index=True)
    category: Mapped[Optional[str]]
    priority: Mapped[int] = mapped_column(Integer, default=50)
    severity: Mapped[int] = mapped_column(Integer, default=1)
    cooldown_days: Mapped[int] = mapped_column(Integer, default=0)
    max_per_day: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON)
    logic: Mapped[dict[str, Any]] = mapped_column(JSON)
    locale: Mapped[str] = mapped_column(String(10), default=settings.default_locale)
    created_by: Mapped[Optional[str]]
    updated_by: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    messages: Mapped[list[RuleMessage]] = relationship("RuleMessage", back_populates="rule")


class RuleMessage(Base):
    __tablename__ = "rule_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rules.id", ondelete="CASCADE"))
    locale: Mapped[str] = mapped_column(String(10), default=settings.default_locale, index=True)
    text: Mapped[str]
    weight: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    rule: Mapped[Rule] = relationship("Rule", back_populates="messages")


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(50), default="default", index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    date: Mapped[_Date] = mapped_column(Date)
    rule_id: Mapped[Optional[str]]
    fired: Mapped[bool] = mapped_column(Boolean, default=False)
    discarded_reason: Mapped[Optional[str]]
    why: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    values: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    message_id: Mapped[Optional[int]]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


def create_all_tables() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine, expire_on_commit=False)


def seed_variables_from_json(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return
    if not isinstance(data, list):
        return
    with get_session() as session:
        for item in data:
            key = item.get("key")
            if not key:
                continue
            exists = session.scalar(select(Variable).where(Variable.key == key))
            if exists:
                continue
            session.add(
                Variable(
                    key=key,
                    label=item.get("label"),
                    description=item.get("description"),
                    unit=item.get("unit"),
                    type=item.get("type", "number"),
                    allowed_aggregators=item.get("allowed_aggregators", {}),
                    valid_min=item.get("valid_range", [None, None])[0],
                    valid_max=item.get("valid_range", [None, None])[1],
                    missing_policy=item.get("missing_policy", "skip"),
                    decimals=item.get("decimals"),
                    category=item.get("category"),
                    tenant_id=item.get("tenant_id", "default"),
                    examples={"examples": item.get("examples", [])},
                )
            )
        session.commit()


def seed_rules_from_json(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return
    if not isinstance(data, list):
        return
    with get_session() as session:
        for item in data:
            rid = item.get("id")
            if not rid:
                continue
            exists = session.get(Rule, rid)
            if exists:
                continue
            messages = item.get("messages", {}).get("candidates", [])
            rule = Rule(
                id=rid,
                version=item.get("version", 1),
                enabled=item.get("enabled", True),
                tenant_id=item.get("tenant_id", "default"),
                category=item.get("category"),
                priority=item.get("priority", 50),
                severity=item.get("severity", 1),
                cooldown_days=item.get("cooldown_days", 0),
                max_per_day=item.get("max_per_day", 0),
                tags=item.get("tags", []),
                logic=item.get("logic", {}),
                locale=item.get("messages", {}).get("locale", settings.default_locale),
            )
            session.add(rule)
            session.flush()
            for msg in messages:
                session.add(
                    RuleMessage(
                        rule_id=rule.id,
                        locale=item.get("messages", {}).get("locale", settings.default_locale),
                        text=msg.get("text", ""),
                        weight=msg.get("weight", 1),
                        active=True,
                    )
                )
        session.commit()


def get_enabled_rules(tenant_id: str = "default") -> list[Rule]:
    with get_session() as session:
        rules = session.scalars(
            select(Rule)
            .options(selectinload(Rule.messages))
            .where(Rule.tenant_id == tenant_id, Rule.enabled == True)
            .order_by(Rule.priority.desc(), Rule.severity.desc())
        ).all()
        return list(rules)


