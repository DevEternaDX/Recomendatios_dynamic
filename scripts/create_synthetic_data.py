#!/usr/bin/env python3
"""
Script para crear datos sintéticos que hagan trigger a las reglas importadas.
Esto nos permite probar que el sistema funciona correctamente.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
import random

def create_synthetic_data():
    """Crea datos sintéticos para probar las reglas."""
    
    # Usuario de prueba
    test_user_id = "4f620746-1ee2-44c4-8338-789cfdb2078f"
    
    # Fechas de prueba (últimos 30 días)
    end_date = date(2025, 3, 4)
    start_date = end_date - timedelta(days=29)
    dates = [start_date + timedelta(days=i) for i in range(30)]
    
    synthetic_data = []
    
    for i, current_date in enumerate(dates):
        # Crear datos base realistas
        row = {
            'user_id': test_user_id,
            'date': current_date.strftime('%Y-%m-%d'),
            
            # Datos de actividad (progresivamente mejores)
            'steps': random.randint(8000, 15000),
            'minutes_light': random.randint(150, 250),
            'minutes_moderate': random.randint(30, 80),
            'minutes_vigorous': random.randint(20, 60),
            'sedentary_min': random.randint(400, 600),
            
            # Datos de sueño
            'rem_sleep_minutes': random.randint(90, 130),
            'asleep_state_minutes': random.randint(400, 480),
            'deep_sleep_state_minutes': random.randint(50, 90),
            'light_sleep_state_minutes': random.randint(200, 300),
            'awake_state_minutes': random.randint(20, 60),
            'avg_breaths_per_min': random.uniform(12.0, 16.0),
            
            # Datos de frecuencia cardíaca
            'heart_rate_average_bpm': random.randint(65, 85),
            'max_heart_rate_bpm': random.randint(140, 180),
            'min_heart_rate_bpm': random.randint(50, 70),
            'resting_heart_rate': random.randint(55, 75),
            'user_max_heart_rate_bpm': 190,  # Fijo para cálculos
            'heart_rate_variability_sdnn': random.uniform(25, 55),
            
            # Variables derivadas sintéticas - ESTAS SON LAS IMPORTANTES
            'acwr': None,  # Se calculará después
            'trimp': None,  # Se calculará después
            'readiness_score': None,  # Se calculará después
            'daily_activity_score': random.uniform(60, 90),
            'estimated_vo2max': random.uniform(35, 50),
            'sleep_score': random.uniform(70, 95),
            'social_jetlag': random.uniform(-2, 2),
            'hrv_rhr_ratio': random.uniform(0.3, 0.8),
        }
        
        synthetic_data.append(row)
    
    # Convertir a DataFrame
    df = pd.DataFrame(synthetic_data)
    
    # Calcular variables derivadas que hagan trigger a las reglas
    for i in range(len(df)):
        # ACWR (Acute:Chronic Workload Ratio)
        # Las reglas requieren acwr > 1.2, así que creamos algunos valores que disparen
        if i < 10:
            # Primeros días: valores bajos
            df.loc[i, 'acwr'] = random.uniform(0.8, 1.1)
        elif i < 20:
            # Días medios: algunos valores que disparen las reglas
            df.loc[i, 'acwr'] = random.uniform(1.3, 1.8)  # > 1.2 ✓
        else:
            # Últimos días: valores variados
            df.loc[i, 'acwr'] = random.uniform(0.9, 1.6)
            
        # TRIMP (Training Impulse) 
        # Las reglas requieren trimp > 150
        if i < 15:
            df.loc[i, 'trimp'] = random.uniform(100, 140)  # Valores bajos
        else:
            df.loc[i, 'trimp'] = random.uniform(160, 250)  # > 150 ✓
            
        # Readiness Score
        # Las reglas requieren readiness_score > 80
        if i % 3 == 0:
            # Cada 3 días, valor alto que dispare la regla
            df.loc[i, 'readiness_score'] = random.uniform(82, 95)  # > 80 ✓
        else:
            df.loc[i, 'readiness_score'] = random.uniform(50, 78)  # Valores normales
    
    return df

def main():
    """Función principal."""
    print("🔧 Creando datos sintéticos para probar las reglas...")
    
    # Crear datos sintéticos
    synthetic_df = create_synthetic_data()
    
    # Cargar datos existentes
    try:
        existing_df = pd.read_csv('data/daily_processed.csv')
        print(f"📊 Datos existentes cargados: {len(existing_df)} filas")
    except FileNotFoundError:
        print("⚠️  No se encontró archivo existente, creando uno nuevo")
        existing_df = pd.DataFrame()
    
    # Remover datos existentes del usuario de prueba para evitar duplicados
    test_user_id = "4f620746-1ee2-44c4-8338-789cfdb2078f"
    if not existing_df.empty:
        existing_df = existing_df[existing_df['user_id'] != test_user_id]
        print(f"🗑️  Removidos datos existentes del usuario {test_user_id}")
    
    # Combinar datos
    if existing_df.empty:
        final_df = synthetic_df
    else:
        # Asegurar que las columnas coincidan
        missing_cols = set(existing_df.columns) - set(synthetic_df.columns)
        for col in missing_cols:
            synthetic_df[col] = None
            
        missing_cols_synthetic = set(synthetic_df.columns) - set(existing_df.columns)
        for col in missing_cols_synthetic:
            existing_df[col] = None
            
        final_df = pd.concat([existing_df, synthetic_df], ignore_index=True)
    
    # Guardar datos actualizados
    final_df.to_csv('data/daily_processed.csv', index=False)
    
    print(f"✅ Datos sintéticos creados y guardados!")
    print(f"📈 Total de filas: {len(final_df)}")
    print(f"👤 Datos sintéticos para usuario: {test_user_id}")
    print(f"📅 Fechas: 2025-02-03 a 2025-03-04 (30 días)")
    
    # Mostrar estadísticas de las variables críticas
    user_data = final_df[final_df['user_id'] == test_user_id]
    print(f"\n📊 Estadísticas para {test_user_id}:")
    print(f"   ACWR > 1.2: {(user_data['acwr'] > 1.2).sum()} días")
    print(f"   TRIMP > 150: {(user_data['trimp'] > 150).sum()} días")  
    print(f"   Readiness > 80: {(user_data['readiness_score'] > 80).sum()} días")
    
    print(f"\n🎯 Datos para 2025-03-04:")
    march_4_data = user_data[user_data['date'] == '2025-03-04']
    if not march_4_data.empty:
        row = march_4_data.iloc[0]
        print(f"   ACWR: {row['acwr']:.2f} ({'✅ DISPARA' if row['acwr'] > 1.2 else '❌ no dispara'}) regla")
        print(f"   TRIMP: {row['trimp']:.2f} ({'✅ DISPARA' if row['trimp'] > 150 else '❌ no dispara'}) regla")
        print(f"   Readiness: {row['readiness_score']:.2f} ({'✅ DISPARA' if row['readiness_score'] > 80 else '❌ no dispara'}) regla")

if __name__ == "__main__":
    main()
