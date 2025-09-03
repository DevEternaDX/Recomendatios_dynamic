# 📚 Documentación ETERNA DX Rules Engine

Bienvenido a la documentación completa del sistema de recomendaciones inteligentes ETERNA DX Rules Engine.

## 🚀 Inicio Rápido

¿Primera vez con el sistema? Comienza aquí:

1. **[README Principal](README.md)** - Visión general y guía de inicio
2. **[Guía de Instalación](README.md#guía-de-inicio)** - Configuración local en 5 minutos
3. **[API Reference](api.md)** - Endpoints principales para integración
4. **[Ejemplos de Uso](README.md#ejemplos-de-uso)** - Casos de uso comunes

## 📖 Documentación por Audiencia

### 👩‍💻 Desarrolladores
- **[Arquitectura del Sistema](arquitectura.md)** - Diseño técnico y patrones
- **[API Reference Completa](api.md)** - Todos los endpoints con ejemplos
- **[Guía de Desarrollo](README.md#configuración-mínima)** - Setup local y workflows

### 🏗️ DevOps/SRE
- **[Guía de Deployment](deployment.md)** - Despliegue en todos los entornos
- **[Monitoreo y Alertas](deployment.md#monitoreo-y-observabilidad)** - Métricas y dashboards
- **[Runbooks Operacionales](deployment.md#procedimientos-operacionales)** - Procedimientos de emergencia

### 🎯 Product Managers
- **[Funcionalidades del Sistema](README.md#visión-general)** - Qué hace el sistema
- **[DSL de Reglas](arquitectura.md#dsl-domain-specific-language)** - Cómo crear reglas de negocio
- **[Analytics y Reportes](api.md#analytics--statistics)** - Métricas disponibles

### 🧪 QA/Testing
- **[Guía de Pruebas](README.md#pruebas)** - Cómo ejecutar tests
- **[Endpoints de Simulación](api.md#rule-evaluation--simulation)** - Testing de reglas
- **[Datos de Ejemplo](README.md#ejemplos-de-uso)** - Datasets para pruebas

## 📋 Índice Completo

### Documentación Principal

| Documento | Descripción | Audiencia |
|-----------|-------------|-----------|
| **[README.md](README.md)** | Visión general, instalación y guía completa | Todos |
| **[arquitectura.md](arquitectura.md)** | Diseño técnico, patrones y diagramas | Desarrolladores |
| **[api.md](api.md)** | Referencia completa de API REST | Desarrolladores |
| **[deployment.md](deployment.md)** | Despliegue, monitoreo y operaciones | DevOps/SRE |

### Secciones Principales

#### 🏛️ Arquitectura y Diseño
- [C4 - Contexto y Contenedores](arquitectura.md#c4---contexto-nivel-1)
- [Grafo de Dependencias](arquitectura.md#grafo-de-dependencias-entre-módulos)
- [Flujos Críticos](arquitectura.md#flujo-crítico-evaluación-de-recomendaciones)
- [Modelo de Datos](arquitectura.md#modelo-de-datos-detallado)
- [DSL de Reglas](arquitectura.md#dsl-domain-specific-language)
- [Patrones de Diseño](arquitectura.md#patrones-de-diseño-implementados)

#### 🔧 API y Desarrollo
- [Gestión de Reglas](api.md#rules-management)
- [Variantes de Mensajes](api.md#message-variants-management)
- [Simulación y Evaluación](api.md#rule-evaluation--simulation)
- [Import/Export](api.md#importexport)
- [Analytics](api.md#analytics--statistics)
- [Variables del Sistema](api.md#variables-management)

#### 🚀 Deployment y Operaciones
- [Configuración por Entornos](deployment.md#configuración-por-entornos)
- [Kubernetes](deployment.md#production-kubernetes)
- [Base de Datos](deployment.md#base-de-datos)
- [Monitoreo](deployment.md#monitoreo-y-observabilidad)
- [CI/CD](deployment.md#cicd-pipeline)
- [Troubleshooting](deployment.md#troubleshooting)

#### 📊 Funcionalidades de Negocio
- [Motor de Reglas](README.md#backend-rules_engine---motor-de-reglas-core)
- [Anti-repetición Inteligente](README.md#funciones-críticas)
- [Selección Ponderada](README.md#funciones-críticas)
- [Auditoría y Logs](api.md#analytics--statistics)
- [Estadísticas](api.md#get-analyticstiggers)

## 🎯 Casos de Uso Comunes

### Crear una Regla Simple
```bash
# Ver guía completa en README.md#ejemplos-de-uso
curl -X POST http://127.0.0.1:8000/rules \
  -H "Content-Type: application/json" \
  -d '{"id": "R-STEPS-LOW", "logic": {...}, "messages": [...]}'
```

### Simular Reglas para Testing
```bash
# Ver API reference completa en api.md#post-simulate
curl -X POST http://127.0.0.1:8000/simulate \
  -d '{"user_id": "test-user", "date": "2025-03-03", "debug": true}'
```

### Importar Reglas desde CSV
```bash
# Ver documentación en api.md#post-rulesimport_csv
curl -X POST http://127.0.0.1:8000/rules/import_csv \
  --data-binary @reglas.csv
```

### Ver Estadísticas de Reglas
```bash
# Ver analytics completos en api.md#get-analyticstiggers
curl "http://127.0.0.1:8000/analytics/triggers?group_by=day"
```

## 🔍 Búsqueda Rápida

### Por Funcionalidad
- **Crear reglas**: [README.md](README.md#ejemplos-de-uso) → [API](api.md#post-rules)
- **DSL de condiciones**: [Arquitectura](arquitectura.md#dsl-domain-specific-language)
- **Anti-repetición**: [Engine.py](README.md#select_message_for_rule)
- **Importar datos**: [API Import](api.md#importexport)
- **Ver estadísticas**: [Analytics API](api.md#analytics--statistics)
- **Deployment**: [Guía completa](deployment.md)

### Por Archivo de Código
- **`backend/rules_engine/engine.py`**: [Documentación](README.md#backend-rules_engine-engine.py-211-327---función-evaluate_user)
- **`backend/api/rules.py`**: [API Reference](api.md#rules-management)
- **`admin-ui/lib/api.ts`**: [Cliente API](README.md#admin-ui-lib-api.ts---cliente-api-typescript)
- **`config.py`**: [Configuración](README.md#configuración-mínima)

### Por Error o Problema
- **404 en endpoints**: [Troubleshooting](deployment.md#troubleshooting)
- **Reglas no disparan**: [Debugging](README.md#problema-reglas-no-disparan-para-usuarios)
- **Performance lento**: [Optimización](deployment.md#2-high-memory-usage)
- **CORS errors**: [Configuración](README.md#problema-cors)

## 📈 Roadmap y Mejoras

### Estado Actual (v0.1.0)
- ✅ Motor de reglas completo con DSL
- ✅ Admin UI funcional
- ✅ API REST completa
- ✅ Sistema de anti-repetición
- ✅ Import/export múltiples formatos
- ✅ Analytics y estadísticas

### Próximas Versiones
- 🔄 **v0.2.0**: Autenticación JWT, Rate limiting, Webhooks
- ⏳ **v0.3.0**: GraphQL API, Real-time notifications
- ⏳ **v0.4.0**: ML-based recommendations, Advanced analytics

Ver [Plan de mejoras completo](README.md#plan-de-mejoras)

## 🤝 Contribución

### Cómo Contribuir
1. **Reportar bugs**: Crear issue con template de bug
2. **Solicitar features**: Usar template de feature request  
3. **Contribuir código**: Fork → Branch → PR
4. **Mejorar documentación**: PRs bienvenidos

### Estándares de Código
- **Python**: PEP 8, type hints, docstrings Google style
- **TypeScript**: ESLint config, JSDoc comments
- **Tests**: Pytest con >80% cobertura
- **Commits**: Conventional commits format

## 📞 Soporte

### Canales de Soporte
- **Issues de GitHub**: Para bugs y feature requests
- **Slack**: `#eterna-rules-engine` para discusiones
- **Email**: `dev-team@eterna.com` para consultas urgentes

### SLA de Respuesta
- **P0 (Crítico)**: 15 minutos
- **P1 (Alto)**: 1 hora  
- **P2 (Medio)**: 4 horas
- **P3 (Bajo)**: 24 horas

Ver [matriz de escalación completa](deployment.md#emergency-contacts)

## 📝 Changelog

### v0.1.0 (2025-03-03)
- 🎉 Release inicial del sistema
- ✅ Motor de reglas con DSL JSON
- ✅ Admin UI completa con Next.js
- ✅ API REST con FastAPI
- ✅ Sistema de variantes con pesos
- ✅ Anti-repetición inteligente
- ✅ Import/export JSON/YAML/CSV
- ✅ Analytics y estadísticas
- ✅ Auditoría completa

Ver [changelog completo](api.md#changelog-api)

---

## 🏷️ Tags y Metadatos

**Tecnologías**: FastAPI, Next.js, SQLAlchemy, React, PostgreSQL, Redis, Kubernetes
**Categorías**: Rules Engine, Recommendations, Healthcare, Analytics, ML
**Audiencia**: Developers, DevOps, Product Managers, QA
**Madurez**: Production Ready (v0.1.0)
**Licencia**: Propietaria - ETERNA Healthcare

---

*Última actualización: 2025-03-03 | Versión documentación: 1.0.0*
