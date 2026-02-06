# 📅 High-Precision Date Reasoning Agent
## Agente de Razonamiento de Fechas para Operaciones Financieras

---

## 🎯 ¿Qué es este proyecto?

Es un **agente inteligente** que convierte consultas en lenguaje natural sobre fechas y períodos en rangos de fechas precisos, diseñado específicamente para operaciones financieras en el contexto peruano.

### Ejemplos de consultas que entiende:

| Consulta | Resultado |
|----------|-----------|
| "Q3 2024" | 2024-07-01 → 2024-09-30 |
| "semana pasada" | Rango de la semana anterior |
| "mes anterior" | Primer y último día del mes pasado |
| "feriados julio 2024" | Lista de feriados bancarios peruanos |
| "cuánto cashback he ganado este mes?" | Detecta período "este mes" |

---

## 🏗️ Arquitectura

### Principio Fundamental

> **"El agente maneja SOLO el entendimiento semántico. Todas las computaciones de fechas las realizan HERRAMIENTAS determinísticas."**

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD RUN                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Puerto 8080 (Público)                   │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              🎨 GRADIO UI (Frontend)                 │  │  │
│  │  │                                                      │  │  │
│  │  │  • Interfaz interactiva                             │  │  │
│  │  │  • 145+ ejemplos de consultas                       │  │  │
│  │  │  • Visualización de resultados                      │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼ (interno)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Puerto 8000 (Interno)                   │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │            🔧 FastAPI Backend (Agente)               │  │  │
│  │  │                                                      │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │  │
│  │  │  │ Semantic    │  │   Query     │  │    Tool     │  │  │  │
│  │  │  │ Parser      │→ │ Decomposer  │→ │ Orchestrator│  │  │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  │  │  │
│  │  │         │                                │          │  │  │
│  │  │         ▼                                ▼          │  │  │
│  │  │  ┌─────────────┐              ┌─────────────────┐   │  │  │
│  │  │  │ Azure OpenAI│              │   HERRAMIENTAS  │   │  │  │
│  │  │  │ (GPT-4)     │              │ (Determinísticas)│   │  │  │
│  │  │  └─────────────┘              └─────────────────┘   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes Principales

### 1. **Herramientas (Tools)** - Fuente de Verdad

| Herramienta | Función |
|-------------|---------|
| `get_current_date_info` | Establece punto de referencia inmutable (fecha/hora actual) |
| `resolve_period` | Convierte "Q3 2024", "mes pasado" → rangos de fechas |
| `get_holiday_calendar` | Retorna feriados del calendario peruano bancario |
| `compute_date_range` | Aritmética de fechas (días hábiles, fin de mes, etc.) |

### 2. **Calendarios**

| Calendario | Descripción |
|------------|-------------|
| `GREGORIAN` | Calendario estándar (solo fines de semana) |
| `PERU_BANKING` | Calendario bancario peruano con feriados oficiales |

#### Feriados Peruanos Incluidos:
- 🎉 Año Nuevo (1 enero)
- ✝️ Semana Santa (calculado con algoritmo Computus)
- 👷 Día del Trabajo (1 mayo)
- 🇵🇪 Fiestas Patrias (28-29 julio)
- 🎖️ Batalla de Angamos (8 octubre)
- ⛪ Todos los Santos (1 noviembre)
- 🙏 Inmaculada Concepción (8 diciembre)
- 🎄 Navidad (25 diciembre)

### 3. **Agente Semántico**

```
Consulta del Usuario
        │
        ▼
┌───────────────┐
│ Semantic      │ ← Usa Azure OpenAI (GPT-4) para entender
│ Parser        │   la intención del usuario
└───────────────┘
        │
        ▼
┌───────────────┐
│ Query         │ ← Descompone consultas complejas en pasos
│ Decomposer    │   simples
└───────────────┘
        │
        ▼
┌───────────────┐
│ Tool          │ ← Ejecuta las herramientas en el orden
│ Orchestrator  │   correcto
└───────────────┘
        │
        ▼
   Resultado
```

---

## 📁 Estructura del Proyecto

```
agent_date/
├── 📄 Dockerfile              # Configuración Docker para Cloud Run
├── 📄 start.sh                # Script de inicio del contenedor
├── 📄 server.py               # Backend FastAPI (puerto 8000)
├── 📄 app.py                  # Frontend Gradio (puerto 8080)
├── 📄 requirements.txt        # Dependencias Python
│
├── 📁 src/date_agent/
│   ├── 📁 agent/              # Lógica del agente
│   │   ├── date_agent.py      # Clase principal DateReasoningAgent
│   │   ├── semantic_parser.py # Parser semántico con Azure OpenAI
│   │   └── query_decomposer.py
│   │
│   ├── 📁 tools/              # FUENTE DE VERDAD
│   │   ├── current_date_tool.py
│   │   ├── resolve_period_tool.py
│   │   ├── holiday_calendar_tool.py
│   │   └── compute_date_range_tool.py
│   │
│   ├── 📁 calendars/          # Implementaciones de calendarios
│   │   ├── gregorian.py
│   │   ├── peru_banking.py
│   │   └── peru_banking_validated.py  # Con validación externa
│   │
│   ├── 📁 localization/       # Soporte multiidioma
│   │   ├── spanish.py         # Patrones en español
│   │   └── english.py
│   │
│   ├── 📁 models/             # Schemas Pydantic
│   │   └── date_models.py
│   │
│   └── 📁 core/               # Configuración y utilidades
│       ├── config.py
│       ├── constants.py
│       └── audit.py           # Trazabilidad de cálculos
│
└── 📁 tests/                  # 289 tests
    ├── 📁 unit/
    │   ├── test_current_date_tool.py
    │   ├── test_resolve_period_tool.py
    │   └── test_ground_truth.py   # Validación con fuentes externas
    │
    └── 📁 integration/
        └── test_query_examples.py  # 153 tests de consultas
```

---

## 🚀 Cómo Usar

### Opción 1: Interfaz Web (Producción)

**URL:** https://date-agent-472802182662.europe-west1.run.app

1. Abre la URL en tu navegador
2. Selecciona un ejemplo del dropdown (145+ consultas)
3. O escribe tu propia consulta
4. Haz clic en "🔍 Process Query"

### Opción 2: Ejecución Local

```bash
# 1. Clonar y entrar al proyecto
cd /Users/bigboy/Sites/Bcp_project/project/0_PERSONAL/agent_date

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales de Azure OpenAI

# 5. Ejecutar
./run.sh
# O manualmente:
python server.py &  # Backend en puerto 8000
python app.py       # Frontend en puerto 7860
```

### Opción 3: Docker Local

```bash
# Construir imagen
docker build -t date-agent .

# Ejecutar
docker run -p 8080:8080 \
    -e AZURE_OPENAI_ENDPOINT=https://... \
    -e AZURE_OPENAI_API_KEY=... \
    date-agent

# Abrir http://localhost:8080
```

---

## 🧪 Cómo Probar

### Ejecutar Tests

```bash
# Todos los tests (289)
pytest tests/ -v

# Solo tests unitarios
pytest tests/unit/ -v

# Solo tests de integración
pytest tests/integration/ -v

# Tests de validación de fechas
pytest tests/unit/test_ground_truth.py -v
```

### Consultas de Prueba Recomendadas

#### Fechas Simples
```
hoy
ayer
semana pasada
mes anterior
Q3 2024
```

#### Consultas con Contexto Financiero
```
cuánto cashback he ganado este mes?
cuáles han sido mis consumos de la semana pasada?
en qué categorías he gastado más el último trimestre?
```

#### Feriados
```
feriados julio 2024
feriados diciembre 2024
```

---

## 🔐 Seguridad

| Componente | Protección |
|------------|------------|
| **Azure OpenAI API Key** | Almacenada en GCP Secret Manager |
| **Backend API** | Solo accesible internamente (puerto 8000) |
| **Frontend** | Único punto de acceso público (puerto 8080) |

---

## 📊 Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| **Archivos Python** | 35 |
| **Tests** | 289 (100% passing) |
| **Ejemplos de consultas** | 145+ |
| **Calendarios soportados** | 2 (Gregoriano, Perú Bancario) |
| **Idiomas** | 2 (Español, Inglés) |
| **Feriados peruanos** | 12+ por año |

---

## 🛠️ Tecnologías

| Tecnología | Uso |
|------------|-----|
| **Python 3.11** | Lenguaje principal |
| **FastAPI** | Backend API |
| **Gradio** | Frontend UI |
| **Azure OpenAI** | Entendimiento semántico (GPT-4) |
| **Pydantic** | Validación de datos |
| **Google Cloud Run** | Hosting serverless |
| **Docker** | Containerización |

---

## 📞 Endpoints API (Internos)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Estado del servicio |
| `/query` | POST | Procesar consulta de fecha |
| `/holidays` | POST | Obtener feriados |
| `/tools` | GET | Listar herramientas disponibles |
| `/calendars` | GET | Listar calendarios disponibles |
| `/examples` | GET | Ejemplos de consultas |

### Ejemplo de Request

```bash
curl -X POST https://date-agent-472802182662.europe-west1.run.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Q3 2024", "timezone": "America/Lima"}'
```

### Ejemplo de Response

```json
{
  "success": true,
  "query": "Q3 2024",
  "start_date": "2024-07-01",
  "end_date": "2024-09-30",
  "calendar_days": 92,
  "period_type": "named_quarter",
  "description": "Tercer trimestre 2024 (1 de julio - 30 de septiembre 2024)",
  "reference_date": "2026-02-04",
  "timezone": "America/Lima",
  "audit_id": "abc123..."
}
```

---

## 🎓 Casos de Uso

1. **Análisis Financiero**: Calcular rangos de fechas para reportes
2. **Chatbots Bancarios**: Entender consultas de usuarios sobre períodos
3. **Business Intelligence**: Normalizar expresiones temporales
4. **Automatización**: Procesar consultas de fechas en pipelines

---

## 👨‍💻 Autor

**Jose Lopez** - j.b.lopez.acc@gmail.com

Proyecto desarrollado para operaciones financieras con soporte completo para el calendario bancario peruano.
