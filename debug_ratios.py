#!/usr/bin/env python3
"""
Script de debug para investigar por qué fallan las variables derivadas.
"""

import pandas as pd
import numpy as np
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ratios.register import register_ratio_features

def debug_ratios():
    """Debug del cálculo de ratios paso a paso."""
    
    print("🔍 DEBUGGING VARIABLES DERIVADAS")
    print("=" * 50)
    
    # Cargar datos procesados
    try:
        df = pd.read_csv('data/daily_processed.csv')
        print(f"✅ Datos cargados: {len(df)} filas, {len(df.columns)} columnas")
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return
    
    # Filtrar para nuestro usuario de prueba
    user_id = "4f620746-1ee2-44c4-8338-789cfdb2078f"
    user_data = df[df['user_id'] == user_id].copy()
    print(f"📊 Datos del usuario {user_id}: {len(user_data)} filas")
    
    if user_data.empty:
        print("❌ No hay datos para el usuario de prueba")
        return
    
    print("\n🔍 COLUMNAS DISPONIBLES:")
    print(f"Columnas: {list(user_data.columns)}")
    
    print("\n🔍 VERIFICANDO DATOS BÁSICOS PARA CÁLCULOS:")
    
    # Verificar datos necesarios para TRIMP
    print("\n📈 TRIMP - Datos necesarios:")
    trimp_cols = ['age_years', 'max_heart_rate_bpm', 'resting_heart_rate_bpm', 'heart_rate_average_bpm', 'sex']
    for col in trimp_cols:
        if col in user_data.columns:
            values = user_data[col].dropna()
            print(f"  ✅ {col}: {len(values)} valores válidos, ejemplo: {values.iloc[0] if len(values) > 0 else 'N/A'}")
        else:
            print(f"  ❌ {col}: FALTA")
    
    # Verificar datos necesarios para ACWR
    print("\n📈 ACWR - Datos necesarios:")
    acwr_cols = ['trimp', 'date', 'user_id']
    for col in acwr_cols:
        if col in user_data.columns:
            values = user_data[col].dropna()
            print(f"  ✅ {col}: {len(values)} valores válidos")
        else:
            print(f"  ❌ {col}: FALTA")
    
    # Verificar datos necesarios para readiness_score
    print("\n📈 READINESS_SCORE - Datos necesarios:")
    readiness_cols = ['sleep_score', 'hrv_rhr_ratio', 'trimp']
    for col in readiness_cols:
        if col in user_data.columns:
            values = user_data[col].dropna()
            print(f"  ✅ {col}: {len(values)} valores válidos")
        else:
            print(f"  ❌ {col}: FALTA")
    
    print("\n🔧 EJECUTANDO register_ratio_features...")
    
    # Intentar ejecutar register_ratio_features
    try:
        # Solo procesar los datos del usuario para debug
        result = register_ratio_features(user_data, patient_path='data/patient_fixed.csv')
        print(f"✅ register_ratio_features ejecutado exitosamente")
        print(f"📊 Resultado: {len(result)} filas, {len(result.columns)} columnas")
        
        # Verificar las variables críticas
        print("\n📈 VARIABLES DERIVADAS RESULTANTES:")
        critical_vars = ['acwr', 'trimp', 'readiness_score']
        
        for var in critical_vars:
            if var in result.columns:
                values = result[var].dropna()
                print(f"  {var}:")
                print(f"    - Valores válidos: {len(values)}/{len(result)}")
                if len(values) > 0:
                    print(f"    - Rango: {values.min():.3f} - {values.max():.3f}")
                    print(f"    - Promedio: {values.mean():.3f}")
                    print(f"    - Últimos 3 valores: {list(values.tail(3))}")
                else:
                    print(f"    - ❌ TODOS LOS VALORES SON NaN")
            else:
                print(f"  ❌ {var}: NO EXISTE EN EL RESULTADO")
        
        # Verificar una fecha específica
        print(f"\n🎯 DATOS PARA 2025-03-04:")
        march_4 = result[result['date'] == '2025-03-04']
        if not march_4.empty:
            row = march_4.iloc[0]
            for var in critical_vars:
                if var in row:
                    print(f"  {var}: {row[var]}")
        else:
            print("  ❌ No hay datos para 2025-03-04")
            
    except Exception as e:
        print(f"❌ Error ejecutando register_ratio_features: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🔍 VERIFICANDO ARCHIVO DE PACIENTE:")
    try:
        patient_df = pd.read_csv('data/patient_fixed.csv')
        print(f"✅ Archivo patient_fixed.csv: {len(patient_df)} filas")
        print(f"📋 Columnas: {list(patient_df.columns)}")
        
        # Verificar si nuestro usuario existe
        if 'id' in patient_df.columns:
            user_in_patient = patient_df[patient_df['id'] == user_id]
            if not user_in_patient.empty:
                print(f"✅ Usuario {user_id} encontrado en patient_fixed.csv")
                row = user_in_patient.iloc[0]
                print(f"  - Sexo: {row.get('gender', 'N/A')}")
                print(f"  - Fecha nacimiento: {row.get('birth_date', 'N/A')}")
                print(f"  - Altura: {row.get('height', 'N/A')}")
                print(f"  - Peso: {row.get('weight', 'N/A')}")
            else:
                print(f"❌ Usuario {user_id} NO encontrado en patient_fixed.csv")
        else:
            print("❌ Columna 'id' no encontrada en patient_fixed.csv")
            
    except Exception as e:
        print(f"❌ Error cargando patient_fixed.csv: {e}")

if __name__ == "__main__":
    debug_ratios()
