# Plan de pruebas funcionales y evidencia

**Fecha:** completar al ejecutar. **Entorno:** Ubuntu/WSL o VPS. **Evaluador:** completar.

| ID | Escenario | Acción | Resultado esperado | Estado / captura |
|---|---|---|---|---|
| P01 | Seguridad | GET `/api/documents` sin token | HTTP 401 | Por registrar |
| P02 | Registro/login | Crear usuario e iniciar sesión | token y chat accesible | Por registrar |
| P03 | Historial privado | Preguntar con usuario A, revisar con B | B no ve el historial de A | Por registrar |
| P04 | Conocimiento base | Preguntar «¿Cómo combinar un blazer con jeans?» después de reindexar | Respuesta con fuente del volumen (si supera filtro) | Por registrar |
| P05 | Fuera del dominio | Preguntar «¿Qué ingredientes lleva el sushi?» | Rechazo explícito, fuentes vacías | Por registrar |
| P06 | Carga | Subir TXT con un hecho de moda inexistente en el corpus | Confirmación y registro en documentos | Por registrar |
| P07 | RAG incremental | Preguntar algo que esté *solamente* en el TXT nuevo | Respuesta con nombre de archivo como fuente | Por registrar |
| P08 | Eliminación | Borrar TXT y volver a preguntar | No usa el documento borrado | Por registrar |
| P09 | Persistencia | Reiniciar backend y consultar documentos | Los documentos persisten en SQLite+Chroma | Por registrar |
| P10 | Seguridad archivos | Subir `.exe` o archivo >10MB | HTTP 422/413, sin indexación | Por registrar |
| P11 | Acceso web | Entrar al dominio HTTPS del frontend | Pantalla de login | Por registrar |
| P12 | Backend público | `/api/health` sin token y con token | 401 sin token / JSON con token | Por registrar |

## Texto TXT de prueba sugerido

Crear `prueba-textura.txt` con más de 40 caracteres:

> En la colección de pruebas de AtteliA, el pañuelo coral llamado Aurora se combina exclusivamente con chaqueta gris grafito y zapatos color marfil. Este dato se incorporó para verificar indexación incremental.

Preguntar: «¿Con qué se combina el pañuelo coral Aurora en la colección de pruebas?»; luego borrar el archivo y repetir.

## Evidencias requeridas

1. Captura del login y del chat autenticado.
2. Captura de respuesta correcta y sus fuentes (verificar contexto realmente recuperado).
3. Captura del rechazo.
4. Captura de subida, nombre del documento y fragmentos procesados.
5. Captura de la pregunta contestada con el documento nuevo.
6. Captura del repositorio público en GitHub con README y árbol de carpetas.
7. Captura del frontend abierto por URL HTTPS y backend bajo `/api/`.
8. Terminal `ollama list`, `docker compose ps` y ejecución de tests con fecha.

**No marcar como «pasó» lo que no se haya ejecutado.** Guardar capturas en `docs/evidencias/` sin datos personales expuestos.
