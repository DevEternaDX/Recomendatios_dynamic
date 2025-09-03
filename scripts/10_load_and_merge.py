# -*- coding: utf-8 -*-
"""
Created on Mon Aug 25 14:41:57 2025

@author: crisf
"""

# 10_load_and_merge.py
import pandas as pd
import numpy as np
from dateutil.parser import parse
import os
import sys





# Configuración de importaciones y rutas
# - Inserta el directorio raíz del proyecto en sys.path para poder importar
#   el módulo de configuración `config.py` sin depender del cwd del intérprete.
# Asegurar que el directorio raíz del proyecto está en sys.path para importar la configuración global
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import FILES, COLMAP, START_DATE, END_DATE, OUT_DIR
from src.ratios.register import register_ratio_features


pd.options.mode.copy_on_write = True





def load_csv(path, parse_dates=None):
    # Carga robusta de CSV con autodetección de separador y parseo de fechas.
    # `sep=None` + `engine='python'` permite que pandas detecte automáticamente
    # si el separador es coma o punto y coma. `parse_dates` delega el parseo
    # a pandas, evitando conversiones manuales.

    return pd.read_csv(path, sep=None, engine="python", parse_dates=parse_dates)





# --- Carga de fuentes crudas (pacientes, actividad, sueño, encuesta)
p  = load_csv(FILES["patient"],          parse_dates=["birth_date"])
a  = load_csv(FILES["activity_daily"],   parse_dates=["date"])
s  = load_csv(FILES["sleep_daily"],      parse_dates=["calculation_date"])
di = load_csv(FILES["survey"],           parse_dates=["date"])





# Normalización de tipos datetime tras la carga
# Asegura que las columnas de fecha están en dtype temporal para operar con filtros y merges

def ensure_date_columns(df, cols):
    cols = [c for c in (cols or []) if c in df.columns]
    if cols:
        df[cols] = df[cols].apply(pd.to_datetime, errors="coerce")





ensure_date_columns(p,  ["birthdate"])           
ensure_date_columns(a,  ["date"])            
ensure_date_columns(s,  ["calculation_date", "date"])  # algunos CSV usan calculation_date
ensure_date_columns(di, ["date"])   





# --- Renombrado a nombres genéricos esperados según COLMAP
# Mapea nombres específicos de tus CSV a un esquema común (patient/activity/sleep/survey)

p  =  p.rename(columns={COLMAP["patient"][k]:   k for k in COLMAP["patient"]   if COLMAP["patient"][k]   in p.columns})
a  =  a.rename(columns={COLMAP["activity"][k]:  k for k in COLMAP["activity"]  if COLMAP["activity"][k]  in a.columns})
s  =  s.rename(columns={COLMAP["sleep"][k]:     k for k in COLMAP["sleep"]     if COLMAP["sleep"][k]     in s.columns})
di = di.rename(columns={COLMAP["survey"][k]:    k for k in COLMAP["survey"]    if COLMAP["survey"][k]    in di.columns})





# Conversión de columnas de fecha tras el renombrado (por si cambiaron los nombres)
if "birthdate" in p.columns:
    p["birthdate"] = pd.to_datetime(p["birthdate"], errors="coerce")
    
if "date" in a.columns:
    a["date"] = pd.to_datetime(a["date"], errors="coerce")
    
if "date" in s.columns:
    s["date"] = pd.to_datetime(s["date"], errors="coerce")
    
if "calculation_date" in s.columns:
    s["calculation_date"] = pd.to_datetime(s["calculation_date"], errors="coerce")
    
if "date" in di.columns:
    di["date"] = pd.to_datetime(di["date"], errors="coerce")
 
    
 


# --- Validación de columnas mínimas requeridas por dataset
# Verifica que existen `user_id` y `date` donde corresponda para poder unir datasets
for name, df in [("activity",a),("sleep",s),("diary",di)]:
    
    if not {"user_id","date"}.issubset(df.columns):
        raise ValueError(f"{name}: faltan columnas obligatorias user_id/date")


if not {"user_id"}.issubset(p.columns): raise ValueError("patient: falta user_id")

    





# --- Filtro por rango de fechas (opcional)
# Define `START_DATE` y `END_DATE` en config.py para recortar el periodo analizado.
# Si están en None, se procesan todas las fechas disponibles.

if START_DATE:
    for df in (a, s, di):
        df.query("date >= @pd.to_datetime(@START_DATE).date()", inplace=True)
        
if END_DATE:
    for df in (a, s, di):
        df.query("date <= @pd.to_datetime(@END_DATE).date()", inplace=True)





# --- Derivación de métricas de sueño: duración y eficiencia
# Acomoda distintos nombres de columnas de inicio/fin de sueño y calcula:
# - `sleep_duration_min` como diferencia entre fin e inicio
# - `sleep_efficiency` aproximada como (1 - awake_minutes / duration) * 100

start_col = 'start_date_time' if 'start_date_time' in s.columns else 'bedtime' if 'bedtime' in s.columns else None
end_col = 'end_date_time' if 'end_date_time' in s.columns else 'waketime' if 'waketime' in s.columns else None

if start_col and end_col:
    # convertir a datetime si aún no lo está
    s[start_col] = pd.to_datetime(s[start_col], errors="coerce")
    s[end_col] = pd.to_datetime(s[end_col], errors="coerce")
    s['sleep_duration_min'] = (s[end_col] - s[start_col]).dt.total_seconds() / 60
    # evitar división por cero
    s['sleep_efficiency'] = (1 - s.get('awake_state_minutes', 0) / s['sleep_duration_min'].replace(0, pd.NA)) * 100

    s['score_fases_sueño'] = ((s['light_sleep_state_minutes']*0.25 + s['deep_sleep_state_minutes']*0.4 + s['rem_sleep_minutes']*0.35) / s['asleep_state_minutes'].replace(0, pd.NA)) * 100
    s['sleep_score'] = 0.7*s['sleep_efficiency'] + 0.3*s['score_fases_sueño']
    
else:
    s['sleep_duration_min'] = pd.NA
    s['sleep_efficiency'] = pd.NA








     



















# --- Cálculo de edad (si no existe) a partir de birthdate

if "age_years" not in p.columns:
    if "birthdate" in p.columns:
        p["age_years"] = ((pd.Timestamp("today") - p["birthdate"]).dt.days // 365)
    else:
        p["age_years"] = np.nan  # si no tienes, puedes imputar luego por media de cohorte, pero mejor dejar NaN





# --- Unificación diaria (merge) de actividad, sueño y encuesta
# Normaliza nombre de inactividad si viene con alias y une por `user_id` y `date`.

if "sedentary_min" not in a.columns and "minutes_inactivity" in a.columns:
    a = a.rename(columns={"minutes_inactivity": "sedentary_min"})


d = (a[["user_id","date","steps","minutes_light","minutes_moderate","minutes_vigorous","sedentary_min"]]
     .merge(s, on=["user_id","date"], how="outer")
     .merge(di, on=["user_id","date"], how="outer"))


# Añade variables demográficas (sexo y edad)
d = d.merge(p[["user_id","sex","age_years"]], on="user_id", how="left")


# Conversión de columnas a tipo numérico (coerciona no numéricos a NaN)
num_cols = ["steps","minutes_light","minutes_moderate","minutes_vigorous","sedentary_min",
            "sleep_duration_min","sleep_efficiency","rhr","hrv_night",
            "sleep_quality_1_5","fatigue_1_5","stress_1_5","mood_1_5","age_years"]
            
for c in num_cols:
    if c in d.columns:
        d[c] = pd.to_numeric(d[c], errors="coerce")




# --- Cálculo y anexado de ratios antes de persistir
# Usamos register_ratio_features sobre el dataset completo para que ratios con ventanas (p.ej. ACWR)
# dispongan del historial necesario. Solo anexamos las columnas de ratios resultantes para evitar
# duplicados de metadatos (p.ej. sex/age) que ya fueron integrados.
try:
    d_enriched = register_ratio_features(d, patient_path=FILES["patient"])
    ratio_cols = [
        "sleep_efficiency",        # puede recalcularse si era NaN
        "daily_activity_score",
        "trimp",
        "estimated_vo2max",
        "acwr",
        "sleep_score",
        "social_jetlag",
        "hrv_rhr_ratio",
        "readiness_score",
    ]
    cols_to_take = [c for c in ratio_cols if c in d_enriched.columns]
    ratios = d_enriched[["user_id","date"] + cols_to_take]
    # Actualizar sin duplicar: usar índice compuesto y update
    d_idx = d.set_index(["user_id","date"])  
    r_idx = ratios.set_index(["user_id","date"]) 
    # Primero, actualizar columnas existentes
    d_idx.update(r_idx)
    # Luego, añadir columnas nuevas que no existan
    for c in r_idx.columns:
        if c not in d_idx.columns:
            d_idx[c] = r_idx[c]
    d = d_idx.reset_index()
except Exception as e:
    # No bloquear el pipeline diario si fallan ratios; continuar con d original
    print(f"Aviso: fallo al calcular ratios en 10_load_and_merge.py: {e}")


# Orden final y persistencia a parquet

d = d.sort_values(["user_id","date"]).reset_index(drop=True)
d.to_parquet(f"{OUT_DIR}/daily_merged.parquet", index=False)
print("OK daily:", d.shape, "users:", d.user_id.nunique())
