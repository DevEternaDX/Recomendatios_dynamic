# Importar configuración desde el archivo global
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import app_settings

# Para compatibilidad con el código existente
settings = app_settings


