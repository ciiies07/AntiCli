# =====================================================================
# CATÁLOGO DE SKILLS OPTIMIZADAS: DIRECCIÓN DE ARTE, UI/UX, 2D & 3D
# =====================================================================

SKILL_UI_UX = """# Skill: Dirección de Arte Visual y Sistemas de Diseño UI/UX

## Principios de Excelencia Visual:
1. **Identidad Propia para Cada Proyecto**:
   - NUNCA uses la misma paleta genérica para todo. Adapta los colores al alma de la aplicación:
     * **Arcade / Juegos Retro**: Contrastes nítidos, marco arcade pulido, tipografía 'Press Start 2P' o 'Space Grotesk'.
     * **Herramientas / Dashboards**: Fondo carbón profundo (#0B0F17) o editorial (#F4F1EA), acentos cian/ámbar, tipografía 'JetBrains Mono' o 'Inter'.
     * **Experiencias Espaciales / Modernas**: Glassmorphism sutil (backdrop-filter: blur(20px)), bordes de 1px con brillo tenue, tipografía 'Plus Jakarta Sans'.
2. **Jerarquía y Acabado Profesional**:
   - Tipografía escalable con `clamp()`, contrastes de legibilidad WCAG AAA, espaciado con escala de 8px (8, 16, 24, 32px).
   - Micro-interacciones con transiciones suaves (`cubic-bezier(0.16, 1, 0.3, 1)`).
"""

SKILL_GAME_DEV = """# Skill: Ingeniería de Videojuegos 2D, "Game Feel" (Juice) y Audio WebAudio

## Regla de Oro: Entrega Juegos 100% Terminados y Jugables
Cuando el usuario pida un juego (Tetris, Snake, Pac-Man, Flappy Bird, Pong, Space Invaders, etc.):
- **IMPLEMENTA LA VERSIÓN DEFINITIVA DE INMEDIATO**: Código 100% completo en un solo archivo con todas las mecánicas, partículas, audio y controles. NUNCA entregues esqueletos a medias ni preguntes si desea sonido o partículas; incorpóralos directamente.
- **AL TERMINAR**: Llama siempre a `validate_code` y luego a `preview` para que el juego se abra automáticamente en el navegador del usuario.

## 1. Identidad Visual por Juego (Diseño de Alta Calidad sin Repetir):
- **Tetris**:
  * Marco arcade moderno y estilizado con sombra de profundidad.
  * Colores oficiales de tetrominós de alto contraste (Cian, Amarillo, Púrpura, Verde, Rojo, Azul, Naranja).
  * Pieza fantasma (Ghost piece) semitransparente para apuntar.
  * Tablero nítido con cuadrícula sutil y panel lateral con Score, Level, Lines y Next Piece.
- **Snake**:
  * Cuadrícula retro-futurista o LCD nítida, comida pulsante con resplandor, estela suave tras la cabeza de la serpiente.
- **Flappy Bird**:
  * Cielo luminoso, nubes procedurales con efecto Parallax, tuberías con volumen, rotación suave del personaje según su velocidad.
- **Pac-Man / Space Invaders**:
  * Atmósfera arcade nocturna, laberinto azul cobalto brillante, pastillas luminosas y animación fluida.

## 2. "Game Feel" y "Juice" Obligatorios en Todo Juego:
- **Partículas Procedurales**: Explosión de partículas con velocidad, fricción y desvanecimiento al limpiar líneas, comer o colisionar.
- **Screen Shake Amortiguado**: Pequeña vibración de pantalla en impactos fuertes o Game Over (`shake = 8`, decae con `shake *= 0.9`).
- **Game Loop a 60 FPS con Delta Time (`dt`)**:
  ```javascript
  let lastTime = performance.now();
  function loop(now) {
    const dt = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;
    update(dt);
    render();
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  ```

## 3. Sintetizador WebAudio API (Zero dependencias externas):
- Incluye siempre una clase de sonido basada en `AudioContext` nativo:
  ```javascript
  class SoundFX {
    constructor() {
      this.ctx = null;
    }
    init() { if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)(); }
    playTone(freq, type='square', duration=0.1, vol=0.2) {
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      gain.gain.setValueAtTime(vol, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
      osc.connect(gain); gain.connect(this.ctx.destination);
      osc.start(); osc.stop(this.ctx.currentTime + duration);
    }
    move() { this.playTone(300, 'sine', 0.05, 0.1); }
    rotate() { this.playTone(450, 'triangle', 0.08, 0.15); }
    line() { this.playTone(600, 'square', 0.2, 0.25); }
    gameover() { this.playTone(150, 'sawtooth', 0.4, 0.3); }
  }
  ```
- Inicializa el `AudioContext` con el primer clic o pulsación de tecla (`init()`).
"""

SKILL_PROCEDURAL_GRAPHICS = """# Skill: Gráficos Procedurales, Canvas 2D, SVG y Shaders

Para generar interfaces ricas sin imágenes pesadas externas:
1. **Canvas 2D Procedural**: Sprites vectoriales dibujados con `ctx.arc()`, `ctx.beginPath()`, gradientes radiales (`ctx.createRadialGradient`) y patrones.
2. **Texturas Dinámicas**: Genera efectos de cuadrícula, estrellas de fondo animadas o partículas con matemáticas simples (`Math.sin`, `Math.cos`).
"""

SKILL_WEBGL_3D = """# Skill: Gráficos 3D Interactivos, Three.js y Shaders

Para proyectos 3D en el navegador:
1. Usa `<script type="importmap">` apuntando a CDN confiables (`https://unpkg.com/three@0.160.0/build/three.module.js`).
2. Para miles de cubos o partículas usa `THREE.InstancedMesh`.
3. Iluminación con `HemisphereLight` + `DirectionalLight` y niebla de fondo sincronizada (`THREE.FogExp2`).
"""

SKILL_TOOL_BUILDER = """# Skill: Herramientas de Software y Aplicaciones Web

1. **Diseño Ergonómico**: Interfaz intuitiva, barra de herramientas accesible, atajos de teclado y datos de ejemplo listos.
2. **Exportación Real**: Botón para exportar o descargar archivos (.json, .png, .txt) o copiar al portapapeles.
"""

DESIGN_PRESETS = {
    "auto": "Camaleónico Inteligente (Adapta la estética y colores al alma de cada juego/app)",
    "arcade": "Arcade Vibrante (Marco gabinete, colores retro iluminados, tipografía arcade)",
    "classic": "Clásico Original (Fidelidad histórica con acabado pulido y limpio)",
    "dungeon": "Fantasía Oscura (Piedra pizarra, fuego ámbar, oro viejo y carmesí)",
    "cozy": "Cozy Minimalista (Tonos cálidos crema y pasteles terrosos, curvas suaves)",
    "gameboy": "Retro Dot-Matrix (Los 4 tonos verde oliva de Game Boy)",
    "swiss": "Swiss Editorial (Fondo cálido, bordes nítidos, tipografía Serif elegante)",
    "hud": "Tactical HUD (Negro obsidiana, biseles clip-path, acentos ámbar/verde radar)",
    "glass": "Spatial Glass (Paneles translúcidos blur 20px, bordes especulares)",
}

SKILLS_CATALOG = {
    "ui-ux-pro": {
        "title": "UI/UX & Art Direction",
        "desc": "Jerarquía visual de alto impacto, tipografías reales, armonía de color adaptada.",
        "content": SKILL_UI_UX,
    },
    "game-architect": {
        "title": "Game Engine & Juice",
        "desc": "Juegos 60fps con DeltaTime, partículas, screen shake, WebAudio nativo y preview.",
        "content": SKILL_GAME_DEV,
    },
    "procedural-art": {
        "title": "Procedural 2D & SVG",
        "desc": "Sprites y texturas generadas en Canvas 2D sin archivos externos.",
        "content": SKILL_PROCEDURAL_GRAPHICS,
    },
    "webgl-3d": {
        "title": "3D Three.js & Voxel",
        "desc": "Escenas 3D interactivas, iluminación cinematográfica y controles.",
        "content": SKILL_WEBGL_3D,
    },
    "tool-craft": {
        "title": "Tool Crafter",
        "desc": "Herramientas de software completas, exportación real y ergonomía.",
        "content": SKILL_TOOL_BUILDER,
    },
}
