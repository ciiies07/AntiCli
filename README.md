# AntiCli (v2.5)

> Entorno agéntico y TUI quirúrgico para modelos locales (Gemma 4, DeepSeek, Qwen) vía `llama.cpp` con visor en vivo, dirección de arte camaleónica, auto-compactación inteligente de contexto y modos Plan/Loop.

---

## 🚀 Características Principales

* **Arsenal de 15 Herramientas Quirúrgicas:** Edición precisa línea por línea (`patch_lines`, `edit`), lectura acotada con visor coloreado (`read`), inspección estructural de clases/DOM (`inspect_code`), validación estática de sintaxis HTML/JS/Python (`validate_code`), búsqueda de archivos y regex (`glob_files`, `grep_search`), búsqueda web en tiempo real (`web_search`, `web_fetch`), memoria persistente (`memory_store`) y comandos de terminal protegidos (`bash`).
* **Telemetría KV en Vivo con `llama.cpp`:** Sincronización exacta en tiempo real con los endpoints nativos `/props` y `/slots` de `llama-server` para monitorear el tamaño de contexto (`n_ctx`), ocupación de caché KV y modelo real activo.
* **Auto-Compactación con Cápsula de Continuidad (Umbral 70%):** Cuando la sesión alcanza el 70% del contexto del slot, genera automáticamente un resumen ligero estructurado (plan, archivos tocados, notas clave) y libera la memoria KV sin perder el hilo de la conversación.
* **Circuit Breaker Anti-Desborde de Tokens:** Límite de seguridad por turno para evitar bucles autónomos de reintentos infinitos, protegiendo la ventana de contexto de modelos locales.
* **Dirección de Arte Camaleónica (Fidelidad al Original por Defecto):**
  * **Juegos Clásicos:** Respeta fielmente la paleta y estética original de juegos históricos (Tetris con colores oficiales, Pac-Man con laberinto azul cobalto, Flappy Bird con cielo diurno, Snake estilo Game Boy LCD).
  * **Estilos Alternativos Bajo Demanda:** Solo aplica estilos específicos (neón, cyberpunk, mazmorra, cozy, retro) si el usuario lo pide explícitamente o configura `/style <preset>`.
* **Modo Plan (`/plan`):** Modo de solo lectura y arquitectura. Bloquea escrituras en disco y enfoca al agente en investigar el código y formular un roadmap visual con `todo_write`.
* **Modo Loop (`/loop [n]` o `/auto`):** Ejecución autónoma paso a paso. Toma el plan de tareas pendientes y ejecuta un turno exclusivo por cada tarea con memoria limpia y fresca, pausable en cualquier momento con `Ctrl+C`.
* **Servidor de Vista Previa en Vivo (`preview`):** Servidor HTTP local multi-hilo con cabeceras `no-cache` y mapeo MIME para abrir y probar juegos, aplicaciones y herramientas en el navegador instantáneamente.

---

## 📦 Requisitos e Instalación

### 1. Servidor local con `llama.cpp`
Inicia tu servidor local de `llama.cpp` (por ejemplo, con Gemma 4, DeepSeek o Qwen):
```bash
llama-server -m tu_modelo.gguf -c 42240 --port 8080
```

### 2. Dependencias de Python
```bash
pip install google-antigravity rich prompt_toolkit
```

### 3. Ejecución
Simplemente escribe en cualquier terminal o consola de Windows:
```bash
anticli
```
*(O `AntiCli`, o `python anticli.py` desde el directorio fuente).*

Opciones de línea de comandos:
```bash
python anticli.py --base-url http://127.0.0.1:8080/v1 --view full
```

| Parámetro | Default | Descripción |
| :--- | :--- | :--- |
| `--model` | `$ANTICLI_MODEL` o `gemma-4-26b-a4b-it` | Nombre del modelo en el servidor (se autodetecta de llama.cpp si está disponible). |
| `--base-url` | `$ANTICLI_BASE_URL` o `http://127.0.0.1:8080/v1` | URL base del servidor OpenAI / llama.cpp. |
| `--view` | `full` | Modo visual de terminal: `full`, `compact`, `quiet`. |
| `--no-think` | `False` | Inicia con el bloque de pensamiento (`<|think|>`) desactivado. |

---

## 🛠️ Arsenal de Herramientas

| Herramienta | Tipo | Propósito |
| :--- | :--- | :--- |
| `bash(command, timeout)` | Ejecución | Comandos de consola protegidos con timeout y árbol de procesos limpio. |
| `read(path, start_line, end_line)` | Lectura | Muestra fragmentos acotados con números de línea para ahorrar contexto. |
| `write(path, content)` | Escritura | Escritura completa de archivos con creación automática de directorios. |
| `edit(path, old_text, new_text)` | Quirúrgica | Reemplazo exacto de fragmentos de código sin reescribir todo el archivo. |
| `patch_lines(path, start, end, new)` | Quirúrgica | Reemplazo directo por rango de líneas cuando los textos son complejos. |
| `validate_code(path)` | QA / Linter | Validación estática de sintaxis HTML/JS (Node.js), Python y JSON. |
| `inspect_code(path)` | Inspección | Extrae firmas de clases, funciones y nodos DOM principales sin leer todo. |
| `glob_files(pattern, path)` | Búsqueda | Localiza rutas de archivos según comodines. |
| `grep_search(pattern, path)` | Búsqueda | Búsqueda regex con número de línea exacto en todo el proyecto. |
| `todo_write(tasks_json)` | Planificación | Dibuja la barra de progreso y el checklist visual de tareas en la terminal. |
| `todo_check(step_number, status)` | Planificación | Actualiza el estado de una tarea (`done` / `in_progress`). |
| `web_search(query, max_results)` | Web | Búsqueda en DuckDuckGo en tiempo real para consultar APIs y librerías. |
| `web_fetch(url)` | Web | Descarga limpia de contenido HTML o Markdown de cualquier sitio web. |
| `memory_store(action, note)` | Memoria | Persistencia de preferencias del usuario y arquitectura en `.anticli_memory.md`. |
| `preview(target, open_browser)` | Entorno | Servidor web HTTP local sin caché para probar aplicaciones en el navegador. |

---

## 🎮 Comandos de la Consola Interactiva

| Comando | Categoría | Descripción |
| :--- | :--- | :--- |
| `/plan [on\|off\|status]` | Arquitectura | Modo solo lectura: investiga y genera plan con `todo_write` sin tocar archivos. |
| `/loop [n]` o `/auto` | Ejecución Bucle | Ejecuta de forma autónoma las tareas del plan paso a paso (def: 5 pasos). |
| `/ctx` o `/tokens` | Telemetría KV | Muestra modelo real, tokens ocupados en llama.cpp y barra de uso de KV cache. |
| `/compact [umbral%]` | Contexto | Compacta la sesión con Cápsula de Continuidad o ajusta el umbral (def: 70%). |
| `/skills [auto\|all\|toggle <id>]` | Agente | Modo Bajo Demanda automático (ahorro de tokens) o fijar skills fijas. |
| `/style [auto\|swiss\|hud\|glass\|arc]` | Arte | Cambia el paradigma estético para evitar diseños repetitivos. |
| `/view [full\|compact\|quiet]` | Visor | Alterna entre visualización completa, compacta o silenciosa. |
| `/show <archivo> [ini] [fin]` | Inspección | Muestra un archivo en consola con sintaxis coloreada. |
| `/check <archivo>` | Auditoría QA | Valida sintaxis JS/HTML (con Node.js), Python o JSON en busca de errores. |
| `/map [ruta]` | Inspección | Extrae mapa de funciones, clases e IDs DOM sin leer todo el archivo. |
| `/memory [add <nota>\|clear]` | Memoria | Muestra o guarda notas persistentes en `.anticli_memory.md`. |
| `/game <idea>` | Creación 2D | Diseña y programa un juego 2D (60fps, partículas, audio WebAudio) y lo abre. |
| `/3d <idea>` | Creación 3D | Diseña una escena o juego 3D con Three.js, luces y Bloom. |
| `/tool <idea>` | Creación App | Diseña y construye una herramienta con personalidad visual propia. |
| `/design <idea>` | Creación UI | Crea una interfaz o dashboard con dirección de arte a medida. |
| `/preview [archivo.html]` | Entorno | Inicia el servidor web local sin caché y abre tu proyecto en el navegador. |
| `/todo [add\|done\|clear]` | Plan en Vivo | Muestra o actualiza la barra de progreso y tareas del agente. |
| `/undo` | Quirúrgico | Deshace inmediatamente el último cambio de archivo (`write`/`edit`/`patch_lines`). |
| `/diff` o `/status` | Git | Muestra el diff actual o el estado del repositorio Git. |
| `/tree` | Entorno | Muestra el árbol visual de archivos del directorio actual. |
| `/save [archivo.md]` | Sesión | Exporta la última respuesta del modelo a un archivo Markdown. |
| `/think` | Agente | Alterna el bloque de razonamiento profundo (`<|think|>`). |
| `/model [nombre]` | Agente | Muestra o cambia el modelo activo en el servidor. |
| `/reset` | Sesión | Limpia la memoria de conversación y el plan de tareas desde cero. |
| `/clear` o `/cls` | Consola | Limpia la pantalla de la terminal sin borrar la memoria del agente. |
| `!<comando>` | Atajo Shell | Ejecuta un comando directo en tu terminal sin gastar tokens. |
| `@<archivo>` *(con Tab)* | Contexto | Inyecta el contenido de un archivo directamente en tu prompt. |

---

## 📄 Licencia

MIT License © 2026 ciiies07.
