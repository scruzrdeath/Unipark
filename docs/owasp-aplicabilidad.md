# OWASP: qué categorías aplican al proyecto

> **Nota sobre la lista.** El proyecto es una API REST, así que se usa el **OWASP API Security Top 10 (edición 2023)**, que es la lista de OWASP publicada en 2023. El Top 10 de aplicaciones web (el más conocido) es de 2021; si la guía se refiere a esa, la correspondencia aproximada está en la última columna.

| # | Categoría (API Security 2023) | ¿Aplica? | Por qué en este proyecto | Equivalente web 2021 |
|---|---|---|---|---|
| API1 | Broken Object Level Authorization | **Sí** | Las reservas pertenecen a un usuario; sin control, otro usuario podría ver, confirmar o cerrar la reserva ajena. | A01 |
| API2 | Broken Authentication | **Sí** | Hay login, contraseñas y tokens JWT. | A07 |
| API3 | Broken Object Property Level Authorization | **Parcial** | Las respuestas usan esquemas propios y no exponen el hash de la contraseña. No hay edición de propiedades sensibles. | A01 |
| API4 | Unrestricted Resource Consumption | **Sí** | Endpoints públicos que consultan APIs externas y hacen cálculos con DuckDB; login sin límite permitiría fuerza bruta. | (sin equivalente directo) |
| API5 | Broken Function Level Authorization | **Pendiente** | Todos los usuarios tienen el mismo rol. Si se agrega un rol administrador, esta categoría pasa a aplicar. | A01 |
| API6 | Unrestricted Access to Sensitive Business Flows | **Sí** | El flujo de reservar se podría abusar para bloquear plazas. Mitigación: una reserva abierta por usuario y vencimiento. | (sin equivalente directo) |
| API7 | Server Side Request Forgery | **Bajo** | La app hace peticiones salientes, pero solo a una URL base fija y un código de dataset de configuración, no a URLs que envíe el usuario. | A10 |
| API8 | Security Misconfiguration | **Sí** | Secretos en `.env`, cabeceras HTTP, documentación Swagger expuesta, errores detallados. | A05 |
| API9 | Improper Inventory Management | **Parcial** | Los endpoints están documentados con OpenAPI, pero no hay versionado (`/v1`). | A05 |
| API10 | Unsafe Consumption of APIs | **Sí** | Se consumen datos de datos.gov.co: hay que tratarlos como no confiables (validar forma, timeouts, circuit breaker, no inyectarlos como HTML). | A08 |

**Otras categorías web 2021 relevantes:** A03 Inyección (SQL parametrizado con SQLAlchemy; DuckDB con valores parametrizados), A06 Componentes vulnerables (Dependabot), A09 Fallos de registro y monitoreo (pendiente: log de eventos de seguridad).
