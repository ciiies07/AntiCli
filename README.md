# π-antigravity (v2.5)

> Entorno agéntico y TUI quirúrgico para modelos locales (Gemma 4, DeepSeek, Qwen) vía `llama.cpp` con visor en vivo, dirección de arte camaleónica, auto-compactación inteligente de contexto y modos Plan/Loop.

---

## ✨ Características Principales

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

## 🚀 Requisitos e Instalación

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
```bash
python pi_antigravity.py
```

Opciones de línea de comandos:
```bash
python pi_antigravity.py --base-url http://127.0.0.1:8080/v1 --view full
```

---

## ⌨️ Centro de Comandos TUI

| Comando | Categoría | Descripción |
| :--- | :--- | :--- |
| `/plan [on\|off\|status]` | Arquitectura | Modo solo lectura: investiga y genera plan con `todo_write` sin tocar archivos |
| `/loop [n]` \| `/auto` | Ejecución Bucle | Ejecuta de forma autónoma las tareas del plan paso a paso (def: 5 pasos) |
| `/ctx` \| `/tokens` | Telemetría KV | Muestra modelo real, contexto en `llama.cpp`, ocupación KV cache y umbral |
| `/compact [umbral%]` | Contexto | Compacta la sesión con Cápsula de Continuidad o ajusta el umbral (def: 70%) |
| `/skills [auto\|all\|toggle]` | Agente | Modo Bajo Demanda automático (ahorra tokens) o fijar skills manualmente |
| `/style [preset]` | Dirección Arte | Cambia la estética (`classic`, `dungeon`, `cozy`, `gameboy`, `swiss`, `hud`, `glass`, `arcade`, `auto`) |
| `/game <idea>` | Creación 2D | Diseña y programa un juego 2D con Game Loop, DeltaTime, partículas y WebAudio |
| `/3d <idea>` | Creación 3D | Diseña una escena o juego 3D interactivo con Three.js, luces y Bloom |
| `/tool <idea>` | Creación App | Diseña y construye una herramienta completa con arquitectura modular |
| `/preview [archivo.html]` | Entorno | Inicia el servidor web local sin caché y abre el proyecto en el navegador |
| `/check <archivo>` | Auditoría QA | Valida sintaxis HTML/JS (con Node.js), Python o JSON |
| `/map [ruta]` | Inspección | Extrae mapa de funciones, clases e IDs DOM sin leer todo el archivo |
| `/undo` | Quirúrgico | Deshace inmediatamente la última modificación de archivo |
| `/clear` \| `/cls` | Consola | Limpia la pantalla de la terminal sin borrar la memoria del agente |

---

## 📄 Licencia

MIT License.
