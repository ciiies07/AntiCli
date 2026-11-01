# =====================================================================
# CATÁLOGO DE SKILLS DE ALTO NIVEL: DIRECCIÓN DE ARTE, UI/UX, 2D & 3D
# =====================================================================

# --- SKILL 1: Camaleón de Dirección de Arte & Sistemas UI/UX ---
SKILL_UI_UX = """# Skill: Dirección de Arte Camaleónica, Sistemas de Diseño UI/UX y Ambientes Gráficos

## REGLA #1: PROHIBIDO EL "DISEÑO GENÉRICO DE IA"
NUNCA uses la misma plantilla aburrida para todo (prohibido repetir siempre el mismo fondo azul oscuro `#111827` con botones violeta `#6366f1`, tarjetas todas iguales centradas y fuente Inter sin personalidad).
Antes de escribir una sola línea de código, **elige una Dirección de Arte única** que encaje con el alma del proyecto o el estilo pedido por el usuario:

### Catálogo de Paradigmas Visuales (Elige y adapta uno según el proyecto):

1. **Swiss Editorial / Brutalismo Refinado** (Ideal para herramientas creativas, portafolios, notas, tipografía, arquitectura):
   - **Paleta**: Papel cálido (`#F4F1EA` o `#EAE6DF`), tinta carbón (`#141413`), acento bermellón internacional (`#FF3300`) o azul cobalto (`#002FA7`).
   - **Geometría**: Bordes expuestos de `1px solid #141413` o `2px solid #141413`, `border-radius: 0px` (esquinas vivas), cuadrículas asimétricas tipo revista, sombras duras desplazadas (`4px 4px 0px #141413`).
   - **Tipografía**: Contraste dramático entre Serif editorial (`Playfair Display`, `Instrument Serif`, `Newsreader`) a gran escala (`clamp(2.5rem, 5vw, 4.5rem)`, `letter-spacing: -0.03em`) y Monospace técnica (`JetBrains Mono`, `Space Mono`) para metadatos numerados (`01 // SECCIÓN`).

2. **Tactical HUD / Cassette Futurism / Industrial Sci-Fi** (Ideal para telemetría, sintetizadores, terminales, estrategia, mechas, monitoreo):
   - **Paleta**: Negro obsidiana (`#07080A`), gris titanio (`#16191E`), ámbar fosforito (`#FFB000`), verde radar (`#00FF66`) o rojo alerta (`#FF2A54`).
   - **Geometría**: Esquinas biseladas a 45° usando `clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))`, miras reticulares (`+` en las esquinas), líneas de escaneo sutiles (`repeating-linear-gradient`), indicadores LED parpadeantes y etiquetas técnicas en mayúsculas (`SYS.RDY // 98.4%`).
   - **Tipografía**: `Chakra Petch`, `Rajdhani`, `Share Tech Mono` o `Orbitron`.

3. **Atmospheric Glass & Spatial Aurora** (Ideal para suites multimedia, clima, música, IA creativa, finanzas modernas):
   - **Paleta**: Profundidad abisal (`#05070E`) con orbes de luz difusa animados en el fondo (`radial-gradient` con `filter: blur(90px)` en tonos cian, magenta, esmeralda o oro).
   - **Geometría**: Paneles translúcidos (`background: rgba(255, 255, 255, 0.04)`, `backdrop-filter: blur(24px) saturate(180%)`), bordes especulares con gradiente (`border: 1px solid rgba(255, 255, 255, 0.14)`, brillo superior `inset 0 1px 0 rgba(255, 255, 255, 0.25)`), `border-radius: 20px`.
   - **Tipografía**: `Plus Jakarta Sans`, `Outfit` o `Syne`.

4. **Organic Botanical / Warm Tactile Studio** (Ideal para bienestar, lectura, cocina, simuladores acogedores, productividad calmada):
   - **Paleta**: Arena suave (`#FAF7F2`), arcilla (`#EFECE6`), verde bosque profundo (`#1C3A27`), terracota (`#D96B43`), texto espresso (`#231F1E`).
   - **Geometría**: Bordes redondeados orgánicos (`24px` a `32px`), sombras cálidas difusas (`0 20px 40px -15px rgba(35, 31, 30, 0.08)`), textura de grano de papel sutil vía filtro SVG `<feTurbulence>`.
   - **Tipografía**: `Fraunces` o `Lora` combinada con `DM Sans`.

5. **Arcade Neon / Cyber-Pop Synthwave** (Solo cuando el proyecto sea explícitamente Synthwave, carreras nocturnas futuristas o estética cyberpunk ochentera; NUNCA por defecto para cualquier juego):
   - **Paleta**: Violeta nocturno (`#0D0221`), rosa láser (`#FF007F`), cian eléctrico (`#00F0FF`), amarillo ácido (`#FFE600`).
   - **Geometría**: Resplandores multicapa (`text-shadow` y `box-shadow` con doble radio de neón), rejillas en perspectiva animadas, cromados e inclinaciones dinámicas (`transform: skewX(-6deg)`).
   - **Tipografía**: `Press Start 2P`, `Bungee`, `Righteous` o `Space Grotesk`.

## REGLA #2: FIDELIDAD AL ESTILO ORIGINAL POR DEFECTO (LA TEMÁTICA DICTA LA PALETA)
- Si el usuario pide un juego o herramienta conocido (Tetris, Pac-Man, Flappy Bird, Snake, Space Invaders, Buscaminas, Pong): **RESPETA SIEMPRE SU ESTILO, PALETA Y TIPOGRAFÍA ORIGINAL POR DEFECTO.**
- NUNCA apliques la misma paleta oscura de neón rosa/cian a todo lo que hagas.
- SOLO si el usuario especifica explícitamente en su petición un estilo alternativo (ej. "Tetris en neón", "Pacman cyberpunk") o activó un `/style` específico, entonces y solo entonces aplica ese estilo.
- Si el proyecto es nuevo o sobre naturaleza, bienestar o productividad: usa tonos coherentes (arenas, arcilla, verdes o maderas), no luces de fiesta.

## REGLA #3: TEXTURAS, ILUMINACIÓN Y MICRO-DETALLES OBLIGATORIOS
- **Google Fonts Reales**: Importa SIEMPRE al inicio del `<head>` las fuentes exactas de Google Fonts que correspondan a la dirección de arte elegida (nunca dejes solo `sans-serif`).
- **Textura Anti-Plano**: Añade atmósfera visual usando al menos uno de estos recursos:
  - Ruido/grano cinematográfico sutil en SVG (`data:image/svg+xml...` con `<feTurbulence>`) con `opacity: 0.035`.
  - Patrón de puntos (`radial-gradient(#ffffff15 1px, transparent 1px); background-size: 20px 20px`) o cuadrícula técnica (`linear-gradient`).
  - Iluminación reactiva al cursor (actualizando variables CSS `--mouse-x`, `--mouse-y` en `mousemove`).
- **Coreografía de Movimiento**:
  - Usa curvas elásticas y naturales: `cubic-bezier(0.22, 1, 0.36, 1)` o `cubic-bezier(0.34, 1.56, 0.64, 1)`.
  - Nunca hagas interfaces mudas: incluye gráficos SVG/Canvas en vivo, contadores animados, atajos de teclado visibles en pantalla (`[ESC]`, `[SPACE]`) y estados vacíos ilustrados.
- **Higiene de archivos**: NUNCA incluyas bloques markdown (```html o ```) dentro del argumento `content` de `write` o `edit`.
"""

# --- SKILL 2: Gráficos Procedurales, Arte Generativo y Shaders ---
SKILL_PROCEDURAL_GRAPHICS = """# Skill: Arte Generativo, Shaders GLSL, Canvas 2D Avanzado e Ilustración SVG

Cuando crees fondos interactivos, visualizadores, herramientas gráficas o efectos visuales:

## 1. Técnicas de Renderizado Procedural (Sin activos externos rotos)
- **Shaders GLSL / WebGL**: Para fondos hipnóticos, fluidos, nebulosas, ondas de plasma o distorsión CRT, usa un `<canvas>` con un Fragment Shader GLSL ligero o Three.js `ShaderMaterial` pasando `u_time`, `u_resolution` y `u_mouse`.
- **Campos de Flujo y Física de Partículas (Canvas 2D)**:
  - Usa Perlin/Simplex noise (implementado en pocas líneas matemáticas) para mover miles de partículas en trayectorias orgánicas.
  - Conecta nodos cercanos con líneas cuya opacidad dependa de la distancia (`1 - dist / maxDist`) y usa `ctx.globalCompositeOperation = 'lighter'` para mezclas aditivas luminosas.
- **Ilustración y Iconografía SVG a Medida**:
  - En lugar de usar solo emojis genéricos, dibuja iconos, cursores, medidores circulares (`stroke-dasharray` / `stroke-dashoffset`) y diagramas vectoriales con `<svg viewBox="...">`, gradientes `<linearGradient>` y filtros `<feGaussianBlur>`.
"""

# --- SKILL 3: Ingeniería de Videojuegos 2D y "Game Feel" ---
SKILL_GAME_DEV = """# Skill: Ingeniería de Videojuegos 2D, Dirección Visual por Género y "Game Feel"

Cuando el usuario pida crear un videojuego 2D (o una colección arcade), cada juego DEBE tener su propia atmósfera gráfica y una jugabilidad impecable:

## 1. REGLA FUNDAMENTAL DE ORO: FIDELIDAD AL ESTILO ORIGINAL POR DEFECTO
Cuando el usuario pida programar un juego conocido o clásico (Tetris, Pac-Man, Flappy Bird, Snake, Asteroids, Space Invaders, Buscaminas, Pong, Breakout, etc.):
- **RESPETA INICIALMENTE EL ESTILO ORIGINAL DEL JUEGO**: Emula con máxima fidelidad sus colores históricos oficiales, su tipografía original y su atmósfera visual auténtica por defecto.
- **PROHIBIDO EL MONOCULTIVO NEÓN**: NUNCA apliques la misma paleta oscura de neón morado/cian a menos que el usuario lo pida expresamente.
- **CUÁNDO APLICAR NEÓN U OTRO ESTILO**: SOLO si el usuario especifica explícitamente en su solicitud que lo desea en neón, cyberpunk o con un estilo alternativo (ej. "Tetris en neón", "Pac-Man cyberpunk"), o si activó un comando `/style` concreto. Si no se especifica ningún estilo, **el diseño y paleta original siempre prevalece**.

### Catálogo de Identidad y Paletas Originales por Género:

1. **Tetris Clásico Original**:
   - **Fondo / Marco**: Gris grafito sobrio (#1A1A1A o #222226), cuadrícula de juego sutil.
   - **Tetrominós (Colores Oficiales de The Tetris Company)**: I=Cian (#00F0F0), O=Amarillo (#F0F000), T=Púrpura (#A000F0), S=Verde (#00F000), Z=Rojo (#F00000), J=Azul (#0000F0), L=Naranja (#F0A000). Cero resplandores cegadores ni distorsiones fuera de época.
   - **Tipografía**: 'Press Start 2P' o 'Space Mono'.

2. **Arcade Clásico Dorado (Pac-Man, Asteroids, Pong, Space Invaders)**:
   - **Fondo**: Negro CRT puro (`#000000` o `#08080C`).
   - **Paleta**: Respeta los colores icónicos de cada clásico (Pac-Man: laberinto azul cobalto `#2121DE`, amarillo Pac `#FFFF00`, pastillas blanco cálido `#FFF5EE`, fantasmas rojo/rosa/cian/naranja; Asteroids: líneas vectoriales fósforo verde `#00FF66` o blanco puro sobre negro estelar).
   - **Tipografía**: Google Fonts `'Press Start 2P'` o `'VT323'`.

3. **Plataformas / Aventura Diurna 8-bit & 16-bit (Flappy Bird, Mario-like, Endless Runner)**:
   - **Fondo**: Cielos celestes brillantes y luminosos (`#4EC0CA`, `#70C5CE` o `#38BDF8`), nubes blancas esponjosas, sol radiante. Cero fondos negros ni estética de discoteca.
   - **Paleta**: Césped y tuberías verde manzana (`#73BF2E`, `#58A020`), tierra tostada (`#DED895`, `#C84C0C`), acentos oro (`#FFD700`).
   - **Tipografía**: Google Fonts `'Pixelify Sans'`, `'Silkscreen'` o `'VT323'`.

4. **Dungeon Crawler / Rogue-like / Fantasía Oscura (Castlevania, Diablo-like, Mazmorras, RPG)**:
   - **Fondo**: Piedra pizarra húmeda (`#121118`, `#1A1924`).
   - **Paleta**: Fuego de antorcha parpadeante (`#FF7700`, `#FFAA00`), oro envejecido (`#D4AF37`), sangre carmesí (`#8B0000`), hierro forjado (`#4A4E69`).
   - **Iluminación**: Niebla de guerra, radio de luz circular alrededor del héroe, humo y partículas de brasas.
   - **Tipografía**: Google Fonts `'Cinzel'`, `'MedievalSharp'` o `'Uncial Antiqua'`.

5. **Retro Portátil / Game Boy Dot-Matrix LCD (Snake clásico, Tetris portátil retro, Tamagotchi)**:
   - **Paleta**: Los 4 tonos icónicos de fósforo verde oliva de la pantalla monocroma original (`#9BBC0F` más claro, `#8BAC0F` medio claro, `#306230` medio oscuro, `#0F380F` negro verdoso). Textura de rejilla de píxeles LCD. Cero luces fluorescentes modernas fuera de época.
   - **Tipografía**: Google Fonts `'VT323'` o `'Press Start 2P'`.

6. **Sci-Fi Táctico / Simulador Naval o Espacial (Submarinos, FTL, Mechas, Batalla Naval)**:
   - **Paleta**: Si es submarino, usa azul abisal profundo (`#020B14`) con verde sonar (`#00E676`), óxido y medidores de presión; si es espacial, negro estelar con HUD militar ámbar (`#FFB000`) o cian radar.
   - **Tipografía**: Google Fonts `'Share Tech Mono'`, `'Chakra Petch'` o `'Orbitron'`.

7. **Cozy / Zen / Minimalist Puzzle (2048, Sudoku, Zen Garden, Solitario, Mahjong)**:
   - **Fondo**: Papel de arroz, arena suave o lino cálido (`#FAF8EF`, `#F5EBE1`, `#EAE5D9`).
   - **Paleta**: Madera pulida (`#8D6E63`), arcilla suave, pasteles terrosos (`#EEE4DA`, `#EDE0C8`, `#F2B179`), salvia y lavanda.
   - **Estilo**: Sombras suaves difusas, esquinas redondeadas táctiles. Cero destellos agresivos.
   - **Tipografía**: Google Fonts `'Outfit'`, `'Plus Jakarta Sans'` o `'Fraunces'`.

8. **Cyber-Pop Synthwave (Solo si el usuario pide explícitamente Neón o Cyberpunk)**:
   - ÚSALO ÚNICAMENTE cuando el usuario pida explícitamente temática Cyberpunk, estética Synthwave o carreras ochenteras. NUNCA como estilo por defecto para cualquier juego.

## 2. Jugabilidad Quirúrgica y Controles Suaves
- **Delta Time (`dt`) con Cap de Seguridad**: Calcula `const dt = Math.min((now - lastTime) / 1000, 0.05)` usando `requestAnimationFrame` para evitar saltos bruscos.
- **Aislamiento de Bucle y Teclado (Crítico en Menús Multi-Juego)**:
  - Guarda siempre el ID del `requestAnimationFrame` activo y cancélalo (`cancelAnimationFrame(activeRafId)`) antes de cambiar de juego o volver al menú.
  - Usa un único estado global de teclas (`const keys = {};`) y un manejador limpio para evitar que los eventos `keydown` se acumulen o que el juego se acelere al reiniciar.
  - Previene el scroll por defecto con `if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space',' '].includes(e.key)) e.preventDefault();`.
- **Interpolación y Suavidad (Cero movimientos bruscos)**:
  - Usa interpolación lineal (`lerp(a, b, 1 - Math.exp(-speed * dt))`) para cámaras, barras de vida, rotaciones de personajes (ej. inclinación suave del pájaro según su velocidad vertical en Flappy Bird) y animaciones de caída o deslizamiento de piezas.

## 3. "Game Feel", Partículas y Audio Procedural Acorde a la Temática
- **Nada de rectángulos planos sin alma**:
  - Dibuja sprites procedurales detallados en Canvas acordes a la temática del juego (ojos expresivos, sombras proyectadas, estelas o texturas de madera/piedra).
  - Diseña fondos con múltiples capas de **Parallax** (montañas lejanas, nubes, estrellas o columnas de mazmorra moviéndose a distintas velocidades).
- **Efectos de Impacto ("Juice")**:
  - **Partículas direccionales** con física (gravedad, fricción y desvanecimiento) al comer, romper líneas, saltar o chocar.
  - **Screen Shake amortiguado** y **Flash de impacto** al perder o lograr un combo.
  - **Textos flotantes animados** (`+100`, `CRITICAL!`, `COMBO x4`) con escalado elástico.
- **Sintetizador WebAudio API Integrado**: Crea una clase `SoundFX` con `AudioContext` que genere sonidos acordes a la temática (bips 8-bit para arcade, sonidos graves de madera o metal para fantasía, tonos armónicos para cozy) con botón de Mute en el HUD.
"""

# --- SKILL 4: Gráficos 3D WebGL, Three.js, Shaders & Voxel Art ---
SKILL_WEBGL_3D = """# Skill: Gráficos 3D Interactivos, Three.js, Voxel Engines y Post-Procesado

Cuando el usuario pida experiencias 3D, motores Voxel, mundos low-poly, visualizadores o juegos 3D en el navegador:

## 1. Arquitectura Three.js Moderna (ES Modules)
- Usa siempre `<script type="importmap">` apuntando a CDN confiables (`https://unpkg.com/three@0.160.0/build/three.module.js` y `three/addons/`).
- **Rendimiento con Instancing**: Para mundos Voxel, partículas masivas o vegetación, usa `THREE.InstancedMesh` agrupado por material/color en lugar de miles de `THREE.Mesh` individuales.
- **Iluminación Cinematográfica y Atmósfera**:
  - Combina `HemisphereLight` (cielo/suelo complementarios) con un `DirectionalLight` principal y `PointLight` acentuados para faroles, portales o fuego.
  - Añade niebla (`THREE.FogExp2`) sincronizada con el fondo y post-procesado `EffectComposer` + `RenderPass` + `UnrealBloomPass` ajustado con elegancia (`strength: 0.45`, `radius: 0.4`, `threshold: 0.82`).
- **HUD 3D Integrado**: Superpón una interfaz HTML/CSS digna de un estudio AAA (con selector de cámaras/climas/modos de luz en vivo, contador de FPS/voxels y controles interactivos).
"""

# --- SKILL 5: Arquitectura de Herramientas de Software ---
SKILL_TOOL_BUILDER = """# Skill: Creación de Herramientas de Software, Automatización y Utilidades CLI/Web

Cuando construyas herramientas técnicas, editores, generadores, analizadores o utilidades de productividad:
1. **Personalidad Visual acorde a la Herramienta**: Una herramienta de audio/síntesis debe parecer hardware de estudio (knobs, vúmetros, LEDs); una herramienta de finanzas o datos debe parecer una terminal cuantitativa de alta precisión; una herramienta de escritura/diseño debe parecer un estudio editorial suizo.
2. **Funcionalidad Real e Inmediata**: Incluye siempre presets/plantillas precargadas con un clic, exportación real (descarga de archivo `.json`, `.png`, `.svg`, `.wav` o copia al portapapeles), deshacer/rehacer y atajos de teclado.
3. **Edición Quirúrgica**: Si el archivo ya existe y el usuario pide ajustes, usa `read` + `edit` o `patch_lines` para modificar con precisión sin perder el resto del trabajo.
"""

# Presets de estilos rápidos para el comando `/style <preset>`
DESIGN_PRESETS = {
    "auto": "Camaleónico Automático (El agente deduce activamente la paleta y estilo ideal según el tema del proyecto)",
    "classic": "Arcade Clásico Dorado (Negro CRT, líneas vectoriales de fósforo verde o blanco, colores retro originales)",
    "dungeon": "Fantasía Oscura & Mazmorra (Piedra pizarra oscura, fuego de antorchas ámbar, oro viejo y carmesí)",
    "cozy": "Cozy & Zen Minimalista (Fondos arena suave y crema, madera cálida, pasteles terrosos y curvas suaves)",
    "gameboy": "Retro Portátil Dot-Matrix (Los 4 tonos de fósforo verde oliva de Game Boy y rejilla LCD)",
    "swiss": "Swiss Editorial & Brutalismo Refinado (Fondos cálidos #F4F1EA, bordes negros 2px, Serif gigante + Monospace, sombras duras)",
    "hud": "Tactical HUD & Industrial Sci-Fi (Negro obsidiana, esquinas biseladas clip-path, ámbar/verde radar, retículas técnicas)",
    "glass": "Atmospheric Spatial Glass & Aurora (Fondos abisales con orbes de luz difusa, paneles cristal blur 24px, bordes especulares)",
    "organic": "Organic Botanical & Warm Tactile (Tonos arena, arcilla, verde bosque y terracota, bordes suaves 28px, grano de papel)",
    "arcade": "Cyber-Pop & Retro Synthwave (Violeta profundo, neón rosa/cian/ácido, rejillas en perspectiva, resplandores intensos)",
}

SKILLS_CATALOG = {
    "ui-ux-pro": {
        "title": "Chameleon Art Direction & UI/UX",
        "desc": "5 paradigmas visuales distintos (Swiss, Tactical HUD, Spatial Glass, Organic, Arcade), tipografía real y texturas.",
        "content": SKILL_UI_UX,
    },
    "procedural-art": {
        "title": "Generative Art, SVG & Shaders",
        "desc": "Gráficos procedurales en Canvas 2D, shaders GLSL, campos de partículas e ilustración vectorial SVG a medida.",
        "content": SKILL_PROCEDURAL_GRAPHICS,
    },
    "game-architect": {
        "title": "Game Design & Juice 2D",
        "desc": "Juegos 60fps con dirección artística propia, parallax, sprites procedurales, interpolación suave y WebAudio.",
        "content": SKILL_GAME_DEV,
    },
    "webgl-3d": {
        "title": "3D WebGL, Three.js & Voxel",
        "desc": "Escenas 3D interactivas, InstancedMesh para Voxels, iluminación cinematográfica, controles de clima y Bloom.",
        "content": SKILL_WEBGL_3D,
    },
    "tool-craft": {
        "title": "Software & Tool Crafter",
        "desc": "Herramientas con estética de hardware/estudio, presets interactivos, exportación real y edición quirúrgica.",
        "content": SKILL_TOOL_BUILDER,
    },
}
