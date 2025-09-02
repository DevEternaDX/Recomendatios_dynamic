from __future__ import annotations

import csv
import os
from datetime import date, timedelta
from typing import Iterable, Tuple


DAILY_HEADERS = [
    "patient_id",
    "date",
    "start_date_time",
    "webhook_date_time",
    "last_webhook_update_date_time",
    "activity_minutes",
    "inactivity_minutes",
    "low_intensity_minutes",
    "moderate_intensity_minutes",
    "continuous_inactive_periods",
    "rest_minutes",
    "vigorous_intensity_minutes",
    "activity_calories",
    "steps",
    "distance_meters",
    "elevation_meters",
    "floors_climbed",
    "heart_rate_average_bpm",
    "max_heart_rate_bpm",
    "min_heart_rate_bpm",
    "resting_heart_rate_bpm",
    "user_max_heart_rate_bpm",
    "heart_rate_variability_rmssd",
    "activity_stress_duration_seconds",
    "avg_stress_level",
    "high_stress_duration_seconds",
    "low_stress_duration_seconds",
    "max_stress_level",
    "medium_stress_duration_seconds",
    "rest_stress_duration_seconds",
    "stress_duration_seconds",
    "stress_samples",
    "device_source",
    "heart_rate_variability_sdnn",
]

SLEEP_HEADERS = [
    "patient_id",
    "calculation_date",
    "start_date_time",
    "end_date_time",
    "heart_rate_average_bpm",
    "max_heart_rate_bpm",
    "min_heart_rate_bpm",
    "resting_heart_rate_bpm",
    "user_max_heart_rate_bpm",
    "rem_sleep_minutes",
    "asleep_state_minutes",
    "deep_sleep_state_minutes",
    "light_sleep_state_minutes",
    "awake_state_minutes",
    "avg_breaths_per_min",
    "max_breaths_per_min",
    "min_breaths_per_min",
    "heart_rate_variability_rmssd",
    "heart_rate_variability_sdnn",
    "device_source",
]


def daterange(start: date, days: int) -> Iterable[date]:
    for i in range(days):
        yield start + timedelta(days=i)


def make_patient_rows(uid: str, start: date, days: int, pattern: str) -> Tuple[list[list], list[list]]:
    daily_rows: list[list] = []
    sleep_rows: list[list] = []

    for d in daterange(start, days):
        # Valores base
        steps = 8000
        vigorous = 10
        rhr = 62
        max_hr = 150
        user_max = 190
        deep = 70

        # Ajustes según patrón para disparar reglas específicas
        if pattern == "high_steps":
            steps = 13000 if (d - start).days % 2 == 0 else 11000
            vigorous = 35
        elif pattern == "low_rhr":
            rhr = 56
        elif pattern == "deep_sleep_ok":
            deep = 90
        elif pattern == "spike_steps":
            steps = 5000 if (d - start).days < days - 3 else 16000
        elif pattern == "mean7_high":
            steps = 12000
        elif pattern == "max_hr_pct_high":
            max_hr = 170
            user_max = 200
        elif pattern == "vigorous_ok":
            vigorous = 45

        daily_rows.append([
            uid,
            d.isoformat(),
            f"{d.isoformat()} 00:00:01",
            f"{d.isoformat()} 00:00:01",
            f"{d.isoformat()} 00:00:01",
            "", "", "", "", "", 1440, "", "", steps, 0, "", "", 80, max_hr, 50, rhr, user_max,
            "", "", "", "", "", "", "", "", "", "", "Fitbit", 40,
        ])

        sleep_rows.append([
            uid,
            d.isoformat(),
            f"{d.isoformat()} 22:00:00",
            f"{(d + timedelta(days=1)).isoformat()} 06:00:00",
            55, max_hr - 90, 45, rhr, user_max, 100, 420, deep, 300, 10, 12.0, 18.0, 10.0, "", 35, "unknown",
        ])

    return daily_rows, sleep_rows


def write_csv(path: str, headers: list[str], rows: list[list]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(headers)
        w.writerows(rows)


def main() -> None:
    start = date.today() - timedelta(days=30)
    days = 21

    patients = [
        ("p_high_steps", "high_steps"),
        ("p_vigorous", "vigorous_ok"),
        ("p_low_rhr", "low_rhr"),
        ("p_deep_ok", "deep_sleep_ok"),
        ("p_spike", "spike_steps"),
        ("p_mean7", "mean7_high"),
        ("p_maxhrpct", "max_hr_pct_high"),
    ]

    daily_rows_all: list[list] = []
    sleep_rows_all: list[list] = []

    for uid, pattern in patients:
        drows, srows = make_patient_rows(uid, start, days, pattern)
        daily_rows_all.extend(drows)
        sleep_rows_all.extend(srows)

    write_csv("data/test_patient_daily_data.csv", DAILY_HEADERS, daily_rows_all)
    write_csv("data/test_patient_sleep_data.csv", SLEEP_HEADERS, sleep_rows_all)
    print("Generados data/test_patient_daily_data.csv y data/test_patient_sleep_data.csv")
    print("Pacientes de prueba:")
    for uid, _ in patients:
        print(" -", uid)


if __name__ == "__main__":
    main()


