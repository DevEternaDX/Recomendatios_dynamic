# -*- coding: utf-8 -*-
"""
Carga y estandarización de metadatos de paciente desde data/patient*.csv.

Interfaces:
- load_patient_metadata(path) -> pd.DataFrame
- standardize_patient_metadata(df) -> pd.DataFrame

Notas:
- No se loguea PII más allá de `patient_id`.
- Se validan rangos y unidades de altura/peso.
"""
from __future__ import annotations

import os
import glob
from typing import Optional

import numpy as np
import pandas as pd


def load_patient_metadata(path: str = "data/patient") -> pd.DataFrame:
    """Carga CSV(s) de metadatos de paciente desde un directorio o un archivo.

    - Si `path` es carpeta, concatena todos los CSV dentro.
    - Delimitador autodetectado por pandas (sep=None, engine='python').
    """
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.csv")))
        frames = []
        for f in files:
            frames.append(pd.read_csv(f, sep=None, engine="python"))
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    if os.path.isfile(path):
        return pd.read_csv(path, sep=None, engine="python")

    return pd.DataFrame()


def _normalize_sex(series: pd.Series) -> pd.Series:
    if series is None:
        return series
    s = series.astype(str).str.strip().str.lower()
    mapping = {
        "m": "male", "male": "male", "h": "male",
        "f": "female", "female": "female", "mujer": "female",
        "varon": "male", "hombre": "male",
        "0": "female", "1": "male",
    }
    out = s.map(mapping).fillna("unknown")
    return out


def _to_cm(height: pd.Series) -> pd.Series:
    if height is None:
        return height
    x = pd.to_numeric(height, errors="coerce")
    # Heurística: valores <= 2.5 interpretarlos como metros
    meters_mask = (x > 0) & (x <= 2.5)
    x = np.where(meters_mask, x * 100.0, x)
    # Rango válido 120–230 cm; fuera de rango → NaN
    x = pd.Series(x).where((x >= 120) & (x <= 230))
    return x


def _to_kg(weight: pd.Series) -> pd.Series:
    if weight is None:
        return weight
    x = pd.to_numeric(weight, errors="coerce")
    # Suponer entrada ya en kg; rango válido 35–250
    x = pd.Series(x).where((x >= 35) & (x <= 250))
    return x


def _compute_age_years(df: pd.DataFrame, birth_col: str) -> pd.Series:
    b = pd.to_datetime(df[birth_col], errors="coerce", dayfirst=True)
    # Edad simple al día de hoy; para edad dinámica por registro, calcular al merge temporal
    age = ((pd.Timestamp("today").normalize() - b).dt.days // 365).astype("float")
    return age


def standardize_patient_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Estandariza columnas a:
    ['patient_id','sex','age_years','height_cm','weight_kg','height_m','bmi']
    
    - Normaliza identificador admitiendo alias: id, user_id, subject_id → patient_id
    - Normaliza sexo a male|female|unknown
    - Calcula age_years si hay date_of_birth/birth_date
    - Convierte unidades de altura/peso y valida rangos
    - Deriva height_m y bmi
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "patient_id","sex","age_years","height_cm","weight_kg","height_m","bmi"
        ])

    out = df.copy()
    # Identificador → patient_id
    id_cols = [c for c in out.columns if c.lower() in {"patient_id","id","user_id","subject_id"}]
    if id_cols:
        out["patient_id"] = out[id_cols[0]]
    else:
        # Si no hay, generar ids anónimos para no filtrar todo
        out["patient_id"] = np.arange(len(out))

    # Sexo
    sex_col = None
    for cand in ["sex","gender","sexo"]:
        if cand in out.columns:
            sex_col = cand
            break
    out["sex"] = _normalize_sex(out[sex_col]) if sex_col else "unknown"

    # Edad
    age_col = None
    for cand in ["age_years","age","edad"]:
        if cand in out.columns:
            age_col = cand
            break
    if age_col:
        out["age_years"] = pd.to_numeric(out[age_col], errors="coerce")
    else:
        dob_col = None
        for cand in ["date_of_birth","birth_date","dob","birthdate"]:
            if cand in out.columns:
                dob_col = cand
                break
        if dob_col:
            out["age_years"] = _compute_age_years(out, dob_col)
        else:
            out["age_years"] = np.nan

    # Altura/Peso
    height_col = None
    for cand in ["height_cm","height","height_m","stature_cm"]:
        if cand in out.columns:
            height_col = cand
            break
    weight_col = None
    for cand in ["weight_kg","weight","peso_kg"]:
        if cand in out.columns:
            weight_col = cand
            break

    out["height_cm"] = _to_cm(out[height_col]) if height_col else np.nan
    out["weight_kg"] = _to_kg(out[weight_col]) if weight_col else np.nan
    out["height_m"] = out["height_cm"] / 100.0
    out["bmi"] = out["weight_kg"] / (out["height_m"] ** 2)

    # Selección final
    cols = ["patient_id","sex","age_years","height_cm","weight_kg","height_m","bmi"]
    return out[cols]


