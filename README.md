# AntiCli (v2.6)

<p align="center">
  <a href="README.md"><b>English</b></a> • <a href="README.es.md"><b>Español</b></a>
</p>

> Surgical agentic environment and TUI for local LLMs (Gemma 4, DeepSeek, Qwen) via `llama.cpp` featuring real-time stream preview, chameleon art direction, native Playwright Chromium browser navigation, dual-language interface (ES/EN), smart 70% context auto-compaction, and Plan/Loop modes.

---

## 🚀 Key Features

* **Arsenal of 16 Surgical Tools:** Line-by-line surgical precision editing (`patch_lines`, `edit`), line-bounded syntax-highlighted reading (`read`), structural class/DOM inspection (`inspect_code`), static syntax checking for HTML/JS/Python/JSON (`validate_code`), glob and regex search (`glob_files`, `grep_search`), real-time web search (`web_search`, `web_fetch`), native headless Chromium browser automation with Playwright (`browser_action`), persistent memory (`memory_store`), and protected shell commands (`bash`).
* **Dual Language Support (English & Spanish):** Seamlessly toggle interface and agent responses with `/lang [es|en]` or the `--lang` CLI flag.
* **Live KV Telemetry with `llama.cpp`:** Real-time polling from native `/props` and `/slots` endpoints in `llama-server` to monitor context window allocation (`n_ctx`), active KV cache tokens, and the loaded GGUF model.
* **Auto-Compaction with Continuity Capsule (70% Threshold):** When a conversation turn reaches 70% of the active slot context, AntiCli automatically condenses the session into a lightweight continuity capsule (retaining goals, active plan, modified files, and key symbols) and clears KV cache tokens to prevent degradation.
* **Anti-Overflow Circuit Breaker:** Hard safety limit per turn to halt rogue autonomous tool call loops, preserving local model context.
* **Chameleon Art Direction (Historical Fidelity by Default):**
  * **Classic Games:** Faithfully adheres to official colors and aesthetics (Tetris official tetrominos, Pac-Man cobalt blue maze, Flappy Bird daytime sky, Snake retro LCD dot-matrix).
  * **On-Demand Styles:** Only applies alternative aesthetics (neon, cyberpunk, dungeon, cozy, swiss editorial, tactical HUD) when explicitly requested or set via `/style <preset>`.
* **Strict Plan Mode (`/plan`):** Read-only architect mode. Blocks filesystem modifications and directs the agent to research code, inspect schemas, and draft a structured plan with `todo_write`.
* **Autonomous Loop Mode (`/loop [n]` or `/auto`):** Autonomous step-by-step execution. Processes pending roadmap tasks sequentially with clean context per step, pausable at any time with `Ctrl+C`.
* **Live Zero-Cache Preview Server (`preview`):** Multi-threaded local HTTP server with `no-cache` headers and broad MIME mapping to instantly launch games, web apps, and dashboards in your browser.
* **Cross-Platform Compatibility:** Runs seamlessly on **Windows**, **Linux**, and **macOS**.

---

## 💻 Cross-Platform Installation

### Prerequisites
* **Python:** 3.10 or higher.
* **llama.cpp server:** Running locally or accessible over the network (e.g. `http://127.0.0.1:8080/v1`).
* **Node.js:** *(Optional)* Recommended for JS/HTML syntax validation with `validate_code`.

---

### 1. Windows Installation

Open **PowerShell** or **Windows Terminal**:

```powershell
# Clone the repository
git clone https://github.com/ciiies07/AntiCli.git
cd AntiCli

# Install in editable mode
pip install -e .

# Install Playwright browser binaries (optional, for browser_action)
playwright install chromium
```

> [!TIP]
> Ensure your Python Scripts folder (e.g., `C:\Users\<User>\AppData\Local\Programs\Python\Python314\Scripts`) is included in your system `PATH`.

---

### 2. Linux Installation (Ubuntu, Debian, Fedora, Arch)

Open your terminal:

```bash
# Clone the repository
git clone https://github.com/ciiies07/AntiCli.git
cd AntiCli

# (Recommended) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Install Playwright browser binaries and OS dependencies
pip install playwright
playwright install chromium
playwright install-deps chromium
```

> [!TIP]
> If installing without a virtualenv (`--user`), make sure `~/.local/bin` is in your `$PATH`:
> ```bash
> export PATH="$HOME/.local/bin:$PATH"
> ```

---

### 3. macOS Installation (Apple Silicon & Intel)

Open **Terminal** or **iTerm2**:

```bash
# Ensure Python 3 is installed (via Homebrew if needed: brew install python)
git clone https://github.com/ciiies07/AntiCli.git
cd AntiCli

# (Recommended) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Install Playwright browser binaries
pip install playwright
playwright install chromium
```

---

## 🏃 Execution

Once installed, run `anticli` from **any directory** on your system:

```bash
anticli
```
*(Or `AntiCli` on Windows / case-insensitive shells).*

### Command-Line Arguments

```bash
anticli --lang en --view full --base-url http://127.0.0.1:8080/v1
```

| Option | Default | Description |
| :--- | :--- | :--- |
| `--lang` | `es` or `$ANTICLI_LANG` | Language for interface and agent responses (`en` = English, `es` = Spanish). |
| `--model` | `gemma-4-26b-a4b-it` or `$ANTICLI_MODEL` | Server model name (auto-detected from llama.cpp `/props` or `/v1/models`). |
| `--base-url` | `http://127.0.0.1:8080/v1` or `$ANTICLI_BASE_URL` | Base URL for OpenAI/llama.cpp server. |
| `--view` | `full` | Terminal live streaming detail level: `full`, `compact`, `quiet`. |
| `--no-think` | `False` | Launch with deep thought reasoning (`<|think|>`) disabled. |
| `prompt` | *(None)* | Optional direct prompt for non-interactive single-turn execution. |

---

## 🛠️ Arsenal of 16 Tools

| Tool | Category | Description |
| :--- | :--- | :--- |
| `bash(command, timeout)` | Execution | Protected console commands with timeout and process tree management. |
| `read(path, start_line, end_line)` | Reading | Reads line-bounded snippets with line numbers to conserve context tokens. |
| `write(path, content)` | Writing | Creates or overwrites complete files with automatic directory generation. |
| `edit(path, old_text, new_text)` | Surgical | Exact in-place text replacement without rewriting the full file. |
| `patch_lines(path, start, end, new)` | Surgical | Direct line-range replacement by line numbers for large files. |
| `validate_code(path)` | QA / Linter | Static syntax checking for HTML/JS (Node.js), Python, and JSON. |
| `inspect_code(path)` | Inspection | Extracts class, function, and DOM ID outline without reading whole files. |
| `glob_files(pattern, path)` | Discovery | Finds file paths matching wildcards/glob patterns. |
| `grep_search(pattern, path)` | Search | Regex search with exact line numbers across the active workspace. |
| `todo_write(tasks_json)` | Planning | Draws the live progress bar and task roadmap checklist in the terminal. |
| `todo_check(step_number, status)` | Planning | Updates task status (`done` / `in_progress`). |
| `web_search(query, max_results)` | Web | Real-time DuckDuckGo search for APIs, documentation, and references. |
| `web_fetch(url)` | Web | Clean HTML/Markdown text scraper for online documentation. |
| `browser_action(url, action, ...)` | Web / Automation | Headless Chromium browser (Playwright) to render JS SPAs, click, fill forms, evaluate JS, or capture screenshots. |
| `memory_store(action, note)` | Memory | Persistent project preferences and architectural notes in `.anticli_memory.md`. |
| `preview(target, open_browser)` | Environment | Local zero-cache HTTP web server to immediately preview projects in your browser. |

---

## 🎮 Interactive Command Center

| Command | Category | Description |
| :--- | :--- | :--- |
| `/lang [es\|en]` | Language | Switch language between English and Spanish on the fly. |
| `/plan [on\|off\|status]` | Architecture | Read-only mode: research and build roadmap with `todo_write` without modifying files. |
| `/loop [n]` or `/auto` | Autonomous Loop | Sequentially execute pending roadmap tasks step-by-step (default: 5 steps). |
| `/ctx` or `/tokens` | KV Telemetry | Show active model, llama.cpp context occupancy, and KV cache usage. |
| `/compact [threshold%]` | Context | Compact session with Continuity Capsule or adjust threshold (default: 70%). |
| `/skills [auto\|all\|toggle <id>]` | Agent | Smart On-Demand mode (saves tokens) or permanently pin specialized skills. |
| `/style [auto\|swiss\|hud\|glass\|arc]` | Art Direction | Switch aesthetic design paradigm to avoid repetitive AI outputs. |
| `/view [full\|compact\|quiet]` | Live Viewer | Switch between maximum detail, compact headers, or quiet terminal mode. |
| `/show <file> [start] [end]` | Inspection | Display any file in terminal with syntax highlighting. |
| `/check <file>` | QA Audit | Validate JS/HTML (via Node.js), Python, or JSON syntax for errors. |
| `/map [path]` | Inspection | Extract class, function, and DOM ID outline without reading entire files. |
| `/memory [add <note>\|clear]` | Memory | View or persist project architectural notes in `.anticli_memory.md`. |
| `/game <idea>` | 2D Creation | Design and program a 2D game (60fps, particles, WebAudio sound) and preview it. |
| `/3d <idea>` | 3D Creation | Design a 3D WebGL / Voxel scene with Three.js, lighting, and Bloom. |
| `/tool <idea>` | App Creation | Design and build a functional tool with distinctive studio ergonomics. |
| `/design <idea>` | UI Creation | Create an interface, dashboard, or design system with custom art direction. |
| `/preview [file.html]` | Environment | Start local zero-cache HTTP web server and launch preview in browser. |
| `/todo [add\|done\|clear]` | Live Plan | View or update real-time plan progress and task checkmarks. |
| `/undo` | Surgical | Immediately revert the last file change (`write`/`edit`/`patch_lines`). |
| `/diff` or `/status` | Git | Show current git diff or repository status. |
| `/tree` | Environment | Display visual directory file tree. |
| `/save [file.md]` | Session | Export model's last response to a Markdown file. |
| `/think` | Agent | Toggle Gemma 4 deep reasoning thought block (`<|think|>`). |
| `/model [name]` | Agent | Show or switch active model on the llama.cpp server. |
| `/reset` | Session | Reset conversation context, turn log, and task plan from scratch. |
| `/clear` or `/cls` | Console | Clear terminal screen without clearing agent memory. |
| `!<command>` | Shell Shortcut | Execute command directly in your OS terminal without spending tokens. |
| `@<file>` *(with Tab)* | Context | Inject file contents directly into your prompt. |

---

## 🎨 Chameleon Art Direction Presets

* **`auto`**: Smart chameleon (infers ideal aesthetic from domain and historical context).
* **`classic`**: Golden arcade & retro CRT (pure black CRT, vector phosphor lines, original retro color schemes).
* **`swiss`**: Swiss Editorial & Refined Brutalism (warm paper `#F4F1EA`, carbon ink `#141413`, international vermilion, large serif typography, hard shadows).
* **`hud`**: Tactical HUD & Cassette Futurism (obsidian black, 45° clip-path beveled corners, radar green/amber, technical reticles).
* **`glass`**: Atmospheric Spatial Glass & Aurora (abyssal depth, 24px blur backdrop filters, specular gradient borders).
* **`organic`**: Organic Botanical & Warm Tactile (sand, clay, forest green, warm diffuse shadows, SVG paper grain).
* **`arcade`**: Cyber-Pop & Retro Synthwave (deep violet, neon pink/cyan, perspective grids, high glow).
* **`gameboy`**: Retro 4-shade olive green dot-matrix LCD.
* **`dungeon`**: Dark slate stone, torchlight amber, ancient gold, and crimson.
* **`cozy`**: Minimalist warm cream and soft earthen pastels.

---

## 📄 License

MIT License © 2026 ciiies07.
