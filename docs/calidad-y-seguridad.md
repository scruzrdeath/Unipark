# Guía de pasos: calidad y seguridad

Todo lo que hay que hacer en la web de GitHub o SonarCloud, en orden.

## 0. Antes de empezar
1. Sube el proyecto a GitHub (rama `main`), incluyendo la carpeta `.github/`.
2. En tu PC, con el entorno activado: `pip install -r requirements.txt -r requirements-dev.txt` y luego `pytest`.
3. Crea tu `.env` a partir de `.env.example` solo si vas a usar MySQL. Para probar el login basta con ejecutar la app; el `JWT_SECRET` puede dejarse sin definir (se genera uno temporal y se avisa en la consola).

## 1. Probar el login (JWT y BCrypt)
1. Arranca `uvicorn parking.main:app --reload` y abre `http://localhost:8000`.
2. Escribe usuario y contraseña (8 o más caracteres, con letra y dígito), pulsa **Register** y luego **Log in**.
3. Reserva una plaza. Pulsa **Log out**: el token queda revocado.
4. En `/docs`: `POST /api/auth/register`, `POST /api/auth/login`, copia el `access_token`, pulsa el botón **Authorize** y pégalo.

## 2. SonarCloud
1. Entra a `https://sonarcloud.io` con tu cuenta de GitHub y elige **Analyze new project** (importa el repositorio).
2. En el método de análisis elige **GitHub Actions**. Desactiva el "Automatic Analysis" del proyecto, porque no puede convivir con el análisis desde CI.
3. SonarCloud te muestra un token. Guárdalo en GitHub: **Settings > Secrets and variables > Actions > New repository secret**, nombre `SONAR_TOKEN`.
4. Edita `sonar-project.properties` con tu `sonar.organization` y `sonar.projectKey` (los muestra SonarCloud).
5. Haz commit y push. El workflow **CI (tests + SonarCloud)** corre solo.
6. En SonarCloud abre **Issues**, ordénalos por severidad, toma los 5 más críticos y créalos como issues de GitHub (plantilla en `docs/issues-sonar-borrador.md`).

## 3. Mutation testing (mutmut)
mutmut 3 no corre de forma nativa en Windows, por eso se ejecuta en GitHub Actions (Linux).
1. En GitHub: pestaña **Actions > Mutation testing (mutmut) > Run workflow**.
2. Cuando termine, abre el job y busca el resumen de `mutmut run`. Calcula:
   **Mutation Score = mutantes eliminados ÷ (eliminados + sobrevivientes) × 100**
3. Descarga el artefacto `mutmut-results` para ver los mutantes que sobrevivieron.
4. Registra el valor aquí:

| Fecha | Mutantes totales | Eliminados | Sobrevivientes | Mutation Score |
|---|---|---|---|---|
| __/__/2026 | | | | % |

Alternativa local: usar WSL (Ubuntu) con `pip install mutmut` y ejecutar `mutmut run` en la carpeta del proyecto.

## 4. GitHub Advanced Security
En el repositorio: **Settings > Code security** (o "Advanced Security").
1. **Dependabot alerts**: Enable. También **Dependabot security updates** (el archivo `.github/dependabot.yml` ya activa las actualizaciones semanales).
2. **Secret scanning**: Enable, y activa **Push protection**.
3. **Code scanning (CodeQL)**: el workflow `.github/workflows/codeql.yml` ya viene listo. No actives el "Default setup" porque chocaría con este workflow.
4. Primer análisis: pestaña **Actions > CodeQL > Run workflow**. Luego revisa los resultados en **Security > Code scanning**.

Nota: en repositorios públicos estas funciones están disponibles sin costo. En repositorios privados dependen de tu plan o de la organización. Si no ves las opciones, es por eso.

## 5. Evidencia para entregar
- Captura de los 5 issues en GitHub y de SonarCloud ordenado por severidad.
- Captura o texto del Mutation Score (tabla anterior).
- `docs/owasp-aplicabilidad.md` y `docs/owasp-checklist.md`.
- Captura de **Security** en GitHub con Code scanning, Secret scanning y Dependabot activos.
