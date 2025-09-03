# -*- coding: utf-8 -*-
"""
Registro de features de ratios: une metadatos de paciente y calcula ratios.
"""
from __future__ import annotations

import pandas as pd

from src.data.patient import load_patient_metadata, standardize_patient_metadata
from src.ratios.compute import (
    compute_sleep_efficiency,
    compute_activity_score,
    compute_trimp,
    compute_vo2max_estimate,
    compute_acwr,
    compute_sleep_score,
    compute_social_jetlag,
    compute_hrv_rhr_ratio,
    compute_readiness_score,
)


def merge_patient_timeseries(timeseries_df: pd.DataFrame, patient_df: pd.DataFrame) -> pd.DataFrame:
    df = timeseries_df.copy()
    # Normalizar claves para merge
    original_user_id = None
    if 'user_id' in df.columns and 'patient_id' not in df.columns:
        original_user_id = df['user_id']
        df = df.rename(columns={'user_id': 'patient_id'})
    
    # Identificar columnas conflictivas antes del merge
    overlapping_cols = set(df.columns) & set(patient_df.columns) - {'patient_id'}
    
    # Hacer merge con sufijos para manejar conflictos
    merged = df.merge(patient_df, on='patient_id', how='left', suffixes=('_ts', '_patient'))
    
    # Resolver conflictos priorizando datos de paciente cuando los de timeseries están vacíos
    for col in overlapping_cols:
        ts_col = f'{col}_ts'
        patient_col = f'{col}_patient'
        
        if ts_col in merged.columns and patient_col in merged.columns:
            # Usar valores de paciente donde timeseries está vacío/NaN
            merged[col] = merged[patient_col].fillna(merged[ts_col])
            # Eliminar columnas temporales
            merged = merged.drop(columns=[ts_col, patient_col])
        elif patient_col in merged.columns:
            # Solo existe la columna de paciente, renombrarla
            merged[col] = merged[patient_col]
            merged = merged.drop(columns=[patient_col])
    
    # Preservar user_id para el resto del pipeline
    if 'user_id' not in merged.columns:
        if original_user_id is not None:
            merged['user_id'] = original_user_id.values
        else:
            merged['user_id'] = merged['patient_id']
    return merged


def register_ratio_features(df_timeseries: pd.DataFrame, patient_path: str = 'data/patient') -> pd.DataFrame:
    """Carga/estandariza patient, une y calcula ratios. Devuelve DataFrame extendido."""
    pat = standardize_patient_metadata(load_patient_metadata(patient_path))
    df = merge_patient_timeseries(df_timeseries, pat)

    # Calcular derivados necesarios
    if 'sleep_efficiency' not in df.columns:
        df['sleep_efficiency'] = compute_sleep_efficiency(df)

    df['daily_activity_score'] = compute_activity_score(df)
    df['trimp'] = compute_trimp(df)
    df['estimated_vo2max'] = compute_vo2max_estimate(df)
    # ACWR requiere historial; si no se dispone, quedará NaN
    if 'date' not in df.columns:
        df['date'] = pd.NaT
    df['acwr'] = compute_acwr(df)

    df['sleep_score'] = compute_sleep_score(df)
    df['social_jetlag'] = compute_social_jetlag(df)
    df['hrv_rhr_ratio'] = compute_hrv_rhr_ratio(df)
    df['readiness_score'] = compute_readiness_score(df)

    # Excluir glucosa y salud mental: no se calculan ni se devuelven métricas de esas categorías
    return df


