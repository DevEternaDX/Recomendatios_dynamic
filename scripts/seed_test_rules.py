from __future__ import annotations

import json
import sys
from typing import Any, Dict
from urllib.request import Request, urlopen


API = "http://127.0.0.1:8000"


def http(method: str, path: str, body: Dict[str, Any] | None = None) -> Any:
    url = f"{API}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers=headers, method=method.upper())
    with urlopen(req) as resp:
        raw = resp.read().decode("utf-8")
        if not raw:
            return None
        return json.loads(raw)


def rule(
    id: str,
    category: str,
    logic: Dict[str, Any],
    priority: int = 50,
    severity: int = 1,
    tenant_id: str = "default",
    text: str | None = None,
) -> Dict[str, Any]:
    return {
        "rule": {
            "id": id,
            "enabled": True,
            "tenant_id": tenant_id,
            "category": category,
            "priority": priority,
            "severity": severity,
            "cooldown_days": 0,
            "max_per_day": 0,
            "tags": [],
            "logic": logic,
            "messages": {
                "locale": "es-ES",
                "candidates": [
                    {
                        "text": text
                        or "Mensaje: {{rule_id}} — {{steps:current:.0f}} pasos, {{sleep_efficiency:current:.2f}} ef.",
                        "weight": 1,
                    }
                ],
            },
        }
    }


def main() -> None:
    # 7 reglas de ejemplo, usando columnas reales de features.py
    payloads = [
        rule(
            id="steps_gt_12000",
            category="actividad",
            logic={"all": [{"var": "steps", "agg": "current", "op": ">", "value": 12000}]},
            priority=70,
            text="Gran día de pasos: {{steps:current:.0f}}"
        ),
        rule(
            id="vigorous_ge_30",
            category="actividad",
            logic={"all": [{"var": "minutes_vigorous", "agg": "current", "op": ">=", "value": 30}]},
            priority=60,
        ),
        rule(
            id="resting_hr_low",
            category="salud",
            logic={"all": [{"var": "resting_heart_rate", "agg": "current", "op": "<", "value": 58}]},
            priority=40,
        ),
        rule(
            id="sleep_deep_between",
            category="sueno",
            logic={"all": [{"var": "deep_sleep_state_minutes", "agg": "current", "op": "between", "value": [60, 120]}]},
            priority=50,
        ),
        rule(
            id="mean7_steps_high",
            category="actividad",
            logic={"all": [{"var": "steps", "agg": "mean_7d", "op": ">", "value": 10000}]},
            priority=55,
        ),
        rule(
            id="zscore_steps_spike",
            category="actividad",
            logic={"all": [{"var": "steps", "agg": "zscore_28d", "op": ">", "value": 1.2}]},
            priority=65,
        ),
        rule(
            id="max_hr_pct_user_max_gt_0_8",
            category="cardio",
            logic={"all": [{"var": "max_hr_pct_user_max", "agg": "current", "op": ">", "value": 0.8}]},
            priority=45,
        ),
    ]

    # Crear reglas
    for p in payloads:
        try:
            resp = http("POST", "/rules", p)
            print("OK:", p["rule"]["id"], resp)
        except Exception as e:
            print("ERR:", p["rule"]["id"], e)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

