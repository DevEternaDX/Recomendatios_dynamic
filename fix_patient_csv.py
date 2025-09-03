#!/usr/bin/env python3
"""
Arreglar el archivo patient.csv que tiene separador ; en lugar de ,
"""

import pandas as pd

def fix_patient_csv():
    # Leer el CSV con separador correcto
    df = pd.read_csv('data/patient.csv', sep=';')
    print(f'✅ Archivo leído con separador ; : {len(df)} filas')
    print(f'📋 Columnas: {list(df.columns)}')
    
    # Verificar nuestro usuario
    user_id = '4f620746-1ee2-44c4-8338-789cfdb2078f'
    user_row = df[df['id'] == user_id]
    if not user_row.empty:
        print(f'✅ Usuario {user_id} encontrado')
        row = user_row.iloc[0]
        print(f'  - Género: {row["gender"]}')
        print(f'  - Fecha nacimiento: {row["birth_date"]}')
        print(f'  - Altura: {row["height"]}')
        print(f'  - Peso: {row["weight"]}')
        
        # Calcular edad
        from datetime import datetime
        birth_date = pd.to_datetime(row["birth_date"], errors='coerce')
        if not pd.isna(birth_date):
            age = (datetime.now() - birth_date).days // 365
            print(f'  - Edad calculada: {age} años')
    else:
        print(f'❌ Usuario {user_id} NO encontrado')
        print("Primeros 5 IDs en el archivo:")
        print(df['id'].head().tolist())
    
    # Guardar con separador correcto (,)
    df.to_csv('data/patient_fixed.csv', index=False, sep=',')
    print('✅ Guardado como patient_fixed.csv con separador correcto')
    
    return df

if __name__ == "__main__":
    fix_patient_csv()
