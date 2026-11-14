# Issues críticos: borrador (reemplazar con los resultados reales de SonarCloud)

> Estos cinco puntos salen de una **revisión manual** del código, no de SonarCloud. Sirven como ejemplo del formato y como pista de lo que probablemente aparezca. Cuando corras SonarCloud, toma los 5 issues más graves que muestre (filtro por severidad), y crea los issues de GitHub con esta misma plantilla.

Plantilla: **Título** · **Severidad** (Blocker / High / Medium / Low) · **Tipo** (Bug / Vulnerabilidad / Hotspot / Code smell) · **Archivo** · **Descripción** · **Propuesta**.

| # | Título | Severidad | Tipo | Archivo | Descripción y propuesta |
|---|---|---|---|---|---|
| 1 | SQL construido con f-string en DuckDB | High | Vulnerabilidad (posible falso positivo) | `infrastructure/analytics_duckdb.py` | Las consultas se arman con f-strings. Los nombres de columna se validan contra las columnas reales y se entrecomillan, y los valores van como parámetros. Documentar la justificación y marcar como falso positivo, o mapear las columnas a una lista blanca. |
| 2 | Generador pseudoaleatorio no criptográfico | Medium | Security hotspot | `infrastructure/simulation.py` | `random.Random` se usa solo para simular sensores, no para seguridad. Revisar el hotspot y marcarlo como "Safe". |
| 3 | `except Exception` demasiado amplio | Medium | Code smell | `infrastructure/simulation.py` | El hilo de simulación captura cualquier excepción para no morir. Se registra con `log.exception`. Acotar a errores esperados o justificar. |
| 4 | Complejidad y duplicación en `AccessService` | Medium | Code smell | `application/services.py` | `confirm_entry` y `register_exit` repiten bloques de bloqueo y guardado, y hay un `raise AssertionError("unreachable")`. Extraer un método común y simplificar el flujo. |
| 5 | Parámetro sin usar y lambda asignada a variable | Low | Code smell | `infrastructure/in_memory.py`, `application/services.py` | `for_update` no se usa en los repositorios en memoria y hay una `lambda` asignada (`count = lambda ...`). Renombrar o documentar el parámetro y reemplazar la lambda por una función. |

## Crear los issues desde la terminal (opcional, con GitHub CLI)
```
gh issue create --title "SQL construido con f-string en DuckDB" --label "security,severity: high" --body "Archivo: infrastructure/analytics_duckdb.py ..."
```
Si no existen las etiquetas, créalas en GitHub (Issues > Labels) o usa el botón **New issue** y escribe la severidad en el título o en una etiqueta.
