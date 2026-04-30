# FocusLens: Plan profesional para un proyecto open source pequeño

> **Idea central:** FocusLens es una herramienta local que usa la webcam para estimar señales simples de presencia y atención durante sesiones de estudio o trabajo. No reconoce identidad, no guarda video y no sube imágenes a internet.

**Fecha del plan:** 2026-04-27  
**Duración objetivo:** 3 días intensivos, aproximadamente 20 a 28 horas  
**Tipo de proyecto:** Python, computer vision, productividad, privacidad local, open source  
**Nivel:** pequeño, demostrable, publicable en GitHub

## Estado local actual

Actualizado: 2026-04-30

Archivos ya creados en el repositorio local:

- [x] `README.md`
- [x] `LICENSE`
- [x] `pyproject.toml`
- [x] `focuslens/config.py`
- [x] `focuslens/__init__.py`
- [x] `focuslens/attention.py`
- [x] `focuslens/camera.py`
- [x] `focuslens/face_tracker.py`
- [x] `focuslens/overlay.py`
- [x] `focuslens/cli.py`
- [x] `focuslens/session.py`
- [x] `focuslens/storage.py`
- [x] `tests/test_attention.py`
- [x] `tests/test_camera.py`
- [x] `tests/test_config.py`
- [x] `tests/test_face_tracker.py`
- [x] `tests/test_overlay.py`
- [x] `tests/test_cli.py`
- [x] `tests/test_session.py`
- [x] `tests/test_storage.py`
- [x] `tests/test_public_api.py`

Verificacion local encontrada:

- `focuslens/overlay.py` y `focuslens/cli.py` ya existen, asi que ya no son el siguiente bloque pendiente.
- `focuslens/session.py` ya existe y convierte estados en metricas de sesion sin tocar frames de camara.
- `focuslens/storage.py` ya existe y guarda resumenes locales en JSON y CSV sin tocar frames de camara.
- Con `.venv\Scripts\python.exe`, pasan `103` tests.
- `sessions/` esta ignorado en `.gitignore` para evitar subir historial personal de sesiones.
- Con `.venv\Scripts\python.exe -m ruff check .`, Ruff pasa sin errores.
- Con `.venv\Scripts\python.exe -m ruff format --check .`, los archivos ya estan formateados.
- El `python` global apunta a Python 3.14 y no tiene `pytest` ni `ruff`; para validar el proyecto se debe usar `.venv` o instalar el proyecto en el entorno activo.
- `focuslens run` ya conecta camara, MediaPipe Face Tracker, clasificador de atencion y overlay, pero todavia requiere un modelo local `assets/face_landmarker.task` o una ruta por `--model-path` / `FOCUSLENS_MODEL_PATH`.
- `focuslens dashboard` ya existe como comando, pero solo lanza Streamlit cuando exista `dashboard.py`.

Siguiente bloque recomendado:

1. Integrar `SessionTracker` y storage en `focuslens/cli.py`, para que `focuslens run` guarde una sesion al cerrar.
2. Ampliar `tests/test_cli.py` para cubrir guardado al finalizar.

Despues de eso, seguir con `dashboard.py`, `docs/privacy.md` y `.github/workflows/ci.yml`.

---

## 1. Resumen ejecutivo

FocusLens será una aplicación local que abre la cámara del computador y detecta estados básicos de una sesión de foco:

- **FOCUSED:** hay rostro y la persona parece mirar al frente.
- **LOOKING_AWAY:** hay rostro, pero la cabeza o mirada está desviada.
- **AWAY:** no hay rostro visible.
- **TOO_CLOSE:** el rostro está demasiado cerca de la cámara.
- **TOO_FAR:** el rostro está demasiado lejos.
- **PAUSED:** la sesión está pausada manualmente.

Al cerrar la sesión, FocusLens guardará un resumen en archivos locales, por ejemplo JSON y CSV:

```json
{
  "started_at": "2026-04-27T09:00:00",
  "ended_at": "2026-04-27T10:15:32",
  "total_seconds": 4532,
  "focused_seconds": 3130,
  "away_seconds": 520,
  "looking_away_events": 23,
  "focus_score": 74.2,
  "presence_score": 88.5
}
```

La primera versión tendrá dos entradas principales:

```bash
focuslens run
focuslens dashboard
```

Forma de desarrollo actual:

```bash
python -m focuslens.cli run
streamlit run dashboard.py
```

Nota: `streamlit run dashboard.py` queda pendiente hasta crear `dashboard.py`.

---

## 2. Investigación y base técnica

### 2.1 MediaPipe Face Landmarker

MediaPipe Face Landmarker permite detectar puntos faciales en imágenes y video. La documentación oficial indica que puede trabajar con imágenes individuales o con transmisión continua, y que genera puntos faciales 3D, valores de expresión facial y matrices de transformación útiles para renderizado o análisis visual.

Para FocusLens, MediaPipe será usado como motor de detección facial. No se usará para reconocer quién es la persona, sino para estimar si hay rostro visible y calcular señales simples de orientación.

**Uso en FocusLens:**

- Detectar si hay rostro.
- Obtener puntos clave de ojos, nariz, boca y contorno facial.
- Estimar si el rostro está centrado o girado.
- Estimar si el rostro está muy cerca o muy lejos según el tamaño relativo de la cara en pantalla.

**Fuente:** Google AI Edge, MediaPipe Face Landmarker for Python  
https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python

---

### 2.2 OpenCV para cámara y video

OpenCV permite abrir una webcam usando `VideoCapture`. La documentación oficial explica que el índice `0` normalmente representa la cámara principal, que el video se procesa frame por frame, y que al terminar se debe liberar la cámara.

Para FocusLens, OpenCV será responsable de abrir la cámara, leer frames y pintar texto encima del video.

**Uso en FocusLens:**

- Abrir la cámara local.
- Leer cada imagen de la cámara.
- Convertir imagen de BGR a RGB cuando sea necesario.
- Mostrar la ventana local con información de estado.
- Dibujar overlays simples: estado, tiempo, contadores.

**Fuente:** OpenCV, Getting Started with Videos  
https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html

---

### 2.3 Streamlit para dashboard

Streamlit permite crear aplicaciones web de datos con Python. La documentación oficial explica que una app se ejecuta con `streamlit run archivo.py` y abre una interfaz local en el navegador.

Para FocusLens, Streamlit será usado para mostrar un dashboard local con el historial de sesiones.

**Uso en FocusLens:**

- Leer archivos JSON o CSV de sesiones.
- Mostrar métricas principales.
- Mostrar tabla de sesiones.
- Mostrar gráficos sencillos de foco, ausencia y distracciones.

**Fuente:** Streamlit Docs, Basic concepts  
https://docs.streamlit.io/library/get-started/main-concepts

---

### 2.4 pyproject.toml y empaquetado Python

La guía oficial de Python Packaging recomienda usar `pyproject.toml` para declarar metadatos del proyecto, dependencias, scripts ejecutables y configuración de herramientas.

Para FocusLens, `pyproject.toml` permitirá que el proyecto se vea profesional y pueda ejecutarse como CLI.

**Uso en FocusLens:**

- Nombre del paquete.
- Versión.
- Dependencias.
- Scripts como `focuslens`.
- Configuración de Ruff, pytest u otras herramientas.

**Fuente:** Python Packaging User Guide, Writing your pyproject.toml  
https://packaging.python.org/en/latest/guides/writing-pyproject-toml

---

### 2.5 GitHub: README, licencia y repositorio saludable

GitHub recomienda que los repositorios tengan README para explicar el proyecto, licencia para permitir uso, modificación y distribución, y archivos como guías de contribución cuando el proyecto busca colaboración.

Para FocusLens, esto es importante porque quieres que parezca open source real, no solo un script subido a GitHub.

**Uso en FocusLens:**

- `README.md` claro.
- `LICENSE` con MIT.
- `CONTRIBUTING.md` simple.
- Issues preparados.
- Etiquetas para contributors.

**Fuentes:**  
GitHub Docs, Best practices for repositories: https://docs.github.com/en/enterprise-cloud@latest/repositories/creating-and-managing-repositories/best-practices-for-repositories  
GitHub Docs, Licensing a repository: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

---

### 2.6 pytest para pruebas

pytest permite escribir pruebas simples y escalables en Python. La documentación oficial muestra que se pueden crear funciones `test_*` y ejecutarlas con `pytest`.

Para FocusLens, no se probará la cámara real en la primera versión, porque eso depende del computador. Se probarán funciones puras, por ejemplo cálculo de métricas, conteo de eventos y clasificación de estados.

**Uso en FocusLens:**

- Probar `SessionTracker`.
- Probar cálculo de `focus_score`.
- Probar cálculo de `presence_score`.
- Probar exportación JSON/CSV.

**Fuente:** pytest docs, Get Started  
https://www.pytest.org/en/8.1.x/getting-started.html

---

### 2.7 Ruff para formato y limpieza

Ruff es una herramienta moderna para formatear y revisar código Python. Su documentación oficial explica que `ruff format` formatea archivos Python y que Ruff busca dar una cadena de herramientas unificada y rápida.

Para FocusLens, Ruff ayuda a que el código se vea limpio desde el primer día.

**Uso en FocusLens:**

- Formatear código.
- Detectar imports sin usar.
- Mantener estilo consistente.
- Ejecutar revisión en CI.

**Fuente:** Ruff Formatter Docs  
https://docs.astral.sh/ruff/formatter/

---

### 2.8 GitHub Actions para CI

GitHub Actions permite crear flujos de integración continua. La documentación oficial incluye una guía para construir y probar proyectos Python.

Para FocusLens, CI servirá para que cada push o pull request ejecute pruebas y revise formato.

**Uso en FocusLens:**

- Instalar Python.
- Instalar dependencias.
- Ejecutar Ruff.
- Ejecutar pytest.

**Fuente:** GitHub Docs, Building and testing Python  
https://docs.github.com/en/actions/tutorials/build-and-test-code/python

---

### 2.9 Privacidad y seguridad open source

NIST Privacy Framework es una herramienta para identificar y gestionar riesgos de privacidad. Para FocusLens esto es clave porque el proyecto usa cámara. Aunque sea local, hay que diseñarlo con cuidado.

OpenSSF Scorecard ayuda a revisar hábitos de seguridad en proyectos open source mediante chequeos automatizados.

**Uso en FocusLens:**

- No guardar imágenes por defecto.
- No subir datos a internet.
- Guardar solo métricas agregadas.
- Documentar claramente qué datos se procesan.
- Agregar configuración de seguridad básica del repositorio.

**Fuentes:**  
NIST Privacy Framework: https://www.nist.gov/privacy-framework  
OpenSSF Scorecard: https://openssf.org/projects/scorecard/

---

## 3. Problema que resuelve

Muchas personas estudian, trabajan o programan durante horas sin saber realmente cuánto tiempo estuvieron enfocadas. Las apps de Pomodoro ayudan, pero dependen de que el usuario registre todo manualmente.

FocusLens propone una solución pequeña:

> Usar señales visuales locales de la cámara para estimar presencia y atención básica, sin convertirlo en vigilancia invasiva.

No busca medir productividad exacta. Busca dar una aproximación útil.

---

## 4. Público objetivo

### Usuarios principales

- Programadores que estudian o trabajan solos.
- Estudiantes que hacen sesiones largas frente al computador.
- Creadores que quieren saber si están bien encuadrados.
- Personas que usan Pomodoro y quieren métricas automáticas.

### Usuarios secundarios

- Streamers que quieren alertas visuales simples.
- Profesores o estudiantes que quieren una demo de computer vision local.
- Contributors de open source que buscan un proyecto pequeño para aportar.

---

## 5. Qué hará FocusLens

### Funciones principales de la versión 1

| Función | Descripción |
|---|---|
| Cámara local | Abre la webcam usando OpenCV. |
| Detección de rostro | Usa MediaPipe para saber si hay cara visible. |
| Estado de presencia | Marca `AWAY` cuando no hay rostro. |
| Atención básica | Marca `FOCUSED` o `LOOKING_AWAY` según orientación simple. |
| Distancia aproximada | Marca `TOO_CLOSE` o `TOO_FAR` según tamaño relativo del rostro. |
| Temporizador | Cuenta duración total de sesión. |
| Métricas | Calcula foco, ausencia, eventos y puntuaciones. |
| Guardado local | Guarda sesiones en JSON y CSV. |
| Dashboard | Muestra resumen con Streamlit. |
| Privacidad | No guarda imágenes ni video por defecto. |

---

## 6. Qué NO hará FocusLens

Esto es muy importante para evitar promesas falsas.

FocusLens no hará:

- Reconocimiento de identidad.
- Detección médica de cansancio.
- Diagnóstico de salud visual.
- Detección real de emociones.
- Vigilancia remota.
- Subida de imágenes a la nube.
- Grabación de video por defecto.
- Evaluación exacta de productividad.

Frase recomendada para README:

> FocusLens estimates simple local signals of presence and attention. It does not identify people, diagnose fatigue, or measure productivity with scientific precision.

---

## 7. Propuesta de valor

FocusLens se diferencia de un detector facial básico porque no se queda en “detectar cara”. Convierte esa detección en una herramienta útil:

```text
Webcam -> puntos faciales -> estado de sesión -> métricas -> resumen local
```

Ventajas:

- Es pequeño y fácil de entender.
- Tiene una utilidad real.
- Es visual y demostrable.
- Encaja con portfolio de IA aplicada.
- Tiene enfoque de privacidad.
- Puede crecer con plugins y comunidad.

---

## 8. Arquitectura propuesta

### 8.1 Flujo general

```text
+----------------+
| Webcam         |
+-------+--------+
        |
        v
+----------------+
| OpenCV Frame   |
+-------+--------+
        |
        v
+-------------------------+
| MediaPipe Face Tracker  |
+-------+-----------------+
        |
        v
+-------------------------+
| Attention Classifier    |
+-------+-----------------+
        |
        v
+-------------------------+
| Session Tracker         |
+-------+-----------------+
        |
        v
+-------------------------+
| JSON / CSV Storage      |
+-------+-----------------+
        |
        v
+-------------------------+
| Streamlit Dashboard     |
+-------------------------+
```

---

### 8.2 Módulos

```text
focuslens/
├── __init__.py
├── camera.py
├── face_tracker.py
├── attention.py
├── session.py
├── storage.py
├── overlay.py
├── config.py
└── cli.py
```

### `camera.py`

Responsabilidad:

- Abrir webcam.
- Leer frames.
- Liberar cámara al salir.

No debe calcular foco ni guardar datos.

---

### `face_tracker.py`

Responsabilidad:

- Recibir un frame.
- Ejecutar MediaPipe.
- Devolver puntos faciales normalizados.
- Devolver caja aproximada del rostro.

Salida sugerida:

```python
@dataclass
class FaceResult:
    detected: bool
    landmarks: list[tuple[float, float, float]]
    face_bbox_ratio: float | None
```

---

### `attention.py`

Responsabilidad:

- Recibir puntos faciales.
- Decidir estado actual.

Estados:

```python
class AttentionState(str, Enum):
    FOCUSED = "focused"
    LOOKING_AWAY = "looking_away"
    AWAY = "away"
    TOO_CLOSE = "too_close"
    TOO_FAR = "too_far"
    PAUSED = "paused"
```

Reglas simples iniciales:

- Si no hay rostro: `AWAY`.
- Si el rostro ocupa demasiado espacio: `TOO_CLOSE`.
- Si el rostro ocupa muy poco espacio: `TOO_FAR`.
- Si nariz/centro facial está muy desplazado: `LOOKING_AWAY`.
- Si está dentro de rango: `FOCUSED`.

---

### `session.py`

Responsabilidad:

- Recibir estado actual cada frame o cada cierto intervalo.
- Acumular tiempo por estado.
- Detectar eventos.
- Calcular puntuaciones.

Métricas:

```text
total_seconds
focused_seconds
away_seconds
looking_away_seconds
too_close_seconds
too_far_seconds
looking_away_events
away_events
focus_score
presence_score
```

---

### `storage.py`

Responsabilidad:

- Guardar JSON.
- Actualizar CSV.
- Crear carpeta `sessions/` si no existe.

Estructura:

```text
sessions/
├── session_2026-04-27_09-00-00.json
└── sessions.csv
```

---

### `overlay.py`

Responsabilidad:

- Dibujar texto sobre el video.
- Mostrar color o texto según estado.
- Mantener la interfaz simple.

Ejemplo visual:

```text
Status: FOCUSED
Session: 00:34:22
Focus: 00:28:10
Away: 00:02:15
Looking away: 8
```

---

### `config.py`

Responsabilidad:

- Centralizar umbrales.

Ejemplo:

```python
MIN_FACE_RATIO = 0.05
MAX_FACE_RATIO = 0.45
LOOKING_AWAY_THRESHOLD = 0.16
EVENT_COOLDOWN_SECONDS = 2.0
SAVE_DIR = "sessions"
```

---

### `cli.py`

Responsabilidad:

- Crear comando `focuslens run`.
- Crear comando `focuslens dashboard`.
- Preparar proyecto para crecer.

---

## 9. Algoritmo de atención simple

La primera versión debe ser práctica, no perfecta.

### 9.1 Presencia

```text
Si MediaPipe detecta rostro -> presente
Si MediaPipe no detecta rostro -> ausente
```

### 9.2 Distancia aproximada

Se puede usar el tamaño relativo de la cara en la imagen.

```text
face_bbox_ratio = area_del_rostro / area_total_del_frame
```

Reglas:

```text
face_bbox_ratio < MIN_FACE_RATIO -> TOO_FAR
face_bbox_ratio > MAX_FACE_RATIO -> TOO_CLOSE
```

### 9.3 Mirada o cabeza fuera

No intentar medir ojos con precisión al inicio. Para 3 días, basta con estimar orientación de cabeza.

Idea simple:

- Tomar puntos de nariz, ojo izquierdo, ojo derecho y centro facial.
- Ver si la nariz se desplaza mucho hacia un lado respecto al centro entre ojos.
- Si el desplazamiento pasa un umbral, clasificar como `LOOKING_AWAY`.

Pseudocódigo:

```python
if not face.detected:
    return AWAY

if face.face_bbox_ratio < MIN_FACE_RATIO:
    return TOO_FAR

if face.face_bbox_ratio > MAX_FACE_RATIO:
    return TOO_CLOSE

nose_x = landmarks[NOSE_INDEX].x
left_eye_x = landmarks[LEFT_EYE_INDEX].x
right_eye_x = landmarks[RIGHT_EYE_INDEX].x
center_x = (left_eye_x + right_eye_x) / 2

head_offset = abs(nose_x - center_x)

if head_offset > LOOKING_AWAY_THRESHOLD:
    return LOOKING_AWAY

return FOCUSED
```

### 9.4 Suavizado

La cámara puede cambiar estado muchas veces por ruido. Para evitarlo:

- No contar evento si dura menos de 1 segundo.
- No contar distracción repetida si ocurrió hace menos de 2 segundos.
- Actualizar métricas por intervalos de tiempo, no por número de frames.

---

## 10. Fórmulas de métricas

### 10.1 Presence Score

Mide cuánto tiempo estuviste frente al computador.

```text
presence_score = ((total_seconds - away_seconds) / total_seconds) * 100
```

### 10.2 Focus Score

Mide cuánto tiempo estuviste en estado `FOCUSED` respecto al tiempo total.

```text
focus_score = (focused_seconds / total_seconds) * 100
```

### 10.3 Attention Score alternativo

Una versión más justa puede ignorar pausas:

```text
active_seconds = total_seconds - paused_seconds
focus_score = (focused_seconds / active_seconds) * 100
```

Para versión 1, usar la fórmula simple y documentarla.

---

## 11. Stack tecnológico

### Stack principal

| Tecnología | Uso | Motivo |
|---|---|---|
| Python 3.11+ | Lenguaje principal | Simple, rápido para prototipos de IA y visión. |
| OpenCV | Cámara y overlays | Estándar para leer webcam y mostrar frames. |
| MediaPipe | Detección facial | Modelo listo para puntos faciales en tiempo real. |
| Streamlit | Dashboard | Permite crear UI local rápido. |
| pandas | Lectura de CSV y métricas | Facilita tablas y datos en dashboard. |
| pytest | Pruebas | Permite probar lógica sin depender de cámara. |
| Ruff | Formato/lint | Mantiene código limpio con poca configuración. |

### Dependencias sugeridas

```toml
[project]
dependencies = [
  "opencv-python>=4.9",
  "mediapipe>=0.10",
  "streamlit>=1.35",
  "pandas>=2.2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "ruff>=0.5",
]
```

Nota: las versiones exactas deben probarse en tu máquina. MediaPipe a veces tiene restricciones según versión de Python y sistema operativo.

---

## 12. Estructura profesional del repositorio

```text
focuslens/
├── .github/
│   └── workflows/
│       └── ci.yml
├── assets/
│   └── demo.gif
├── docs/
│   ├── privacy.md
│   ├── architecture.md
│   └── roadmap.md
├── examples/
│   └── sample_session.json
├── focuslens/
│   ├── __init__.py
│   ├── camera.py
│   ├── face_tracker.py
│   ├── attention.py
│   ├── session.py
│   ├── storage.py
│   ├── overlay.py
│   ├── config.py
│   └── cli.py
├── tests/
│   ├── test_attention.py
│   ├── test_session.py
│   └── test_storage.py
├── dashboard.py
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

---

## 13. Comandos esperados

### Instalación para desarrollo

```bash
git clone https://github.com/Flames4fun/focuslens.git
cd focuslens
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

### Ejecutar sesión

```bash
focuslens run
```

Alternativa inicial:

```bash
python -m focuslens.cli run
```

### Ejecutar dashboard

```bash
focuslens dashboard
```

Alternativa inicial:

```bash
streamlit run dashboard.py
```

### Ejecutar pruebas

```bash
pytest -q
```

### Formatear

```bash
ruff format .
ruff check .
```

---

## 14. Plan de 3 días intensivos

### Día 1: núcleo visual

**Objetivo:** cámara funcionando y detección de estados básicos.

#### Tareas

- Crear repo.
- Crear entorno virtual.
- Instalar OpenCV y MediaPipe.
- Implementar `camera.py`.
- Implementar `face_tracker.py`.
- Implementar `attention.py` básico.
- Mostrar overlay en pantalla.
- Salir con tecla `q`.

#### Entregable del día

Una ventana con cámara y estado:

```text
Status: FOCUSED
Face: DETECTED
Session: 00:03:12
```

#### Criterios de aceptación

- La cámara abre correctamente.
- Si sales del cuadro, cambia a `AWAY`.
- Si vuelves, cambia a `FOCUSED`.
- Si giras mucho la cabeza, cambia a `LOOKING_AWAY`.

#### Tiempo estimado

```text
7 a 9 horas
```

---

### Día 2: sesiones, métricas y persistencia

**Objetivo:** convertir detecciones en datos útiles.

#### Tareas

- Implementar `SessionTracker`.
- Medir tiempo por estado.
- Contar eventos de distracción.
- Agregar pausa con tecla `p`.
- Agregar reinicio con tecla `r`.
- Guardar resumen en JSON.
- Actualizar archivo CSV con historial.
- Crear tests de sesión y métricas.

#### Entregable del día

Al cerrar la app, se guarda:

```text
sessions/session_YYYY-MM-DD_HH-MM-SS.json
sessions/sessions.csv
```

#### Criterios de aceptación

- El JSON se crea al terminar.
- El CSV agrega una nueva fila por sesión.
- `focus_score` y `presence_score` se calculan bien.
- Los tests de métricas pasan.

#### Tiempo estimado

```text
7 a 10 horas
```

---

### Día 3: dashboard, documentación y publicación

**Objetivo:** que el proyecto parezca producto open source.

#### Tareas

- Crear `dashboard.py` con Streamlit.
- Mostrar última sesión.
- Mostrar tabla de sesiones.
- Mostrar métricas principales.
- Agregar gráficos simples.
- Crear README profesional.
- Crear `docs/privacy.md`.
- Crear `CONTRIBUTING.md`.
- Agregar licencia MIT.
- Agregar GitHub Actions con pytest y Ruff.
- Grabar demo GIF.
- Crear issues iniciales.

#### Entregable del día

Repositorio listo para enseñar.

#### Criterios de aceptación

- `streamlit run dashboard.py` abre dashboard.
- README explica instalación, uso, privacidad y limitaciones.
- CI ejecuta tests.
- Hay demo visual.

#### Tiempo estimado

```text
7 a 9 horas
```

---

## 15. Alcance final de la versión 1

### Incluido

- Webcam local.
- Detección de rostro.
- Estados de foco.
- Métricas de sesión.
- JSON y CSV local.
- Dashboard local.
- README.
- Licencia.
- Tests básicos.
- CI básico.
- Documento de privacidad.

### No incluido

- Login.
- Base de datos externa.
- API web.
- Docker.
- Cloud.
- Reconocimiento facial por identidad.
- Detección médica.
- Notificaciones del sistema.
- Empaquetado para Windows con `.exe`.

---

## 16. Backlog posterior

Estas ideas quedan para después de los 3 días.

### Versión 1.1

- Modo Pomodoro.
- Configuración por archivo YAML.
- Notificaciones de escritorio.
- Exportar reportes HTML.
- Mejor calibración de umbrales.

### Versión 1.2

- Plugin para OBS.
- Integración Discord status.
- Modo streamer: encuadre, luz baja, fuera de cámara.
- Reporte semanal.

### Versión 2.0

- App de escritorio.
- Sistema de plugins.
- Multi-cámara.
- Modelos alternativos.
- Empaquetado multiplataforma.

---

## 17. Privacidad por diseño

Como el proyecto usa cámara, la privacidad debe estar en el centro.

### Reglas del proyecto

1. No guardar imágenes por defecto.
2. No guardar video por defecto.
3. No subir nada a internet.
4. No identificar personas.
5. Guardar solo métricas agregadas.
6. Explicar claramente qué se procesa.
7. Permitir borrar sesiones fácilmente.
8. Incluir documento `docs/privacy.md`.

### Texto sugerido para README

```md
## Privacy

FocusLens runs locally on your machine. Webcam frames are processed in memory and are not saved by default. The app only stores session summaries such as focused time, away time, and event counts. FocusLens does not identify people, does not upload images, and does not require an account.
```

---

## 18. Riesgos y mitigaciones

| Riesgo | Explicación | Mitigación |
|---|---|---|
| MediaPipe no instala bien | Puede depender de versión de Python/SO. | Usar Python 3.11 y documentar instalación. |
| Cámara no abre | Algunas webcams fallan por permisos. | Mensaje claro y troubleshooting. |
| Detección imprecisa | Luz mala o rostro parcial. | Documentar limitaciones y ajustar umbrales. |
| Proyecto parece vigilancia | La cámara genera desconfianza. | Enfatizar local-first y no guardar imágenes. |
| Alcance crece demasiado | Fácil querer meter muchas features. | Mantener V1 cerrada. |
| Dashboard consume tiempo | Streamlit puede distraer. | Dashboard simple con tabla y métricas. |

---

## 19. README recomendado

Estructura sugerida:

```md
# FocusLens

Privacy-first local focus tracker powered by webcam-based face landmarks.

## What it does

FocusLens estimates simple work-session signals such as presence, looking away, distance from camera, and focused time. It runs locally and stores only session summaries.

## Features

- Local webcam processing
- Face presence detection
- Basic attention estimation
- Away-from-desk timer
- Looking-away counter
- JSON/CSV export
- Streamlit dashboard
- Privacy-first: no image storage, no cloud upload

## Install

...

## Usage

...

## Privacy

...

## Limitations

...

## Roadmap

...

## Contributing

...

## License

MIT
```

---

## 20. GitHub Issues iniciales

Crear estos issues al publicar:

1. `Add Pomodoro mode`
2. `Improve head pose estimation`
3. `Add HTML report export`
4. `Add desktop notifications`
5. `Improve dashboard charts`
6. `Add Windows troubleshooting guide`
7. `Add sample session files`
8. `Add configuration file support`

Etiquetas:

```text
good first issue
help wanted
documentation
enhancement
bug
privacy
```

---

## 21. CI sugerido

Archivo:

```text
.github/workflows/ci.yml
```

Contenido base:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Ruff check
        run: ruff check .

      - name: Ruff format check
        run: ruff format --check .

      - name: Run tests
        run: pytest -q
```

---

## 22. pyproject.toml sugerido

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "focuslens"
version = "0.1.0"
description = "Privacy-first local focus tracker powered by webcam-based face landmarks."
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
authors = [
  { name = "Luis Carlos Fuentes De Avila" }
]
dependencies = [
  "opencv-python>=4.9",
  "mediapipe>=0.10",
  "streamlit>=1.35",
  "pandas>=2.2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "ruff>=0.5",
]

[project.scripts]
focuslens = "focuslens.cli:main"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## 23. Tests mínimos

### `tests/test_session.py`

Casos:

- Una sesión vacía no falla.
- El tiempo enfocado se suma.
- El tiempo ausente se suma.
- `focus_score` no divide por cero.
- Los eventos se cuentan una sola vez por cooldown.

### `tests/test_attention.py`

Casos:

- Sin rostro devuelve `AWAY`.
- Rostro pequeño devuelve `TOO_FAR`.
- Rostro grande devuelve `TOO_CLOSE`.
- Rostro centrado devuelve `FOCUSED`.
- Rostro desviado devuelve `LOOKING_AWAY`.

### `tests/test_storage.py`

Casos:

- Guarda JSON.
- Agrega fila a CSV.
- Crea carpeta si no existe.

---

## 24. Demo GIF

El demo debe mostrar solo lo necesario:

1. Abres `focuslens run`.
2. Aparece estado `FOCUSED`.
3. Giras la cabeza y aparece `LOOKING_AWAY`.
4. Sales del cuadro y aparece `AWAY`.
5. Cierras y se guarda resumen.
6. Abres dashboard.

Duración ideal:

```text
20 a 40 segundos
```

---

## 25. Mensaje de posicionamiento

Frase corta:

> FocusLens is a privacy-first local focus tracker powered by webcam-based face landmarks.

Frase en español:

> FocusLens es una herramienta local que usa puntos faciales de la webcam para estimar presencia y foco durante sesiones de trabajo o estudio, sin guardar video ni reconocer identidad.

---

## 26. Checklist final antes de publicar

- [ ] README completo.
- [x] Licencia MIT.
- [ ] Instalación probada desde cero.
- [ ] `focuslens run` funciona.
- [ ] `streamlit run dashboard.py` funciona.
- [x] JSON se guarda correctamente desde `focuslens/storage.py`.
- [x] CSV se actualiza correctamente desde `focuslens/storage.py`.
- [x] Tests pasan con `.venv\Scripts\python.exe -m pytest` (`103` tests).
- [x] Ruff pasa con `.venv\Scripts\python.exe -m ruff check .` y `.venv\Scripts\python.exe -m ruff format --check .`.
- [ ] CI configurado.
- [ ] Demo GIF añadido.
- [ ] `docs/privacy.md` añadido.
- [ ] Issues iniciales creados.

---

## 27. Conclusión

FocusLens es una idea adecuada para 3 días porque combina utilidad real, computer vision, privacidad y presentación open source sin depender de modelos pesados ni infraestructura compleja.

La clave es mantener la versión 1 pequeña:

```text
Detectar -> clasificar -> medir -> guardar -> mostrar
```

Si la versión 1 queda limpia, el proyecto puede crecer de forma natural hacia Pomodoro, reportes, plugins, streaming y app de escritorio.

---

## 28. Referencias

1. Google AI Edge. MediaPipe Face Landmarker for Python. https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python
2. OpenCV. Getting Started with Videos. https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html
3. Streamlit Docs. Basic concepts. https://docs.streamlit.io/library/get-started/main-concepts
4. Python Packaging User Guide. Writing your pyproject.toml. https://packaging.python.org/en/latest/guides/writing-pyproject-toml
5. GitHub Docs. Best practices for repositories. https://docs.github.com/en/enterprise-cloud@latest/repositories/creating-and-managing-repositories/best-practices-for-repositories
6. GitHub Docs. Licensing a repository. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
7. pytest documentation. Get Started. https://www.pytest.org/en/8.1.x/getting-started.html
8. Ruff Docs. The Ruff Formatter. https://docs.astral.sh/ruff/formatter/
9. GitHub Docs. Building and testing Python. https://docs.github.com/en/actions/tutorials/build-and-test-code/python
10. NIST. Privacy Framework. https://www.nist.gov/privacy-framework
11. OpenSSF. Scorecard. https://openssf.org/projects/scorecard/
