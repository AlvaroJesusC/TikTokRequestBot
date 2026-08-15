# 🎵 TikTok LIVE Song Request Bot - App Nativa de Escritorio (Windows 11)

Aplicación nativa de escritorio moderna para Windows 11 desarrollada en Python (`CustomTkinter`), diseñada para responder a solicitudes de canciones en tiempo real desde el chat de tu TikTok LIVE.

---

## 🌟 Tres Motores de Reproducción en 1 Clic

1. **🔴 Modo YouTube (Auto / Headless / MP3 Nativo):**
   - Tus espectadores piden canciones con `!play <canción o artista>`.
   - El bot busca en YouTube, descarga el audio en formato MP3 puro y lo reproduce en segundo plano con Pygame (cero ventanas emergentes).
   - **Auto-limpieza inteligente:** Elimina automáticamente el archivo MP3 del disco en cuanto termina de reproducirse, manteniendo las canciones en cola protegidas.
   - **No requiere ninguna cuenta ni tener Spotify abierto.**

2. **🟢 Modo Spotify Connect (Oficial OAuth):**
   - Controla Spotify mediante la API oficial de Spotipy con vinculación en 1 clic.
   - Requiere Spotify Premium y credenciales en `config.yaml`.

3. **📁 Modo Música Local:**
   - Reproduce archivos `.mp3`, `.wav`, `.ogg` o `.flac` colocados en tu carpeta `music/` con búsqueda difusa (*Fuzzy Matching*).

---

## 🚀 Instalación y Ejecución

### 1. Instalar dependencias
En PowerShell:
```powershell
pip install -r requirements.txt
```

### 2. Configurar
Copia `config.example.yaml` a `config.yaml` y rellena tu usuario de TikTok (y opcionalmente las credenciales de Spotify):
```powershell
copy config.example.yaml config.yaml
```

### 3. Iniciar la App
```powershell
python main.py
```

---

## 📦 Estructura del Proyecto

```
bot-musica/
├── main.py                  # Punto de entrada principal
├── config.yaml              # Tu configuración local (no se sube a git)
├── config.example.yaml      # Plantilla de configuración
├── requirements.txt         # Dependencias de Python
│
├── bot/                     # Lógica del bot de TikTok LIVE
│   ├── config_manager.py    # Carga y guarda config.yaml
│   ├── command_parser.py    # Parser de comandos del chat (!play, !skip, etc.)
│   ├── live_bot.py          # Orquestador central del bot
│   ├── permissions.py       # Gestión de permisos (streamer, mods)
│   └── queue_manager.py     # Gestión de cola e historial
│
├── player/                  # Motores de reproducción
│   ├── base.py              # Clase base abstracta
│   ├── youtube_player.py    # Motor YouTube (yt-dlp + pygame)
│   ├── spotify_player.py    # Motor Spotify Connect (spotipy)
│   └── local_file_player.py # Motor de archivos locales
│
├── gui/                     # Interfaz gráfica de escritorio
│   └── desktop_app.py       # App principal (CustomTkinter)
│
├── updater/                 # Sistema de auto-actualización
│   ├── version.py           # Versión actual y constantes del repo
│   ├── checker.py           # Consulta GitHub Releases API
│   ├── installer.py         # Descarga y reemplazo en caliente del .exe
│   └── ui.py                # Ventana modal de actualización
│
├── scripts/                 # Herramientas auxiliares
│   ├── build_exe.py         # Compilador a .exe con PyInstaller
│   ├── build_exe.bat        # Atajo para compilar en Windows
│   └── test_connection.py   # Test de conectividad con TikTok
│
├── music/                   # Carpeta para archivos de música local
│   └── LEEME.txt
│
└── data/                    # Datos locales (caché, historial)
    └── cache/
```

---

## 🔄 Sistema de Auto-Actualización

La app comprueba automáticamente al iniciar si hay una nueva versión en [GitHub Releases](https://github.com/AlvaroJesusC/TikTokRequestBot/releases). También puedes comprobarlo manualmente desde **⚙️ Ajustes → 🔍 Buscar Actualizaciones**.

Si ejecutas la versión `.exe`, la actualización se descarga e instala automáticamente con un solo clic, reiniciando la aplicación con la nueva versión.

### Compilar a .exe
```powershell
python scripts/build_exe.py
```
O haz doble clic en `scripts/build_exe.bat`. El ejecutable se genera en `dist/TikTokRequestBot.exe`.

---

## 🎮 ¿Cómo se usa?

1. En la barra superior de la ventana:
   - Selecciona tu motor favorito: `🔴 YouTube (Auto)`, `🟢 Spotify (Beta)` o `📁 Local`.
   - Escribe tu `@usuario` de TikTok (o cualquier directo activo para probar).
   - Haz clic en **⚡ Conectar**.
2. Tus espectadores ya pueden pedir canciones en el chat con:
   ```text
   !play <nombre de la canción o artista>
   ```
3. También puedes solicitar canciones manualmente desde la caja de texto de la app o controlar la cola con los botones integrados.
