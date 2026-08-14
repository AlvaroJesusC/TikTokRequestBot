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

### 2. Iniciar la App
```powershell
python main.py
```

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
