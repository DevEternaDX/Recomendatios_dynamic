from __future__ import annotations

import random
import re
from typing import Any, Dict


PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)(?::([a-zA-Z0-9_]+))?(?::([^}]+))?\s*\}\}")


def select_weighted_random(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    weights = [max(0, int(c.get("weight", 1))) for c in candidates]
    total = sum(weights)
    if total <= 0:
        weights = [1] * len(candidates)
    return random.choices(candidates, weights=weights, k=1)[0]


def render_message(template: str, features: Dict[str, Dict[str, Any]]) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def repl(match: re.Match[str]) -> str:
        var = match.group(1)
        agg = match.group(2) or "current"
        fmt = match.group(3) or ""
        value = None
        try:
            value = features.get(var, {}).get(agg, None)
        except Exception:  # noqa: BLE001
            value = None
        if value is None:
            warnings.append(f"placeholder {var}:{agg} no disponible")
            return ""
        try:
            if fmt:
                return ("{:" + fmt + "}").format(value)
            return str(value)
        except Exception:  # noqa: BLE001
            warnings.append(f"formato inválido en placeholder {var}:{agg}:{fmt}")
            return str(value)

    rendered = PLACEHOLDER_RE.sub(repl, template)
    return rendered, warnings


