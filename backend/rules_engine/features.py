from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict

import os

import numpy as np
import pandas as pd


@dataclass
class FeatureComputationContext:
    user_id: str
    target_date: date


def load_base_dataframe() -> pd.DataFrame:
    """Carga y fusiona los CSV reales de actividad y sueño.

    - data/patient_daily_data.csv
    - data/patient_sleep_data.csv

    Devuelve un DataFrame con columnas normalizadas y una fila por (user_id, date).
    Si los ficheros no existen o hay error, retorna un DataFrame vacío con las
    columnas básicas para evitar romper la API.
    """
    # Permitir override de rutas de CSV vía variables de entorno para testing
    daily_path = os.getenv("DAILY_CSV_PATH", os.path.join("data", "patient_daily_data.csv"))
    sleep_path = os.getenv("SLEEP_CSV_PATH", os.path.join("data", "patient_sleep_data.csv"))

    def _empty_df() -> pd.DataFrame:
        cols = [
        "date",
        "user_id",
            "steps",
        "minutes_light",
        "minutes_moderate",
            "minutes_vigorous",
        "heart_rate_average_bpm",
        "max_heart_rate_bpm",
        "min_heart_rate_bpm",
        "resting_heart_rate",
        "user_max_heart_rate_bpm",
        "rem_sleep_minutes",
        "asleep_state_minutes",
        "deep_sleep_state_minutes",
            "light_sleep_state_minutes",
            "awake_state_minutes",
            "avg_breaths_per_min",
            "heart_rate_variability_sdnn",
        ]
        return pd.DataFrame(columns=cols)

    try:
        # Leer CSV de actividad (separador ';')
        d = pd.read_csv(
            daily_path,
            sep=";",
            engine="python",
            parse_dates=[c for c in ["date", "start_date_time", "webhook_date_time", "last_webhook_update_date_time"] if os.path.exists(daily_path)],
        )
        # Normalizar nombres
        d = d.rename(
            columns={
                "patient_id": "user_id",
                "low_intensity_minutes": "minutes_light",
                "moderate_intensity_minutes": "minutes_moderate",
                "vigorous_intensity_minutes": "minutes_vigorous",
                "resting_heart_rate_bpm": "resting_heart_rate",
                "heart_rate_variability_sdnn": "heart_rate_variability_sdnn",
            }
        )
        # Asegurar columnas clave
        if "date" in d.columns:
            d["date"] = pd.to_datetime(d["date"], errors="coerce")
        if "user_id" in d.columns:
            d["user_id"] = d["user_id"].astype(str)
        # Subconjunto útil
        keep_d = [
            c
            for c in [
                "user_id",
                "date",
                "steps",
                "minutes_light",
                "minutes_moderate",
                "minutes_vigorous",
                "heart_rate_average_bpm",
                "max_heart_rate_bpm",
                "min_heart_rate_bpm",
                "resting_heart_rate",
                "user_max_heart_rate_bpm",
                "heart_rate_variability_sdnn",
            ]
            if c in d.columns
        ]
        d = d[keep_d]
    except Exception:
        d = _empty_df()

    try:
        # Leer CSV de sueño (separador ';')
        s = pd.read_csv(
            sleep_path,
            sep=";",
            engine="python",
            parse_dates=[c for c in ["calculation_date", "start_date_time", "end_date_time"] if os.path.exists(sleep_path)],
        )
        s = s.rename(
            columns={
                "patient_id": "user_id",
                "calculation_date": "date",
            }
        )
        if "date" in s.columns:
            s["date"] = pd.to_datetime(s["date"], errors="coerce")
        if "user_id" in s.columns:
            s["user_id"] = s["user_id"].astype(str)
        keep_s = [
            c
            for c in [
                "user_id",
                "date",
                "rem_sleep_minutes",
                "asleep_state_minutes",
                "deep_sleep_state_minutes",
                "light_sleep_state_minutes",
                "awake_state_minutes",
        "avg_breaths_per_min",
        "heart_rate_variability_sdnn",
                "resting_heart_rate_bpm",
                "max_heart_rate_bpm",
                "min_heart_rate_bpm",
                "user_max_heart_rate_bpm",
            ]
            if c in s.columns
        ]
        s = s[keep_s]
        # Homogeneizar resting_heart_rate si viene con sufijo _bpm
        if "resting_heart_rate" not in s.columns and "resting_heart_rate_bpm" in s.columns:
            s = s.rename(columns={"resting_heart_rate_bpm": "resting_heart_rate"})
    except Exception:
        s = _empty_df()

    try:
        # Fusionar outer para no perder filas
        df = pd.merge(d, s, on=["user_id", "date"], how="outer", suffixes=("", "_s"))
    except Exception:
        df = _empty_df()

    # Orden y tipos básicos
    if not df.empty:
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Asegurar tipos numéricos donde aplique
        for col in df.columns:
            if col in {"user_id", "date"}:
                continue
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.sort_values(["user_id", "date"]).reset_index(drop=True)

    return df


def rolling_mean(series: pd.Series, window_days: int) -> float | None:
    try:
        return float(series.tail(window_days).mean())
    except Exception:  # noqa: BLE001
        return None


def rolling_median(series: pd.Series, window_days: int) -> float | None:
    try:
        return float(series.tail(window_days).median())
    except Exception:  # noqa: BLE001
        return None


def zscore(series: pd.Series, window_days: int) -> float | None:
    try:
        arr = series.tail(window_days).astype(float).values
        if len(arr) == 0:
            return None
        mu = float(np.mean(arr))
        sd = float(np.std(arr))
        if sd == 0:
            return 0.0
        return float((arr[-1] - mu) / sd)
    except Exception:  # noqa: BLE001
        return None


def build_features(df: pd.DataFrame, target_date: date, user_id: str) -> Dict[str, Dict[str, Any]]:
    user_df = df[(df["user_id"] == user_id) & (df["date"] <= pd.Timestamp(target_date))].sort_values("date")

    features: Dict[str, Dict[str, Any]] = {}

    def add(key: str, agg: str, value: Any) -> None:
        features.setdefault(key, {})[agg] = None if pd.isna(value) else value

    if user_df.empty:
        return features

    # Current values
    last = user_df.iloc[-1]
    for key in user_df.columns:
        if key in {"date", "user_id"}:
            continue
        add(key, "current", last.get(key))

    # Rolling windows
    for key in user_df.columns:
        if key in {"date", "user_id"}:
            continue
        s = user_df[key].astype(float)
        add(key, "mean_3d", rolling_mean(s, 3))
        add(key, "mean_7d", rolling_mean(s, 7))
        add(key, "mean_14d", rolling_mean(s, 14))
        add(key, "median_14d", rolling_median(s, 14))
        # delta_pct_3v14 = mean_3d/mean_14d - 1
        m3 = features.get(key, {}).get("mean_3d")
        m14 = features.get(key, {}).get("mean_14d")
        if m3 is not None and m14 not in (None, 0):
            add(key, "delta_pct_3v14", (m3 / m14) - 1)
        else:
            add(key, "delta_pct_3v14", None)
        add(key, "zscore_28d", zscore(s, 28))

    # Derived features
    max_hr = features.get("max_heart_rate_bpm", {}).get("current")
    user_max_hr = features.get("user_max_heart_rate_bpm", {}).get("current")
    if max_hr is not None and user_max_hr not in (None, 0):
        add("max_hr_pct_user_max", "current", max_hr / user_max_hr)

    return features


