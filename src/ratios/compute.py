# -*- coding: utf-8 -*-
"""
Cálculo de ratios (según docs/documentacion_ratios/*), excluyendo glucosa y salud mental.
Incluye funciones puras pandas/numpy y utilidades rolling.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_sleep_efficiency(df: pd.DataFrame) -> pd.Series:
    # Si ya existe, devolverla
    if 'sleep_efficiency' in df.columns:
        return pd.to_numeric(df['sleep_efficiency'], errors='coerce')

    # Helper para asegurar Series
    def _as_series(val):
        if isinstance(val, pd.Series):
            return val
        return pd.Series(val, index=df.index)

    # Columnas alternativas para inicio/fin y awake
    start = _as_series(pd.to_datetime(df.get('start_time'), errors='coerce'))
    start_alt = _as_series(pd.to_datetime(df.get('start_date_time'), errors='coerce'))
    start = start.fillna(start_alt).fillna(_as_series(pd.to_datetime(df.get('bedtime'), errors='coerce')))

    end = _as_series(pd.to_datetime(df.get('end_time'), errors='coerce'))
    end_alt = _as_series(pd.to_datetime(df.get('end_date_time'), errors='coerce'))
    end = end.fillna(end_alt).fillna(_as_series(pd.to_datetime(df.get('waketime'), errors='coerce')))

    awake = _as_series(pd.to_numeric(df.get('awake_minutes'), errors='coerce'))
    awake_alt = _as_series(pd.to_numeric(df.get('awake_state_minutes'), errors='coerce'))
    awake = awake.fillna(awake_alt)

    tib = (end - start).dt.total_seconds() / 60.0
    eff = np.where((tib > 0) & (~pd.isna(awake)), np.clip(100 * (1 - (awake / tib)), 0, 100), np.nan)
    return pd.Series(eff, index=df.index, name='sleep_efficiency')


def compute_activity_score(df: pd.DataFrame) -> pd.Series:
    # Basado en METs (docs/scores-calculation.md)
    def _as_series(val):
        if isinstance(val, pd.Series):
            return val
        return pd.Series(val, index=df.index)

    light = _as_series(pd.to_numeric(df.get('minutes_light'), errors='coerce')).fillna(0)
    moderate = _as_series(pd.to_numeric(df.get('minutes_moderate'), errors='coerce')).fillna(0)
    vigorous = _as_series(pd.to_numeric(df.get('minutes_vigorous'), errors='coerce')).fillna(0)
    steps = _as_series(pd.to_numeric(df.get('steps'), errors='coerce')).fillna(0)

    points = (
        2.5 * light * 1.0 +
        4.0 * moderate * 2.0 +
        8.0 * vigorous * 3.0 +
        0.055 * steps * 1.0
    )
    # Score relativo a objetivos máximos (heurístico según docs)
    max_points = (
        2.5 * 60 * 1.0 +  # light 60m
        4.0 * 30 * 2.0 +  # moderate 30m
        8.0 * 15 * 3.0 +  # vigorous 15m
        0.055 * 10000 * 1.0  # steps 10k
    )
    score = np.clip(points / max_points * 100.0, 0, 100)
    return pd.Series(score, index=df.index, name='daily_activity_score')


def compute_trimp(df: pd.DataFrame) -> pd.Series:
    # Usar Tanaka para HRmax si falta
    def _ensure_series(x):
        if hasattr(x, 'fillna'):
            return x
        return pd.Series(x, index=df.index)

    age = _ensure_series(pd.to_numeric(df.get('age_years'), errors='coerce'))
    hr_max = _ensure_series(pd.to_numeric(df.get('max_heart_rate_bpm'), errors='coerce'))
    hr_rest = _ensure_series(pd.to_numeric(df.get('resting_heart_rate_bpm'), errors='coerce'))
    hr_avg = _ensure_series(pd.to_numeric(df.get('heart_rate_average_bpm'), errors='coerce'))
    # Preferir activity_minutes; si no existe o es NaN, derivar de intensidades
    minutes = _ensure_series(pd.to_numeric(df.get('activity_minutes'), errors='coerce'))
    
    # Si activity_minutes no existe o está vacío, derivar de intensidades
    if minutes.isna().all():
        light = _ensure_series(pd.to_numeric(df.get('minutes_light'), errors='coerce')).fillna(0)
        moderate = _ensure_series(pd.to_numeric(df.get('minutes_moderate'), errors='coerce')).fillna(0) 
        vigorous = _ensure_series(pd.to_numeric(df.get('minutes_vigorous'), errors='coerce')).fillna(0)
        minutes = light + moderate + vigorous
    
    sex = df.get('sex')

    est_max = 208 - (0.7 * age.fillna(35))
    hr_max = hr_max.fillna(est_max)
    hr_rest = hr_rest.fillna(hr_avg * 0.6)
    
    # Si no tenemos resting_heart_rate, usar una estimación más conservadora
    if hr_rest.isna().all():
        hr_rest = hr_avg * 0.65  # Aproximación más realista
    
    reserve = pd.Series(hr_max - hr_rest, index=df.index).replace(0, np.nan)
    frac = np.clip((hr_avg - hr_rest) / reserve, 0, 1)
    # sex puede ser serie o scalar; normalizar a array alineado
    sex_arr = (sex if hasattr(sex, '__len__') and not isinstance(sex, str) else pd.Series([sex] * len(df), index=df.index))
    beta = np.where((sex_arr == 'female') | (sex_arr == 'FEMALE'), 1.67, 1.92)
    duration_h = (minutes.fillna(0) / 60.0)
    trimp = duration_h * frac * np.exp(beta * frac)
    return pd.Series(trimp, index=df.index, name='trimp')


def compute_vo2max_estimate(df: pd.DataFrame) -> pd.Series:
    def _as_series(val):
        if isinstance(val, pd.Series):
            return val
        return pd.Series(val, index=df.index)

    hr_max = _as_series(pd.to_numeric(df.get('max_heart_rate_bpm'), errors='coerce'))
    hr_rest = _as_series(pd.to_numeric(df.get('resting_heart_rate_bpm'), errors='coerce'))
    vo2 = 15.3 * (hr_max / pd.Series(hr_rest, index=df.index).replace(0, np.nan))
    return pd.Series(vo2, index=df.index, name='estimated_vo2max')


def compute_acwr(df: pd.DataFrame, trimp_col: str = 'trimp', date_col: str = 'date', user_col: str = 'user_id') -> pd.Series:
    if trimp_col not in df.columns or date_col not in df.columns or user_col not in df.columns:
        return pd.Series(np.nan, index=df.index, name='acwr')

    tmp = df[[user_col, date_col, trimp_col]].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors='coerce')

    # ordenar por user y fecha pero conservar el índice original para alineación
    tmp = tmp.sort_values([user_col, date_col])

    # calcular ventanas móviles por grupo y mantener el índice original
    def _compute_group_acwr(g: pd.DataFrame) -> pd.DataFrame:
        # g tiene índice original de df
        g2 = g.copy()
        g2[date_col] = pd.to_datetime(g2[date_col], errors='coerce')
        g2 = g2.sort_values(date_col)
        # usar rolling sobre DataFrame con on=date_col
        acute = g2.rolling('7D', on=date_col)[trimp_col].sum()
        chronic = g2.rolling('28D', on=date_col)[trimp_col].mean()
        res = (acute / pd.Series(chronic, index=chronic.index).replace(0, np.nan)).rename('__res')
        # mantener índice original para reindexado posterior
        return res.to_frame()

    parts = []
    for name, group in tmp.groupby(user_col):
        if group.empty:
            continue
        g_sorted = group.sort_values(date_col)
        acute = g_sorted[trimp_col].rolling(window=7, min_periods=1).sum()
        chronic = g_sorted[trimp_col].rolling(window=28, min_periods=1).mean()
        res_series = (acute / pd.Series(chronic, index=chronic.index).replace(0, np.nan)).rename('__res')
        parts.append(res_series)

    if not parts:
        return pd.Series(np.nan, index=df.index, name='acwr')

    res = pd.concat(parts).sort_index()
    # Alinear con el índice original del DataFrame de entrada
    res_aligned = res.reindex(df.index)
    return pd.Series(res_aligned.values, index=df.index, name='acwr')


def compute_sleep_score(df: pd.DataFrame) -> pd.Series:
    def _as_series(val):
        if isinstance(val, pd.Series):
            return val
        return pd.Series(val, index=df.index)

    eff = _as_series(pd.to_numeric(df.get('sleep_efficiency'), errors='coerce'))
    # Aceptar alias con sufijo _state_ para datos de etapas de sueño
    deep = _as_series(pd.to_numeric(
        df.get('deep_sleep_minutes') if 'deep_sleep_minutes' in df.columns else df.get('deep_sleep_state_minutes'),
        errors='coerce'
    ))
    rem = _as_series(pd.to_numeric(df.get('rem_sleep_minutes'), errors='coerce'))
    light = _as_series(pd.to_numeric(
        df.get('light_sleep_minutes') if 'light_sleep_minutes' in df.columns else df.get('light_sleep_state_minutes'),
        errors='coerce'
    ))
    asleep = _as_series(pd.to_numeric(
        df.get('asleep_minutes') if 'asleep_minutes' in df.columns else df.get('asleep_state_minutes'),
        errors='coerce'
    ))
    stages = (deep * 0.4 + rem * 0.35 + light * 0.25) / pd.Series(asleep, index=df.index).replace(0, np.nan) * 100.0
    score = 0.7 * eff + 0.3 * stages
    return pd.Series(np.clip(score, 0, 100), index=df.index, name='sleep_score')


def compute_social_jetlag(df: pd.DataFrame) -> pd.Series:
    # Robust series helpers
    def _as_series(val):
        if isinstance(val, pd.Series):
            return val
        return pd.Series(val, index=df.index)

    date = _as_series(pd.to_datetime(df.get('date'), errors='coerce'))
    start = _as_series(pd.to_datetime(df.get('start_time'), errors='coerce'))

    # Si faltan columnas críticas, devolver NaN
    if date.isna().all() or start.isna().all():
        return pd.Series(np.nan, index=df.index, name='social_jetlag')

    # Hora decimal de inicio de sueño
    hour = start.dt.hour + start.dt.minute / 60.0
    dow = date.dt.dayofweek
    is_weekend = dow.isin([5, 6])

    # Determinar columna de usuario
    user_col = 'user_id' if 'user_id' in df.columns else ('patient_id' if 'patient_id' in df.columns else None)
    if user_col is None:
        return pd.Series(np.nan, index=df.index, name='social_jetlag')

    # Calcular medias por usuario para laborales y fines de semana
    weekday_mean = hour[~is_weekend].groupby(df.loc[~is_weekend, user_col]).mean()
    weekend_mean = hour[is_weekend].groupby(df.loc[is_weekend, user_col]).mean()

    # Mapear medias a cada fila
    weekday_map = df[user_col].map(weekday_mean)
    weekend_map = df[user_col].map(weekend_mean)

    jetlag = (weekend_map - weekday_map).abs()
    return pd.Series(jetlag.values, index=df.index, name='social_jetlag')


def compute_hrv_rhr_ratio(df: pd.DataFrame) -> pd.Series:
    # Columna HRV alternativa: 'hrv_night'
    def _as_series(val):
        if isinstance(val, pd.Series):
            return val
        return pd.Series(val, index=df.index)

    hrv = _as_series(pd.to_numeric(df.get('heart_rate_variability_rmssd'), errors='coerce'))
    if hrv.isna().all() and 'hrv_night' in df.columns:
        hrv = _as_series(pd.to_numeric(df.get('hrv_night'), errors='coerce'))

    # Columna RHR alternativa: 'rhr'
    rhr = _as_series(pd.to_numeric(df.get('resting_heart_rate_bpm'), errors='coerce'))
    if rhr.isna().all() and 'rhr' in df.columns:
        rhr = _as_series(pd.to_numeric(df.get('rhr'), errors='coerce'))
    ratio = hrv / pd.Series(rhr, index=df.index).replace(0, np.nan)
    return pd.Series(ratio, index=df.index, name='hrv_rhr_ratio')


def compute_readiness_score(df: pd.DataFrame) -> pd.Series:
    def _as_series(val):
        if isinstance(val, pd.Series):
            return val
        return pd.Series(val, index=df.index)

    sleep = _as_series(pd.to_numeric(df.get('sleep_score'), errors='coerce'))
    hrv_ratio = _as_series(pd.to_numeric(df.get('hrv_rhr_ratio'), errors='coerce'))
    trimp = _as_series(pd.to_numeric(df.get('trimp'), errors='coerce'))
    # Normalizaciones simples a 0-100 (si faltan métricas, resultará NaN)
    hrv_norm = np.clip((hrv_ratio - 0.3) / (1.5 - 0.3) * 100.0, 0, 100)
    trimp_norm = np.clip(trimp / 300.0 * 100.0, 0, 100)
    score = 0.4 * sleep + 0.3 * hrv_norm + 0.3 * (100 - trimp_norm)
    return pd.Series(score, index=df.index, name='readiness_score')


