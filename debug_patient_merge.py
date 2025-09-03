#!/usr/bin/env python3
"""
Debug del merge de datos de paciente
"""

import pandas as pd
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.patient import load_patient_metadata, standardize_patient_metadata
from src.ratios.register import merge_patient_timeseries

def debug_patient_merge():
    print('🔍 DEBUGGING MERGE DE DATOS DE PACIENTE')
    print('=' * 50)
    
    # Cargar datos de actividad del usuario
    df = pd.read_csv('data/daily_processed.csv')
    user_id = '4f620746-1ee2-44c4-8338-789cfdb2078f'
    user_data = df[df['user_id'] == user_id].copy()
    print(f'📊 Datos de actividad del usuario: {len(user_data)} filas')
    print(f'   Columnas clave: user_id={user_data["user_id"].iloc[0] if len(user_data) > 0 else "N/A"}')
    
    # Cargar archivo de paciente
    print('\n📋 CARGANDO DATOS DE PACIENTE:')
    patient_df = load_patient_metadata('data/patient_fixed.csv')
    print(f'   Raw: {len(patient_df)} filas, columnas: {list(patient_df.columns)}')
    
    # Estandarizar
    patient_std = standardize_patient_metadata(patient_df)
    print(f'   Estandarizado: {len(patient_std)} filas, columnas: {list(patient_std.columns)}')
    
    # Verificar nuestro usuario en patient
    user_patient = patient_std[patient_std['patient_id'] == user_id]
    if not user_patient.empty:
        print(f'✅ Usuario {user_id} en patient estandarizado:')
        row = user_patient.iloc[0]
        for col in patient_std.columns:
            print(f'     - {col}: {row[col]}')
    else:
        print(f'❌ Usuario {user_id} NO encontrado en patient estandarizado')
        print('   Primeros 3 patient_ids:')
        print(f'   {patient_std["patient_id"].head(3).tolist()}')
    
    # Intentar merge
    print('\n🔗 INTENTANDO MERGE:')
    try:
        merged = merge_patient_timeseries(user_data, patient_std)
        print(f'✅ Merge exitoso: {len(merged)} filas, {len(merged.columns)} columnas')
        
        # Verificar columnas de paciente en el resultado
        patient_cols = ['sex', 'age_years', 'height_cm', 'weight_kg']
        print('\n📊 DATOS DE PACIENTE EN MERGE:')
        for col in patient_cols:
            if col in merged.columns:
                values = merged[col].dropna()
                print(f'   ✅ {col}: {len(values)} valores válidos')
                if len(values) > 0:
                    print(f'      Ejemplo: {values.iloc[0]}')
            else:
                print(f'   ❌ {col}: NO EXISTE')
                
    except Exception as e:
        print(f'❌ Error en merge: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_patient_merge()
