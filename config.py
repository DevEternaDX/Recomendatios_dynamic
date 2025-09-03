# config.py - Configuración global del proyecto
"""
Configuración centralizada para todo el proyecto.
Incluye tanto configuración del backend como del procesamiento de datos.
"""

from datetime import date
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Configuración de la aplicación FastAPI y motor de reglas."""
    
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    # Aplicación
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Base de datos
    database_url: str = "sqlite:///./rules.db"

    # Localización
    default_locale: str = "es-ES"

    # Límites de recomendaciones
    max_recs_per_day: int = 3
    max_recs_per_category_per_day: int = 1

    # Anti-repetición de variantes
    anti_repeat_days: int = 7

    # Seguridad
    auth_enabled: bool = False


class DataProcessingSettings:
    """Configuración para scripts de procesamiento de datos."""
    
    # Rango de fechas a analizar (None = todo)
    START_DATE = None     # e.g., "2025-01-01"
    END_DATE = None       # e.g., "2025-08-25"

    # Directorios
    DATA_DIR = "data"
    OUT_DIR = "output"

    # Rutas de archivos
    FILES = {
    "activity_daily": f"{DATA_DIR}/patient_daily_data.csv",
    "sleep_daily": f"{DATA_DIR}/patient_sleep_data.csv",
    "patient": f"{DATA_DIR}/patient_fixed.csv",
    "survey": f"{DATA_DIR}/survey.csv",
}

    # Mapeo de columnas CSV -> esquema normalizado
    COLMAP = {
        "patient": {
            "user_id": "id",
            "sex": "gender",
            "birthdate": "birth_date",
        },
        "activity": {
            "user_id": "patient_id",
            "date": "date",
            "steps": "steps",
            "minutes_light": "low_intensity_minutes",
            "minutes_moderate": "moderate_intensity_minutes",
            "minutes_vigorous": "vigorous_intensity_minutes",
            "minutes_inactivity": "inactivity_minutes",
        },
        "sleep": {
            "user_id": "patient_id",
            "date": "calculation_date",
            "sleep_duration_min": "sleep_duration",
            "sleep_efficiency": "sleep_efficency",
            "bedtime": "start_date_time",
            "waketime": "end_date_time",
        },
        "survey": {
            "user_id": "user_id",
            "date": "date",
            "sleep_quality_1_5": "sleep",
            "nutrition_1_5": "nutrition",
            "stress_1_5": "stress",
            "other": "other"
        }
    }


# Instancias globales
app_settings = AppSettings()
data_settings = DataProcessingSettings()

# Para compatibilidad con el código existente del backend
settings = app_settings

# Para compatibilidad con scripts de procesamiento
FILES = data_settings.FILES
COLMAP = data_settings.COLMAP
START_DATE = data_settings.START_DATE
END_DATE = data_settings.END_DATE
OUT_DIR = data_settings.OUT_DIR
