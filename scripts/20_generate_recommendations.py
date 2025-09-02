from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable

from backend.rules_engine.engine import evaluate_user


def write_recs_today(rows: Iterable[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "date",
        "tenant_id",
        "user_id",
        "rule_id",
        "category",
        "severity",
        "priority",
        "message_id",
        "message_text",
        "locale",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main() -> None:
    tenant_id = "default"
    users = ["demo_user"]
    today = date.today()

    all_rows: list[dict[str, str]] = []
    for uid in users:
        events = evaluate_user(uid, today, tenant_id=tenant_id)
        for e in events:
            all_rows.append(
                {
                    "date": str(e.date),
                    "tenant_id": e.tenant_id,
                    "user_id": e.user_id,
                    "rule_id": e.rule_id,
                    "category": e.category or "",
                    "severity": str(e.severity),
                    "priority": str(e.priority),
                    "message_id": str(e.message_id or ""),
                    "message_text": e.message_text,
                    "locale": e.locale,
                }
            )

    write_recs_today(all_rows, Path("output/recs_today.csv"))


if __name__ == "__main__":
    main()


