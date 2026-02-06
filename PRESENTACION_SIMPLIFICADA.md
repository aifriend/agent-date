# 📅 Agente de Razonamiento de Fechas

Agente que convierte consultas en lenguaje natural sobre fechas y períodos en rangos precisos, orientado a operaciones financieras en Perú.

---

## 🎯 ¿Qué hace?

| Consulta | Resultado |
|----------|-----------|
| "Q3 2024" | 2024-07-01 → 2024-09-30 |
| "semana pasada" | Rango de la semana anterior |
| "feriados julio 2024" | Lista de feriados bancarios peruanos |

---

## 🏗️ Arquitectura

### Principio fundamental

> El agente maneja **solo** el entendimiento semántico.  
> Los cálculos de fechas los ejecutan **herramientas determinísticas**.

---

### Vista general: Cloud Run

| Capa | Puerto | Componente | Rol |
|------|--------|------------|-----|
| **Acceso público** | 8080 | Gradio UI | Interfaz web, consultas, ejemplos |
| **Interno** | 8000 | FastAPI + Agente | Backend, orquestación del flujo |

Flujo: Usuario → Gradio (8080) → FastAPI (8000) → Agente → Herramientas → Respuesta

---

### Flujo del agente (capas internas)

```
    Consulta del usuario
            │
            ▼
    ┌───────────────────┐
    │  Semantic Parser  │  ← Azure OpenAI (GPT-4) entiende la intención
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ Query Decomposer  │  ← Genera plan de ejecución (tool calls)
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐
    │ Tool Orchestrator │  ← Ejecuta herramientas en orden
    └─────────┬─────────┘
              │
              ├──────────────────────┐
              ▼                      ▼
    ┌──────────────────┐   ┌────────────────────┐
    │  Azure OpenAI    │   │    Herramientas    │
    │  (GPT-4)         │   │  (determinísticas) │
    └──────────────────┘   └────────────────────┘
              │                      │
              └──────────┬───────────┘
                         ▼
                   Resultado
```

---

### Componentes del agente

| Componente | Qué hace |
|------------|----------|
| **Semantic Parser** | Interpreta la intención con Azure OpenAI (GPT-4). Extrae: tipo de consulta, período, calendario, exclusión de feriados. Fallback con patrones para expresiones comunes. |
| **Query Decomposer** | Convierte la intención en plan de ejecución. Descompone consultas complejas en pasos ordenados. Maneja: semántica, calendario, días hábiles, bordes, composición. |
| **Tool Orchestrator** | Ejecuta las herramientas según el plan. Secuencia: referencia → resolve → holidays → compute. Sintetiza el resultado final. |

---

### Herramientas (fuente de verdad)

| Herramienta | Qué hace |
|-------------|----------|
| **`get_current_date_info`** | **Se llama SIEMPRE primero.** Punto de referencia: fecha actual, límites semana/mes, lookback (6 meses). |
| **`resolve_period`** | Expresiones → rangos de fechas. "Q3 2024", "semana pasada", "mes anterior". Español e inglés. |
| **`get_holiday_calendar`** | Lista de feriados y no hábiles en un rango. Para consultas con días hábiles o exclusión de festivos. |
| **`compute_date_range`** | Aritmética: sumar/restar días (calendario o hábiles), semanas, meses; fin de mes, siguiente día hábil. |

---

### Calendarios

| Calendario | Qué hace |
|------------|----------|
| **GREGORIAN** | Solo fines de semana como no hábiles. |
| **PERU_BANKING** | Fines de semana + feriados peruanos (Año Nuevo, Semana Santa, Fiestas Patrias, Navidad, etc.). |

---

### Otros componentes

| Módulo | Función |
|--------|---------|
| `localization/` | Patrones y formateo en español e inglés. |
| `models/` | Schemas Pydantic para inputs/outputs. |
| `core/` | Configuración, constantes, auditoría de cálculos. |

---

## 🚀 Uso

**Web:** https://date-agent-472802182662.europe-west1.run.app

---

## 🛠️ Stack

Python 3.11 · FastAPI · Gradio · Azure OpenAI · Docker · Google Cloud Run

---

## 👨‍💻 Autor

Jose Lopez - j.b.lopez.acc@gmail.com
