# Sistema de Recomendaciones Inteligentes - ETERNA DX

## Visión general

**ETERNA DX Rules Engine** es un sistema completo de recomendaciones personalizadas para pacientes basado en datos de actividad física, sueño y bienestar. El sistema evalúa reglas configurables contra métricas derivadas de datos biométricos para generar recomendaciones contextuales y personalizadas.

### Propósito y alcance

- **Propósito**: Generar recomendaciones inteligentes de salud y bienestar basadas en patrones de actividad, sueño y métricas fisiológicas
- **Dominios clave**: 
  - Motor de reglas configurable con DSL propio
  - Procesamiento de datos biométricos y derivación de features
  - Sistema anti-repetición inteligente
  - Interfaz administrativa web
  - API REST completa con auditoría

### Tecnologías principales

- **Backend**: FastAPI (Python 3.9+), SQLAlchemy, Pydantic
- **Frontend**: Next.js 14, React 18, TypeScript, TailwindCSS  
- **Base de datos**: SQLite (desarrollo), escalable a PostgreSQL/MySQL
- **Procesamiento**: Pandas, NumPy para análisis de series temporales
- **Infraestructura**: Uvicorn, PowerShell scripts

### Puntos de entrada

- **API REST**: `http://127.0.0.1:8000` - Endpoints para evaluación, gestión de reglas y analytics
- **Admin UI**: `http://127.0.0.1:3000` - Interfaz web para gestión de reglas y visualización
- **Scripts CLI**: `scripts/10_load_and_merge.py` - Procesamiento de datos CSV
- **Simulación**: Endpoint `/simulate` para testing de reglas contra fechas específicas

### Riesgos técnicos principales

⚠️ **Seguridad**: Autenticación deshabilitada por defecto (`auth_enabled: false`)
⚠️ **Rendimiento**: Procesamiento síncrono de features por usuario/fecha
⚠️ **Escalabilidad**: SQLite no apto para producción con múltiples usuarios concurrentes  
⚠️ **Complejidad**: DSL de reglas requiere validación exhaustiva de sintaxis

---

## Arquitectura

### C4 - Contexto (Nivel 1)

```mermaid
flowchart TD
    User[👤 Administrador<br/>Gestiona reglas y ve analytics] 
    Patient[👤 Paciente<br/>Recibe recomendaciones]
    DataSources[📊 Fuentes de Datos<br/>CSV: actividad, sueño, encuestas]
    
    System[🏥 ETERNA DX Rules Engine<br/>Sistema de recomendaciones]
    
    User --> System
    Patient --> System  
    DataSources --> System
    
    System --> Patient
    System --> User
```

### C4 - Contenedores (Nivel 2)

```mermaid
flowchart TD
    subgraph "ETERNA DX Rules Engine"
        AdminUI[🖥️ Admin UI<br/>Next.js/React<br/>Puerto 3000]
        API[⚙️ FastAPI Backend<br/>Python/SQLAlchemy<br/>Puerto 8000]
        DB[(🗄️ SQLite Database<br/>rules.db)]
        DataProcessor[📈 Data Processor<br/>Pandas/NumPy<br/>Scripts Python]
    end
    
    AdminUser[👤 Admin] --> AdminUI
    APIUser[👤 External Client] --> API
    DataFiles[📁 CSV Files] --> DataProcessor
    
    AdminUI <--> API
    API <--> DB
    DataProcessor <--> DataFiles
    DataProcessor --> DB
    
    API --> ProcessedData[📊 Processed Features<br/>daily_processed.csv]
```

### Grafo de dependencias entre módulos

```mermaid
flowchart TD
    subgraph "Backend Core"
        App[app.py] --> Config[config.py]
        App --> Persistence[persistence.py]
        App --> Routers[API Routers]
    end
    
    subgraph "Rules Engine"
        Engine[engine.py] --> DSL[dsl.py]
        Engine --> Features[features.py] 
        Engine --> Messages[messages.py]
        Engine --> Persistence
        Features --> Config
    end
    
    subgraph "API Layer"
        Routers --> Rules[rules.py]
        Routers --> Analytics[analytics.py]
        Routers --> Evaluate[evaluate.py]
        Rules --> Engine
        Analytics --> Persistence
        Evaluate --> Engine
    end
    
    subgraph "Data Processing"
        Scripts[scripts/] --> SrcRatios[src/ratios/]
        Scripts --> Config
        SrcRatios --> DataPatient[src/data/patient.py]
    end
    
    subgraph "Frontend"
        AdminUI[admin-ui/] --> APIClient[lib/api.ts]
        AdminUI --> Components[React Components]
    end
    
    APIClient --> API
```

### Flujo crítico: Evaluación de recomendaciones

```mermaid
sequenceDiagram
    participant C as Cliente/UI
    participant API as FastAPI
    participant Engine as Rules Engine  
    participant Features as Feature Builder
    participant DB as SQLite
    
    C->>API: POST /simulate {user_id, date}
    API->>Engine: evaluate_user(user_id, date)
    Engine->>Features: load_base_dataframe()
    Features->>Features: load CSV/processed data
    Features-->>Engine: DataFrame
    Engine->>Features: build_features(df, date, user_id)
    Features->>Features: calculate rolling means, ACWR, TRIMP, etc
    Features-->>Engine: feature_dict
    Engine->>DB: get_enabled_rules()
    DB-->>Engine: List[Rule]
    
    loop Para cada regla
        Engine->>Engine: eval_node(rule.logic, features)
        Engine->>Engine: select_message_for_rule() 
        Engine->>DB: check anti-repetition (recent Audits)
        Engine->>Engine: weighted_random_selection()
        Engine->>DB: INSERT Audit (fired=True/False)
    end
    
    Engine->>Engine: enforce_cooldowns()
    Engine->>Engine: resolve_conflicts() 
    Engine-->>API: List[RecommendationEvent]
    API-->>C: {events: [...], debug: {...}}
```

### Proceso de derivación de features

```mermaid
flowchart TD
    A[📁 Raw CSV Files<br/>activity, sleep, patient, survey] --> B[🔄 Load & Merge<br/>scripts/10_load_and_merge.py]
    B --> C[🔗 Merge Patient Metadata<br/>src/ratios/register.py]
    C --> D[📊 Calculate Ratios<br/>src/ratios/compute.py]
    
    D --> E[Rolling Windows<br/>mean_3d, mean_7d, mean_14d]
    D --> F[ACWR Calculation<br/>Acute:Chronic Workload Ratio]  
    D --> G[TRIMP Calculation<br/>Training Impulse]
    D --> H[HRV/RHR Ratios<br/>Heart Rate Variability]
    
    E --> I[📄 daily_processed.csv]
    F --> I
    G --> I  
    H --> I
    
    I --> J[⚙️ Rules Engine<br/>Feature Loading]
    J --> K[🎯 Rule Evaluation]
```

### Estados de reglas y mensajes

```mermaid
stateDiagram-v2
    [*] --> Draft: Crear regla
    Draft --> Enabled: Activar
    Draft --> Disabled: Desactivar
    Enabled --> Disabled: Desactivar
    Disabled --> Enabled: Activar
    Enabled --> Triggered: Condiciones cumplidas
    Triggered --> Cooldown: Aplicar cooldown
    Cooldown --> Enabled: Cooldown expirado
    Enabled --> [*]: Eliminar
    Disabled --> [*]: Eliminar
    
    state Triggered {
        [*] --> MessageSelection
        MessageSelection --> WeightedRandom: Múltiples variantes
        MessageSelection --> SingleMessage: Una variante
        WeightedRandom --> AntiRepetition: Verificar historial
        AntiRepetition --> MessageRendered: Template + variables
        MessageRendered --> [*]
    }
```

### Modelo de datos (ERD)

```mermaid
erDiagram
    VARIABLES ||--o{ RULE_CONDITIONS : references
    RULES ||--o{ RULE_MESSAGES : contains
    RULES ||--o{ AUDITS : generates
    RULE_MESSAGES ||--o{ AUDITS : "selected in"
    CHANGE_LOGS ||--o{ RULES : tracks
    
    VARIABLES {
        int id PK
        string key UK "e.g., steps, hrv_rhr_ratio"
        string label
        string description
        string unit
        string type "number|boolean|string"
        json allowed_aggregators
        float valid_min
        float valid_max
        string missing_policy
        string tenant_id
    }
    
    RULES {
        string id PK "e.g., R-ACT-TRIMP-HRV-03"
        int version
        boolean enabled
        string tenant_id
        string category "activity|sleep|nutrition"
        int priority "1-100"
        int severity "1-5"
        int cooldown_days
        int max_per_day
        json logic "DSL conditions"
        json tags
        datetime created_at
        datetime updated_at
    }
    
    RULE_MESSAGES {
        int id PK
        string rule_id FK
        string locale "es-ES"
        string text "Template con {{variables}}"
        int weight "1-10 para selección ponderada"
        boolean active
    }
    
    AUDITS {
        int id PK
        string tenant_id
        string user_id "UUID del paciente"
        date date "Fecha de evaluación"
        string rule_id FK
        boolean fired
        string discarded_reason
        json why "Condiciones evaluadas"
        json values "Features del usuario"
        int message_id FK "Variante seleccionada"
        datetime created_at
    }
    
    CHANGE_LOGS {
        int id PK
        datetime created_at
        string user "admin|editor"
        string role
        string action "create|update|delete"
        string entity_type "rule|message"
        string entity_id
        json before
        json after
    }
```

---

## Guía de inicio

### Requisitos

- **Python**: 3.9+ con pip
- **Node.js**: 18+ con npm
- **Sistema operativo**: Windows 10+ (scripts PowerShell), Linux, macOS

### Instalación

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd def_recomendations

# 2. Backend - Crear entorno virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS  
source .venv/bin/activate

# 3. Instalar dependencias Python
pip install -r requirements.txt

# 4. Frontend - Instalar dependencias Node.js
cd admin-ui
npm install
cd ..

# 5. Procesar datos iniciales (opcional)
python scripts/10_load_and_merge.py
```

### Configuración mínima

Crear `.env` en la raíz (opcional, usa defaults):

```env
# Aplicación
APP_ENV=development
APP_HOST=127.0.0.1  
APP_PORT=8000

# Base de datos
DATABASE_URL=sqlite:///./rules.db

# Límites de recomendaciones
MAX_RECS_PER_DAY=3
MAX_RECS_PER_CATEGORY_PER_DAY=1
ANTI_REPEAT_DAYS=7

# Seguridad (⚠️ CAMBIAR EN PRODUCCIÓN)
AUTH_ENABLED=false
```

### Comandos principales

```bash
# Desarrollo - Ambos servicios (Windows)
.\run-dev.ps1

# Desarrollo - Manual
# Terminal 1: Backend
.venv\Scripts\activate
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend  
cd admin-ui
npm run dev

# Procesamiento de datos
python scripts/10_load_and_merge.py

# Tests
python -m pytest backend/tests/

# Build frontend para producción
cd admin-ui  
npm run build
npm start
```

### Estructura de carpetas

```
def_recomendations/
├── 📁 admin-ui/              # Frontend Next.js
│   ├── app/                  # App Router pages
│   │   ├── rules/           # Gestión de reglas
│   │   ├── stats/           # Analytics y gráficos
│   │   ├── logs/            # Audit logs
│   │   └── simulate/        # Testing de reglas
│   └── lib/api.ts           # Cliente API
├── 📁 backend/              # API FastAPI
│   ├── api/                 # Endpoints REST
│   ├── rules_engine/        # Core del motor de reglas
│   │   ├── engine.py        # Evaluación principal
│   │   ├── dsl.py          # DSL de condiciones
│   │   ├── features.py     # Derivación de métricas
│   │   └── persistence.py  # Modelos SQLAlchemy
│   └── app.py              # Aplicación principal
├── 📁 data/                # Datos CSV de entrada
│   ├── patient_daily_data.csv
│   ├── patient_sleep_data.csv  
│   ├── patient_fixed.csv
│   └── daily_processed.csv    # Generado por scripts
├── 📁 scripts/             # Procesamiento de datos
│   └── 10_load_and_merge.py  # ETL principal
├── 📁 src/                 # Lógica de features
│   ├── ratios/             # Cálculos de métricas
│   └── data/               # Utilidades de datos
├── config.py               # Configuración centralizada
├── requirements.txt        # Dependencias Python
└── run-dev.ps1            # Script desarrollo Windows
```

### Ejemplos de uso

**1. Crear una regla simple**
```bash
curl -X POST http://127.0.0.1:8000/rules \
  -H "Content-Type: application/json" \
  -d '{
    "id": "R-STEPS-LOW",
    "category": "activity", 
    "priority": 70,
    "logic": {
      "all": [{
        "var": "steps",
        "agg": "current", 
        "op": "<",
        "value": 5000
      }]
    },
    "messages": [{
      "text": "¡Hoy has caminado menos! Intenta dar {{steps}} pasos más.",
      "weight": 1
    }]
  }'
```

**2. Simular reglas para un usuario**
```bash
curl -X POST http://127.0.0.1:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "4f620746-1ee2-44c4-8338-789cfdb2078f",
    "date": "2025-03-03"
  }'
```

**3. Ver estadísticas de una regla**
```bash  
curl http://127.0.0.1:8000/rules/R-STEPS-LOW/stats
```

---

## Documentación por capa

### Módulos principales

#### `backend.rules_engine` - Motor de reglas core
- **Responsabilidad**: Evaluación de condiciones, selección de mensajes, anti-repetición
- **API pública**: `evaluate_user()`, `build_features()`, `select_weighted_random()`
- **Dependencias**: SQLAlchemy (persistencia), Pandas (features), Jinja2 (templates)
- **Invariantes**: 
  - Siempre genera Audit por cada evaluación
  - Respeta cooldowns y límites por día/categoría
  - Features se calculan una vez por usuario/fecha

#### `backend.api` - Capa REST
- **Responsabilidad**: Endpoints HTTP, validación Pydantic, manejo de errores
- **API pública**: `/rules`, `/simulate`, `/analytics`, `/variables`  
- **Dependencias**: FastAPI, rules_engine
- **Invariantes**: 
  - Autenticación por contexto (`_current_user()`)
  - Logs de cambios en operaciones CUD
  - Validación de roles para operaciones sensibles

#### `admin-ui` - Interfaz administrativa  
- **Responsabilidad**: CRUD de reglas, visualización de analytics, testing
- **API pública**: Páginas React con Server/Client Components
- **Dependencias**: Next.js 14, TailwindCSS, Axios
- **Invariantes**:
  - Estado local con React hooks
  - Comunicación vía API REST únicamente
  - Confirmaciones para operaciones destructivas

#### `src.ratios` - Derivación de métricas
- **Responsabilidad**: Cálculo de ACWR, TRIMP, rolling windows, z-scores
- **API pública**: `register_ratio_features()`, `compute_*()` functions
- **Dependencias**: Pandas, NumPy
- **Invariantes**:
  - Funciones puras sin efectos secundarios
  - Manejo robusto de NaN/missing values
  - Preserva índices temporales de DataFrames

### Archivos críticos

#### `backend/rules_engine/engine.py:211-327` - Función `evaluate_user`
```python
def evaluate_user(user_id: str, target_day: date, tenant_id: str = "default", debug: bool = False) -> list[RecommendationEvent]:
    """
    Evalúa todas las reglas activas para un usuario en una fecha específica.
    
    Args:
        user_id: UUID del paciente
        target_day: Fecha de evaluación  
        tenant_id: Tenant para multi-tenancy
        debug: Si retornar información de debug
    
    Returns:
        Lista de eventos de recomendación después de aplicar cooldowns y límites
        
    Complexity: O(R * C) donde R=reglas activas, C=condiciones por regla
    
    Side effects:
        - Inserta registros Audit en BD
        - Puede generar I/O para cargar CSV si no está en cache
    """
```

**Patrones aplicados**: 
- Strategy (diferentes tipos de nodos DSL)
- Template Method (evaluación + filtros + persistencia)
- Observer (auditoría de cada evaluación)

**Hotspots de extensión**:
- `eval_node()`: Añadir nuevos tipos de condiciones DSL
- `resolve_conflicts()`: Lógica de priorización personalizada
- `select_message_for_rule()`: Algoritmos de selección alternativos

#### `backend/rules_engine/features.py:200-262` - Función `build_features`

```python  
def build_features(df: pd.DataFrame, target_day: date, user_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Construye diccionario de features para evaluación de reglas.
    
    Calcula rolling windows, deltas porcentuales y métricas derivadas
    para un usuario específico hasta una fecha objetivo.
    
    Args:
        df: DataFrame con datos procesados (daily_processed.csv)
        target_day: Fecha límite para cálculos
        user_id: ID del usuario a procesar
        
    Returns:
        Dict[variable][aggregation] = valor
        Ejemplo: {"steps": {"current": 8500, "mean_7d": 7200}, ...}
        
    Complexity: O(N * W) donde N=días de datos, W=ventana máxima (14d)
    
    Side effects: None (función pura)
    
    Raises:
        ValueError: Si columnas no numéricas se intentan convertir a float
    """
```

**Edge cases conocidos**:
- Usuario sin datos: retorna dict vacío con logging
- Fechas futuras: filtra hasta target_day inclusive  
- Columnas mixtas: excluye text/datetime de rolling calculations
- NaN handling: propagación controlada según `missing_policy`

#### `admin-ui/lib/api.ts` - Cliente API TypeScript

```typescript
/**
 * Cliente API para comunicación con backend FastAPI.
 * 
 * Maneja autenticación, serialización JSON y manejo de errores HTTP.
 * Todas las funciones son async y lanzan AxiosError en fallos.
 * 
 * @example
 * ```typescript
 * const rules = await listRules()
 * const result = await simulateRules({user_id: "123", date: "2025-03-03"})
 * ```
 */
```

**Funciones principales**:
- `listRules()`: GET /rules con paginación implícita
- `createRule(data)`: POST /rules con validación Pydantic
- `simulateRules({user_id, date})`: POST /simulate  
- `exportRules()`: GET /rules/export formato JSON
- `importRules(content)`: POST /rules/import con validación
- `deleteAllRules()`: DELETE /rules/all con confirmación requerida

### Clases principales

#### `Rule` (SQLAlchemy Model)
- **Rol**: Entidad central del sistema, define lógica de evaluación
- **Relaciones**: 1:N con RuleMessage, 1:N con Audit
- **Invariantes**: 
  - `id` único y inmutable post-creación
  - `logic` debe ser JSON válido parseable por DSL
  - `enabled=false` excluye de evaluaciones
- **Concurrencia**: Sin bloqueos optimistas, última escritura gana

#### `RecommendationEvent` (Dataclass)
- **Rol**: DTO para eventos generados por el motor
- **Campos clave**: `user_id`, `rule_id`, `message_text`, `why` (explicabilidad)
- **Invariantes**: Inmutable post-creación, serializable a JSON

#### `RuleModel` (Pydantic) 
- **Rol**: Validación y parsing de DSL de reglas
- **Validaciones**: Sintaxis de condiciones, referencias a variables existentes
- **Transformaciones**: Convierte dict raw a objetos tipados (NumericLeaf, GroupAll, etc.)

### Funciones críticas

#### `compare(op: str, left: Any, right: Any) -> bool` 
```python
def compare(op: str, left: Any, right: Any) -> bool:
    """
    Operador de comparación universal para evaluación de condiciones.
    
    Soporta: <, <=, >, >=, ==, between, in
    Manejo robusto de None/NaN values.
    
    Args:
        op: Operador como string  
        left: Valor observado (puede ser None)
        right: Valor de comparación o lista para 'between'/'in'
        
    Returns:
        bool: Resultado de comparación, False si left is None
        
    Examples:
        >>> compare("<", 100, 200)  # True
        >>> compare("between", 15, [10, 20])  # True  
        >>> compare("in", "A", ["A", "B"])  # True
        >>> compare(">", None, 50)  # False (None safety)
    """
```

#### `select_weighted_random(candidates: List[dict]) -> dict | None`
```python
def select_weighted_random(candidates: List[dict]) -> dict | None:
    """
    Selección aleatoria ponderada de mensaje de regla.
    
    Implementa weighted sampling usando pesos como probabilidades relativas.
    Usado para variabilidad en mensajes de una misma regla.
    
    Args:
        candidates: Lista de dicts con keys 'weight', 'text', 'id'
        
    Returns:
        Dict seleccionado o None si lista vacía
        
    Complexity: O(n) donde n = len(candidates)
    
    Algorithm: 
        1. Suma total de pesos
        2. Random float en [0, total)  
        3. Iteración acumulativa hasta encontrar bin
    """
```

#### `render_message(template: str, features: dict) -> Tuple[str, List[str]]`
```python
def render_message(template: str, features: dict) -> Tuple[str, List[str]]:
    """
    Renderiza template Jinja2 con variables de features del usuario.
    
    Soporta interpolación de valores calculados en mensajes personalizados.
    Manejo de errores para templates inválidos o variables faltantes.
    
    Args:
        template: String con placeholders {{variable.aggregation}}
        features: Dict anidado de features por usuario
        
    Returns:
        (mensaje_final, warnings): Tuple con texto final y lista de warnings
        
    Examples:
        >>> render_message("Tus pasos: {{steps.current}}", {"steps": {"current": 8500}})
        ("Tus pasos: 8500", [])
        
        >>> render_message("HRV: {{hrv.missing}}", {"hrv": {}})  
        ("HRV: {{hrv.missing}}", ["Variable 'hrv.missing' no encontrada"])
    """
```

---

## Calidad, seguridad y rendimiento

### Seguridad

⚠️ **Crítico - Autenticación deshabilitada**
- **Ubicación**: `config.py:35` - `auth_enabled: bool = False`
- **Riesgo**: Acceso sin restricciones a todos los endpoints de administración
- **Mitigación**: Implementar OAuth2/JWT antes de producción
- **TODO**: Integrar con sistema de identidad corporativo

🔒 **Validación de entradas**
- **Pydantic**: Validación automática en todos los endpoints API
- **SQLAlchemy**: Prevención de SQL injection vía ORM  
- **DSL parsing**: Validación de sintaxis de reglas antes de persistir
- **Sanitización**: Templates Jinja2 con escape automático

🛡️ **Permisos y roles**
- **Ubicación**: `backend/api/rules.py:37-40` - `_require_role()`
- **Roles**: `admin` (CRUD completo), `editor` (sin delete), `viewer` (solo lectura)
- **Enforcement**: Decorador en endpoints sensibles
- **Auditoría**: Logs de cambios en `ChangeLog` tabla

⚠️ **Riesgos de inyección**
- **Templates**: Jinja2 permite código Python - validar templates de usuarios
- **CSV import**: `csv.Sniffer` puede ser vulnerable a CSV injection
- **JSON fields**: Validar estructura de `logic` y `values` en reglas

### Rendimiento

🚀 **Hotspots de CPU/memoria**
- **`build_features()`**: O(N*W) - cachear por usuario/fecha si es posible
- **`evaluate_user()`**: O(R*C) - considerar lazy loading de reglas
- **Rolling windows**: Pandas `.rolling()` - usar ventanas fijas vs expandidas
- **CSV loading**: `pandas.read_csv()` - considerar chunking para archivos >100MB

💾 **Optimizaciones de I/O**
- **Database**: Índices en `user_id`, `date`, `rule_id` para queries frecuentes  
- **CSV caching**: Cargar `daily_processed.csv` una vez por proceso
- **Batch processing**: Evaluar múltiples usuarios/fechas en lote

🔄 **Puntos para caché**
- **Features por usuario**: Cache TTL=1h para datos del día actual
- **Reglas activas**: Cache invalidado solo en cambios de reglas
- **Variables metadata**: Cache permanente (raramente cambia)

📊 **Paginación requerida**
- **`/analytics/logs`**: Sin límites - puede ser lento con >10K audits
- **`/rules/{id}/stats`**: Agregaciones sin ventana temporal
- **Admin UI**: Listas de reglas sin paginación client-side

### Concurrencia

🔒 **Secciones críticas**
- **Audit writes**: Sin transacciones - posibles race conditions en contadores
- **Rule evaluation**: Stateless pero shared session - usar session pools
- **CSV processing**: No thread-safe - usar locks para escritura concurrente

⚡ **Asincronía potencial**
- **`evaluate_user()`**: Convertir a async para I/O no bloqueante
- **Background jobs**: Procesamiento de datos diario vía Celery/RQ
- **WebSockets**: Real-time updates de reglas en Admin UI

### Observabilidad

📝 **Logging estructurado**
```python
# TODO(backend/rules_engine/engine.py:304): Implementar structured logging
import structlog
logger = structlog.get_logger()
logger.info("rule_evaluated", user_id=user_id, rule_id=rule.id, fired=fired)
```

📊 **Métricas sugeridas**
- **Contadores**: `rules_evaluated_total`, `recommendations_generated_total`
- **Histogramas**: `evaluation_duration_seconds`, `feature_calculation_seconds`  
- **Gauges**: `active_rules_count`, `users_with_data_count`

🔍 **Trazas distribuidas**
- **Span names**: `evaluate_user`, `build_features`, `select_message`
- **Tags**: `user_id`, `rule_id`, `tenant_id`, `fired`
- **Herramientas**: OpenTelemetry + Jaeger/DataDog

### Compatibilidad

📅 **Breaking changes potenciales**
- **DSL evolution**: Cambios en sintaxis de `logic` field
- **API versioning**: Sin versionado actual en endpoints
- **Database schema**: Migraciones Alembic no configuradas
- **CSV format**: Cambios en columnas esperadas por `COLMAP`

🔄 **Backward compatibility**
- **Rule versions**: Campo `version` sin uso actual
- **Message templates**: Cambios en variables disponibles
- **API responses**: Campos adicionales rompen clientes estrictos

---

## Pruebas

### Ejecutar tests

```bash
# Todos los tests
python -m pytest backend/tests/ -v

# Tests específicos  
python -m pytest backend/tests/test_health.py -v
python -m pytest backend/tests/test_simulate_minimal.py -v

# Con cobertura (TODO: configurar coverage.py)
python -m pytest --cov=backend backend/tests/
```

### Cobertura estimada

**TODO(cobertura_real)**: Configurar `pytest-cov` para métricas exactas

- **backend/api/**: ~60% (endpoints principales cubiertos)
- **backend/rules_engine/**: ~40% (lógica core parcial)  
- **admin-ui/**: ~20% (sin tests unitarios configurados)
- **scripts/**: ~10% (solo smoke tests)

### Casos de prueba mínimos por función crítica

#### `evaluate_user()`
- ✅ Usuario sin datos → retorna lista vacía
- ✅ Regla simple que dispara → genera RecommendationEvent  
- ⚠️ Regla con cooldown activo → filtrada por enforce_cooldowns
- ⚠️ Múltiples reglas, límites por día → resolve_conflicts aplicado
- ❌ Features con NaN → manejo de missing_policy
- ❌ Template inválido → warnings en render_message

#### `build_features()`  
- ✅ DataFrame vacío → dict vacío
- ⚠️ Usuario con 1 día de datos → rolling windows con NaN
- ❌ Columnas no numéricas → exclusión sin error
- ❌ Fechas futuras → filtrado correcto

#### `compare()`
- ✅ Operadores básicos (<, >, ==) → correctos
- ✅ between con rango válido → funcional  
- ✅ Valor None → siempre False
- ❌ Operador inválido → comportamiento por defecto

#### API endpoints
- ✅ GET /rules → lista reglas activas
- ✅ POST /simulate → evaluación básica
- ⚠️ POST /rules con DSL inválido → error 400
- ❌ DELETE /rules/{id} inexistente → error 404
- ❌ Endpoints sin auth cuando auth_enabled=true

### Fixtures y datos de ejemplo

```python
# backend/tests/conftest.py (TODO: crear)
@pytest.fixture
def sample_user_data():
    return pd.DataFrame({
        'user_id': ['test-user-123'] * 30,
        'date': pd.date_range('2025-01-01', periods=30),
        'steps': np.random.randint(5000, 15000, 30),
        'sleep_duration': np.random.normal(7.5, 1.0, 30),
        'hrv_rhr_ratio': np.random.normal(1.0, 0.1, 30),
    })

@pytest.fixture  
def simple_rule():
    return Rule(
        id="TEST-STEPS-LOW",
        enabled=True,
        logic={"all": [{"var": "steps", "agg": "current", "op": "<", "value": 6000}]},
        category="activity",
        priority=50,
        messages=[RuleMessage(text="Camina más hoy", weight=1, active=True)]
    )
```

### Property-based testing (TODO)

```python
# Ejemplo con Hypothesis
from hypothesis import given, strategies as st

@given(st.integers(min_value=0, max_value=50000))
def test_steps_comparison_properties(steps_value):
    """Los pasos siempre deben compararse consistentemente."""
    assert compare(">=", steps_value, 0) == True
    assert compare("<", steps_value, steps_value) == False
    assert compare("==", steps_value, steps_value) == True
```

---

## Despliegue & Operaciones

### Esquemas y migraciones

**Base de datos**:
```bash
# Crear tablas (automático en startup)
python -c "from backend.rules_engine.persistence import create_all_tables; create_all_tables()"

# TODO: Configurar Alembic para migraciones
alembic init alembic
alembic revision --autogenerate -m "Initial schema"  
alembic upgrade head
```

**Seeds iniciales**:
- `backend/seeds/variables_seed.json`: Variables disponibles para DSL
- `backend/seeds/rules_seed.json`: Reglas de ejemplo
- Ejecutión automática en `app.py:46-47`

### Orquestación

#### Docker (TODO: crear Dockerfile)
```dockerfile
# Multi-stage build
FROM node:18-alpine AS frontend-build
WORKDIR /app/admin-ui
COPY admin-ui/package*.json ./
RUN npm ci --only=production
COPY admin-ui/ ./
RUN npm run build

FROM python:3.11-slim AS backend
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY config.py ./
COPY --from=frontend-build /app/admin-ui/out ./static/

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Variables de entorno (producción)
```bash
# Aplicación
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000

# Base de datos (PostgreSQL recomendado)
DATABASE_URL=postgresql://user:pass@localhost/eterna_rules

# Seguridad (CRÍTICO)
AUTH_ENABLED=true
SECRET_KEY=<REDACTED>
CORS_ORIGINS=https://admin.empresa.com

# Límites de producción  
MAX_RECS_PER_DAY=5
ANTI_REPEAT_DAYS=14

# Observabilidad
LOG_LEVEL=INFO
SENTRY_DSN=<REDACTED>
METRICS_ENDPOINT=http://prometheus:9090
```

### Runbooks - Procedimientos ante fallos

#### Problema: Reglas no disparan para usuarios
```bash
# 1. Verificar datos procesados
ls -la data/daily_processed.csv
python -c "import pandas as pd; print(pd.read_csv('data/daily_processed.csv').info())"

# 2. Verificar features del usuario
curl -X POST http://localhost:8000/simulate \
  -d '{"user_id": "USER_ID", "date": "2025-03-03", "debug": true}' | jq '.debug'

# 3. Verificar reglas activas
curl http://localhost:8000/rules | jq '.[] | select(.enabled == true)'

# 4. Check recent audits
sqlite3 rules.db "SELECT * FROM audits WHERE user_id='USER_ID' ORDER BY created_at DESC LIMIT 10;"
```

#### Problema: Performance lenta en evaluación
```bash
# 1. Profiling de evaluación
python -c "
import cProfile
from backend.rules_engine.engine import evaluate_user
from datetime import date
cProfile.run('evaluate_user(\"test-user\", date(2025, 3, 3))')
"

# 2. Verificar tamaño de datos
du -sh data/
wc -l data/daily_processed.csv

# 3. Optimizar queries de BD
sqlite3 rules.db "EXPLAIN QUERY PLAN SELECT * FROM audits WHERE user_id='X' AND date >= '2025-03-01';"
```

#### Problema: Admin UI no conecta con backend
```bash
# 1. Verificar CORS
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:8000/rules

# 2. Verificar backend health
curl http://localhost:8000/health

# 3. Check logs de ambos servicios
tail -f uvicorn.log
tail -f admin-ui/next.log
```

### Cron jobs y tareas programadas

```bash
# Procesamiento diario de datos (6:00 AM)
0 6 * * * cd /app && python scripts/10_load_and_merge.py >> logs/etl.log 2>&1

# Limpieza de audits antiguos (semanal)  
0 2 * * 0 sqlite3 /app/rules.db "DELETE FROM audits WHERE created_at < date('now', '-90 days');"

# Backup de base de datos (diario)
0 1 * * * cp /app/rules.db /backups/rules_$(date +\%Y\%m\%d).db
```

---

## Índice API rápido

| Endpoint | Método | Archivo | Responsabilidad | Ejemplo |
|----------|--------|---------|-----------------|---------|
| `/health` | GET | `health.py:8` | Health check básico | `{"status": "ok"}` |
| `/rules` | GET | `rules.py:54` | Listar reglas activas | `[{"id": "R-1", "enabled": true}]` |
| `/rules` | POST | `rules.py:81` | Crear nueva regla | `{"id": "R-NEW"}` |
| `/rules/{id}` | GET | `rules.py:124` | Obtener regla específica | `{"id": "R-1", "logic": {...}}` |
| `/rules/{id}` | PUT | `rules.py:165` | Actualizar regla completa | `{"id": "R-1"}` |
| `/rules/{id}` | DELETE | `rules.py:247` | Eliminar regla | `{"deleted": true}` |
| `/rules/all` | DELETE | `rules.py:213` | Eliminar todas las reglas | `{"deleted": 10, "message": "..."}` |
| `/rules/{id}/variants` | POST | `rules.py:244` | Añadir variante de mensaje | `{"id": 123}` |
| `/rules/{id}/variants/{msg_id}` | PATCH | `rules.py:266` | Actualizar variante específica | `{"updated": true}` |
| `/rules/{id}/variants/{msg_id}` | DELETE | `rules.py:288` | Eliminar variante | `{"deleted": true}` |
| `/rules/export` | GET | `rules.py:330` | Exportar reglas JSON | `[{"id": "R-1", ...}]` |
| `/rules/import` | POST | `rules.py:351` | Importar reglas JSON/YAML | `{"imported": 5, "updated": 2}` |
| `/rules/import_csv` | POST | `rules.py:451` | Importar desde CSV | `{"imported": 10}` |
| `/rules/{id}/stats` | GET | `rules.py:539` | Estadísticas de disparos | `{"total_triggers": 45}` |
| `/rules/{id}/changelog` | GET | `rules.py:554` | Historial de cambios | `[{"action": "update", ...}]` |
| `/rules/{id}/enable` | POST | `rules.py:581` | Activar/desactivar regla | `{"enabled": true}` |
| `/rules/{id}/clone` | POST | `rules.py:596` | Clonar regla existente | `{"id": "R-1-COPY"}` |
| `/simulate` | POST | `evaluate.py:15` | Simular reglas para usuario/fecha | `{"events": [...], "debug": {...}}` |
| `/variables` | GET | `variables.py:20` | Listar variables disponibles | `[{"key": "steps", "type": "number"}]` |
| `/analytics/logs` | GET | `analytics.py:15` | Logs de auditoría con filtros | `[{"user_id": "X", "fired": true}]` |
| `/analytics/triggers` | GET | `analytics.py:45` | Estadísticas de triggers por regla | `{"R-1": {"count": 10, "dates": [...]}}` |

### Links internos a documentación

- **Autenticación**: Ver [Seguridad](#seguridad) → `_current_user()` en `rules.py:30`
- **DSL de reglas**: Ver [Arquitectura](#proceso-de-derivación-de-features) → `dsl.py` 
- **Anti-repetición**: Ver [engine.py:116-158](#funciones-críticas) → `select_message_for_rule()`
- **Features derivadas**: Ver [Flujo crítico](#flujo-crítico-evaluación-de-recomendaciones) → `build_features()`
- **Configuración**: Ver [config.py](#configuración-mínima) para todas las variables

---

## Plan de mejoras

### Prioridades (Impacto vs Esfuerzo)

#### 🔥 Crítico - Seguridad (Alto impacto, Medio esfuerzo)
1. **Implementar autenticación real** 
   - `TODO(config.py:35)`: Cambiar `auth_enabled=True` 
   - `TODO(backend/api/rules.py:31-35)`: Integrar OAuth2/JWT
   - **Esfuerzo**: 3-5 días, **Impacto**: Crítico para producción

2. **Validación exhaustiva de DSL**
   - `TODO(backend/rules_engine/dsl.py)`: Sandbox para evaluación segura
   - **Esfuerzo**: 2-3 días, **Impacto**: Previene code injection

#### ⚡ Performance - Optimizaciones (Alto impacto, Bajo esfuerzo)  
3. **Cache de features por usuario/fecha**
   - `TODO(backend/rules_engine/features.py:200)`: Redis/memory cache
   - **Esfuerzo**: 1-2 días, **Impacto**: 5-10x speedup en evaluaciones

4. **Async endpoints**
   - `TODO(backend/api/evaluate.py:15)`: Convertir `/simulate` a async
   - **Esfuerzo**: 2 días, **Impacto**: Mejor concurrencia

5. **Database indexing**
   - `TODO(backend/rules_engine/persistence.py:100-114)`: Índices en Audit queries
   - **Esfuerzo**: 1 día, **Impacto**: Queries 10x más rápidas

#### 🛠️ Funcionalidad - Extensiones (Medio impacto, Medio esfuerzo)
6. **API versioning**
   - `TODO(backend/app.py:20)`: Versionado semántico en endpoints
   - **Esfuerzo**: 2-3 días, **Impacto**: Compatibilidad futura

7. **Batch evaluation**  
   - `TODO(backend/rules_engine/engine.py:211)`: Evaluar múltiples usuarios/fechas
   - **Esfuerzo**: 3-4 días, **Impacto**: Escalabilidad para reportes

8. **Real-time notifications**
   - `TODO(admin-ui)`: WebSockets para updates de reglas
   - **Esfuerzo**: 4-5 días, **Impacto**: UX mejorada

#### 📊 Observabilidad (Medio impacto, Bajo esfuerzo)
9. **Structured logging**
   - `TODO(backend/rules_engine/engine.py:304)`: structlog + JSON format
   - **Esfuerzo**: 1-2 días, **Impacto**: Debugging más eficiente

10. **Metrics & monitoring**
    - `TODO(backend/app.py)`: Prometheus metrics + Grafana dashboards  
    - **Esfuerzo**: 2-3 días, **Impacto**: Visibilidad operacional

### Decisiones arquitectónicas inferidas (ADR)

#### ADR-001: SQLite para desarrollo, PostgreSQL para producción
- **Contexto**: Necesidad de persistencia simple en dev, escalable en prod
- **Decisión**: SQLAlchemy ORM con database_url configurable
- **Consecuencias**: Fácil desarrollo, migración transparente, algunas features específicas de PostgreSQL no disponibles en dev

#### ADR-002: DSL propio vs reglas Python nativas  
- **Contexto**: Balance entre flexibilidad y seguridad para reglas de negocio
- **Decisión**: DSL JSON con validación Pydantic vs eval() de código Python
- **Consecuencias**: Más seguro, menos flexible, curva de aprendizaje para usuarios avanzados

#### ADR-003: Monolito vs microservicios
- **Contexto**: Simplicidad de desarrollo vs escalabilidad
- **Decisión**: Monolito FastAPI con separación modular interna
- **Consecuencias**: Más simple de desplegar y debuggear, límites de escalabilidad horizontal

#### ADR-004: Anti-repetición basada en historial vs estado en memoria
- **Contexto**: Evitar spam de mismas recomendaciones a usuarios
- **Decisión**: Query de tabla Audit vs cache en memoria/Redis
- **Consecuencias**: Consistente entre restarts, más lento, no requiere infraestructura adicional

#### Propuestas de ADR futuras
- **ADR-005**: Estrategia de cache distribuido (Redis vs in-memory)
- **ADR-006**: Event sourcing para auditoría vs tabla de cambios
- **ADR-007**: GraphQL vs REST para Admin UI API
- **ADR-008**: Procesamiento de datos en streaming vs batch diario

---

## Glosario técnico

- **ACWR**: Acute:Chronic Workload Ratio - Ratio entre carga de trabajo aguda (últimos 7 días) y crónica (últimos 28 días)
- **Anti-repetición**: Mecanismo que evita mostrar la misma variante de mensaje al mismo usuario en N días
- **Audit**: Registro de cada evaluación de regla (disparada o no) con contexto completo
- **DSL**: Domain Specific Language - Lenguaje específico para definir condiciones de reglas en JSON
- **Feature**: Métrica derivada calculada a partir de datos raw (ej: rolling means, z-scores)
- **TRIMP**: Training Impulse - Métrica de carga de entrenamiento basada en duración e intensidad
- **Cooldown**: Período mínimo entre disparos de la misma regla para el mismo usuario
- **Tenant**: Entidad organizacional para multi-tenancy (ej: hospital, clínica)
- **Rolling window**: Ventana deslizante para cálculos estadísticos (ej: media de 7 días)
- **Weighted random**: Selección aleatoria donde cada opción tiene probabilidad proporcional a su peso

