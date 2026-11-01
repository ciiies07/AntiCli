import logging
logging.getLogger('google_genai').setLevel(logging.ERROR)
logging.getLogger('google_genai.types').setLevel(logging.ERROR)
import argparse
import asyncio
import difflib
import fnmatch
import html
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

VERSION = "2.5"
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme

from google.antigravity import (
    Agent,
    AgentBehavior,
    BuiltinTools,
    CapabilitiesConfig,
    CustomSystemInstructions,
    InlineSkill,
    LocalOpenAIAgentConfig,
)
from google.antigravity.types import Text, Thought, ToolCall, ToolResult

from skills import DESIGN_PRESETS, SKILLS_CATALOG

# Forzar salida UTF-8 en consolas de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# =====================================================================
# TEMA VISUAL SOBRIO Y COLORIDO ("CYBER-SOBER DARK")
# =====================================================================

ANTICLI_THEME = Theme(

    {
        "brand": "bold #a855f7",
        "accent": "bold #38bdf8",
        "ok": "bold #10b981",
        "warn": "bold #f59e0b",
        "err": "bold #f43f5e",
        "muted": "#64748b",
        "thought": "italic #64748b",
        "strike_muted": "strike #64748b",
        "tool.bash": "bold #f59e0b",
        "tool.read": "bold #38bdf8",
        "tool.write": "bold #10b981",
        "tool.edit": "bold #d946ef",
        "tool.search": "bold #818cf8",
        "tool.web": "bold #2dd4bf",
    }
)

console = Console(theme=ANTICLI_THEME)

# =====================================================================
# ESTADO GLOBAL DEL ENTORNO AGÉNTICO
# =====================================================================

SESSION_CWD = Path.cwd()
MAX_OUTPUT_CHARS = 10000

# Modos de visualización en vivo ("full" = código/diffs/stdout en vivo, "compact" = solo cabeceras, "quiet" = mínimo)
VIEW_MODE = "full"

# Historial de backups en memoria para `/undo` (ruta -> lista de contenidos anteriores)
FILE_BACKUPS: dict[Path, list[str | None]] = {}
LAST_MODIFIED_FILES: list[Path] = []

# Lista de tareas (Todo-list) del agente en tiempo real
AGENT_TODOS: list[dict[str, str]] = []

# Skills forzadas manualmente (vacío = modo bajo demanda automático para ahorrar ventana de contexto)
ACTIVE_SKILLS: set[str] = set()
SKILLS_ON_DEMAND: bool = True
ACTIVE_STYLE: str = "auto"

# Configuración de Auto-Compactación y Continuidad de Contexto
COMPACT_THRESHOLD_PCT: float = 70.0  # Umbral del 70% de n_ctx para auto-compactación
HANDOFF_CAPSULE: str = ""            # Cápsula de continuidad inyectada tras compactar la sesión
SESSION_TURN_LOG: list[dict[str, str]] = []  # Resumen ligero de turnos para construir la cápsula de continuidad

# Modo Plan y Circuit Breaker de Herramientas
PLAN_MODE: bool = False
MAX_TOOL_CALLS_PER_TURN: int = 8      # Límite máximo de llamadas consecutivas de herramientas en un turno
CURRENT_TURN_TOOL_CALLS: int = 0      # Contador de llamadas a herramientas en el turno activo

def _registrar_llamada_herramienta(nombre: str) -> str | None:
    """Registra una llamada a herramienta y activa el Circuit Breaker si se entra en bucle descontrolado."""
    global CURRENT_TURN_TOOL_CALLS
    CURRENT_TURN_TOOL_CALLS += 1
    if CURRENT_TURN_TOOL_CALLS > MAX_TOOL_CALLS_PER_TURN:
        return (
            f"[CIRCUIT BREAKER ACTIVADO] Se ha alcanzado el límite de seguridad de {MAX_TOOL_CALLS_PER_TURN} llamadas a herramientas "
            f"en este turno. Detén la ejecución autónoma aquí, resume al usuario lo realizado y consulta cómo proceder para "
            f"no agotar la ventana de contexto."
        )
    return None

# Servidor HTTP de vista previa en segundo plano
PREVIEW_SERVER: ThreadingHTTPServer | None = None
PREVIEW_PORT: int | None = None

# Metadatos en vivo extraídos de llama.cpp (/props, /slots, /v1/models)
SERVER_INFO: dict = {
    "online": False,
    "model_name": "",
    "model_path": "",
    "n_ctx": 0,           # Contexto por slot asignado en llama-server
    "n_ctx_train": 0,     # Contexto máximo entrenado del modelo GGUF
    "total_slots": 1,
    "used_tokens": 0,     # Tokens actualmente ocupados en el contexto / slot
    "models": [],
}


def _truncate_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    omitted = len(text) - max_chars
    return (
        f"{text[:half]}\n\n"
        f"... [Salida truncada: {omitted} caracteres omitidos] ...\n\n"
        f"{text[-half:]}"
    )


def _resolve_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (SESSION_CWD / p).resolve()
    return p


def _guardar_backup(p: Path):
    """Guarda el estado previo de un archivo antes de modificarlo para permitir `/undo`."""
    prev = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None
    FILE_BACKUPS.setdefault(p, []).append(prev)
    if p in LAST_MODIFIED_FILES:
        LAST_MODIFIED_FILES.remove(p)
    LAST_MODIFIED_FILES.append(p)


def _limpiar_fences_llm(path: str, content: str) -> tuple[str, bool]:
    """Elimina cercas Markdown (```html ... ```) accidentales que los modelos locales suelen añadir al escribir archivos."""
    if Path(path).suffix.lower() in (".md", ".markdown"):
        return content, False

    limpio = content
    modificado = False

    # Caso 1: Todo el archivo envuelto en ```lang ... ```
    m_full = re.match(r"^\s*```[a-zA-Z0-9_-]*\r?\n(.*?)\r?\n```\s*$", limpio, flags=re.DOTALL)
    if m_full:
        return m_full.group(1), True

    # Caso 2: Cerca inicial suelta al principio del archivo
    if re.match(r"^\s*```[a-zA-Z0-9_-]*\r?\n", limpio):
        limpio = re.sub(r"^\s*```[a-zA-Z0-9_-]*\r?\n", "", limpio, count=1)
        modificado = True

    # Caso 3: Cerca final ` ``` ` suelta al final del archivo (como ocurrió en index.html)
    if re.search(r"\r?\n```\s*$", limpio):
        limpio = re.sub(r"\r?\n```\s*$", "\n", limpio, count=1)
        modificado = True

    # Auto-reparar etiquetas de cierre HTML mal formadas (ej. </div\n -> </div>\n) generadas a veces por LLMs locales
    if Path(path).suffix.lower() in (".html", ".htm"):
        limpio_reparado = re.sub(r"</([a-zA-Z1-6]+)(?=\s*[\r\n])", r"</\1>", limpio)
        if limpio_reparado != limpio:
            limpio = limpio_reparado
            modificado = True

    return limpio, modificado


def _validar_sintaxis_automatica(p: Path) -> str | None:
    """Verifica automáticamente errores de sintaxis en archivos recién escritos/editados para que el agente los corrija al instante."""
    ext = p.suffix.lower()
    try:
        if ext == ".py":
            source = p.read_text(encoding="utf-8", errors="replace")
            compile(source, str(p.name), "exec")
        elif ext == ".json":
            source = p.read_text(encoding="utf-8", errors="replace")
            json.loads(source)
        elif ext in (".html", ".htm"):
            source = p.read_text(encoding="utf-8", errors="replace")
            open_scripts = len(re.findall(r"<script\b[^>]*>", source, flags=re.IGNORECASE))
            close_scripts = len(re.findall(r"</script\s*>", source, flags=re.IGNORECASE))
            if open_scripts != close_scripts:
                return f"Advertencia HTML: {open_scripts} etiqueta(s) <script> abierta(s) vs {close_scripts} cerrada(s)."
    except SyntaxError as e:
        return f"Error de sintaxis en línea {e.lineno}: {e.msg}"
    except Exception as e:
        return f"Advertencia de validación: {e}"
    return None


def _detectar_lexer(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    mapa = {
        "py": "python",
        "js": "javascript",
        "mjs": "javascript",
        "ts": "typescript",
        "tsx": "tsx",
        "jsx": "jsx",
        "html": "html",
        "htm": "html",
        "css": "css",
        "json": "json",
        "md": "markdown",
        "sh": "bash",
        "ps1": "powershell",
        "yml": "yaml",
        "yaml": "yaml",
        "toml": "toml",
        "rs": "rust",
        "go": "go",
        "cpp": "cpp",
        "c": "c",
        "sql": "sql",
    }
    return mapa.get(ext, "text")


def _mostrar_codigo_en_vivo(path: str, content: str, start_line: int = 1, titulo: str = "", max_lines: int = 55):
    """Muestra un panel con el código resaltado cuando VIEW_MODE == 'full'."""
    if VIEW_MODE != "full":
        return
    lines = content.splitlines()
    muestra = "\n".join(lines[:max_lines])
    lexer = _detectar_lexer(path)
    sub = (
        f"[muted]+{len(lines) - max_lines} líneas más (usa /show {path} para ver completo)[/muted]"
        if len(lines) > max_lines
        else f"[muted]{len(lines)} líneas[/muted]"
    )
    syntax = Syntax(
        muestra,
        lexer,
        theme="monokai",
        line_numbers=True,
        start_line=start_line,
        word_wrap=True,
        background_color="default",
    )
    console.print(
        Panel(
            syntax,
            title=f"[bold white]{titulo or path}[/bold white]",
            subtitle=sub,
            border_style="bright_black",
            box=ROUNDED,
            padding=(0, 1),
        )
    )


def _mostrar_diff_en_vivo(path: str, old_content: str, new_content: str):
    """Muestra un panel con el diff unificado coloreado cuando VIEW_MODE == 'full'."""
    if VIEW_MODE != "full":
        return
    diff_lines = list(
        difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
            n=3,
        )
    )
    if not diff_lines:
        return
    added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
    max_lines = 65
    preview = "\n".join(diff_lines[:max_lines])
    sub = f"[ok]+{added}[/ok] [err]-{removed}[/err]"
    if len(diff_lines) > max_lines:
        sub += f" [muted](+{len(diff_lines) - max_lines} líneas de diff omitidas)[/muted]"
    syntax = Syntax(preview, "diff", theme="monokai", background_color="default", word_wrap=True)
    console.print(
        Panel(
            syntax,
            title=f"[tool.edit]Δ diff[/tool.edit] [bold white]{path}[/bold white]",
            subtitle=sub,
            border_style="#a855f7",
            box=ROUNDED,
            padding=(0, 1),
        )
    )


# =====================================================================
# LAS 10 HERRAMIENTAS QUIRÚRGICAS Y DE CREACIÓN (CON VISOR EN VIVO)
# =====================================================================

def bash(command: str, timeout: int = 120) -> str:
    """Ejecuta un comando en la terminal dentro del directorio actual y devuelve stdout/stderr.
    
    Args:
        command: Comando de consola a ejecutar.
        timeout: Tiempo máximo de espera en segundos (por defecto 120).
    """
    global SESSION_CWD
    cb = _registrar_llamada_herramienta("bash")
    if cb:
        return cb

    if PLAN_MODE:
        return "Error: El MODO PLAN está activo (solo lectura). No se permite ejecutar comandos del sistema."

    if sys.platform == "win32":
        cmd_low = command.strip().lower()
        if cmd_low.startswith("sed ") or " sed -i" in cmd_low:
            return (
                "Error en bash: El comando 'sed' no existe en Windows. "
                "Para modificar archivos usa la herramienta quirúrgica 'edit' o 'patch_lines'."
            )
        if cmd_low.startswith("grep ") or " | grep " in cmd_low:
            return (
                "Error en bash: Usa la herramienta 'grep_search' en lugar de llamar a 'grep' en Windows."
            )

    if VIEW_MODE != "quiet":
        console.print(f"  [tool.bash]⚡ bash[/tool.bash] [bold white]{command}[/bold white]")

    # Cambio de directorio persistente si el comando es `cd ...`
    cd_match = re.match(r"^\s*cd\s+(.+)$", command.strip())
    if cd_match and "&&" not in command and ";" not in command and "|" not in command:
        target = cd_match.group(1).strip().strip('"').strip("'")
        new_dir = _resolve_path(target)
        if new_dir.is_dir():
            SESSION_CWD = new_dir
            os.chdir(SESSION_CWD)
            return f"Directorio actual cambiado a: {SESSION_CWD}"
        return f"Error: El directorio '{target}' no existe."

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        t0 = time.perf_counter()
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=str(SESSION_CWD),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        collected_lines: list[str] = []
        shown_live = 0
        max_live_lines = 22

        # Hilo lector para evitar que un bloqueo en stdout impida aplicar el timeout
        def _reader():
            assert process.stdout is not None
            for line in process.stdout:
                clean_line = line.rstrip("\r\n")
                collected_lines.append(clean_line)
                if VIEW_MODE == "full":
                    nonlocal shown_live
                    if shown_live < max_live_lines:
                        console.print(f"    [muted]│[/muted] {clean_line}", highlight=False)
                        shown_live += 1
                    elif shown_live == max_live_lines:
                        console.print("    [muted]│ ... (ejecutando y capturando resto de salida)[/muted]")
                        shown_live += 1

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()
        reader_thread.join(timeout=timeout)

        if reader_thread.is_alive():
            if sys.platform == "win32":
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
                except Exception:
                    process.kill()
            else:
                process.kill()
            console.print(f"  [err]✗ Timeout tras {timeout}s[/err]")
            partial = "\n".join(collected_lines[-30:])
            return f"Error: El comando excedió el tiempo límite de {timeout} segundos.\nSalida parcial:\n{partial}"

        process.wait(timeout=5)
        elapsed = time.perf_counter() - t0
        output = "\n".join(collected_lines).strip()

        if process.returncode != 0:
            console.print(f"  [err]✗ Salida: {process.returncode}[/err] [muted]({elapsed:.1f}s)[/muted]")
        elif VIEW_MODE != "quiet":
            console.print(
                f"  [ok]✓ ok[/ok] [muted]({len(collected_lines)} líneas en {elapsed:.1f}s)[/muted]"
            )
        return _truncate_output(output) if output else "(Comando ejecutado sin salida)"
    except Exception as e:
        return f"Error ejecutando bash: {e}"


def read(path: str, start_line: int = 1, end_line: int = 200) -> str:
    """Lee un archivo local mostrando números de línea (por defecto líneas 1 a 200).
    
    Args:
        path: Ruta del archivo a leer.
        start_line: Línea inicial (basada en 1, por defecto 1).
        end_line: Línea final (incluida, por defecto 200).
    """
    cb = _registrar_llamada_herramienta("read")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(
            f"  [tool.read]📖 read[/tool.read] [bold white]{path}[/bold white] [muted](líneas {start_line}-{end_line})[/muted]"
        )
    try:
        p = _resolve_path(path)
        if not p.exists():
            return f"Error: El archivo '{path}' no existe."
        if p.is_dir():
            items = [f"{x.name}/" if x.is_dir() else x.name for x in sorted(p.iterdir())]
            return f"'{path}' es un directorio. Contenido ({len(items)} elementos):\n" + "\n".join(items[:200])

        raw = p.read_bytes()
        if b"\x00" in raw[:4096]:
            return f"Error: '{path}' parece ser un archivo binario ({len(raw)} bytes)."

        content = raw.decode("utf-8", errors="replace")
        lines = content.splitlines()
        total = len(lines)
        nota_rango = ""
        if end_line - start_line > 250:
            end_line = start_line + 250
            nota_rango = " [Rango acotado a 250 líneas máx por llamada; usa inspect_code o avanza start_line si requieres más]"
        start_idx = max(0, start_line - 1)
        selected = lines[start_idx:end_line]

        if VIEW_MODE == "full" and selected:
            _mostrar_codigo_en_vivo(
                path,
                "\n".join(selected[:30]),
                start_line=start_idx + 1,
                titulo=f"📖 Vista previa: {path} ({start_idx + 1}-{min(end_line, total)} de {total})",
            )

        numbered = [f"{i + start_idx + 1:4d} | {line}" for i, line in enumerate(selected)]
        header = f"Archivo: {path} (Mostrando {start_idx + 1}-{min(end_line, total)} de {total} líneas){nota_rango}\n"
        return _truncate_output(header + "\n".join(numbered))
    except Exception as e:
        return f"Error leyendo {path}: {e}"


def write(path: str, content: str) -> str:
    """Crea o sobrescribe un archivo completo con el contenido especificado.
    
    Args:
        path: Ruta del archivo a crear o sobrescribir.
        content: Contenido completo del archivo (sin bloques markdown ``` envolventes).
    """
    cb = _registrar_llamada_herramienta("write")
    if cb:
        return cb

    if PLAN_MODE:
        return (
            "Error: El MODO PLAN está activo (solo lectura / arquitectura). "
            "No se permite crear o sobrescribir archivos. Usa 'todo_write' para estructurar el plan."
        )

    content, fue_limpiado = _limpiar_fences_llm(path, content)
    lines_count = len(content.splitlines())
    if VIEW_MODE != "quiet":
        nota_fences = " [warn](fences ``` limpiados auto)[/warn]" if fue_limpiado else ""
        console.print(
            f"  [tool.write]📝 write[/tool.write] [bold white]{path}[/bold white] "
            f"[muted]({lines_count} líneas, {len(content)} bytes)[/muted]{nota_fences}"
        )
    try:
        p = _resolve_path(path)
        es_nuevo = not p.is_file()
        old_content = p.read_text(encoding="utf-8", errors="replace") if not es_nuevo else ""
        _guardar_backup(p)

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

        if es_nuevo:
            _mostrar_codigo_en_vivo(path, content, start_line=1, titulo=f"✨ Nuevo archivo: {path}")
        else:
            _mostrar_diff_en_vivo(path, old_content, content)

        aviso_sintaxis = _validar_sintaxis_automatica(p)
        if aviso_sintaxis:
            console.print(f"  [warn]⚠ {aviso_sintaxis}[/warn]")
            return f"Archivo {path} escrito ({lines_count} líneas), pero atención: {aviso_sintaxis}{_auto_avanzar_plan('write', path)}"

        return f"Archivo {path} escrito correctamente ({lines_count} líneas).{_auto_avanzar_plan('write', path)}"
    except Exception as e:
        return f"Error escribiendo {path}: {e}"


def _reemplazar_flexible(norm_content: str, norm_old: str, norm_new: str) -> tuple[str | None, int]:
    """Intenta reemplazo exacto primero; si falla por espacios al final de línea, intenta coincidencia línea por línea ignorando trailing spaces."""
    if norm_old in norm_content:
        count = norm_content.count(norm_old)
        if count == 1:
            return norm_content.replace(norm_old, norm_new, 1), 1
        return None, count

    # Fallback: comparar ignorando espacios en blanco a la derecha de cada línea
    content_lines = norm_content.split("\n")
    old_lines = norm_old.split("\n")
    if not old_lines or len(old_lines) > len(content_lines):
        return None, 0

    old_stripped = [l.rstrip() for l in old_lines]
    matches = []
    n_old = len(old_lines)
    for i in range(len(content_lines) - n_old + 1):
        window = [content_lines[i + j].rstrip() for j in range(n_old)]
        if window == old_stripped:
            matches.append(i)

    if len(matches) == 1:
        idx = matches[0]
        new_lines = content_lines[:idx] + norm_new.split("\n") + content_lines[idx + n_old :]
        return "\n".join(new_lines), 1
    return None, len(matches)


def edit(path: str, old_text: str, new_text: str) -> str:
    """Reemplaza un bloque de texto (old_text) por otro (new_text) en un archivo.
    
    Args:
        path: Ruta del archivo a modificar.
        old_text: Bloque de texto existente que se desea reemplazar.
        new_text: Nuevo texto que reemplazará a old_text.
    """
    cb = _registrar_llamada_herramienta("edit")
    if cb:
        return cb

    if PLAN_MODE:
        return (
            "Error: El MODO PLAN está activo (solo lectura / arquitectura). "
            "No se permite editar archivos. Usa 'todo_write' para estructurar el plan."
        )

    if VIEW_MODE != "quiet":
        console.print(f"  [tool.edit]🔧 edit[/tool.edit] [bold white]{path}[/bold white]")
    try:
        p = _resolve_path(path)
        if not p.is_file():
            return f"Error: El archivo {path} no existe."

        content = p.read_text(encoding="utf-8")
        norm_content = content.replace("\r\n", "\n")
        norm_old = old_text.replace("\r\n", "\n")
        norm_new = new_text.replace("\r\n", "\n")

        nuevo_contenido, count = _reemplazar_flexible(norm_content, norm_old, norm_new)
        if count == 0:
            console.print(f"  [err]✗ No se encontró coincidencia de old_text en {path}[/err]")
            return (
                f"Error: No se encontró coincidencia de 'old_text' en {path}. "
                f"Usa 'read' o 'patch_lines' para verificar los números de línea exactos."
            )
        if count > 1:
            console.print(f"  [err]✗ Coincidencia ambigua ({count} veces) en {path}[/err]")
            return (
                f"Error: 'old_text' aparece {count} veces en {path}. "
                f"Incluye más líneas de contexto o usa 'patch_lines'."
            )

        assert nuevo_contenido is not None
        _guardar_backup(p)
        p.write_text(nuevo_contenido, encoding="utf-8")
        _mostrar_diff_en_vivo(path, norm_content, nuevo_contenido)

        aviso_sintaxis = _validar_sintaxis_automatica(p)
        if aviso_sintaxis:
            console.print(f"  [warn]⚠ {aviso_sintaxis}[/warn]")
            return f"Edición aplicada en {path}, pero atención: {aviso_sintaxis}{_auto_avanzar_plan('edit', path)}"

        return f"Edición aplicada con éxito en {path}.{_auto_avanzar_plan('edit', path)}"
    except Exception as e:
        return f"Error editando {path}: {e}"


def patch_lines(path: str, start_line: int, end_line: int, new_content: str) -> str:
    """Reemplaza un rango exacto de líneas [start_line, end_line] (basado en 1, inclusivo) en un archivo. Ideal cuando edit falla por indentación.
    
    Args:
        path: Ruta del archivo a modificar.
        start_line: Primera línea a reemplazar (basada en 1, como muestra `read`).
        end_line: Última línea a reemplazar (incluida).
        new_content: Nuevo bloque de código que ocupará ese rango de líneas.
    """
    cb = _registrar_llamada_herramienta("patch_lines")
    if cb:
        return cb

    if PLAN_MODE:
        return (
            "Error: El MODO PLAN está activo (solo lectura / arquitectura). "
            "No se permite modificar líneas de archivos. Usa 'todo_write' para estructurar el plan."
        )

    if VIEW_MODE != "quiet":
        console.print(
            f"  [tool.edit]🩹 patch_lines[/tool.edit] [bold white]{path}[/bold white] "
            f"[muted](líneas {start_line}-{end_line})[/muted]"
        )
    try:
        p = _resolve_path(path)
        if not p.is_file():
            return f"Error: El archivo {path} no existe."

        old_raw = p.read_text(encoding="utf-8").replace("\r\n", "\n")
        lines = old_raw.split("\n")
        total = len(lines)
        if start_line < 1 or end_line < start_line or start_line > total:
            return f"Error: Rango inválido ({start_line}-{end_line}) para un archivo de {total} líneas."

        clean_new, _ = _limpiar_fences_llm(path, new_content.replace("\r\n", "\n"))
        new_lines = clean_new.split("\n") if clean_new else []
        updated_lines = lines[: start_line - 1] + new_lines + lines[end_line:]
        nuevo_texto = "\n".join(updated_lines)

        _guardar_backup(p)
        p.write_text(nuevo_texto, encoding="utf-8")
        _mostrar_diff_en_vivo(path, old_raw, nuevo_texto)

        aviso_sintaxis = _validar_sintaxis_automatica(p)
        if aviso_sintaxis:
            console.print(f"  [warn]⚠ {aviso_sintaxis}[/warn]")
            return f"Rango {start_line}-{end_line} actualizado en {path}, pero atención: {aviso_sintaxis}{_auto_avanzar_plan('patch_lines', path)}"

        return f"Líneas {start_line}-{end_line} reemplazadas con éxito en {path} (nuevo total: {len(updated_lines)} líneas).{_auto_avanzar_plan('patch_lines', path)}"
    except Exception as e:
        return f"Error en patch_lines sobre {path}: {e}"


def glob_files(pattern: str = "**/*", path: str = ".") -> str:
    """Busca archivos por nombre o patrón glob rápidamente (ignorando .git, node_modules, __pycache__).
    
    Args:
        pattern: Patrón glob (ej. '*.py', '**/*.html', 'src/**/*.ts').
        path: Directorio base donde buscar (por defecto '.').
    """
    cb = _registrar_llamada_herramienta("glob_files")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(
            f"  [tool.search]🔍 glob_files[/tool.search] [bold white]{pattern}[/bold white] [muted]en {path}[/muted]"
        )
    try:
        base = _resolve_path(path)
        ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        resultados = []
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            for f in files:
                full = Path(root) / f
                rel = full.relative_to(base).as_posix()
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(f, pattern):
                    resultados.append(rel)
                    if len(resultados) >= 200:
                        break
            if len(resultados) >= 200:
                break
        if VIEW_MODE == "full" and resultados:
            muestra = ", ".join(resultados[:8])
            extra = f" (+{len(resultados) - 8} más)" if len(resultados) > 8 else ""
            console.print(f"    [muted]↳ {len(resultados)} encontrado(s): {muestra}{extra}[/muted]")
        return "\n".join(resultados) if resultados else "No se encontraron archivos con ese patrón."
    except Exception as e:
        return f"Error en glob_files: {e}"


def grep_search(pattern: str, path: str = ".", file_pattern: str = "*") -> str:
    """Busca expresiones regulares o texto dentro de los archivos del proyecto con número de línea.
    
    Args:
        pattern: Texto o expresión regular a buscar.
        path: Archivo o directorio donde buscar (por defecto '.').
        file_pattern: Filtro glob de archivos (ej. '*.py', '*.js').
    """
    cb = _registrar_llamada_herramienta("grep_search")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(
            f"  [tool.search]🔎 grep_search[/tool.search] [bold white]'{pattern}'[/bold white] [muted]en {path} ({file_pattern})[/muted]"
        )
    try:
        regex = re.compile(pattern, re.IGNORECASE)
        base = _resolve_path(path)
        ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
        matches = []

        archivos_a_buscar = [base] if base.is_file() else []
        if base.is_dir():
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
                for f in files:
                    if fnmatch.fnmatch(f, file_pattern):
                        archivos_a_buscar.append(Path(root) / f)

        for arch in archivos_a_buscar:
            try:
                raw = arch.read_bytes()
                if b"\x00" in raw[:2048]:
                    continue
                lines = raw.decode("utf-8", errors="replace").splitlines()
                rel = arch.relative_to(SESSION_CWD).as_posix() if arch.is_relative_to(SESSION_CWD) else str(arch)
                for idx, line in enumerate(lines, 1):
                    if regex.search(line):
                        matches.append(f"{rel}:{idx}: {line.strip()[:140]}")
                        if len(matches) >= 120:
                            break
                if len(matches) >= 120:
                    break
            except Exception:
                continue

        if VIEW_MODE == "full" and matches:
            for m in matches[:6]:
                console.print(f"    [muted]│ {m}[/muted]", highlight=False)
            if len(matches) > 6:
                console.print(f"    [muted]│ ... (+{len(matches) - 6} coincidencias más)[/muted]")

        return "\n".join(matches) if matches else f"Sin coincidencias para '{pattern}'."
    except Exception as e:
        return f"Error en grep_search: {e}"


def todo_write(tasks_json: str) -> str:
    """Crea o reemplaza la lista visual de tareas (roadmap) del agente y la muestra en consola.
    
    Args:
        tasks_json: JSON string con una lista de objetos: [{"task": "Descripción", "status": "pending|in_progress|done"}].
    """
    global AGENT_TODOS
    cb = _registrar_llamada_herramienta("todo_write")
    if cb:
        return cb
    try:
        items = json.loads(tasks_json)
        if isinstance(items, list):
            AGENT_TODOS = items
            # Si ninguna tarea está en curso ni completada, activar automáticamente la primera
            if AGENT_TODOS and all(t.get("status", "pending") == "pending" for t in AGENT_TODOS):
                AGENT_TODOS[0]["status"] = "in_progress"
            _imprimir_panel_todos()
            return f"Lista de tareas actualizada ({len(AGENT_TODOS)} tareas). Usa `todo_check(step_number, status)` o `todo_write` conforme avances."
        return "Error: tasks_json debe ser una lista JSON de objetos {task, status}."
    except Exception as e:
        return f"Error parseando tasks_json: {e}"


def todo_check(step_number: int, status: str = "done") -> str:
    """Actualiza rápidamente el estado de un paso específico del plan (1-based) y avanza automáticamente el siguiente a 'in_progress'.
    
    Args:
        step_number: Número del paso en la lista (empezando en 1).
        status: Nuevo estado ('done', 'in_progress', 'pending'). Por defecto 'done'.
    """
    global AGENT_TODOS
    cb = _registrar_llamada_herramienta("todo_check")
    if cb:
        return cb
    if not AGENT_TODOS:
        return "No hay un plan activo. Usa `todo_write` primero."
    idx = step_number - 1
    if idx < 0 or idx >= len(AGENT_TODOS):
        return f"Error: El paso {step_number} no existe (hay {len(AGENT_TODOS)} pasos)."

    AGENT_TODOS[idx]["status"] = status.lower()
    # Si se marcó como 'done' y no hay ningún otro 'in_progress', poner el siguiente 'pending' en 'in_progress'
    if status.lower() == "done" and not any(t.get("status") == "in_progress" for t in AGENT_TODOS):
        for t in AGENT_TODOS[idx + 1 :]:
            if t.get("status", "pending") == "pending":
                t["status"] = "in_progress"
                break

    _imprimir_panel_todos()
    done_count = sum(1 for t in AGENT_TODOS if t.get("status") == "done")
    return f"Paso {step_number} marcado como '{status}' ({done_count}/{len(AGENT_TODOS)} completados)."


def _auto_avanzar_plan(accion: str, detalle: str = "") -> str:
    """Avanza automáticamente el progreso visual del plan cuando el agente ejecuta herramientas clave."""
    global AGENT_TODOS
    if not AGENT_TODOS:
        return ""

    cambio = False
    if accion == "preview":
        # Buscar paso de previsualización o la tarea en curso y marcarla como done
        for t in AGENT_TODOS:
            task_low = t.get("task", "").lower()
            if t.get("status") != "done" and any(k in task_low for k in ("preview", "previsualiz", "navegador", "servidor", "lanzar", "probar")):
                t["status"] = "done"
                cambio = True
        if not cambio:
            in_prog = next((t for t in AGENT_TODOS if t.get("status") == "in_progress"), None)
            if in_prog:
                in_prog["status"] = "done"
                cambio = True
    elif accion in ("write", "edit", "patch_lines"):
        # Buscar la tarea actualmente en progreso (o la primera pendiente) y completarla, activando la siguiente
        in_prog_idx = next(
            (i for i, t in enumerate(AGENT_TODOS) if t.get("status") == "in_progress"),
            None,
        )
        if in_prog_idx is None:
            in_prog_idx = next(
                (i for i, t in enumerate(AGENT_TODOS) if t.get("status", "pending") == "pending"),
                None,
            )
        if in_prog_idx is not None:
            AGENT_TODOS[in_prog_idx]["status"] = "done"
            cambio = True
            for nxt in AGENT_TODOS[in_prog_idx + 1 :]:
                if nxt.get("status", "pending") == "pending":
                    nxt["status"] = "in_progress"
                    break

    if cambio and VIEW_MODE != "quiet":
        _imprimir_panel_todos()

    pendientes = [
        f"#{i + 1} ({t.get('status')}): {t.get('task')}"
        for i, t in enumerate(AGENT_TODOS)
        if t.get("status") != "done"
    ]
    if pendientes:
        return f"\n[Estado del Plan: quedan {len(pendientes)} paso(s) -> {'; '.join(pendientes[:3])}]"
    return "\n[Estado del Plan: ¡Todos los pasos completados (100%)!]"


def _finalizar_plan_al_terminar_turno():
    """Muestra el estado real del plan al finalizar el turno sin forzar tareas pendientes a done."""
    global AGENT_TODOS
    if not AGENT_TODOS:
        return
    done_count = sum(1 for t in AGENT_TODOS if t.get("status") == "done")
    if done_count == len(AGENT_TODOS) and VIEW_MODE != "quiet":
        _imprimir_panel_todos()


def _imprimir_panel_todos():
    if not AGENT_TODOS:
        console.print("  [muted]No hay tareas registradas en este momento.[/muted]")
        return
    total = len(AGENT_TODOS)
    done_count = sum(1 for t in AGENT_TODOS if t.get("status", "").lower() == "done")
    pct = int((done_count / total) * 100) if total > 0 else 0
    bar_width = 18
    filled = int((done_count / total) * bar_width) if total > 0 else 0
    barra = f"[ok]{'━' * filled}[/ok][muted]{'─' * (bar_width - filled)}[/muted] [bold white]{pct}%[/bold white]"

    lineas = [f"  Progreso: {barra} [muted]({done_count}/{total} completadas)[/muted]\n"]
    for i, t in enumerate(AGENT_TODOS, 1):
        status = t.get("status", "pending").lower()
        desc = t.get("task", "")
        if status == "done":
            lineas.append(f"  [ok]✔ {i}.[/ok] [strike_muted]{desc}[/strike_muted]")
        elif status == "in_progress":
            lineas.append(f"  [warn]▶ {i}.[/warn] [bold white]{desc}[/bold white] [warn]● en curso[/warn]")
        else:
            lineas.append(f"  [muted]○ {i}. {desc}[/muted]")
    console.print(
        Panel(
            "\n".join(lineas),
            title=f"[brand]📋 Plan de Ejecución en Vivo ({done_count}/{total})[/brand]",
            border_style="#10b981" if done_count == total else "#6366f1",
            box=ROUNDED,
            padding=(0, 1),
        )
    )


def web_fetch(url: str) -> str:
    """Descarga y extrae el contenido legible de una página web o documentación técnica.
    
    Args:
        url: URL completa (http:// o https://) a consultar.
    """
    cb = _registrar_llamada_herramienta("web_fetch")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(f"  [tool.web]🌐 web_fetch[/tool.web] [bold white]{url}[/bold white]")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        if "<html" in raw.lower() or "<body" in raw.lower():
            raw = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = html.unescape(raw)
            raw = re.sub(r"\s+", " ", raw).strip()
        return _truncate_output(raw, max_chars=16000)
    except Exception as e:
        return f"Error descargando {url}: {e}"


class _DynamicQuietHTTPHandler(SimpleHTTPRequestHandler):
    """Sirve siempre desde el SESSION_CWD actual y desactiva caché para que los cambios en juegos/apps se vean al instante."""

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".json": "application/json",
        ".wasm": "application/wasm",
        ".svg": "image/svg+xml",
        ".css": "text/css",
        ".html": "text/html",
    }

    def translate_path(self, path: str) -> str:
        from urllib.parse import unquote
        path = path.split("?", 1)[0].split("#", 1)[0]
        rel = unquote(path).lstrip("/")
        return str((SESSION_CWD / rel).resolve())

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def log_message(self, format, *args):
        pass


def preview(target: str = "index.html", open_browser: bool = True) -> str:
    """Inicia un servidor HTTP local sin caché en segundo plano y abre tu juego o herramienta HTML/Web en el navegador.
    
    Args:
        target: Archivo HTML o ruta local a previsualizar (ej. 'index.html', 'game.html').
        open_browser: Si es True, abre automáticamente el navegador del usuario.
    """
    global PREVIEW_SERVER, PREVIEW_PORT
    cb = _registrar_llamada_herramienta("preview")
    if cb:
        return cb
    try:
        if PREVIEW_SERVER is None:
            PREVIEW_SERVER = ThreadingHTTPServer(("127.0.0.1", 0), _DynamicQuietHTTPHandler)
            PREVIEW_PORT = PREVIEW_SERVER.server_port
            t = threading.Thread(target=PREVIEW_SERVER.serve_forever, daemon=True)
            t.start()

        clean_target = target.lstrip("/\\")
        url = f"http://127.0.0.1:{PREVIEW_PORT}/{clean_target}"
        console.print(
            f"  [tool.web]🚀 preview[/tool.web] Servidor local activo en: [bold underline cyan]{url}[/bold underline cyan]"
        )
        if open_browser:
            webbrowser.open(url)
        return f"Servidor de vista previa activo en {url} (Navegador abierto={open_browser}).{_auto_avanzar_plan('preview', target)}"
    except Exception as e:
        return f"Error iniciando vista previa: {e}"


def validate_code(path: str) -> str:
    """Realiza una auditoría estática y de sintaxis profunda sobre un archivo (.html, .js, .mjs, .py, .json) usando compiladores locales (Node.js / Python).
    
    Args:
        path: Ruta del archivo a auditar (ej. 'index.html', 'app.js', 'script.py').
    """
    cb = _registrar_llamada_herramienta("validate_code")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(f"  [tool.search]🧪 validate_code[/tool.search] [bold white]{path}[/bold white]")
    try:
        p = _resolve_path(path)
        if not p.is_file():
            return f"Error: El archivo '{path}' no existe."

        ext = p.suffix.lower()
        source = p.read_text(encoding="utf-8", errors="replace")
        errores: list[str] = []

        if ext == ".py":
            try:
                compile(source, str(p.name), "exec")
            except SyntaxError as e:
                errores.append(f"Python SyntaxError en línea {e.lineno}: {e.msg}")

        elif ext == ".json":
            try:
                json.loads(source)
            except Exception as e:
                errores.append(f"JSON inválido: {e}")

        elif ext in (".js", ".mjs"):
            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as tf:
                tf.write(source)
                temp_name = tf.name
            try:
                res = subprocess.run(["node", "--check", temp_name], capture_output=True, text=True, timeout=10)
                if res.returncode != 0:
                    errores.append(f"Node.js SyntaxError:\n{res.stderr.strip()}")
            except FileNotFoundError:
                pass
            finally:
                Path(temp_name).unlink(missing_ok=True)

        elif ext in (".html", ".htm"):
            import tempfile
            # 1. Verificar balance de etiquetas críticas de bloque
            for tag in ("script", "style"):
                abiertas = len(re.findall(rf"<{tag}\b[^>]*>", source, flags=re.IGNORECASE))
                cerradas = len(re.findall(rf"</{tag}\s*>", source, flags=re.IGNORECASE))
                if abiertas != cerradas:
                    errores.append(f"Etiqueta <{tag}> desbalanceada ({abiertas} abiertas vs {cerradas} cerradas).")

            # 2. Extraer cada bloque <script> (excepto importmap/json) y validarlo con `node --check`
            bloques = re.finditer(r"<script([^>]*)>(.*?)</script\s*>", source, flags=re.DOTALL | re.IGNORECASE)
            for idx, m in enumerate(bloques, 1):
                attrs, js_code = m.group(1).lower(), m.group(2)
                if "importmap" in attrs or "application/json" in attrs or not js_code.strip():
                    continue
                if "src=" in attrs and not js_code.strip():
                    continue
                with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as tf:
                    tf.write(js_code)
                    temp_name = tf.name
                try:
                    res = subprocess.run(["node", "--check", temp_name], capture_output=True, text=True, timeout=10)
                    if res.returncode != 0:
                        err_clean = res.stderr.replace(temp_name, f"{path} (script #{idx})").strip()
                        errores.append(f"Error JS en bloque <script #{idx}>:\n{err_clean}")
                except FileNotFoundError:
                    pass
                finally:
                    Path(temp_name).unlink(missing_ok=True)

        if errores:
            msg = "\n".join(errores)
            console.print(f"  [err]✗ Se detectaron problemas en {path}:[/err]\n[muted]{msg}[/muted]")
            return f"VALIDACIÓN FALLIDA en {path}:\n{msg}"

        console.print(f"  [ok]✓ Código validado sin errores de sintaxis ({path})[/ok]")
        return f"OK: {path} pasó todas las pruebas de sintaxis y estructura correctamente."
    except Exception as e:
        return f"Error validando {path}: {e}"


def inspect_code(path: str = ".") -> str:
    """Extrae el mapa estructural de símbolos (clases, funciones, ids HTML, variables globales) de un archivo o directorio sin gastar tokens leyendo todo el código.
    
    Args:
        path: Ruta de un archivo o carpeta (por defecto '.').
    """
    cb = _registrar_llamada_herramienta("inspect_code")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(f"  [tool.search]🧬 inspect_code[/tool.search] [bold white]{path}[/bold white]")
    try:
        target = _resolve_path(path)
        archivos = [target] if target.is_file() else []
        if target.is_dir():
            ignore = {".git", "node_modules", "__pycache__", ".venv", "venv"}
            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in ignore]
                for f in sorted(files):
                    if Path(f).suffix.lower() in (".py", ".js", ".ts", ".html", ".css"):
                        archivos.append(Path(root) / f)

        resumen_total = []
        for arch in archivos[:25]:
            lines = arch.read_text(encoding="utf-8", errors="replace").splitlines()
            rel = arch.relative_to(SESSION_CWD).as_posix() if arch.is_relative_to(SESSION_CWD) else arch.name
            simbolos = []
            for idx, line in enumerate(lines, 1):
                s = line.strip()
                # Python / JS / HTML symbols
                if re.match(r"^(async\s+)?(def|class|function)\s+[a-zA-Z0-9_]+", s):
                    simbolos.append(f"  L{idx:4d}: {s[:90]}")
                elif re.match(r"^(const|let|var)\s+[a-zA-Z0-9_]+\s*=\s*(\([^)]*\)|[a-zA-Z0-9_]+)\s*=>", s):
                    simbolos.append(f"  L{idx:4d}: {s[:90]}")
                elif re.match(r"^(async\s+)?[a-zA-Z0-9_$]+\s*\([^)]*\)\s*\{", s) and not any(s.startswith(k) for k in ("if", "for", "while", "switch", "catch")):
                    simbolos.append(f"  L{idx:4d}: [method] {s[:90]}")
                elif "id=" in s and ("<div" in s or "<canvas" in s or "<button" in s or "<section" in s or "<nav" in s):
                    simbolos.append(f"  L{idx:4d}: [DOM] {s[:90]}")
            header = f"📄 {rel} ({len(lines)} líneas):"
            resumen_total.append(header + ("\n" + "\n".join(simbolos[:60]) if simbolos else " (sin símbolos principales)"))

        salida = "\n\n".join(resumen_total) if resumen_total else "No se encontraron archivos de código para inspeccionar."
        if VIEW_MODE == "full" and resumen_total:
            console.print(Panel(salida[:2500], title="[accent]🧬 Mapa de Símbolos[/accent]", border_style="bright_black", box=ROUNDED))
        return _truncate_output(salida)
    except Exception as e:
        return f"Error en inspect_code: {e}"


def web_search(query: str, max_results: int = 6) -> str:
    """Busca en internet en tiempo real (documentación, librerías, referencias de diseño, APIs) y devuelve títulos, URLs y resúmenes.
    
    Args:
        query: Consulta de búsqueda.
        max_results: Número máximo de resultados (por defecto 6).
    """
    cb = _registrar_llamada_herramienta("web_search")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(f"  [tool.web]🌍 web_search[/tool.web] [bold white]'{query}'[/bold white]")
    try:
        from urllib.parse import quote_plus, unquote
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        bloques = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            raw,
            flags=re.DOTALL,
        )
        if not bloques:
            # Fallback si DuckDuckGo devuelve layout alternativo
            bloques = [
                (m.group(1), m.group(2), "")
                for m in re.finditer(r'<a[^>]+class="[^"]*result[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', raw, flags=re.DOTALL)
                if "duckduckgo.com" not in m.group(1)
            ]
        resultados = []
        for href, title_html, snip_html in bloques[:max_results]:
            if "uddg=" in href:
                href = unquote(href.split("uddg=", 1)[1].split("&", 1)[0])
            t_clean = html.unescape(re.sub(r"<[^>]+>", "", title_html)).strip()
            s_clean = html.unescape(re.sub(r"<[^>]+>", "", snip_html)).strip()
            resultados.append(f"- {t_clean}\n  URL: {href}\n  Resumen: {s_clean}")

        if VIEW_MODE == "full" and resultados:
            console.print(f"    [muted]↳ {len(resultados)} resultado(s) web encontrados[/muted]")
        return "\n\n".join(resultados) if resultados else f"No se encontraron resultados para '{query}'."
    except Exception as e:
        return f"Error en web_search: {e}"


def _get_memory_file() -> Path:
    f_new = SESSION_CWD / ".anticli_memory.md"
    f_old = SESSION_CWD / ".pi_memory.md"
    if f_new.is_file():
        return f_new
    if f_old.is_file():
        return f_old
    return f_new


def memory_store(action: str = "read", note: str = "") -> str:
    """Lee o guarda notas persistentes del proyecto en `.anticli_memory.md` (preferencias del usuario, arquitectura, decisiones de diseño).
    
    Args:
        action: 'read' para leer la memoria actual, 'add' para agregar una nota, 'clear' para limpiar.
        note: Texto a guardar cuando action='add'.
    """
    mem_file = _get_memory_file()
    cb = _registrar_llamada_herramienta("memory_store")
    if cb:
        return cb
    if VIEW_MODE != "quiet":
        console.print(f"  [brand]🧠 memory_store[/brand] [bold white]{action}[/bold white]")
    try:
        if action == "read":
            if not mem_file.is_file():
                return "Memoria del proyecto vacía (.anticli_memory.md aún no existe)."
            return mem_file.read_text(encoding="utf-8", errors="replace")
        elif action == "add":
            existente = mem_file.read_text(encoding="utf-8", errors="replace") if mem_file.is_file() else "# Memoria del Proyecto (AntiCli)\n\n"
            nuevo = existente.rstrip() + f"\n- {note.strip()}\n"
            mem_file.write_text(nuevo, encoding="utf-8")
            return f"Nota guardada en {mem_file.name}."
        elif action == "clear":
            if mem_file.is_file():
                mem_file.unlink()
            return "Memoria del proyecto eliminada."
        return "Error: action debe ser 'read', 'add' o 'clear'."
    except Exception as e:
        return f"Error en memory_store: {e}"


ALL_TOOLS = [
    bash,
    read,
    write,
    edit,
    patch_lines,
    validate_code,
    inspect_code,
    glob_files,
    grep_search,
    todo_write,
    todo_check,
    web_search,
    web_fetch,
    memory_store,
    preview,
]


# =====================================================================
# AUTOCOMPLETADO INTELIGENTE (/comandos, argumentos y @archivos)
# =====================================================================

class AntiCliCompleter(Completer):
    """Autocompleta comandos '/' al inicio, modos de comandos y rutas de archivos tras '@'."""

    def __init__(self):
        self.commands = [
            "/plan",
            "/plan on",
            "/plan off",
            "/plan status",
            "/loop",
            "/loop 3",
            "/loop 5",
            "/auto",
            "/help",
            "/view",
            "/view full",
            "/view compact",
            "/view quiet",
            "/show",
            "/check",
            "/map",
            "/memory",
            "/ctx",
            "/compact",
            "/skills",
            "/skills auto",
            "/skills all",
            "/style",
            "/style auto",
            "/style classic",
            "/style dungeon",
            "/style cozy",
            "/style gameboy",
            "/style swiss",
            "/style hud",
            "/style glass",
            "/style organic",
            "/style arcade",
            "/design",
            "/game",
            "/3d",
            "/tool",
            "/todo",
            "/undo",
            "/tree",
            "/preview",
            "/diff",
            "/status",
            "/save",
            "/reset",
            "/think",
            "/model",
            "/cd",
            "/pwd",
            "/tokens",
            "/clear",
            "/cls",
            "/q",
            "/exit",
        ]
        self.cmd_completer = WordCompleter(self.commands, ignore_case=True, sentence=True)
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/show ") or text.startswith("/preview ") or text.startswith("/cd ") or text.startswith("/check ") or text.startswith("/map "):
            cmd_prefix, _, path_part = text.partition(" ")
            sub_doc = document.__class__(path_part, cursor_position=len(path_part))
            for comp in self.path_completer.get_completions(sub_doc, complete_event):
                yield Completion(
                    comp.text,
                    start_position=comp.start_position,
                    display=comp.display,
                    display_meta="ruta",
                )
            return

        if text.startswith("/"):
            yield from self.cmd_completer.get_completions(document, complete_event)
            return

        at_idx = text.rfind("@")
        if at_idx != -1 and (at_idx == 0 or text[at_idx - 1].isspace()):
            prefix = text[at_idx + 1 :]
            if " " not in prefix:
                sub_doc = document.__class__(prefix, cursor_position=len(prefix))
                for comp in self.path_completer.get_completions(sub_doc, complete_event):
                    yield Completion(
                        comp.text,
                        start_position=comp.start_position,
                        display=comp.display,
                        display_meta="archivo",
                    )


# =====================================================================
# ROUTER DE SKILLS BAJO DEMANDA Y GESTIÓN DE CONTEXTO (70% UMBRAL)
# =====================================================================

SKILL_KEYWORDS: dict[str, list[str]] = {
    "webgl-3d": [
        "3d", "three.js", "threejs", "webgl", "voxel", "shader", "glsl",
        "bloom", "cubo", "esfera", "camara 3d", "escena 3d", "mesh", "raycaster",
    ],
    "game-architect": [
        "juego", "game", "arcade", "jugable", "tetris", "snake", "flappy", "pong",
        "rpg", "plataformas", "shooter", "enemigo", "colision", "colisión", "puntaje",
        "score", "vidas", "nivel", "boss", "jugador", "player", "fps", "gameloop",
        "menu de juego", "menú de juego", "minijuego",
    ],
    "procedural-art": [
        "particula", "partícula", "shader", "canvas", "animacion", "animación",
        "procedural", "audio", "sonido", "webaudio", "efecto", "visualizador",
        "fractal", "ondas", "generativo", "sprite", "neon", "neón",
    ],
    "ui-ux-pro": [
        "ui", "ux", "interfaz", "diseño", "diseno", "dashboard", "panel", "web",
        "html", "css", "landing", "app", "aplicacion", "aplicación", "menu", "menú",
        "boton", "botón", "formulario", "modal", "estetica", "estética", "grafico",
        "gráfico", "calculadora", "editor", "reproductor", "portafolio", "tienda",
    ],
    "tool-craft": [
        "herramienta", "tool", "script", "cli", "utilidad", "automatiza", "conversor",
        "analizador", "generador", "monitor", "gestor", "sistema", "api", "scraper",
    ],
}


def detectar_skills_para_prompt(texto: str) -> list[str]:
    """Detecta qué skills son relevantes para la solicitud actual sin cargar todas a la vez."""
    t_low = texto.lower()
    seleccionadas: list[str] = []

    # 1. Comandos explícitos de modo
    if "modo 3d webgl" in t_low or t_low.startswith("/3d"):
        seleccionadas.extend(["webgl-3d", "ui-ux-pro"])
    elif "modo game architect" in t_low or t_low.startswith("/game"):
        seleccionadas.extend(["game-architect", "procedural-art", "ui-ux-pro"])
    elif "modo dirección de arte" in t_low or t_low.startswith("/design"):
        seleccionadas.extend(["ui-ux-pro", "procedural-art"])
    elif "modo tool crafter" in t_low or t_low.startswith("/tool"):
        seleccionadas.extend(["tool-craft", "ui-ux-pro"])

    # 2. Detección por intención semántica / palabras clave
    for sk_id, kw_list in SKILL_KEYWORDS.items():
        if sk_id not in seleccionadas and any(kw in t_low for kw in kw_list):
            seleccionadas.append(sk_id)

    # Si es un juego 2D o 3D, asegurar que tenga también dirección de arte UI/UX para los menús/HUD
    if ("game-architect" in seleccionadas or "webgl-3d" in seleccionadas) and "ui-ux-pro" not in seleccionadas:
        seleccionadas.append("ui-ux-pro")

    # Preservar orden y limitar a máximo 2 skills bajo demanda por turno para cuidar los tokens
    resultado_unico = []
    for s in seleccionadas:
        if s not in ACTIVE_SKILLS and s not in resultado_unico:
            resultado_unico.append(s)
    return resultado_unico[:2]


def construir_capsula_continuidad() -> str:
    """Construye un resumen ultra compacto del estado de la sesión (archivos, símbolos, plan y últimos turnos) para conservar la memoria al compactar."""
    partes = ["[CÁPSULA DE CONTINUIDAD DE CONTEXTO — SESIÓN COMPACTADA AUTOMÁTICAMENTE]"]

    if SESSION_TURN_LOG:
        ultimos = SESSION_TURN_LOG[-4:]
        lineas_t = [
            f"  - Usuario pidió: {t['user'][:200]} -> Agente respondió: {t['assistant'][:220]}"
            for t in ultimos
        ]
        partes.append("Historial reciente resumido:\n" + "\n".join(lineas_t))

    if AGENT_TODOS:
        lineas_plan = [
            f"  {i + 1}. [{t.get('status', 'pending').upper()}] {t.get('task', '')}"
            for i, t in enumerate(AGENT_TODOS)
        ]
        partes.append("Estado actual del Plan de Ejecución (`AGENT_TODOS`):\n" + "\n".join(lineas_plan))

    if LAST_MODIFIED_FILES:
        resumen_archivos = []
        for arch in LAST_MODIFIED_FILES[-6:]:
            if arch.is_file():
                try:
                    lines = arch.read_text(encoding="utf-8", errors="replace").splitlines()
                    rel = arch.relative_to(SESSION_CWD).as_posix() if arch.is_relative_to(SESSION_CWD) else arch.name
                    simbolos = []
                    for idx, line in enumerate(lines, 1):
                        s = line.strip()
                        if re.match(r"^(async\s+)?(def|class|function)\s+[a-zA-Z0-9_]+", s):
                            simbolos.append(f"L{idx}:{s[:55]}")
                    sim_str = f" | Símbolos: {', '.join(simbolos[:8])}" if simbolos else ""
                    resumen_archivos.append(f"  - {rel} ({len(lines)} líneas){sim_str}")
                except Exception:
                    pass
        if resumen_archivos:
            partes.append(
                "Archivos creados/modificados en esta sesión (usa `read` o `inspect_code` si necesitas ver su contenido):\n"
                + "\n".join(resumen_archivos)
            )

    partes.append("Continúa atendiendo al usuario con fluidez sin repetir trabajo ya completado.")
    return "\n\n".join(partes)


def construir_system_prompt(thinking: bool) -> str:
    os_info = f"{sys.platform} ({os.name})"
    prefix = "<|think|>\n" if thinking else ""

    skills_bloque = ""
    if ACTIVE_SKILLS:
        partes_skills = [
            SKILLS_CATALOG[k]["content"] for k in ACTIVE_SKILLS if k in SKILLS_CATALOG
        ]
        if partes_skills:
            skills_bloque = "\n\n# SKILLS ESPECIALIZADAS FIJADAS\n" + "\n\n".join(partes_skills)

    directiva_estilo = ""
    if ACTIVE_STYLE != "auto" and ACTIVE_STYLE in DESIGN_PRESETS:
        directiva_estilo = (
            f"\n\n# DIRECCIÓN DE ARTE ACTIVA FIJADA POR EL USUARIO: {ACTIVE_STYLE.upper()}\n"
            f"Aplica obligatoriamente este paradigma visual en cualquier interfaz o experiencia gráfica: {DESIGN_PRESETS[ACTIVE_STYLE]}"
        )
    else:
        directiva_estilo = (
            "\n\n# DIRECCIÓN DE ARTE CAMALEÓNICA (MODO AUTO)\n"
            "1. FIDELIDAD AL ORIGINAL POR DEFECTO: Si el usuario pide un juego o herramienta conocido "
            "(ej. Tetris, Pac-Man, Flappy Bird, Snake, Space Invaders, Buscaminas, Pong), "
            "RESPETA POR DEFECTO Y EN PRIMER LUGAR SU ESTILO, PALETA DE COLORES Y TIPOGRAFÍA ORIGINAL HISTÓRICA.\n"
            "2. ESTILOS ALTERNATIVOS SOLO BAJO DEMANDA: Solo aplica estilos alternativos (ej. neón, cyberpunk, "
            "brutalismo, etc.) si el usuario lo pide explícitamente en su solicitud (ej. 'tetris en neón', 'pacman cyberpunk') "
            "o si activó un comando `/style` concreto. Si no se especifica estilo, el diseño original se respeta al 100%.\n"
            "3. CREACIONES NUEVAS: Si es una idea original sin referente previo, deduce una atmósfera visual coherente con su temática."
        )

    directiva_plan = ""
    if PLAN_MODE:
        directiva_plan = (
            "\n\n# MODO PLAN ACTIVO (ESTRICTO MODO ARQUITECTO - SOLO LECTURA)\n"
            "Estás en Modo Plan. Tienes PROHIBIDO crear o modificar archivos (`write`, `edit`, `patch_lines`, `bash` están bloqueados).\n"
            "Tu tarea exclusiva es investigar el código con `read`, `inspect_code`, `glob_files`, `grep_search` o buscar en internet, "
            "diseñar la arquitectura técnica y estructurar un plan de tareas numerado con `todo_write` para revisión del usuario."
        )

    mem_file = _get_memory_file()
    mem_bloque = ""
    if mem_file.is_file():
        try:
            mem_txt = mem_file.read_text(encoding="utf-8", errors="replace").strip()
            if mem_txt:
                mem_bloque = f"\n\n# MEMORIA PERSISTENTE DEL PROYECTO (.anticli_memory.md)\n{mem_txt[:3000]}"
        except Exception:
            pass

    return (
        f"{prefix}Eres AntiCli, un agente de ingeniería de software, dirección de arte UI/UX y creación de videojuegos 2D/3D "
        f"de terminal minimalista y quirúrgico.\n"
        f"Entorno actual: SO={os_info} | Directorio={SESSION_CWD}\n\n"
        f"Dispones de este arsenal de 15 herramientas:\n"
        f"- `bash(command, timeout)`: ejecuta comandos de consola, git, tests o scripts.\n"
        f"- `read(path, start_line, end_line)`: lee archivos mostrando líneas numeradas.\n"
        f"- `write(path, content)`: crea o sobrescribe un archivo completo (NUNCA pongas bloques ``` dentro de `content`).\n"
        f"- `edit(path, old_text, new_text)`: realiza reemplazos quirúrgicos de texto.\n"
        f"- `patch_lines(path, start_line, end_line, new_content)`: reemplaza directamente un rango de líneas por número (útil en archivos grandes o si `edit` falla).\n"
        f"- `validate_code(path)`: verifica errores de sintaxis en archivos HTML/JS (usando Node.js), Python o JSON antes de darlos por terminados.\n"
        f"- `inspect_code(path)`: extrae el mapa de clases, funciones e IDs DOM sin leer todo el archivo.\n"
        f"- `glob_files(pattern, path)`: encuentra archivos rápidamente por nombre/patrón.\n"
        f"- `grep_search(pattern, path, file_pattern)`: busca código o regex con línea exacta.\n"
        f"- `todo_write(tasks_json)`: crea tu lista visual de tareas en la consola del usuario.\n"
        f"- `todo_check(step_number, status)`: marca un paso del plan como 'done' o 'in_progress' (actualiza el progreso en pantalla al instante).\n"
        f"- `web_search(query, max_results)`: busca en internet en tiempo real (documentación, librerías, APIs).\n"
        f"- `web_fetch(url)`: descarga el texto de una URL específica.\n"
        f"- `memory_store(action, note)`: lee o guarda notas persistentes del proyecto en `.anticli_memory.md`.\n"
        f"- `preview(target, open_browser)`: levanta un servidor web local y abre el juego o herramienta en el navegador.\n\n"
        f"Reglas de oro:\n"
        f"1. En tareas de múltiples pasos (como crear un juego o una herramienta completa), inicia llamando a `todo_write` para mostrar tu plan y llama a `todo_check(step_number, 'done')` al completar cada etapa.\n"
        f"2. Cuando crees juegos web 2D/3D o herramientas HTML/JS, valida el archivo con `validate_code` y al terminar lánzalo con `preview`.\n"
        f"3. Para modificar archivos existentes grandes, usa primero `inspect_code` o `read` y aplica cambios con `edit` o `patch_lines` en vez de reescribir todo con `write`.\n"
        f"4. En Windows, NUNCA ejecutes herramientas de Linux como 'sed' o 'grep' en bash; usa 'edit', 'patch_lines', 'grep_search' o 'read'.\n"
        f"5. Evita bucles de reescritura masiva con 'write': si hay un error puntual de sintaxis, corrígelo con 'patch_lines' o 'edit'.\n"
        f"6. Respeta inicialmente el estilo original del juego o referente histórico; solo aplica estilo neón, cyberpunk o alternativo si el usuario lo especifica explícitamente en el prompt o mediante `/style`.\n"
        f"7. Sé directo, técnico y conciso. Responde en español."
        f"{directiva_plan}"
        f"{directiva_estilo}"
        f"{mem_bloque}"
        f"{skills_bloque}"
    )


def crear_config(model: str, base_url: str, thinking: bool = True) -> LocalOpenAIAgentConfig:
    prompt = construir_system_prompt(thinking)
    return LocalOpenAIAgentConfig(
        model=model,
        base_url=base_url,
        tools=ALL_TOOLS,
        system_instructions=CustomSystemInstructions(text=prompt),
        workspaces=[str(SESSION_CWD)],
        capabilities=CapabilitiesConfig(
            enabled_tools=BuiltinTools.none(),
            enable_subagents=False,
            agent_behavior=AgentBehavior.MINIMAL,
        ),
    )


def _http_get_json(url: str, timeout: float = 1.2) -> dict | list | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "Connection": "close"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def sincronizar_info_llamacpp(base_url: str) -> dict:
    """Extrae directamente de llama.cpp (/v1/models, /props y /slots) el nombre real del modelo, n_ctx y tokens en uso."""
    global SERVER_INFO
    clean = base_url.rstrip("/")
    if clean.endswith("/v1"):
        v1_base = clean
        root_base = clean[:-3]
    else:
        v1_base = clean + "/v1"
        root_base = clean

    # 1. Consultar /v1/models (estándar OpenAI + metadatos extendidos de llama.cpp)
    models_data = _http_get_json(f"{v1_base}/models")
    if isinstance(models_data, dict):
        SERVER_INFO["online"] = True
        lista = models_data.get("data", [])
        modelos = [m.get("id", "") for m in lista if m.get("id")]
        SERVER_INFO["models"] = modelos
        if lista and isinstance(lista[0], dict):
            m0 = lista[0]
            if m0.get("id"):
                SERVER_INFO["model_name"] = Path(m0["id"]).stem if ("/" in m0["id"] or "\\" in m0["id"]) else m0["id"]
            meta = m0.get("meta", {})
            if isinstance(meta, dict) and meta.get("n_ctx_train"):
                SERVER_INFO["n_ctx_train"] = int(meta["n_ctx_train"])
    else:
        SERVER_INFO["online"] = False
        return SERVER_INFO

    # 2. Consultar /props (endpoint nativo de llama-server con n_ctx real y ruta del GGUF)
    props_data = _http_get_json(f"{root_base}/props")
    if isinstance(props_data, dict):
        SERVER_INFO["online"] = True
        gen_settings = props_data.get("default_generation_settings", {})
        if isinstance(gen_settings, dict) and gen_settings.get("n_ctx"):
            SERVER_INFO["n_ctx"] = int(gen_settings["n_ctx"])
        elif props_data.get("n_ctx"):
            SERVER_INFO["n_ctx"] = int(props_data["n_ctx"])

        if props_data.get("total_slots"):
            SERVER_INFO["total_slots"] = int(props_data["total_slots"])

        m_alias = props_data.get("model_alias") or props_data.get("model_path") or ""
        if m_alias:
            SERVER_INFO["model_path"] = str(m_alias)
            nombre_limpio = Path(str(m_alias)).name
            if nombre_limpio.lower().endswith(".gguf"):
                nombre_limpio = nombre_limpio[:-5]
            if nombre_limpio:
                SERVER_INFO["model_name"] = nombre_limpio

    # 3. Consultar /slots (tokens exactos evaluados en caché KV y contexto por slot)
    slots_data = _http_get_json(f"{root_base}/slots")
    if isinstance(slots_data, list) and slots_data:
        SERVER_INFO["online"] = True
        max_past = 0
        for s in slots_data:
            if isinstance(s, dict):
                if s.get("n_ctx") and not SERVER_INFO["n_ctx"]:
                    SERVER_INFO["n_ctx"] = int(s["n_ctx"])
                n_past = int(
                    s.get("n_prompt_tokens")
                    or s.get("n_past")
                    or s.get("n_prompt_tokens_processed")
                    or 0
                )
                if n_past > max_past:
                    max_past = n_past
        if max_past > 0:
            SERVER_INFO["used_tokens"] = max_past

    return SERVER_INFO


def verificar_servidor(base_url: str) -> tuple[bool, list[str]]:
    info = sincronizar_info_llamacpp(base_url)
    return bool(info["online"]), list(info["models"])


def _formatear_resumen_args(args: dict) -> str:
    partes = []
    for k, v in args.items():
        if isinstance(v, str):
            if len(v) > 48 or "\n" in v:
                lineas = len(v.splitlines())
                partes.append(f"{k}=<{lineas} líneas, {len(v)} chars>")
            else:
                partes.append(f"{k}={v!r}")
        else:
            partes.append(f"{k}={v!r}")
    return ", ".join(partes)


async def ejecutar_turno(agent: Agent, mensaje: str, skills_inyectadas: set[str] | None = None) -> tuple[str, bool]:
    """Envía un mensaje al agente, inyecta skills bajo demanda o cápsula de continuidad, y verifica el umbral del 70% de contexto."""
    global HANDOFF_CAPSULE, CURRENT_TURN_TOOL_CALLS
    CURRENT_TURN_TOOL_CALLS = 0
    en_pensamiento = False
    cabecera_pensamiento_impresa = False
    buffer_respuesta = ""
    buffer_tag_pendiente = ""
    t_inicio = time.perf_counter()

    bloques_contexto_turno = []

    # 1. Si venimos de una compactación de contexto (/compact o auto 70%), inyectar la cápsula de continuidad
    if HANDOFF_CAPSULE:
        bloques_contexto_turno.append(HANDOFF_CAPSULE)
        HANDOFF_CAPSULE = ""

    # 2. Inyección de Skills Bajo Demanda (solo cuando el prompt las requiere y aún no se han enviado en esta sesión)
    if SKILLS_ON_DEMAND:
        skills_detectadas = detectar_skills_para_prompt(mensaje)
        nuevas_skills = [
            s for s in skills_detectadas
            if skills_inyectadas is None or s not in skills_inyectadas
        ]
        if nuevas_skills:
            if skills_inyectadas is not None:
                skills_inyectadas.update(nuevas_skills)
            if VIEW_MODE != "quiet":
                etiquetas = ", ".join(f"[bold #a855f7]{s}[/bold #a855f7]" for s in nuevas_skills)
                console.print(f"  [muted]⚡ Skills activadas bajo demanda para esta tarea:[/muted] {etiquetas}")
            textos_sk = [SKILLS_CATALOG[s]["content"] for s in nuevas_skills if s in SKILLS_CATALOG]
            bloques_contexto_turno.append(
                "[GUÍAS ESPECIALIZADAS ACTIVADAS BAJO DEMANDA PARA ESTA TAREA]\n" + "\n\n".join(textos_sk)
            )

    mensaje_efectivo = (
        "\n\n".join(bloques_contexto_turno) + f"\n\n[SOLICITUD DEL USUARIO]\n{mensaje}"
        if bloques_contexto_turno
        else mensaje
    )

    respuesta = await agent.chat(mensaje_efectivo)

    try:
        async for chunk in respuesta.chunks:
            if isinstance(chunk, Thought):
                if VIEW_MODE != "quiet":
                    if not cabecera_pensamiento_impresa:
                        console.print("  [brand]💭 Razonando...[/brand]")
                        cabecera_pensamiento_impresa = True
                    console.print(chunk.text, style="thought", end="", highlight=False)
                continue

            if isinstance(chunk, ToolCall):
                if en_pensamiento or cabecera_pensamiento_impresa:
                    console.print()
                    en_pensamiento = False
                    cabecera_pensamiento_impresa = False
                if VIEW_MODE == "full":
                    resumen = _formatear_resumen_args(chunk.args or {})
                    console.print(
                        f"  [muted]⚙ preparando llamada →[/muted] [accent]{chunk.name}[/accent][muted]({resumen})[/muted]"
                    )
                continue

            if isinstance(chunk, ToolResult):
                if chunk.error:
                    console.print(f"  [err]✗ Error en {chunk.name}: {chunk.error}[/err]")
                continue

            if isinstance(chunk, Text):
                token = buffer_tag_pendiente + chunk.text
                buffer_tag_pendiente = ""

                # Si el token termina con un posible inicio de etiqueta incompleta (ej. "<|thi" o "<|/"),
                # retener ese sufijo hasta el siguiente chunk para no imprimir etiquetas partidas.
                partial_match = re.search(r"<\|?/?[a-zA-Z]*\|?$", token)
                if partial_match and len(partial_match.group(0)) < 12:
                    buffer_tag_pendiente = partial_match.group(0)
                    token = token[: partial_match.start()]

                for open_tag in ("<|think|>", "<think>"):
                    if open_tag in token:
                        en_pensamiento = True
                        if VIEW_MODE != "quiet" and not cabecera_pensamiento_impresa:
                            console.print("  [brand]💭 Razonando...[/brand]")
                            cabecera_pensamiento_impresa = True
                        token = token.replace(open_tag, "")

                for close_tag in ("<|/think|>", "</think>"):
                    if close_tag in token:
                        partes = token.split(close_tag, 1)
                        if partes[0] and VIEW_MODE != "quiet":
                            console.print(partes[0], style="thought", end="", highlight=False)
                        en_pensamiento = False
                        cabecera_pensamiento_impresa = False
                        if VIEW_MODE != "quiet":
                            console.print("\n")
                        token = partes[1]

                if not token:
                    continue

                if en_pensamiento:
                    if VIEW_MODE != "quiet":
                        console.print(token, style="thought", end="", highlight=False)
                else:
                    console.print(token, end="", highlight=False)
                    buffer_respuesta += token

        if buffer_tag_pendiente:
            console.print(buffer_tag_pendiente, end="", highlight=False)
            buffer_respuesta += buffer_tag_pendiente

        _finalizar_plan_al_terminar_turno()
        console.print()

        # Guardar resumen ligero del turno para futura compactación de contexto
        SESSION_TURN_LOG.append(
            {
                "user": mensaje.strip().replace("\n", " ")[:240],
                "assistant": buffer_respuesta.strip().replace("\n", " ")[:280],
            }
        )

        duracion = time.perf_counter() - t_inicio
        usage = respuesta.usage_metadata
        # Sincronizar con llama.cpp para actualizar los tokens ocupados y el límite de contexto real
        sincronizar_info_llamacpp(agent._config.base_url or "http://127.0.0.1:8080/v1")
        requiere_compactacion = False

        # Si el servidor no reportó tokens ocupados en /slots (offline o mock), estimar con usage
        if SERVER_INFO.get("used_tokens", 0) == 0 and usage and usage.total_token_count > 0:
            SERVER_INFO["used_tokens"] = usage.prompt_token_count // max(1, CURRENT_TURN_TOOL_CALLS)

        if usage and usage.total_token_count > 0:
            tps = usage.candidates_token_count / duracion if duracion > 0 else 0
            n_ctx = SERVER_INFO.get("n_ctx", 0)
            ctx_info = ""
            if n_ctx > 0:
                usados = SERVER_INFO["used_tokens"]
                pct_ctx = (usados / n_ctx) * 100
                ctx_info = f" │ 🧠 Ctx: {usados:,}/{n_ctx:,} ({pct_ctx:.1f}% / umbral {COMPACT_THRESHOLD_PCT:.0f}%)"
                if pct_ctx >= COMPACT_THRESHOLD_PCT:
                    requiere_compactacion = True
            console.print(
                f"  [muted]⏱ {duracion:.1f}s ({tps:.1f} tok/s) │ 📊 {usage.prompt_token_count:,} in → "
                f"{usage.candidates_token_count:,} out{ctx_info}[/muted]"
            )
        else:
            n_ctx = SERVER_INFO.get("n_ctx", 0)
            usados = SERVER_INFO.get("used_tokens", 0)
            if n_ctx > 0 and (usados / n_ctx) * 100 >= COMPACT_THRESHOLD_PCT:
                requiere_compactacion = True

        return buffer_respuesta, requiere_compactacion

    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n  [warn]⚠ Generación cancelada por el usuario.[/warn]")
        try:
            await respuesta.cancel()
        except Exception:
            pass
        return buffer_respuesta, False


# =====================================================================
# UTILIDADES DEL ENTORNO AGÉNTICO (SHOW, UNDO, TREE, SKILLS, HELP)
# =====================================================================

def mostrar_archivo_completo(cmd_arg: str):
    """Muestra un archivo en consola con números de línea y resaltado de sintaxis (`/show <archivo> [inicio] [fin]`)."""
    partes = cmd_arg.split()
    if not partes:
        console.print("  [warn]Uso: /show <archivo> [linea_inicio] [linea_fin][/warn]")
        return
    ruta = partes[0]
    p = _resolve_path(ruta)
    if not p.is_file():
        console.print(f"  [err]✗ El archivo '{ruta}' no existe.[/err]")
        return
    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    start = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 1
    end = int(partes[2]) if len(partes) > 2 and partes[2].isdigit() else min(len(lines), start + 150)
    recorte = "\n".join(lines[max(0, start - 1) : end])
    syntax = Syntax(
        recorte,
        _detectar_lexer(ruta),
        theme="monokai",
        line_numbers=True,
        start_line=start,
        word_wrap=True,
        background_color="default",
    )
    console.print(
        Panel(
            syntax,
            title=f"[accent]📄 {ruta}[/accent] [muted](líneas {start}-{min(end, len(lines))} de {len(lines)})[/muted]",
            border_style="#38bdf8",
            box=ROUNDED,
        )
    )


def deshacer_ultimo_cambio():
    """Restaura el último archivo modificado o creado por write/edit/patch_lines."""
    if not LAST_MODIFIED_FILES:
        console.print("  [warn]No hay cambios recientes en esta sesión para deshacer.[/warn]")
        return
    target = LAST_MODIFIED_FILES[-1]
    historial = FILE_BACKUPS.get(target, [])
    if not historial:
        console.print("  [warn]No hay estado anterior guardado para ese archivo.[/warn]")
        return
    contenido_previo = historial.pop()
    if not historial:
        LAST_MODIFIED_FILES.pop()

    rel = target.relative_to(SESSION_CWD) if target.is_relative_to(SESSION_CWD) else target
    if contenido_previo is None:
        if target.is_file():
            target.unlink()
        console.print(f"  [ok]↩ Deshecho:[/ok] Archivo nuevo [bold white]{rel}[/bold white] eliminado.")
    else:
        actual = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else ""
        target.write_text(contenido_previo, encoding="utf-8")
        console.print(f"  [ok]↩ Deshecho:[/ok] [bold white]{rel}[/bold white] restaurado a su versión anterior.")
        _mostrar_diff_en_vivo(str(rel), actual, contenido_previo)


def mostrar_arbol_proyecto(max_depth: int = 2):
    ignore = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode"}
    lineas = [f"[accent]📂 {SESSION_CWD.name or SESSION_CWD}[/accent]"]

    def _recorrer(dir_path: Path, prefijo: str, depth: int):
        if depth > max_depth:
            return
        try:
            items = [
                x for x in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                if x.name not in ignore
            ]
        except Exception:
            return
        for idx, item in enumerate(items[:40]):
            es_ultimo = idx == len(items[:40]) - 1
            conector = "└── " if es_ultimo else "├── "
            if item.is_dir():
                lineas.append(f"{prefijo}{conector}[bold #38bdf8]{item.name}/[/bold #38bdf8]")
                nuevo_pref = prefijo + ("    " if es_ultimo else "│   ")
                _recorrer(item, nuevo_pref, depth + 1)
            else:
                size_kb = item.stat().st_size / 1024
                lineas.append(f"{prefijo}{conector}[white]{item.name}[/white] [muted]({size_kb:.1f} KB)[/muted]")

    _recorrer(SESSION_CWD, "", 1)
    console.print(Panel("\n".join(lineas), title="[brand]Estructura del Proyecto[/brand]", border_style="bright_black", box=ROUNDED))


def mostrar_tabla_skills():
    modo_str = "[ok]BAJO DEMANDA (Auto)[/ok]" if SKILLS_ON_DEMAND else "[warn]MANUAL[/warn]"
    table = Table(
        title=f"🎨 Skills de Diseño, Juegos 2D/3D y Herramientas — Modo: {modo_str}",
        box=ROUNDED,
        border_style="bright_black",
    )
    table.add_column("ID", style="bold #38bdf8")
    table.add_column("Estado", justify="center")
    table.add_column("Nombre", style="bold white")
    table.add_column("Descripción", style="muted")
    for k, info in SKILLS_CATALOG.items():
        if k in ACTIVE_SKILLS:
            activo = "[ok]● FIJA[/ok]"
        elif SKILLS_ON_DEMAND:
            activo = "[#a855f7]⚡ AUTO (Bajo Demanda)[/#a855f7]"
        else:
            activo = "[muted]○ INACTIVA[/muted]"
        table.add_row(k, activo, info["title"], info["desc"])
    console.print(table)
    console.print(
        "  [muted]Usa[/muted] [yellow]/skills auto[/yellow] [muted](bajo demanda),[/muted] "
        "[yellow]/skills all[/yellow] [muted](fijar todas) o[/muted] [yellow]/skills toggle <id>[/yellow]"
    )


def mostrar_tabla_estilos():
    table = Table(title="🎭 Direcciones de Arte UI/UX Disponibles (/style)", box=ROUNDED, border_style="#a855f7")
    table.add_column("Preset", style="bold #f59e0b", no_wrap=True)
    table.add_column("Estado", justify="center")
    table.add_column("Paradigma Visual y Atmósfera", style="white")
    for k, desc in DESIGN_PRESETS.items():
        activo = "[ok]● ACTIVO[/ok]" if k == ACTIVE_STYLE else "[muted]○[/muted]"
        table.add_row(k, activo, desc)
    console.print(table)
    console.print("  [muted]Usa[/muted] [yellow]/style <preset>[/yellow] [muted](ej. /style swiss, /style hud, /style glass, /style auto) para cambiar la estética.[/muted]")


def imprimir_panel_contexto(base_url: str, agent: Agent | None = None):
    """Muestra un panel detallado con el nombre real del modelo, ruta GGUF y ventana de contexto en vivo extraída de llama.cpp."""
    info = sincronizar_info_llamacpp(base_url)
    if agent is not None and info.get("used_tokens", 0) == 0:
        u = agent.conversation.total_usage
        if u and u.prompt_token_count > 0:
            info["used_tokens"] = u.prompt_token_count // max(1, agent.conversation.turn_count)

    n_ctx = info.get("n_ctx") or 0
    usados = info.get("used_tokens") or 0
    libres = max(0, n_ctx - usados) if n_ctx > 0 else 0
    pct = (usados / n_ctx * 100) if n_ctx > 0 else 0.0

    bar_w = 28
    filled = min(bar_w, int((usados / n_ctx) * bar_w)) if n_ctx > 0 else 0
    color_bar = "ok" if pct < 65 else ("warn" if pct < 85 else "err")
    barra = f"[{color_bar}]{'█' * filled}[/{color_bar}][muted]{'░' * (bar_w - filled)}[/muted] [bold white]{pct:.1f}%[/bold white]"

    lineas = [
        f"  [muted]Servidor:[/muted]       [accent]{base_url}[/accent] ({'[ok]ONLINE[/ok]' if info['online'] else '[err]OFFLINE[/err]'})",
        f"  [muted]Modelo activo:[/muted]  [bold white]{info.get('model_name') or 'Desconocido'}[/bold white]",
    ]
    if info.get("model_path"):
        lineas.append(f"  [muted]Archivo GGUF:[/muted]   [muted]{info['model_path']}[/muted]")
    if n_ctx > 0:
        lineas.append(f"  [muted]Contexto Slot:[/muted]  [bold #38bdf8]{n_ctx:,}[/bold #38bdf8] tokens (Slots totales: {info.get('total_slots', 1)})")
        lineas.append(f"  [muted]Tokens en uso:[/muted]  [bold white]{usados:,}[/bold white] usados │ [ok]{libres:,}[/ok] disponibles")
        lineas.append(f"  [muted]Ocupación KV:[/muted]   {barra}")
    else:
        lineas.append("  [muted]Contexto Slot:[/muted]  [warn]No reportado aún por el servidor (/props o /slots)[/warn]")

    if info.get("n_ctx_train"):
        lineas.append(f"  [muted]Ctx Entrenado:[/muted]  {info['n_ctx_train']:,} tokens máx nativos")
    lineas.append(
        f"  [muted]Auto-Compact:[/muted]   [bold #f59e0b]{COMPACT_THRESHOLD_PCT:.0f}%[/bold #f59e0b] "
        f"[muted](compactación automática con cápsula de continuidad │ /compact para forzar o cambiar)[/muted]"
    )

    console.print(
        Panel(
            "\n".join(lineas),
            title="[brand]🧠 Telemetría de Contexto y Modelo (llama.cpp)[/brand]",
            border_style="#38bdf8",
            box=ROUNDED,
            padding=(0, 1),
        )
    )


def imprimir_banner(modelo: str, base_url: str, online: bool):
    estado_srv = "[ok]● ONLINE[/ok]" if online else f"[err]○ OFFLINE ({base_url})[/err]"
    if ACTIVE_SKILLS:
        skills_txt = ", ".join(f"[#a855f7]{s}[/#a855f7]" for s in sorted(ACTIVE_SKILLS))
        if SKILLS_ON_DEMAND:
            skills_txt += " [muted]+ ⚡ Bajo Demanda[/muted]"
    elif SKILLS_ON_DEMAND:
        skills_txt = "[#a855f7]⚡ Bajo Demanda (Auto-Smart)[/#a855f7] [muted](ahorro de tokens activo)[/muted]"
    else:
        skills_txt = "ninguna"
    n_ctx = SERVER_INFO.get("n_ctx", 0)
    ctx_str = (
        f" [muted]│ Ctx:[/muted] [bold #38bdf8]{n_ctx // 1024}k ({n_ctx:,} tok, auto-compact {COMPACT_THRESHOLD_PCT:.0f}%)[/bold #38bdf8]"
        if n_ctx >= 1024
        else f" [muted]│ Auto-Compact:[/muted] [bold #38bdf8]{COMPACT_THRESHOLD_PCT:.0f}%[/bold #38bdf8]"
    )
    contenido = (
        f"[brand]AntiCli v2.5[/brand] [muted]│[/muted] [bold white]{modelo}[/bold white] {estado_srv}{ctx_str}\n"
        f"[muted]Directorio:[/muted] [accent]{SESSION_CWD}[/accent] [muted]│[/muted] "
        f"[muted]Vista:[/muted] [warn]{VIEW_MODE.upper()}[/warn] [muted]│[/muted] "
        f"[muted]Arte:[/muted] [bold #a855f7]{ACTIVE_STYLE.upper()}[/bold #a855f7]\n"
        f"[muted]Skills:[/muted] {skills_txt}\n"
        f"[muted]Comandos clave:[/muted] [yellow]/help[/yellow] • [yellow]/plan[/yellow] • [yellow]/loop[/yellow] • [yellow]/ctx[/yellow] • [yellow]/compact[/yellow] • "
        f"[yellow]/style[/yellow] • [yellow]/game[/yellow] • [yellow]/3d[/yellow] • [yellow]/tool[/yellow] • [yellow]/preview[/yellow]"
    )
    console.print(Panel.fit(contenido, border_style="#6366f1", box=ROUNDED, padding=(0, 2)))


def imprimir_ayuda():
    t = Table(box=ROUNDED, border_style="#6366f1", title="[brand]Centro de Comandos AntiCli v2.5[/brand]", show_lines=False)
    t.add_column("Comando / Atajo", style="bold #f59e0b", no_wrap=True)
    t.add_column("Categoría", style="#38bdf8")
    t.add_column("Descripción", style="white")

    filas = [
        ("/plan [on|off|status]", "Arquitectura", "Modo solo lectura: investiga y genera plan con todo_write sin tocar archivos"),
        ("/loop [n]  |  /auto", "Ejecución Bucle", "Ejecuta de forma autónoma las tareas del plan paso a paso (def: 5 pasos)"),
        ("/ctx  |  /tokens", "Telemetría KV", "Muestra el modelo real, contexto en llama.cpp, uso de KV cache y umbral"),
        ("/compact [umbral%]", "Contexto", "Compacta la sesión con Cápsula de Continuidad o ajusta el umbral (def: 70%)"),
        ("/skills [auto|all|toggle <id>]", "Agente", "Modo Bajo Demanda automático (ahorra tokens) o fijar skills manualmente"),
        ("/style [auto|swiss|hud|glass|organic|arcade]", "Dirección Arte", "Cambia el paradigma estético para evitar diseños repetitivos"),
        ("/view [full|compact|quiet]", "Visor en Vivo", "Controla si ves código nuevo, diffs, llamadas y consola en tiempo real"),
        ("/show <archivo> [ini] [fin]", "Inspección", "Muestra cualquier archivo en consola con sintaxis coloreada"),
        ("/check <archivo>", "Auditoría QA", "Valida sintaxis JS/HTML (con Node.js), Python o JSON en busca de errores"),
        ("/map [ruta]", "Inspección", "Extrae el mapa de funciones, clases e IDs DOM sin leer todo el archivo"),
        ("/memory [add <nota>|clear]", "Memoria", "Muestra o guarda notas persistentes del proyecto en .pi_memory.md"),
        ("/game <idea>", "Creación 2D", "Diseña y programa un juego 2D (60fps, partículas, audio WebAudio) y lo abre"),
        ("/3d <idea>", "Creación 3D", "Diseña una escena o juego 3D / Voxel con Three.js, luces y Bloom"),
        ("/tool <idea>", "Creación App", "Diseña y construye una herramienta con personalidad visual propia"),
        ("/design <idea>", "Creación UI", "Crea una interfaz, estudio o dashboard con dirección de arte a medida"),
        ("/preview [archivo.html]", "Entorno", "Inicia el servidor web local sin caché y abre tu proyecto en el navegador"),
        ("/todo [add|done|clear]", "Plan en Vivo", "Muestra o actualiza la barra de progreso y tareas del agente"),
        ("/undo", "Quirúrgico", "Deshace inmediatamente el último cambio de archivo (`write`/`edit`/`patch_lines`)"),
        ("/diff  |  /status", "Git & Código", "Muestra el diff actual o el estado del repositorio Git"),
        ("/tree", "Entorno", "Muestra el árbol visual de archivos del directorio actual"),
        ("/save [archivo.md]", "Sesión", "Exporta la última respuesta del modelo a un archivo Markdown"),
        ("/think", "Agente", "Alterna el bloque de pensamiento profundo (<|think|>) de Gemma 4"),
        ("/model [nombre]", "Agente", "Muestra o cambia el modelo activo en el servidor"),
        ("/reset", "Sesión", "Limpia por completo la memoria y el plan de tareas desde cero"),
        ("/clear  |  /cls", "Consola", "Limpia la pantalla de la terminal sin borrar la memoria del agente"),
        ("!<comando>", "Atajo Shell", "Ejecuta un comando directo en tu terminal sin gastar tokens"),
        ("@<archivo> (con Tab)", "Contexto", "Inyecta el contenido de un archivo directamente en tu prompt"),
    ]
    for cmd, cat, desc in filas:
        t.add_row(cmd, cat, desc)
    console.print(t)


def procesar_adjuntos(user_input: str) -> str:
    if "@" not in user_input:
        return user_input
    palabras = user_input.split()
    archivos_adjuntos = []
    for p in palabras:
        if p.startswith("@") and len(p) > 1:
            ruta_str = p[1:].strip(",.;:")
            ruta_arch = _resolve_path(ruta_str)
            if ruta_arch.is_file():
                try:
                    contenido_arch = ruta_arch.read_text(encoding="utf-8", errors="replace")
                    contenido_trunc = _truncate_output(contenido_arch, max_chars=24000)
                    archivos_adjuntos.append(
                        f"\n--- Contenido de {ruta_str} ---\n{contenido_trunc}\n--- Fin de {ruta_str} ---"
                    )
                    console.print(f"  [accent]📎 Adjuntado:[/accent] [white]{ruta_str}[/white] [muted]({len(contenido_arch)} bytes)[/muted]")
                except Exception as e:
                    console.print(f"  [err]⚠ No se pudo adjuntar {ruta_str}: {e}[/err]")
    if archivos_adjuntos:
        return user_input + "\n" + "\n".join(archivos_adjuntos)
    return user_input


# =====================================================================
# BUCLE INTERACTIVO PRINCIPAL (TUI CON BARRA DE ESTADO)
# =====================================================================

async def main():
    global SESSION_CWD, VIEW_MODE, ACTIVE_STYLE, SKILLS_ON_DEMAND, COMPACT_THRESHOLD_PCT, HANDOFF_CAPSULE, PLAN_MODE

    parser = argparse.ArgumentParser(
        description="AntiCli v2.5: Entorno agéntico quirúrgico con visor en vivo, auto-compactación de contexto y skills bajo demanda."
    )
    parser.add_argument("prompt", nargs="*", help="Prompt directo para ejecución de un solo turno.")
    parser.add_argument(
        "--model",
        default=os.environ.get("ANTICLI_MODEL", os.environ.get("PI_MODEL", "gemma-4-26b-a4b-it")),
        help="Nombre del modelo en el servidor (default: gemma-4-26b-a4b-it o $ANTICLI_MODEL).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ANTICLI_BASE_URL", os.environ.get("PI_BASE_URL", "http://127.0.0.1:8080/v1")),
        help="URL del servidor OpenAI/llama.cpp (default: http://127.0.0.1:8080/v1 o $ANTICLI_BASE_URL).",
    )
    parser.add_argument(
        "--view",
        choices=["full", "compact", "quiet"],
        default="full",
        help="Nivel de visualización en tiempo real (default: full).",
    )
    parser.add_argument(
        "--no-think",
        action="store_true",
        help="Iniciar con el modo de razonamiento (<|think|>) desactivado.",
    )
    args = parser.parse_args()

    VIEW_MODE = args.view
    thinking_activo = not args.no_think
    modelo_actual = args.model
    base_url = args.base_url
    ultima_respuesta_md = ""

    online, modelos_remotos = verificar_servidor(base_url)
    # Si el usuario no forzó un --model distinto por CLI y llama.cpp reporta su nombre real en /props o /v1/models, adoptarlo automáticamente
    if online and SERVER_INFO.get("model_name") and args.model == os.environ.get("ANTICLI_MODEL", os.environ.get("PI_MODEL", "gemma-4-26b-a4b-it")):
        if modelos_remotos and modelo_actual not in modelos_remotos:
            modelo_actual = modelos_remotos[0]
        elif SERVER_INFO.get("model_name"):
            modelo_actual = SERVER_INFO["model_name"]

    config = crear_config(modelo_actual, base_url, thinking_activo)

    if args.prompt:
        pedido = procesar_adjuntos(" ".join(args.prompt))
        if not online:
            console.print(f"[err]✗ No se detectó servidor activo en {base_url}.[/err]")
            return
        async with Agent(config) as agent:
            await ejecutar_turno(agent, pedido)
        return

    kb = KeyBindings()

    @kb.add("escape", "enter")
    def _(event):
        event.current_buffer.insert_text("\n")

    def _barra_estado():
        think_str = "ON" if thinking_activo else "OFF"
        todos_done = sum(1 for t in AGENT_TODOS if t.get("status") == "done")
        todos_str = f" │ 📋 {todos_done}/{len(AGENT_TODOS)}" if AGENT_TODOS else ""
        preview_str = f" │ 🌐 :{PREVIEW_PORT}" if PREVIEW_PORT else ""
        plan_str = " │ <style fg='#fbbf24'>📋 PLAN</style>" if PLAN_MODE else ""
        n_ctx = SERVER_INFO.get("n_ctx", 0)
        usados = SERVER_INFO.get("used_tokens", 0)
        if n_ctx > 0:
            pct = (usados / n_ctx) * 100
            ctx_str = f" │ 🧠 Ctx: <style fg='#38bdf8'>{usados // 1000}k/{n_ctx // 1024}k ({pct:.0f}%)</style>"
        else:
            ctx_str = ""
        nombre_corto = (SERVER_INFO.get("model_name") or modelo_actual)[:22]
        return HTML(
            f" <b>AntiCli</b> <style fg='#94a3b8'>{nombre_corto}</style>{ctx_str} "
            f"│ Dir: <style fg='#38bdf8'>{SESSION_CWD.name or SESSION_CWD}</style> "
            f"│ Vista: <style fg='#10b981'>{VIEW_MODE.upper()}</style> "
            f"│ Arte: <style fg='#a855f7'>{ACTIVE_STYLE.upper()}</style> "
            f"│ Think: <style fg='#f59e0b'>{think_str}</style>"
            f"{plan_str}{todos_str}{preview_str} │ <style fg='#64748b'>/plan • /loop • /help</style>"
        )

    session = PromptSession(
        history=FileHistory(str(Path.home() / ".anticli_history")),
        auto_suggest=AutoSuggestFromHistory(),
        completer=AntiCliCompleter(),
        key_bindings=kb,
        bottom_toolbar=_barra_estado,
    )

    prompt_style = Style.from_dict(
        {
            "cwd": "bold #38bdf8",
            "mode": "#a855f7",
            "prompt": "bold #10b981",
            "bottom-toolbar": "bg:#0f172a #cbd5e1",
        }
    )

    imprimir_banner(modelo_actual, base_url, online)

    while True:
        try:
            async with Agent(config) as agent:
                skills_inyectadas_sesion: set[str] = set()
                while True:
                    try:
                        carpeta_corta = SESSION_CWD.name or str(SESSION_CWD)
                        icono_vista = {"full": "👁", "compact": "⚡", "quiet": "🔇"}[VIEW_MODE]
                        etiqueta_modo = f"[📋 PLAN]" if PLAN_MODE else f"[{icono_vista} {VIEW_MODE}]"
                        user_input = await session.prompt_async(
                            [
                                ("class:cwd", f"\n{carpeta_corta} "),
                                ("class:mode", f"{etiqueta_modo} "),
                                ("class:prompt", "❯ "),
                            ],
                            style=prompt_style,
                        )
                        user_input = user_input.strip()
                    except (EOFError, KeyboardInterrupt):
                        console.print("\n[muted]Sesión finalizada.[/muted]")
                        return

                    if not user_input:
                        continue

                    # --- SALIDA ---
                    if user_input in ["/q", "/quit", "/exit", "salir"]:
                        console.print("[muted]Sesión finalizada.[/muted]")
                        return

                    # --- LIMPIAR PANTALLA ---
                    if user_input in ["/clear", "/cls"]:
                        console.clear()
                        continue

                    # --- AYUDA ---
                    if user_input == "/help":
                        imprimir_ayuda()
                        continue

                    # --- INSPECCIÓN DE ARCHIVOS (/show, /check, /map, /memory) ---
                    if user_input.startswith("/show"):
                        mostrar_archivo_completo(user_input[5:].strip())
                        continue

                    if user_input.startswith("/check"):
                        target = user_input[6:].strip() or "index.html"
                        validate_code(target)
                        continue

                    if user_input.startswith("/map"):
                        target = user_input[4:].strip() or "."
                        res_map = inspect_code(target)
                        if VIEW_MODE != "full":
                            console.print(res_map)
                        continue

                    if user_input.startswith("/memory"):
                        arg_mem = user_input[7:].strip()
                        if not arg_mem:
                            console.print(Panel(memory_store("read"), title="[brand]🧠 Memoria del Proyecto (.anticli_memory.md)[/brand]", border_style="#a855f7", box=ROUNDED))
                        elif arg_mem == "clear":
                            console.print(f"  [ok]{memory_store('clear')}[/ok]")
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            break
                        elif arg_mem.startswith("add "):
                            console.print(f"  [ok]{memory_store('add', arg_mem[4:])}[/ok]")
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            break
                        else:
                            console.print("  [warn]Uso: /memory  |  /memory add <nota>  |  /memory clear[/warn]")
                        continue

                    # --- COMPACTACIÓN INTELIGENTE DE CONTEXTO (/compact) ---
                    if user_input.startswith("/compact"):
                        partes = user_input.split()
                        if len(partes) > 1:
                            val_str = partes[1].rstrip("%")
                            try:
                                nuevo_umbral = float(val_str)
                                if 10.0 <= nuevo_umbral <= 95.0:
                                    COMPACT_THRESHOLD_PCT = nuevo_umbral
                                    console.print(
                                        f"  [ok]🧠 Umbral de auto-compactación ajustado al {COMPACT_THRESHOLD_PCT:.0f}% de la ventana de contexto.[/ok]"
                                    )
                                else:
                                    console.print("  [warn]El umbral debe estar entre 10% y 95% (ej. /compact 70).[/warn]")
                            except ValueError:
                                console.print("  [warn]Uso: /compact (compactar ahora)  |  /compact <porcentaje> (ej. /compact 70)[/warn]")
                            continue

                        HANDOFF_CAPSULE = construir_capsula_continuidad()
                        SERVER_INFO["used_tokens"] = 0
                        console.print(
                            Panel(
                                HANDOFF_CAPSULE,
                                title="[ok]♻ Contexto Compactado con Cápsula de Continuidad[/ok]",
                                subtitle="[muted]Historial pesado liberado; el agente conserva el plan, archivos y objetivos[/muted]",
                                border_style="#10b981",
                                box=ROUNDED,
                            )
                        )
                        break

                    # --- MODO PLAN (/plan) ---
                    if user_input.startswith("/plan"):
                        sub_cmd = user_input[5:].strip().lower()
                        if sub_cmd in ("on", "1", "true"):
                            PLAN_MODE = True
                            console.print(
                                "  [brand]📋 MODO PLAN ACTIVADO (Solo lectura / Arquitectura).[/brand]\n"
                                "  [muted]Herramientas de modificación bloqueadas. El agente investigará y estructurará el plan con todo_write.[/muted]"
                            )
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            break
                        elif sub_cmd in ("off", "0", "false"):
                            PLAN_MODE = False
                            console.print("  [ok]✓ Modo Plan desactivado. Herramientas quirúrgicas habilitadas.[/ok]")
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            break
                        elif sub_cmd == "status":
                            st = "[brand]ACTIVADO (Solo Lectura)[/brand]" if PLAN_MODE else "[ok]DESACTIVADO (Ejecución libre)[/ok]"
                            console.print(f"  [muted]Estado Modo Plan:[/muted] {st}")
                            _imprimir_panel_todos()
                            continue
                        else:
                            PLAN_MODE = not PLAN_MODE
                            if PLAN_MODE:
                                console.print(
                                    "  [brand]📋 MODO PLAN ACTIVADO (Solo lectura / Arquitectura).[/brand]\n"
                                    "  [muted]Herramientas de modificación bloqueadas. El agente investigará y estructurará el plan con todo_write.[/muted]"
                                )
                            else:
                                console.print("  [ok]✓ Modo Plan desactivado. Herramientas quirúrgicas habilitadas.[/ok]")
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            break

                    # --- MODO LOOP (/loop o /auto) ---
                    if user_input.startswith("/loop") or user_input.startswith("/auto"):
                        if PLAN_MODE:
                            console.print("  [warn]No puedes ejecutar /loop mientras el MODO PLAN esté activo. Desactívalo primero con `/plan off`.[/warn]")
                            continue

                        if not AGENT_TODOS:
                            console.print("  [warn]No hay tareas en el plan de ejecución (`AGENT_TODOS`). Pide al agente un análisis o usa `/todo add <tarea>` para crearlas.[/warn]")
                            continue

                        max_iter = 5
                        partes = user_input.split()
                        if len(partes) > 1 and partes[1].isdigit():
                            max_iter = int(partes[1])

                        console.print(
                            Panel(
                                f"Iniciando ejecución autónoma por etapas (máximo {max_iter} pasos).\n"
                                f"[muted]Presiona Ctrl+C en cualquier momento para pausar el bucle sin perder el progreso.[/muted]",
                                title="[brand]🔄 MODO LOOP AUTÓNOMO INICIADO[/brand]",
                                border_style="#6366f1",
                                box=ROUNDED,
                            )
                        )

                        paso_ejecutado = 0
                        while paso_ejecutado < max_iter:
                            siguiente_tarea = None
                            siguiente_idx = -1
                            for i, t in enumerate(AGENT_TODOS):
                                if t.get("status") != "done":
                                    siguiente_tarea = t
                                    siguiente_idx = i
                                    break

                            if not siguiente_tarea:
                                console.print("  [ok]🎉 ¡Todas las tareas del plan han sido completadas con éxito (100%)![/ok]")
                                break

                            siguiente_tarea["status"] = "in_progress"
                            paso_ejecutado += 1
                            desc_tarea = siguiente_tarea.get("task", "")

                            console.print(
                                Panel(
                                    f"[bold white]Paso {siguiente_idx + 1}/{len(AGENT_TODOS)}:[/bold white] {desc_tarea}",
                                    title=f"[warn]🔄 MODO LOOP ({paso_ejecutado}/{max_iter})[/warn]",
                                    border_style="#f59e0b",
                                    box=ROUNDED,
                                )
                            )

                            prompt_loop = (
                                f"MODO LOOP AUTOMÁTICO - PASO {siguiente_idx + 1}/{len(AGENT_TODOS)}:\n"
                                f"Tarea a ejecutar: '{desc_tarea}'.\n"
                                f"Instrucciones:\n"
                                f"1. Concéntrate EXCLUSIVAMENTE en completar esta tarea de forma quirúrgica.\n"
                                f"2. Modifica o crea el código necesario y valida con `validate_code`.\n"
                                f"3. Llama a `todo_check({siguiente_idx + 1}, 'done')` al finalizar."
                            )

                            try:
                                ultima_respuesta_md, req_comp = await ejecutar_turno(
                                    agent, prompt_loop, skills_inyectadas_sesion
                                )
                                if req_comp:
                                    HANDOFF_CAPSULE = construir_capsula_continuidad()
                                    SERVER_INFO["used_tokens"] = 0
                                    console.print(
                                        Panel(
                                            HANDOFF_CAPSULE,
                                            title="[ok]♻ Contexto Compactado con Cápsula de Continuidad durante Loop[/ok]",
                                            border_style="#10b981",
                                            box=ROUNDED,
                                        )
                                    )
                                    break
                            except KeyboardInterrupt:
                                console.print("\n  [warn]⚠ Modo Loop pausado por el usuario. El progreso actual se ha preservado.[/warn]")
                                break

                        continue

                    # --- CONTROL DE VISUALIZACIÓN EN VIVO (/view) ---
                    if user_input.startswith("/view"):
                        partes = user_input.split()
                        if len(partes) == 1:
                            ciclo = {"full": "compact", "compact": "quiet", "quiet": "full"}
                            VIEW_MODE = ciclo[VIEW_MODE]
                        elif partes[1].lower() in ("full", "compact", "quiet"):
                            VIEW_MODE = partes[1].lower()
                        else:
                            console.print("  [warn]Uso: /view [full | compact | quiet][/warn]")
                            continue
                        descripciones = {
                            "full": "MÁXIMO DETALLE (ves código nuevo, diffs coloreados, llamadas y salida de comandos en vivo)",
                            "compact": "COMPACTO (solo ves qué herramienta se invoca sin paneles de código)",
                            "quiet": "SILENCIOSO (solo ves la respuesta final del agente)",
                        }
                        console.print(f"  [ok]👁 Modo de visualización:[/ok] [bold white]{VIEW_MODE.upper()}[/bold white] — {descripciones[VIEW_MODE]}")
                        continue

                    # --- DIRECCIÓN DE ARTE (/style) ---
                    if user_input.startswith("/style"):
                        partes = user_input.split()
                        if len(partes) == 1:
                            mostrar_tabla_estilos()
                        elif partes[1].lower() in DESIGN_PRESETS:
                            ACTIVE_STYLE = partes[1].lower()
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            console.print(
                                f"  [ok]🎭 Dirección de Arte fijada en:[/ok] [bold white]{ACTIVE_STYLE.upper()}[/bold white] "
                                f"— {DESIGN_PRESETS[ACTIVE_STYLE]}"
                            )
                            break
                        else:
                            console.print(f"  [err]Estilo desconocido. Opciones: {', '.join(DESIGN_PRESETS.keys())}[/err]")
                        continue

                    # --- GESTIÓN DE SKILLS (/skills) ---
                    if user_input.startswith("/skills"):
                        partes = user_input.split()
                        if len(partes) >= 2 and partes[1].lower() == "auto":
                            SKILLS_ON_DEMAND = True
                            ACTIVE_SKILLS.clear()
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            console.print(
                                "  [ok]⚡ Skills en modo BAJO DEMANDA (Auto-Smart):[/ok] "
                                "Solo se inyectarán cuando la tarea lo requiera para ahorrar ventana de contexto."
                            )
                            break
                        elif len(partes) >= 2 and partes[1].lower() == "all":
                            SKILLS_ON_DEMAND = False
                            ACTIVE_SKILLS.update(SKILLS_CATALOG.keys())
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            console.print("  [warn]● Todas las skills han sido fijadas permanentemente en el System Prompt.[/warn]")
                            break
                        elif len(partes) >= 3 and partes[1] == "toggle":
                            sk_id = partes[2].strip()
                            if sk_id in SKILLS_CATALOG:
                                if sk_id in ACTIVE_SKILLS:
                                    ACTIVE_SKILLS.remove(sk_id)
                                    console.print(f"  [warn]○ Skill '{sk_id}' quitada de fijas (queda disponible bajo demanda).[/warn]")
                                else:
                                    ACTIVE_SKILLS.add(sk_id)
                                    console.print(f"  [ok]● Skill '{sk_id}' fijada permanentemente (contexto actualizado).[/ok]")
                                config = crear_config(modelo_actual, base_url, thinking_activo)
                                break
                            else:
                                console.print(f"  [err]Skill '{sk_id}' no existe. Opciones: {', '.join(SKILLS_CATALOG.keys())}[/err]")
                        else:
                            mostrar_tabla_skills()
                        continue

                    # --- PLAN DE TAREAS (/todo) ---
                    if user_input.startswith("/todo"):
                        partes = user_input.split(maxsplit=2)
                        if len(partes) == 1:
                            _imprimir_panel_todos()
                        elif partes[1] == "clear":
                            AGENT_TODOS.clear()
                            console.print("  [ok]✔ Plan de tareas limpiado.[/ok]")
                        elif partes[1] == "done" and len(partes) == 3 and partes[2].isdigit():
                            console.print(f"  [ok]{todo_check(int(partes[2]), 'done')}[/ok]")
                        elif partes[1] == "add" and len(partes) == 3:
                            AGENT_TODOS.append({"task": partes[2].strip(), "status": "pending"})
                            _imprimir_panel_todos()
                        else:
                            console.print("  [warn]Uso: /todo  |  /todo add <tarea>  |  /todo done <N>  |  /todo clear[/warn]")
                        continue

                    # --- DESHACER CAMBIOS (/undo) ---
                    if user_input == "/undo":
                        deshacer_ultimo_cambio()
                        continue

                    # --- ÁRBOL DE ARCHIVOS (/tree) ---
                    if user_input == "/tree":
                        mostrar_arbol_proyecto()
                        continue

                    # --- VISTA PREVIA WEB (/preview) ---
                    if user_input.startswith("/preview"):
                        partes = user_input.split(maxsplit=1)
                        target = partes[1].strip() if len(partes) > 1 else "index.html"
                        preview(target, open_browser=True)
                        continue

                    # --- EXPORTAR ÚLTIMA RESPUESTA (/save) ---
                    if user_input.startswith("/save"):
                        if not ultima_respuesta_md.strip():
                            console.print("  [warn]No hay respuesta previa para guardar.[/warn]")
                            continue
                        partes = user_input.split(maxsplit=1)
                        destino = _resolve_path(partes[1].strip() if len(partes) > 1 else "ultima_respuesta.md")
                        destino.write_text(ultima_respuesta_md, encoding="utf-8")
                        console.print(f"  [ok]💾 Respuesta guardada en:[/ok] {destino}")
                        continue

                    # --- RESET / THINK / MODEL ---
                    if user_input == "/reset":
                        AGENT_TODOS.clear()
                        SESSION_TURN_LOG.clear()
                        HANDOFF_CAPSULE = ""
                        SERVER_INFO["used_tokens"] = 0
                        console.print("[warn]↻ Contexto, historial y lista de tareas reiniciados desde cero.[/warn]")
                        break

                    if user_input == "/think":
                        thinking_activo = not thinking_activo
                        config = crear_config(modelo_actual, base_url, thinking_activo)
                        estado = "ACTIVADO" if thinking_activo else "DESACTIVADO"
                        console.print(f"[warn]🧠 Modo Thinking {estado} (contexto reiniciado).[/warn]")
                        break

                    if user_input.startswith("/model"):
                        partes = user_input.split(maxsplit=1)
                        if len(partes) == 1:
                            _, m_list = verificar_servidor(base_url)
                            console.print(f"  [accent]Modelo actual:[/accent] {modelo_actual}")
                            if m_list:
                                console.print(f"  [muted]Disponibles en servidor: {', '.join(m_list)}[/muted]")
                        else:
                            modelo_actual = partes[1].strip()
                            config = crear_config(modelo_actual, base_url, thinking_activo)
                            console.print(f"[warn]⇄ Modelo cambiado a '{modelo_actual}' (contexto reiniciado).[/warn]")
                            break
                        continue

                    if user_input == "/pwd":
                        console.print(f"  [accent]{SESSION_CWD}[/accent]")
                        continue

                    if user_input.startswith("/cd "):
                        res_cd = bash(f"cd {user_input[4:].strip()}")
                        console.print(f"  [accent]{res_cd}[/accent]")
                        config = crear_config(modelo_actual, base_url, thinking_activo)
                        continue

                    if user_input == "/diff":
                        out = bash("git diff")
                        if out and out != "(Comando ejecutado sin salida)":
                            console.print(Syntax(out[:6000], "diff", theme="monokai", background_color="default"))
                        else:
                            console.print("  [muted]No hay diferencias en git.[/muted]")
                        continue

                    if user_input == "/status":
                        out = bash("git status -sb")
                        console.print(out)
                        continue

                    if user_input in ("/tokens", "/ctx", "/context"):
                        imprimir_panel_contexto(base_url, agent)
                        u = agent.conversation.total_usage
                        console.print(
                            f"  [accent]📊 Acumulado sesión ({agent.conversation.turn_count} turnos):[/accent] "
                            f"{u.prompt_token_count:,} in + {u.candidates_token_count:,} out = "
                            f"[bold white]{u.total_token_count:,}[/bold white] tokens"
                        )
                        continue

                    # --- ATAJO !<comando> ---
                    if user_input.startswith("!"):
                        cmd_out = bash(user_input[1:].strip())
                        if VIEW_MODE != "full" and cmd_out and cmd_out != "(Comando ejecutado sin salida)":
                            console.print(cmd_out)
                        continue

                    # --- COMANDOS DE CREACIÓN GUIADA (/game, /3d, /tool, /design) ---
                    if user_input.startswith("/game "):
                        idea = user_input[6:].strip()
                        user_input = (
                            f"MODO GAME ARCHITECT ACTIVADO: Diseña y construye un videojuego completo y jugable para: '{idea}'. "
                            f"1) Crea primero un plan con `todo_write` y actualiza cada paso con `todo_check` conforme avances. "
                            f"2) ESTILO VISUAL Y FIDELIDAD HISTÓRICA: Si '{idea}' es un juego clásico/conocido (ej. Tetris, Pac-Man, Flappy Bird, Snake, Space Invaders, Pong, Buscaminas, etc.), "
                            f"RESPETA INICIALMENTE SU ESTILO, PALETA DE COLORES Y TIPOGRAFÍA ORIGINAL HISTÓRICA. Solo aplica un estilo alternativo (como neón, synthwave o cyberpunk) "
                            f"si el usuario lo especificó explícitamente en su pedido (ej. 'tetris en neón'); si no se especifica, el estilo original se respeta al 100%. "
                            f"3) Implementa Game Loop con DeltaTime seguro (cap 0.05s), estados (MENU, PLAYING, PAUSE, GAME OVER), "
                            f"prevención de scroll con flechas/espacio, sistema de partículas, screen-shake, HUD y WebAudio procedural acorde al estilo del juego. "
                            f"4) Escribe el código puro con `write` (sin bloques ```) y al terminar ábrelo con `preview`."
                        )
                    elif user_input.startswith("/3d "):
                        idea = user_input[4:].strip()
                        user_input = (
                            f"MODO 3D WEBGL & VOXEL ARCHITECT ACTIVADO: Crea una experiencia o juego 3D interactivo para: '{idea}'. "
                            f"1) Planifica con `todo_write` y actualiza el progreso con `todo_check`. "
                            f"2) Usa Three.js vía importmap ES Modules, InstancedMesh para rendimiento, iluminación atmosférica con niebla, "
                            f"EffectComposer + UnrealBloomPass, controles suaves y UI superpuesta elegante. "
                            f"3) Guarda el código puro con `write` (sin bloques ```) y ábrelo con `preview`."
                        )
                    elif user_input.startswith("/tool "):
                        idea = user_input[6:].strip()
                        user_input = (
                            f"MODO TOOL CRAFTER ACTIVADO: Diseña y construye una herramienta completa y funcional para: '{idea}'. "
                            f"1) Planifica los pasos con `todo_write` y actualízalos con `todo_check`. "
                            f"2) Aplica una arquitectura modular, manejo de errores, datos de ejemplo listos para usar y una interfaz "
                            f"oscura sobria y colorida. "
                            f"3) Verifica su funcionamiento (con `bash` o `preview`)."
                        )
                    elif user_input.startswith("/design "):
                        idea = user_input[8:].strip()
                        estilo_nota = (
                            f"aplicando el paradigma '{ACTIVE_STYLE.upper()}' ({DESIGN_PRESETS[ACTIVE_STYLE]})"
                            if ACTIVE_STYLE != "auto"
                            else "eligiendo el paradigma de Dirección de Arte más original y adecuado (Swiss Editorial, Tactical HUD, Spatial Glass, Organic Botanical o Cyber-Pop Arcade)"
                        )
                        user_input = (
                            f"MODO DIRECCIÓN DE ARTE UI/UX ACTIVADO: Crea una interfaz, aplicación o experiencia gráfica memorable para: '{idea}', {estilo_nota}. "
                            f"1) Planifica con `todo_write` y actualiza el progreso con `todo_check`. "
                            f"2) Importa Google Fonts reales, añade texturas (grano SVG, cuadrícula técnica o shaders/canvas procedural), "
                            f"micro-interacciones con curvas elásticas y componentes interactivos 100% funcionales. "
                            f"3) Escribe el código puro con `write` y ábrelo con `preview` al finalizar."
                        )

                    # Procesar archivos @adjuntos
                    prompt_final = procesar_adjuntos(user_input)

                    console.print(Rule(style="bright_black"))
                    ultima_respuesta_md, requiere_compactacion = await ejecutar_turno(
                        agent, prompt_final, skills_inyectadas_sesion
                    )

                    # Si alcanzamos o superamos el umbral del 70% de n_ctx, compactar automáticamente la sesión con Cápsula de Continuidad
                    if requiere_compactacion:
                        HANDOFF_CAPSULE = construir_capsula_continuidad()
                        usados_prev = SERVER_INFO.get("used_tokens", 0)
                        n_ctx_actual = SERVER_INFO.get("n_ctx", 0)
                        SERVER_INFO["used_tokens"] = 0
                        console.print(
                            Panel(
                                f"[warn]Se alcanzó el umbral del {COMPACT_THRESHOLD_PCT:.0f}% de contexto "
                                f"({usados_prev:,} / {n_ctx_actual:,} tokens).[/warn]\n"
                                f"[ok]✔ Se ha generado una Cápsula de Continuidad automática[/ok] (conservando tu plan de tareas, "
                                f"mapa de archivos modificados y resumen de conversación) y se ha liberado la caché KV para "
                                f"mantener máxima velocidad y precisión en el siguiente turno.",
                                title="[brand]♻ Auto-Compactación de Contexto Activada (70%)[/brand]",
                                border_style="#f59e0b",
                                box=ROUNDED,
                            )
                        )
                        break

        except Exception as e:
            console.print(f"\n[err]✗ Error en el motor del agente:[/err] {e}")
            console.print(
                f"[muted]Verifica que tu servidor local esté corriendo en {base_url} "
                f"o escribe /q para salir.[/muted]"
            )
            try:
                cmd = await session.prompt_async([("class:prompt", "\nReintentar [Enter] o /q ❯ ")], style=prompt_style)
                if cmd.strip() in ["/q", "/quit", "/exit", "salir"]:
                    return
            except (EOFError, KeyboardInterrupt):
                return


if __name__ == "__main__":
    asyncio.run(main())
