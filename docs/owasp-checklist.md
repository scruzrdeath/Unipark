# Checklist de 10 controles de seguridad (OWASP API Security 2023)

Estado: **Hecho** (implementado y con prueba), **Parcial** (hecho con limitaciones) o **Pendiente de activar** (requiere un paso en GitHub).

| # | Control | Categoría OWASP | Estado | Evidencia |
|---|---|---|---|---|
| 1 | Las contraseñas se guardan solo como hash **BCrypt** (nunca en texto plano) y se exige una política mínima (8 a 72 bytes, letra y dígito). | API2 | Hecho | `infrastructure/bcrypt_hasher.py`, `tests/infrastructure/test_bcrypt_hasher.py`, `tests/application/test_auth_service.py` |
| 2 | **JWT** firmado (HS256) con secreto de al menos 32 bytes tomado del entorno, con vencimiento (30 min) y claims obligatorios; se rechaza `alg: none`. | API2, API8 | Hecho | `infrastructure/security.py`, `tests/infrastructure/test_security.py` |
| 3 | **Logout** que revoca el token (lista de revocados por `jti`). | API2 | Parcial | `application/auth_service.py`. Limitación: la lista vive en memoria de un solo proceso. |
| 4 | **Bloqueo temporal** tras 5 intentos de login fallidos por usuario, y mensaje igual para usuario inexistente o clave incorrecta. | API2, API4 | Hecho | `AuthService.login`, pruebas de bloqueo. |
| 5 | **Autorización por objeto**: cada reserva solo la puede ver, confirmar o cerrar su dueño. El usuario sale del token, no del cuerpo de la petición. | API1 | Hecho | `ReservationService`, `AccessService`, `tests/application/test_ownership.py` |
| 6 | **Validación de entradas** y consultas parametrizadas: esquemas Pydantic con longitudes, `page_size` máximo 100, SQLAlchemy y DuckDB con valores como parámetros. | API3, API4, inyección | Hecho | `api/schemas.py`, `infrastructure/analytics_duckdb.py` |
| 7 | **Consumo seguro de APIs externas**: URL base fija, timeout, reintentos limitados, circuit breaker, validación de la forma del JSON y caché. | API7, API10 | Hecho | `infrastructure/open_data.py`, `tests/infrastructure/test_open_data.py` |
| 8 | **Secretos fuera del código**: `.env` en `.gitignore`, `JWT_SECRET` por variable de entorno y **Secret Scanning** con push protection en GitHub. | API8 | Pendiente de activar | `.gitignore`, `.env.example`. Falta activar Secret Scanning (ver guía). |
| 9 | **Cabeceras de seguridad** (`nosniff`, `X-Frame-Options`, `no-store`) y UI sin `innerHTML` con datos externos (previene XSS). | API8 | Hecho | `api/app.py`, `api/static/index.html`. Pendiente: Content-Security-Policy. |
| 10 | **Análisis continuo**: CodeQL, SonarCloud en CI y alertas de Dependabot. | API8, API9 | Pendiente de activar | `.github/workflows/*.yml`, `.github/dependabot.yml` |

## Pendientes conocidos (fuera de esta entrega)
- Límite de peticiones global (rate limiting) y revocación de tokens compartida entre varios procesos.
- Roles (por ejemplo administrador) y autorización por función.
- HTTPS y HSTS en el despliegue, CORS explícito y registro de eventos de seguridad.
