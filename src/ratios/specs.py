# -*- coding: utf-8 -*-
"""
Especificación de ratios (entradas, ventanas, thresholds, dirección).
Fuente de verdad: docs/documentacion_ratios/* (excluye glucosa y salud mental).
"""
from __future__ import annotations

RATIOS_SPEC = {
    # 1. score de actividad diaria (basado en METs)
    "daily_activity_score": {
        "category": "actividad",
        "inputs": [
            "minutes_light", "minutes_moderate", "minutes_vigorous", "steps"
        ],
        "windows": [],
        "reverse": False,
    },
    # 2. TRIMP
    "trimp": {
        "category": "actividad",
        "inputs": [
            "heart_rate_average_bpm", "resting_heart_rate_bpm",
            "max_heart_rate_bpm", "activity_minutes", "sex", "age_years"
        ],
        "windows": ["sum_7d", "mean_28d"],
        "reverse": False,
    },
    # 3. VO2max estimado
    "estimated_vo2max": {
        "category": "actividad",
        "inputs": ["max_heart_rate_bpm", "resting_heart_rate_bpm"],
        "windows": [],
        "reverse": False,
    },
    # 4. ACWR (TRIMP 7d / TRIMP 28d)
    "acwr": {
        "category": "actividad",
        "inputs": ["trimp"],
        "windows": ["sum_7d", "mean_28d"],
        "reverse": False,
    },
    # 5. sleep_score (compuesto)
    "sleep_score": {
        "category": "sueño",
        "inputs": [
            "sleep_efficiency", "deep_sleep_minutes",
            "rem_sleep_minutes", "light_sleep_minutes", "asleep_minutes"
        ],
        "windows": [],
        "reverse": False,
    },
    # 6. social_jetlag (menor es mejor)
    "social_jetlag": {
        "category": "sueño",
        "inputs": ["start_time", "date"],
        "windows": ["rolling_14d"],
        "reverse": True,
    },
    # 7. hrv_rhr_ratio
    "hrv_rhr_ratio": {
        "category": "recuperacion",
        "inputs": ["heart_rate_variability_rmssd", "resting_heart_rate_bpm"],
        "windows": [],
        "reverse": False,
    },
    # 8. readiness_score (compuesto)
    "readiness_score": {
        "category": "recuperacion",
        "inputs": ["sleep_score", "hrv_rhr_ratio", "trimp"],
        "windows": [],
        "reverse": False,
    },
    # 9. sleep_efficiency (si no está, recalcular)
    "sleep_efficiency": {
        "category": "sueño",
        "inputs": ["start_time", "end_time", "awake_minutes"],
        "windows": [],
        "reverse": False,
    },
}


