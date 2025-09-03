# API Reference - ETERNA DX Rules Engine

## Información General

**Base URL**: `http://127.0.0.1:8000` (desarrollo) | `https://api.eterna.com` (producción)
**Versión**: v0.1.0
**Formato**: JSON
**Autenticación**: Bearer Token (TODO: actualmente deshabilitada)

## Autenticación

```bash
# Actualmente deshabilitada (auth_enabled=false)
# Futuro: JWT Bearer token
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8000/rules
```

## Health Check

### GET /health

Verifica el estado del servicio.

```bash
curl http://127.0.0.1:8000/health
```

**Respuesta exitosa (200)**:
```json
{
  "status": "ok",
  "timestamp": "2025-03-03T10:30:00Z"
}
```

---

## Rules Management

### GET /rules

Lista todas las reglas con filtros opcionales.

**Parámetros de consulta**:
- `enabled` (bool): Filtrar por estado activo/inactivo
- `category` (str): Filtrar por categoría (activity, sleep, nutrition)
- `tenant_id` (str): Filtrar por tenant (default: "default")

```bash
# Todas las reglas
curl http://127.0.0.1:8000/rules

# Solo reglas activas de actividad
curl "http://127.0.0.1:8000/rules?enabled=true&category=activity"
```

**Respuesta exitosa (200)**:
```json
[
  {
    "id": "R-ACT-STEPS-LOW",
    "version": 1,
    "enabled": true,
    "tenant_id": "default",
    "category": "activity",
    "priority": 70,
    "severity": 2,
    "cooldown_days": 1,
    "max_per_day": 1,
    "tags": ["beginner", "steps"],
    "logic": {
      "all": [
        {
          "var": "steps",
          "agg": "current",
          "op": "<",
          "value": 5000,
          "required": true
        }
      ]
    },
    "locale": "es-ES",
    "created_by": "admin",
    "updated_by": "admin",
    "created_at": "2025-03-01T10:00:00Z",
    "updated_at": "2025-03-01T10:00:00Z",
    "messages": [
      {
        "id": 123,
        "locale": "es-ES",
        "text": "¡Hoy has caminado solo {{steps.current}} pasos! Intenta llegar a 10,000.",
        "weight": 3,
        "active": true
      },
      {
        "id": 124,
        "locale": "es-ES", 
        "text": "Tus pasos están bajos hoy: {{steps.current}}. ¡Sal a caminar!",
        "weight": 2,
        "active": true
      }
    ]
  }
]
```

### POST /rules

Crea una nueva regla.

**Body (JSON)**:
```json
{
  "id": "R-SLEEP-SHORT",
  "category": "sleep",
  "priority": 80,
  "severity": 3,
  "cooldown_days": 2,
  "max_per_day": 1,
  "tags": ["sleep", "recovery"],
  "logic": {
    "all": [
      {
        "var": "sleep_duration",
        "agg": "current",
        "op": "<",
        "value": 6.5,
        "required": true
      }
    ]
  },
  "messages": [
    {
      "text": "Dormiste solo {{sleep_duration.current}} horas. Intenta dormir 7-9 horas.",
      "weight": 1
    }
  ]
}
```

**Respuesta exitosa (201)**:
```json
{
  "id": "R-SLEEP-SHORT",
  "message": "Regla creada exitosamente"
}
```

**Errores**:
- `400`: Datos inválidos o DSL malformado
- `409`: ID de regla ya existe
- `403`: Sin permisos para crear reglas

### GET /rules/{rule_id}

Obtiene una regla específica por ID.

```bash
curl http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW
```

**Respuesta exitosa (200)**: Mismo formato que elemento de GET /rules

**Errores**:
- `404`: Regla no encontrada

### PUT /rules/{rule_id}

Actualiza una regla completa (reemplaza todos los campos).

**Body (JSON)**: Mismo formato que POST /rules

```bash
curl -X PUT http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW \
  -H "Content-Type: application/json" \
  -d '{"id": "R-ACT-STEPS-LOW", "enabled": false, ...}'
```

**Respuesta exitosa (200)**:
```json
{
  "id": "R-ACT-STEPS-LOW",
  "message": "Regla actualizada exitosamente"
}
```

### DELETE /rules/{rule_id}

Elimina una regla específica.

```bash
curl -X DELETE http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW
```

**Respuesta exitosa (200)**:
```json
{
  "id": "R-ACT-STEPS-LOW",
  "message": "Regla eliminada exitosamente"
}
```

**Errores**:
- `404`: Regla no encontrada
- `403`: Sin permisos para eliminar

### DELETE /rules/all

⚠️ **PELIGROSO**: Elimina TODAS las reglas (solo para testing).

```bash
curl -X DELETE http://127.0.0.1:8000/rules/all
```

**Respuesta exitosa (200)**:
```json
{
  "deleted": 133,
  "deleted_messages": 1295,
  "message": "Se eliminaron 133 reglas y 1295 mensajes"
}
```

---

## Message Variants Management

### POST /rules/{rule_id}/variants

Añade una nueva variante de mensaje a una regla existente.

```bash
curl -X POST http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW/variants \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Nueva variante: {{steps.current}} pasos registrados hoy.",
    "weight": 2,
    "active": true
  }'
```

**Respuesta exitosa (201)**:
```json
{
  "id": 125,
  "message": "Variante de mensaje añadida"
}
```

### PATCH /rules/{rule_id}/variants/{message_id}

Actualiza una variante específica de mensaje.

```bash
curl -X PATCH http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW/variants/125 \
  -H "Content-Type: application/json" \
  -d '{
    "weight": 5,
    "active": false
  }'
```

**Respuesta exitosa (200)**:
```json
{
  "id": 125,
  "message": "Variante actualizada"
}
```

### DELETE /rules/{rule_id}/variants/{message_id}

Elimina una variante específica de mensaje.

```bash
curl -X DELETE http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW/variants/125
```

**Respuesta exitosa (200)**:
```json
{
  "id": 125,
  "message": "Variante eliminada"
}
```

---

## Rule Operations

### POST /rules/{rule_id}/enable

Activa o desactiva una regla.

```bash
curl -X POST http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW/enable \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

**Respuesta exitosa (200)**:
```json
{
  "id": "R-ACT-STEPS-LOW",
  "enabled": true,
  "message": "Regla activada"
}
```

### POST /rules/{rule_id}/clone

Clona una regla existente con nuevo ID.

```bash
curl -X POST http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW/clone \
  -H "Content-Type: application/json" \
  -d '{"new_id": "R-ACT-STEPS-LOW-V2"}'
```

**Respuesta exitosa (201)**:
```json
{
  "id": "R-ACT-STEPS-LOW-V2",
  "message": "Regla clonada exitosamente"
}
```

---

## Import/Export

### GET /rules/export

Exporta todas las reglas en formato JSON.

```bash
curl http://127.0.0.1:8000/rules/export > reglas_backup.json
```

**Respuesta exitosa (200)**:
```json
[
  {
    "id": "R-ACT-STEPS-LOW",
    "version": 1,
    "enabled": true,
    "category": "activity",
    "priority": 70,
    "logic": {...},
    "messages": {...}
  }
]
```

### POST /rules/import

Importa reglas desde JSON o YAML.

**Parámetros de consulta**:
- `format` (str): "json" o "yaml" (default: auto-detecta)
- `overwrite` (bool): Si sobrescribir reglas existentes (default: false)

```bash
# Importar JSON
curl -X POST http://127.0.0.1:8000/rules/import \
  -H "Content-Type: application/json" \
  -d @reglas_backup.json

# Importar YAML
curl -X POST "http://127.0.0.1:8000/rules/import?format=yaml" \
  -H "Content-Type: text/yaml" \
  --data-binary @reglas.yaml
```

**Respuesta exitosa (200)**:
```json
{
  "imported": 5,
  "updated": 2,
  "errors": [],
  "message": "Importación completada: 5 nuevas, 2 actualizadas"
}
```

**Errores en importación**:
```json
{
  "imported": 3,
  "updated": 1,
  "errors": [
    {
      "rule_id": "R-INVALID",
      "error": "Campo 'logic' requerido"
    }
  ],
  "message": "Importación parcial: 3 nuevas, 1 actualizada, 1 error"
}
```

### POST /rules/import_csv

Importa reglas desde CSV con formato específico.

**Formato CSV esperado**:
```csv
message_id,category,template_text
STEPS_001,activity,"Camina más: {{steps.current}} pasos hoy"
STEPS_002,activity,"¡Solo {{steps.current}} pasos! Intenta 10,000"
SLEEP_001,sleep,"Dormiste {{sleep_duration.current}}h. Objetivo: 7-9h"
```

```bash
curl -X POST http://127.0.0.1:8000/rules/import_csv \
  -H "Content-Type: text/csv" \
  --data-binary @reglas.csv
```

**Respuesta exitosa (200)**:
```json
{
  "imported": 10,
  "updated": 3,
  "grouped_rules": 5,
  "message": "CSV importado: 5 reglas creadas con 13 variantes"
}
```

---

## Rule Evaluation & Simulation

### POST /simulate

Simula la evaluación de reglas para un usuario en una fecha específica.

**Body (JSON)**:
```json
{
  "user_id": "4f620746-1ee2-44c4-8338-789cfdb2078f",
  "date": "2025-03-03",
  "tenant_id": "default",
  "debug": true
}
```

```bash
curl -X POST http://127.0.0.1:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "4f620746-1ee2-44c4-8338-789cfdb2078f",
    "date": "2025-03-03",
    "debug": true
  }'
```

**Respuesta exitosa (200)**:
```json
{
  "events": [
    {
      "date": "2025-03-03",
      "tenant_id": "default",
      "user_id": "4f620746-1ee2-44c4-8338-789cfdb2078f",
      "rule_id": "R-ACT-STEPS-LOW",
      "category": "activity",
      "severity": 2,
      "priority": 70,
      "message_id": 123,
      "message_text": "¡Hoy has caminado solo 3,247 pasos! Intenta llegar a 10,000.",
      "locale": "es-ES",
      "why": [
        {
          "type": "numeric",
          "var": "steps",
          "agg": "current",
          "op": "<",
          "threshold": 5000,
          "observed": 3247,
          "result": true
        }
      ]
    }
  ],
  "debug": {
    "user_features": {
      "steps": {
        "current": 3247,
        "mean_7d": 6543.2,
        "delta_pct_3v14": -0.23
      },
      "sleep_duration": {
        "current": 7.2,
        "mean_7d": 7.1
      }
    },
    "rules_evaluated": [
      {
        "rule_id": "R-ACT-STEPS-LOW",
        "fired": true,
        "priority": 70,
        "severity": 2,
        "why": [
          {
            "type": "numeric",
            "var": "steps",
            "agg": "current", 
            "op": "<",
            "threshold": 5000,
            "observed": 3247,
            "result": true
          }
        ]
      },
      {
        "rule_id": "R-SLEEP-QUALITY",
        "fired": false,
        "priority": 60,
        "severity": 1,
        "why": [
          {
            "type": "numeric",
            "var": "sleep_quality",
            "agg": "current",
            "op": "<",
            "threshold": 3,
            "observed": 4,
            "result": false
          }
        ]
      }
    ],
    "performance": {
      "total_duration_ms": 245,
      "feature_calculation_ms": 123,
      "rule_evaluation_ms": 89,
      "database_queries": 7
    }
  }
}
```

**Errores**:
- `400`: Parámetros inválidos (user_id, date)
- `404`: Usuario sin datos para la fecha especificada
- `500`: Error interno en evaluación

---

## Analytics & Statistics

### GET /analytics/logs

Obtiene logs de auditoría con filtros avanzados.

**Parámetros de consulta**:
- `user_id` (str): Filtrar por usuario específico
- `rule_id` (str): Filtrar por regla específica
- `fired` (bool): Solo eventos disparados (true) o no disparados (false)
- `date_from` (date): Fecha inicial (formato: YYYY-MM-DD)
- `date_to` (date): Fecha final
- `limit` (int): Número máximo de resultados (default: 100)
- `offset` (int): Desplazamiento para paginación

```bash
# Últimos 50 eventos disparados
curl "http://127.0.0.1:8000/analytics/logs?fired=true&limit=50"

# Eventos de usuario específico en rango de fechas
curl "http://127.0.0.1:8000/analytics/logs?user_id=4f620746-1ee2-44c4-8338-789cfdb2078f&date_from=2025-03-01&date_to=2025-03-03"
```

**Respuesta exitosa (200)**:
```json
{
  "logs": [
    {
      "id": 1234,
      "tenant_id": "default",
      "user_id": "4f620746-1ee2-44c4-8338-789cfdb2078f",
      "date": "2025-03-03",
      "rule_id": "R-ACT-STEPS-LOW",
      "fired": true,
      "discarded_reason": null,
      "message_id": 123,
      "created_at": "2025-03-03T10:30:45Z",
      "why": {
        "conditions": [
          {
            "type": "numeric",
            "var": "steps",
            "agg": "current",
            "op": "<",
            "threshold": 5000,
            "observed": 3247,
            "result": true
          }
        ]
      },
      "values": {
        "steps": {"current": 3247, "mean_7d": 6543.2},
        "sleep_duration": {"current": 7.2}
      }
    }
  ],
  "pagination": {
    "total": 1547,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

### GET /analytics/triggers

Obtiene estadísticas de disparos por regla con series temporales.

**Parámetros de consulta**:
- `rule_id` (str): Regla específica (opcional, default: todas)
- `date_from` (date): Fecha inicial
- `date_to` (date): Fecha final
- `group_by` (str): Agrupación temporal ("day", "week", "month")

```bash
# Estadísticas de todas las reglas por día
curl "http://127.0.0.1:8000/analytics/triggers?date_from=2025-03-01&date_to=2025-03-07&group_by=day"

# Estadísticas de regla específica
curl "http://127.0.0.1:8000/analytics/triggers?rule_id=R-ACT-STEPS-LOW&group_by=day"
```

**Respuesta exitosa (200)**:
```json
{
  "summary": {
    "total_triggers": 1247,
    "unique_users": 89,
    "unique_rules": 23,
    "date_range": {
      "from": "2025-03-01",
      "to": "2025-03-07"
    }
  },
  "by_rule": {
    "R-ACT-STEPS-LOW": {
      "total_triggers": 234,
      "unique_users": 67,
      "avg_per_day": 33.4,
      "timeline": [
        {"date": "2025-03-01", "triggers": 31, "users": 12},
        {"date": "2025-03-02", "triggers": 28, "users": 11},
        {"date": "2025-03-03", "triggers": 45, "users": 18}
      ]
    },
    "R-SLEEP-SHORT": {
      "total_triggers": 156,
      "unique_users": 34,
      "avg_per_day": 22.3,
      "timeline": [
        {"date": "2025-03-01", "triggers": 19, "users": 8},
        {"date": "2025-03-02", "triggers": 23, "users": 9}
      ]
    }
  },
  "timeline_aggregate": [
    {"date": "2025-03-01", "total_triggers": 178, "unique_users": 45},
    {"date": "2025-03-02", "total_triggers": 203, "unique_users": 52},
    {"date": "2025-03-03", "total_triggers": 267, "unique_users": 61}
  ]
}
```

### GET /rules/{rule_id}/stats

Obtiene estadísticas detalladas de una regla específica.

```bash
curl http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW/stats
```

**Respuesta exitosa (200)**:
```json
{
  "rule_id": "R-ACT-STEPS-LOW",
  "total_evaluations": 2341,
  "total_triggers": 567,
  "trigger_rate": 0.242,
  "unique_users_triggered": 89,
  "last_triggered": "2025-03-03T14:22:00Z",
  "avg_triggers_per_user": 6.4,
  "message_variants": [
    {
      "message_id": 123,
      "text": "¡Hoy has caminado solo {{steps.current}} pasos!",
      "times_selected": 234,
      "selection_rate": 0.413
    },
    {
      "message_id": 124,
      "text": "Tus pasos están bajos hoy: {{steps.current}}",
      "times_selected": 333,
      "selection_rate": 0.587
    }
  ],
  "performance": {
    "avg_evaluation_time_ms": 23.4,
    "avg_feature_calculation_ms": 12.1
  }
}
```

### GET /rules/{rule_id}/changelog

Obtiene el historial de cambios de una regla.

**Parámetros de consulta**:
- `limit` (int): Número máximo de cambios (default: 50)
- `offset` (int): Desplazamiento para paginación

```bash
curl "http://127.0.0.1:8000/rules/R-ACT-STEPS-LOW/changelog?limit=10"
```

**Respuesta exitosa (200)**:
```json
{
  "changes": [
    {
      "id": 789,
      "created_at": "2025-03-03T09:15:00Z",
      "user": "admin",
      "role": "admin", 
      "action": "update",
      "entity_type": "rule",
      "entity_id": "R-ACT-STEPS-LOW",
      "before": {
        "enabled": false,
        "priority": 60
      },
      "after": {
        "enabled": true,
        "priority": 70
      }
    },
    {
      "id": 788,
      "created_at": "2025-03-02T16:30:00Z",
      "user": "editor_user",
      "role": "editor",
      "action": "create",
      "entity_type": "message",
      "entity_id": "124",
      "before": null,
      "after": {
        "rule_id": "R-ACT-STEPS-LOW",
        "text": "Nueva variante de mensaje",
        "weight": 2,
        "active": true
      }
    }
  ],
  "pagination": {
    "total": 23,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

---

## Variables Management

### GET /variables

Lista todas las variables disponibles para usar en reglas DSL.

**Parámetros de consulta**:
- `category` (str): Filtrar por categoría (activity, sleep, hrv, etc.)
- `type` (str): Filtrar por tipo (number, boolean, string)
- `tenant_id` (str): Filtrar por tenant

```bash
# Todas las variables
curl http://127.0.0.1:8000/variables

# Solo variables de actividad
curl "http://127.0.0.1:8000/variables?category=activity"
```

**Respuesta exitosa (200)**:
```json
[
  {
    "id": 1,
    "key": "steps",
    "label": "Pasos diarios",
    "description": "Número total de pasos registrados en el día",
    "unit": "steps",
    "type": "number",
    "allowed_aggregators": {
      "current": "Valor del día actual",
      "mean_7d": "Media de 7 días",
      "mean_14d": "Media de 14 días",
      "delta_pct_3v14": "Cambio porcentual 3d vs 14d"
    },
    "valid_min": 0,
    "valid_max": 50000,
    "missing_policy": "skip",
    "decimals": 0,
    "category": "activity",
    "tenant_id": "default",
    "examples": {
      "examples": [8500, 12300, 6700, 15400]
    }
  },
  {
    "id": 2,
    "key": "sleep_duration",
    "label": "Duración del sueño",
    "description": "Horas totales de sueño por noche",
    "unit": "hours",
    "type": "number",
    "allowed_aggregators": {
      "current": "Valor de la noche anterior",
      "mean_7d": "Media de 7 noches",
      "mean_14d": "Media de 14 noches"
    },
    "valid_min": 0,
    "valid_max": 24,
    "missing_policy": "skip",
    "decimals": 1,
    "category": "sleep",
    "tenant_id": "default",
    "examples": {
      "examples": [7.2, 8.1, 6.5, 9.0]
    }
  }
]
```

---

## Error Codes & Responses

### Códigos de estado HTTP

| Código | Significado | Casos de uso |
|--------|-------------|--------------|
| `200` | OK | Operación exitosa |
| `201` | Created | Recurso creado exitosamente |
| `400` | Bad Request | Datos inválidos o malformados |
| `401` | Unauthorized | Token de autenticación inválido |
| `403` | Forbidden | Sin permisos para la operación |
| `404` | Not Found | Recurso no encontrado |
| `409` | Conflict | Recurso ya existe (ej: ID duplicado) |
| `422` | Unprocessable Entity | Validación de Pydantic falló |
| `500` | Internal Server Error | Error interno del servidor |

### Formato de errores

```json
{
  "detail": "Descripción del error",
  "error_code": "VALIDATION_ERROR",
  "field_errors": {
    "logic.all.0.value": "Valor debe ser numérico"
  },
  "timestamp": "2025-03-03T10:30:00Z"
}
```

### Errores comunes

#### Validación DSL (400)
```json
{
  "detail": "Sintaxis DSL inválida",
  "error_code": "DSL_VALIDATION_ERROR",
  "field_errors": {
    "logic.all.0.var": "Variable 'invalid_var' no existe",
    "logic.all.0.op": "Operador 'invalid_op' no soportado"
  }
}
```

#### Regla no encontrada (404)
```json
{
  "detail": "Regla con ID 'R-NONEXISTENT' no encontrada",
  "error_code": "RULE_NOT_FOUND"
}
```

#### Sin permisos (403)
```json
{
  "detail": "Permiso denegado",
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "required_role": "admin",
  "current_role": "viewer"
}
```

#### Error interno (500)
```json
{
  "detail": "Error interno del servidor",
  "error_code": "INTERNAL_ERROR",
  "request_id": "req_123456789"
}
```

---

## Rate Limiting & Quotas

### Límites por endpoint (TODO: implementar)

| Endpoint | Límite | Ventana |
|----------|--------|---------|
| `POST /simulate` | 100 req/min | Por IP |
| `POST /rules` | 10 req/min | Por usuario |
| `GET /analytics/*` | 1000 req/hour | Por usuario |
| `POST /rules/import*` | 5 req/hour | Por usuario |

### Headers de rate limiting

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1677834600
```

---

## Webhooks (TODO: futura implementación)

### POST /webhooks/rules

Registra webhook para notificaciones de eventos de reglas.

```json
{
  "url": "https://mi-app.com/webhook/rules",
  "events": ["rule.triggered", "rule.created", "rule.updated"],
  "secret": "webhook_secret_key"
}
```

### Eventos disponibles

- `rule.triggered`: Regla disparada para un usuario
- `rule.created`: Nueva regla creada
- `rule.updated`: Regla modificada
- `rule.deleted`: Regla eliminada
- `evaluation.completed`: Evaluación completada para usuario/fecha

### Payload de webhook

```json
{
  "event": "rule.triggered",
  "timestamp": "2025-03-03T10:30:00Z",
  "data": {
    "user_id": "4f620746-1ee2-44c4-8338-789cfdb2078f",
    "rule_id": "R-ACT-STEPS-LOW",
    "message_text": "¡Hoy has caminado solo 3,247 pasos!",
    "severity": 2,
    "category": "activity"
  },
  "signature": "sha256=abc123..."
}
```

---

## SDK y Librerías Cliente

### Python SDK (TODO)

```python
from eterna_rules import RulesClient

client = RulesClient(base_url="http://127.0.0.1:8000", token="your_token")

# Crear regla
rule = client.rules.create({
    "id": "MY-RULE",
    "logic": {"all": [{"var": "steps", "op": "<", "value": 5000}]},
    "messages": [{"text": "Camina más hoy!"}]
})

# Simular evaluación
result = client.simulate(user_id="user123", date="2025-03-03")
print(f"Eventos generados: {len(result.events)}")
```

### JavaScript SDK (TODO)

```javascript
import { RulesClient } from '@eterna/rules-sdk';

const client = new RulesClient({
  baseURL: 'http://127.0.0.1:8000',
  token: 'your_token'
});

// Listar reglas
const rules = await client.rules.list({ enabled: true });

// Simular evaluación
const simulation = await client.simulate({
  userId: 'user123',
  date: '2025-03-03',
  debug: true
});
```

---

## Changelog API

### v0.1.0 (Actual)
- ✅ CRUD completo de reglas
- ✅ Sistema de variantes de mensajes con pesos
- ✅ Evaluación y simulación de reglas
- ✅ Import/export JSON/YAML/CSV
- ✅ Analytics y estadísticas básicas
- ✅ Anti-repetición inteligente
- ✅ Sistema de auditoría y logs

### v0.2.0 (Próximo)
- 🔄 Autenticación JWT/OAuth2
- 🔄 Rate limiting
- 🔄 Webhooks
- 🔄 Batch evaluation endpoints
- 🔄 GraphQL API alternativa

### v0.3.0 (Futuro)
- ⏳ API versioning (/v1/, /v2/)
- ⏳ Real-time WebSocket API
- ⏳ ML-based rule recommendations
- ⏳ Advanced analytics endpoints
