# Sustentación AtteliA · guion de 9 minutos

**Antes de empezar:** Ubuntu, Ollama con ambos modelos, backend, frontend, base indexada y cuenta de prueba listos; TXT de prueba local; conexión a internet; dominio operativo (si ya está desplegado).

| Tiempo | Diapositiva | Guion y demostración |
|---|---|---|
| 0:00–0:45 | 1 | Presentación de AtteliA e integrantes. «Asesora de moda con respuestas respaldadas por documentos». |
| 0:45–1:30 | 2 | Problema: asistentes generales pueden dar consejos sin trazabilidad. Objetivo y alcance del dominio moda. |
| 1:30–2:20 | 3 | Arquitectura: React → FastAPI protegido → LangGraph → Ollama + Chroma; SQLite para usuarios/historial. |
| 2:20–3:05 | 4 | Stack y ejecución local: qwen2.5:3b y bge-m3; Chroma; estructura del repositorio. |
| 3:05–4:05 | 5 | Mostrar `graph.py`: clasificación, recuperación, decisión `decidir_contexto`, rechazo/generación, validación. |
| 4:05–5:30 | 6 | Mostrar login, enviar consulta positiva de moda y fuentes. Preguntar sushi y mostrar rechazo explícito. |
| 5:30–6:45 | 7 | Cargar `prueba-textura.txt`, confirmar fragmentos, hacer pregunta del pañuelo Aurora y ver nueva fuente. |
| 6:45–7:30 | 8 | Seguridad: token Bearer, rutas protegidas, documentos aislados, historial. Evidencia rápida de prueba 401. |
| 7:30–8:20 | 9 | Mostrar GitHub y URL HTTPS desplegada; aclarar lo que esté realmente publicado. |
| 8:20–9:00 | 10 | Resultados, limitaciones de umbral semántico, siguiente iteración. Conclusiones. |

## Plan B si falla internet o el despliegue

Demostrar localmente sin afirmar que existe una URL pública. Mostrar pruebas HTTP reales, `ollama list`, indexación y código del grafo. Señalar el despliegue como pendiente y explicar los pasos, sin inventar capturas.

## Preguntas que pueden hacerte

- **¿Por qué LangGraph?** Permite rutas explícitas y auditables según evidencia suficiente, en lugar de generar siempre.
- **¿Por qué RAG?** Porque permite cambiar y ampliar el corpus sin reentrenar el LLM, y mostrar fuentes.
- **¿Por qué dos modelos?** qwen2.5:3b genera la respuesta; bge-m3 representa semánticamente texto y preguntas para recuperar pasajes.
- **¿Cómo se evita inventar?** Dos filtros de búsqueda, un nodo de rechazo y prompts con exclusividad de contexto; no es garantía absoluta.
- **¿Cómo aislan usuarios?** SQLite filtra por usuario e índices Chroma separados por identificador de usuario.
- **¿Qué ocurre con PDF escaneado?** No se extrae texto; se explica el requisito de OCR.
- **¿En Vercel funciona Ollama?** No basta un frontend estático: se necesita un servidor adicional con recursos para el modelo local autohospedado.
