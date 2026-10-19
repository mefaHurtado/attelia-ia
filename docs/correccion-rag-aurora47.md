# Corrección de fidelidad documental: prueba Aurora-47

## Hallazgo
La ingesta de `prueba_rag_attelia_aurora47.txt` funcionó: el agente mostró su fuente. Sin embargo, produjo una recomendación que incluía cinturón, camiseta de rayas y bolso, mientras el documento establecía una combinación **exclusiva** con chaqueta gris grafito, pantalón marfil y zapatos azul petróleo. Citar una fuente no basta para demostrar fidelidad factual.

## Causa y mitigaciones
- Recuperación híbrida que mezclaba volúmenes generales con un documento de prueba identificable por `Aurora-47`. Ahora, si la pregunta contiene un identificador tipo `Aurora-47`, solo se aceptan fragmentos que contienen ese mismo identificador.
- La categoría `accesorio` podía inducir a un modelo pequeño a sugerir accesorios aunque el texto suministrado describiera un conjunto exacto. Ahora, **únicamente cuando** el documento recuperado contiene una pareja `Pregunta de verificación` y `Respuesta registrada` coincidente con la consulta, se devuelve la respuesta registrada de forma extractiva, sin volver a generarla ni reescribirla.
- Las preguntas que no incluyen respuesta registrada continúan por el generador RAG existente. Esta medida no garantiza ausencia total de alucinaciones en respuestas generativas: se deben realizar pruebas adicionales y registrar errores.

## Cómo validar
1. Mantener Ollama, FastAPI y Vite ejecutándose.
2. Reiniciar solamente FastAPI después de copiar el parche (`Ctrl+C` y el comando habitual de uvicorn).
3. Abrir AtteliA, iniciar sesión y preguntar **sin** el texto «Copiar pregunta»:
   `¿Cómo se combina el pañuelo coral Aurora-47 según el documento de prueba?`
4. Comprobar que la respuesta menciona exactamente: **chaqueta gris grafito, pantalón marfil, zapatos azul petróleo**.
5. Comprobar que aparece como fuente `prueba_rag_attelia_aurora47.txt`, sin citar otros volúmenes en esta consulta con identificador.
6. Verificar que sigue rechazando consultas fuera del corpus, como `¿Quién ganó el Mundial de Fútbol de 2022?`.
7. Ejecutar `PYTHONPATH=backend pytest -q backend/tests` dentro del proyecto; en Ubuntu deben estar instaladas las dependencias del backend.

## Alcance de la evidencia
La coincidencia en Aurora-47 demuestra recuperación incremental y respuesta extractiva para un registro explícito. No demuestra por sí sola que todas las respuestas libres de AtteliA estén fundamentadas; requiere evaluación continua.
