from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from backend.rules_engine.registry import ALLOWED_AGGREGATORS


ComparisonOp = Literal["<", "<=", ">", ">=", "==", "between", "in"]


class VarRef(BaseModel):
    var: str
    agg: str = Field(description="Aggregator name", default="current")
    scale: Optional[float] = Field(default=None)

    @model_validator(mode="after")
    def validate_agg(self) -> "VarRef":
        if self.agg not in ALLOWED_AGGREGATORS:
            raise ValueError(f"Aggregator '{self.agg}' no permitido")
        return self


class NumericLeaf(BaseModel):
    var: str
    agg: str = "current"
    op: ComparisonOp
    value: Any
    required: bool = False

    @model_validator(mode="after")
    def validate_all(self) -> "NumericLeaf":
        if self.agg not in ALLOWED_AGGREGATORS:
            raise ValueError(f"Aggregator '{self.agg}' no permitido")
        if self.op == "between":
            if not (isinstance(self.value, (list, tuple)) and len(self.value) == 2):
                raise ValueError("'between' requiere [min,max]")
        return self


class RelativeLeaf(BaseModel):
    left: VarRef
    op: ComparisonOp
    right: VarRef
    required: bool = False


class GroupAll(BaseModel):
    all: list["Node"]


class GroupAny(BaseModel):
    any: list["Node"]


class GroupNone(BaseModel):
    none: list["Node"]


Node = GroupAll | GroupAny | GroupNone | NumericLeaf | RelativeLeaf


class MessageCandidate(BaseModel):
    id: Optional[str] = None
    text: str
    weight: int = 1


class RuleMessages(BaseModel):
    locale: str = "es-ES"
    candidates: list[MessageCandidate]


class RuleModel(BaseModel):
    id: str
    version: int = 1
    enabled: bool = True
    tenant_id: str = "default"
    category: str
    priority: int = Field(ge=0, le=100, default=50)
    severity: int = Field(ge=1, le=3, default=1)
    cooldown_days: int = Field(ge=0, le=30, default=0)
    max_per_day: int = Field(ge=0, le=10, default=0)
    tags: list[str] = Field(default_factory=list)
    logic: Node
    messages: RuleMessages


