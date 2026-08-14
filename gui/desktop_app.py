"""
Aplicación de Escritorio Nativa para Windows 11 (CustomTkinter)
==============================================================
Panel de control con validación estricta del comando '!play <canción>'
y gestión de caché automática con ventana de ajustes.
"""

import os
import sys
import threading
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from tkinter import messagebox

try:
    import customtkinter as ctk
except ImportError:
    print("[GUI] Error: customtkinter no está instalado.")
    print("Ejecuta: pip install customtkinter")
    sys.exit(1)

from bot.live_bot import LiveBotOrchestrator
from bot.config_manager import load_config, save_config
from updater import APP_VERSION, check_updates_background

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class DesktopApp(ctk.CTk):
    def __init__(self, orchestrator: LiveBotOrchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = load_config()

        # Ventana de Windows 11
        self.title(f"🎵 TikTok LIVE SongBot {APP_VERSION} - YouTube & Spotify Controller")
        self.geometry("1120x780")
        self.minsize(980, 680)

        self.is_connected = False
        self.current_filter = "Todos"
        self.raw_logs: List[Dict[str, str]] = []

        # Event Loop Asyncio Permanente
        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_event_loop, daemon=True)
        self.async_thread.start()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_main_panel()
        self._create_logs_panel()

        self._connect_orchestrator_callbacks()
        self.after(1000, self._playback_refresh_loop)
        self._load_initial_values()

        # Comprobar actualizaciones automáticamente en segundo plano al iniciar
        self.after(2500, lambda: check_updates_background(self, silent=True, log_callback=self.append_log))


    def _run_async_event_loop(self):
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    # --- 1. HEADER & BARRA DE CONEXIÓN ---
    def _create_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#131722")
        header_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header_frame.grid_columnconfigure(3, weight=1)

        # Brand
        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=12, pady=10, sticky="w")
        
        lbl_logo = ctk.CTkLabel(brand_frame, text="🎵", font=("Segoe UI Emoji", 24))
        lbl_logo.pack(side="left", padx=(0, 8))
        
        title_frame = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        title_row = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(title_row, text="TikTok LIVE SongBot", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        lbl_ver = ctk.CTkLabel(
            title_row,
            text=APP_VERSION,
            font=("Segoe UI", 10, "bold"),
            fg_color="#1e293b",
            text_color="#38bdf8",
            corner_radius=6,
            padx=6,
            pady=1
        )
        lbl_ver.pack(side="left", padx=6)

        ctk.CTkLabel(title_frame, text="Comando: !play <canción>", font=("Segoe UI", 11), text_color="#94a3b8").pack(anchor="w")

        # Selector de Modo (Rojo YouTube, Verde Spotify, Amarillo Local)
        self.mode_selector = ctk.CTkSegmentedButton(
            header_frame,
            values=["🔴 YouTube (Auto)", "🟢 Spotify (Beta)", "📁 Local"],
            command=self._on_mode_change,
            selected_color="#ef4444",
            selected_hover_color="#dc2626",
            font=("Segoe UI", 11, "bold")
        )
        self.mode_selector.grid(row=0, column=1, padx=8, pady=10)

        # Botón de Vincular Spotify
        self.btn_spotify_auth = ctk.CTkButton(
            header_frame,
            text="🔗 Vincular Spotify",
            command=self._toggle_spotify_link,
            width=140,
            fg_color="#1ed760",
            hover_color="#16a34a",
            text_color="#000000",
            font=("Segoe UI", 11, "bold")
        )
        self.btn_spotify_auth.grid(row=0, column=2, padx=8, pady=10)

        # Barra de Conexión TikTok LIVE
        conn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        conn_frame.grid(row=0, column=4, padx=12, pady=10, sticky="e")

        self.entry_username = ctk.CTkEntry(conn_frame, placeholder_text="@tu_usuario", width=140)
        self.entry_username.pack(side="left", padx=4)
        self.entry_username.bind("<Return>", lambda e: self._toggle_connect())

        self.btn_connect = ctk.CTkButton(
            conn_frame,
            text="⚡ Conectar",
            command=self._toggle_connect,
            width=90,
            fg_color="#fe2c55",
            hover_color="#e01740",
            font=("Segoe UI", 12, "bold")
        )
        self.btn_connect.pack(side="left", padx=4)

        self.lbl_status_badge = ctk.CTkLabel(
            conn_frame,
            text="🔴 Desconectado",
            fg_color="#261b20",
            text_color="#ff4757",
            corner_radius=8,
            padx=8,
            pady=4,
            font=("Segoe UI", 11, "bold")
        )
        self.lbl_status_badge.pack(side="left", padx=6)

        btn_settings = ctk.CTkButton(
            conn_frame,
            text="⚙️",
            width=36,
            command=self._open_settings_dialog,
            fg_color="#334155",
            hover_color="#475569"
        )
        btn_settings.pack(side="left", padx=4)

    # --- 2. PANEL PRINCIPAL ---
    def _create_main_panel(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, padx=16, pady=6, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=4)
        main_frame.grid_columnconfigure(1, weight=5)
        main_frame.grid_rowconfigure(0, weight=1)

        # COLUMNA IZQUIERDA
        left_col = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        left_col.grid_rowconfigure(0, weight=1)
        left_col.grid_columnconfigure(0, weight=1)

        # Card Sonando Ahora
        now_playing_card = ctk.CTkFrame(left_col, corner_radius=12, fg_color="#131722")
        now_playing_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        self.lbl_card_mode = ctk.CTkLabel(now_playing_card, text="🎧 SONANDO EN YOUTUBE (SOLO AUDIO)", font=("Segoe UI", 13, "bold"), text_color="#38bdf8")
        self.lbl_card_mode.pack(anchor="w", padx=16, pady=(14, 8))

        self.lbl_track_title = ctk.CTkLabel(
            now_playing_card,
            text="No hay canciones en reproducción",
            font=("Segoe UI", 16, "bold"),
            wraplength=380,
            justify="left"
        )
        self.lbl_track_title.pack(anchor="w", padx=16, pady=(4, 2))

        self.lbl_track_artist = ctk.CTkLabel(
            now_playing_card,
            text="Escribe en la caja o en el chat: !play <canción>",
            font=("Segoe UI", 13),
            text_color="#94a3b8",
            wraplength=380,
            justify="left"
        )
        self.lbl_track_artist.pack(anchor="w", padx=16, pady=(0, 6))

        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(now_playing_card, height=8, corner_radius=4, progress_color="#1ed760")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(10, 2))

        self.lbl_time = ctk.CTkLabel(now_playing_card, text="00:00 / 00:00", font=("Consolas", 11), text_color="#64748b")
        self.lbl_time.pack(anchor="e", padx=16, pady=(0, 10))

        # Controles
        ctrls_frame = ctk.CTkFrame(now_playing_card, fg_color="transparent")
        ctrls_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_play_pause = ctk.CTkButton(
            ctrls_frame,
            text="▶ Reanudar",
            width=100,
            command=self._on_play_pause,
            fg_color="#1ed760",
            hover_color="#16a34a",
            text_color="#000000",
            font=("Segoe UI", 12, "bold")
        )
        self.btn_play_pause.pack(side="left", padx=(0, 8))

        self.btn_skip = ctk.CTkButton(
            ctrls_frame,
            text="⏭ Saltar (!skip)",
            width=110,
            command=self._on_skip,
            fg_color="#334155",
            hover_color="#475569"
        )
        self.btn_skip.pack(side="left", padx=4)

        # Volumen
        vol_frame = ctk.CTkFrame(ctrls_frame, fg_color="transparent")
        vol_frame.pack(side="right")
        ctk.CTkLabel(vol_frame, text="🔊", font=("Segoe UI Emoji", 12)).pack(side="left", padx=4)
        self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=1, width=90, command=self._on_volume_change, progress_color="#1ed760")
        self.vol_slider.set(0.8)
        self.vol_slider.pack(side="left", padx=4)

        # --- Lista de Comandos del Chat con checkbox de habilitar/deshabilitar ---
        cmds_box = ctk.CTkFrame(now_playing_card, fg_color="#181f2f", corner_radius=8)
        cmds_box.pack(fill="x", padx=16, pady=(0, 12))

        title_row = ctk.CTkFrame(cmds_box, fg_color="transparent")
        title_row.pack(fill="x", padx=10, pady=(6, 4))
        ctk.CTkLabel(
            title_row,
            text="💬 COMANDOS DEL CHAT (Desmarcar para deshabilitar):",
            font=("Segoe UI", 10, "bold"),
            text_color="#94a3b8"
        ).pack(anchor="w")

        grid_frame = ctk.CTkFrame(cmds_box, fg_color="transparent")
        grid_frame.pack(fill="x", padx=8, pady=(0, 8))
        grid_frame.grid_columnconfigure((0, 1), weight=1)

        chat_commands = [
            ("play", "!play <canción>", "Pedir canción"),
            ("skip", "!skip", "Saltar pista"),
            ("pause", "!pause / !resume", "Pausar / Reanudar"),
            ("clear", "!clear", "Vaciar cola (Mod)")
        ]

        self.cmd_widgets = {}

        for idx, (key, cmd, desc) in enumerate(chat_commands):
            col = idx % 2
            row = idx // 2
            f = ctk.CTkFrame(grid_frame, fg_color="#0f172a", corner_radius=6)
            f.grid(row=row, column=col, padx=4, pady=3, sticky="ew")

            cmd_badge = ctk.CTkLabel(
                f,
                text=cmd,
                font=("Consolas", 11, "bold"),
                text_color="#ffffff",
                fg_color="#2b384e",
                corner_radius=4,
                padx=6,
                pady=2
            )
            cmd_badge.pack(side="left", padx=(4, 2), pady=4)

            if key == "skip":
                initial_skip_perm = self.config.get("permissions", {}).get("skip_permission", "mods")
                default_val = "🌍 Todos" if "all" in str(initial_skip_perm).lower() or "todo" in str(initial_skip_perm).lower() else "👥 Mods"
                
                self.opt_skip_perm = ctk.CTkOptionMenu(
                    f,
                    values=["👥 Mods", "🌍 Todos"],
                    width=86,
                    height=20,
                    font=("Segoe UI", 10, "bold"),
                    dropdown_font=("Segoe UI", 10),
                    fg_color="#1e293b",
                    button_color="#334155",
                    button_hover_color="#475569",
                    command=self._on_skip_permission_change
                )
                self.opt_skip_perm.set(default_val)
                self.opt_skip_perm.pack(side="left", padx=2, pady=4)
                desc_widget = self.opt_skip_perm
            else:
                desc_widget = ctk.CTkLabel(
                    f,
                    text=desc,
                    font=("Segoe UI", 10),
                    text_color="#94a3b8"
                )
                desc_widget.pack(side="left", padx=2, pady=4)

            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(
                f,
                text="",
                variable=var,
                width=20,
                height=20,
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=4,
                fg_color="#1ed760",
                hover_color="#16a34a",
                checkmark_color="#000000",
                command=lambda k=key, b=cmd_badge, d=desc_widget, v=var: self._on_toggle_command(k, b, d, v)
            )
            cb.pack(side="right", padx=6, pady=4)

            self.cmd_widgets[key] = (cb, var, cmd_badge, desc_widget)

        # Card Solicitud Manual (Validación Estricta !play)
        add_card = ctk.CTkFrame(left_col, corner_radius=12, fg_color="#131722")
        add_card.grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(add_card, text="➕ SOLICITUD MANUAL CON COMANDO !play", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        
        add_input_frame = ctk.CTkFrame(add_card, fg_color="transparent")
        add_input_frame.pack(fill="x", padx=14, pady=(0, 12))
        
        self.entry_manual_song = ctk.CTkEntry(add_input_frame, placeholder_text="Escribe: !play <canción o artista>...")
        self.entry_manual_song.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_manual_song.bind("<Return>", lambda e: self._on_add_manual_song())

        self.btn_add_manual = ctk.CTkButton(
            add_input_frame,
            text="Enviar !play",
            width=90,
            command=self._on_add_manual_song,
            fg_color="#1ed760",
            hover_color="#16a34a",
            text_color="#000000",
            font=("Segoe UI", 11, "bold")
        )
        self.btn_add_manual.pack(side="right")

        # COLUMNA DERECHA: COLA
        right_col = ctk.CTkFrame(main_frame, corner_radius=12, fg_color="#131722")
        right_col.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        right_col.grid_rowconfigure(1, weight=1)
        right_col.grid_columnconfigure(0, weight=1)

        queue_header = ctk.CTkFrame(right_col, fg_color="transparent")
        queue_header.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")
        
        ctk.CTkLabel(queue_header, text="📋 COLA DE ESPERA (FIFO)", font=("Segoe UI", 13, "bold")).pack(side="left")
        self.lbl_queue_count = ctk.CTkLabel(queue_header, text="0 canciones", font=("Segoe UI", 11), text_color="#94a3b8")
        self.lbl_queue_count.pack(side="left", padx=8)

        self.btn_clear_queue = ctk.CTkButton(
            queue_header,
            text="🗑️ Vaciar Cola",
            width=90,
            height=26,
            command=self._on_clear_queue,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            font=("Segoe UI", 11)
        )
        self.btn_clear_queue.pack(side="right")

        self.queue_scroll = ctk.CTkScrollableFrame(right_col, fg_color="#0b0e17", corner_radius=8)
        self.queue_scroll.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.queue_scroll.grid_columnconfigure(0, weight=1)

        self._render_empty_queue()

    # --- 3. PANEL DE LOGS ---
    def _create_logs_panel(self):
        logs_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#131722")
        logs_card.grid(row=2, column=0, padx=16, pady=(6, 16), sticky="nsew")
        logs_card.grid_columnconfigure(0, weight=1)
        logs_card.grid_rowconfigure(1, weight=1)

        logs_header = ctk.CTkFrame(logs_card, fg_color="transparent")
        logs_header.grid(row=0, column=0, padx=14, pady=(10, 6), sticky="ew")

        ctk.CTkLabel(logs_header, text="💬 CHAT EN VIVO DE TIKTOK Y REGISTRO", font=("Segoe UI", 12, "bold")).pack(side="left")

        self.log_filter_selector = ctk.CTkSegmentedButton(
            logs_header,
            values=["Todos", "🎵 Solicitudes (!play)", "💬 Chat"],
            command=self._on_log_filter_change,
            height=24,
            font=("Segoe UI", 11)
        )
        self.log_filter_selector.set("Todos")
        self.log_filter_selector.pack(side="left", padx=16)

        btn_clear_logs = ctk.CTkButton(
            logs_header,
            text="🧹 Limpiar",
            width=70,
            height=24,
            command=self._clear_logs,
            fg_color="#334155",
            hover_color="#475569",
            font=("Segoe UI", 11)
        )
        btn_clear_logs.pack(side="right")

        self.logs_textbox = ctk.CTkTextbox(
            logs_card,
            height=160,
            corner_radius=8,
            fg_color="#0b0e17",
            font=("Consolas", 11),
            wrap="word"
        )
        self.logs_textbox.grid(row=1, column=0, padx=12, pady=0, sticky="nsew")
        self.logs_textbox.configure(state="disabled")

        self.logs_textbox.tag_config("chat", foreground="#f8fafc")
        self.logs_textbox.tag_config("song", foreground="#1ed760")
        self.logs_textbox.tag_config("player", foreground="#38bdf8")
        self.logs_textbox.tag_config("admin", foreground="#facc15")
        self.logs_textbox.tag_config("warning", foreground="#fb923c")
        self.logs_textbox.tag_config("error", foreground="#f87171")
        self.logs_textbox.tag_config("system", foreground="#94a3b8")

        self.append_log("system", "🚀 Bot listo. Para pedir canciones en la app o en el chat debes escribir: !play <canción>")

    # --- 4. CALLBACKS & SYNC ---
    def _connect_orchestrator_callbacks(self):
        self.orchestrator.on_log_callback = lambda lvl, msg: self.after(0, self.append_log, lvl, msg)
        self.orchestrator.on_status_callback = lambda st, det: self.after(0, self._update_status_ui, st, det)
        self.orchestrator.on_comment_callback = lambda c: self.after(0, self._on_chat_comment, c)
        self.orchestrator.on_queue_update_callback = lambda: self.after(0, self._refresh_queue_ui)
        self.orchestrator.on_player_update_callback = lambda: self.after(0, self._refresh_player_ui)

    def _load_initial_values(self):
        saved_uid = self.config.get("tiktok", {}).get("unique_id", "")
        if saved_uid:
            self.entry_username.insert(0, saved_uid)

        saved_mode = self.config.get("player_mode", "youtube")
        if saved_mode == "youtube":
            self.mode_selector.set("🔴 YouTube (Auto)")
        elif saved_mode == "spotify":
            self.mode_selector.set("🟢 Spotify (Beta)")
        else:
            self.mode_selector.set("📁 Local")

        self._update_mode_selector_color(saved_mode)
        self._update_spotify_auth_button()
        self._refresh_player_ui()
        self._refresh_queue_ui()

    def _update_spotify_auth_button(self):
        sp = self.orchestrator.spotify_player
        if sp.is_linked:
            name = sp.user_profile.get("display_name", "Vinculado") if sp.user_profile else "Vinculado"
            self.btn_spotify_auth.configure(
                text=f"🟢 {name}",
                fg_color="#14532d",
                hover_color="#166534",
                text_color="#86efac"
            )
        else:
            self.btn_spotify_auth.configure(
                text="🔗 Vincular Spotify",
                fg_color="#1ed760",
                hover_color="#16a34a",
                text_color="#000000"
            )

    def _toggle_spotify_link(self):
        sp = self.orchestrator.spotify_player
        if sp.is_linked:
            if messagebox.askyesno("Spotify", "¿Deseas desvincular tu cuenta de Spotify actual?"):
                sp.unlink_account()
                self._update_spotify_auth_button()
                self.append_log("system", "Spotify desvinculado.")
        else:
            self.append_log("info", "🔗 Abriendo navegador para vincular tu cuenta de Spotify...")
            threading.Thread(target=self._async_link_spotify, daemon=True).start()

    def _async_link_spotify(self):
        success = self.orchestrator.spotify_player.link_account()
        if success:
            self.after(0, self._update_spotify_auth_button)
            self.after(0, self.append_log, "success", "🟢 ¡Cuenta de Spotify vinculada exitosamente!")
        else:
            self.after(0, self.append_log, "error", "❌ Error al vincular con Spotify.")

    def append_log(self, level: str, message: str):
        self.raw_logs.append({"level": level, "message": message})
        self._render_log_entry(level, message)

    def _render_log_entry(self, level: str, message: str):
        if self.current_filter == "🎵 Solicitudes (!play)" and level not in ["song", "player"]:
            return
        if self.current_filter == "💬 Chat" and level != "chat":
            return

        self.logs_textbox.configure(state="normal")
        self.logs_textbox.insert("end", message + "\n", level)
        self.logs_textbox.see("end")
        self.logs_textbox.configure(state="disabled")

    def _on_chat_comment(self, comment_data: Dict[str, Any]):
        timestamp = comment_data.get("timestamp", datetime.now().strftime("%H:%M:%S"))
        msg = f"[{timestamp}] [CHAT] {comment_data.get('nickname')} (@{comment_data.get('user')}): {comment_data.get('comment')}"
        self.append_log("chat", msg)

    def _update_status_ui(self, status: str, details: Dict[str, Any]):
        if status == "CONNECTED":
            self.is_connected = True
            self.lbl_status_badge.configure(text="🟢 En Vivo", fg_color="#14532d", text_color="#86efac")
            self.btn_connect.configure(text="⏹ Desconectar", fg_color="#334155", hover_color="#475569")
        elif status == "CONNECTING":
            self.is_connected = False
            self.lbl_status_badge.configure(text="🟡 Conectando...", fg_color="#713f12", text_color="#fde047")
            self.btn_connect.configure(text="Cancelando...", fg_color="#713f12")
        elif status == "OFFLINE":
            self.is_connected = False
            self.lbl_status_badge.configure(text="🔴 Fuera de Línea", fg_color="#450a0a", text_color="#fca5a5")
            self.btn_connect.configure(text="⚡ Conectar", fg_color="#fe2c55", hover_color="#e01740")
        else:
            self.is_connected = False
            self.lbl_status_badge.configure(text="🔴 Desconectado", fg_color="#261b20", text_color="#ff4757")
            self.btn_connect.configure(text="⚡ Conectar", fg_color="#fe2c55", hover_color="#e01740")

    def _refresh_player_ui(self):
        player_state = self.orchestrator.current_player.get_status()
        track = player_state.get("current_track")
        is_playing = player_state.get("is_playing", False)
        is_paused = player_state.get("is_paused", False)

        mode = self.orchestrator.player_mode
        if mode == "spotify":
            self.lbl_card_mode.configure(text="🎧 SONANDO DESDE SPOTIFY (EN DESARROLLO)", text_color="#1ed760")
            self.progress_bar.configure(progress_color="#1ed760")
        elif mode == "youtube":
            self.lbl_card_mode.configure(text="🎧 SONANDO DESDE YOUTUBE (MP3)", text_color="#ef4444")
            self.progress_bar.configure(progress_color="#ef4444")
        else:
            self.lbl_card_mode.configure(text="🎧 SONANDO MÚSICA LOCAL (EN DESARROLLO)", text_color="#eab308")
            self.progress_bar.configure(progress_color="#eab308")

        if is_playing and not is_paused:
            self.btn_play_pause.configure(text="⏸ Pausar", fg_color="#facc15", text_color="#000000")
        else:
            self.btn_play_pause.configure(text="▶ Reanudar", fg_color="#1ed760", text_color="#000000")

        if track:
            self.lbl_track_title.configure(text=track.get("title", "Desconocido"))
            self.lbl_track_artist.configure(text=track.get("artist", "Desconocido"))
        else:
            self.lbl_track_title.configure(text="No hay canciones en reproducción")
            self.lbl_track_artist.configure(text="Escribe en la caja o en el chat: !play <canción>")

        current = player_state.get("current_time", 0.0)
        duration = player_state.get("duration", 0.0)
        self.lbl_time.configure(text=f"{self._format_time(current)} / {self._format_time(duration)}")
        if duration > 0:
            self.progress_bar.set(min(1.0, max(0.0, current / duration)))
        else:
            self.progress_bar.set(0)

    def _playback_refresh_loop(self):
        try:
            self._refresh_player_ui()
        except Exception:
            pass
        self.after(1000, self._playback_refresh_loop)

    def _refresh_queue_ui(self):
        queue = self.orchestrator.queue_manager.get_queue()
        self.lbl_queue_count.configure(text=f"{len(queue)} canciones")

        for widget in self.queue_scroll.winfo_children():
            widget.destroy()

        if not queue:
            self._render_empty_queue()
            return

        for idx, item in enumerate(queue):
            track = item.get("track", {})
            title = track.get("title", "Canción")
            artist = track.get("artist", "")
            user = item.get("requested_by", "anónimo")
            item_id = item.get("id")

            item_frame = ctk.CTkFrame(self.queue_scroll, fg_color="#131722", corner_radius=6)
            item_frame.pack(fill="x", padx=4, pady=4)
            item_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(item_frame, text=f"#{idx+1}", font=("Consolas", 12, "bold"), text_color="#1ed760", width=30).grid(row=0, column=0, padx=6, pady=6)
            
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.grid(row=0, column=1, padx=4, pady=4, sticky="w")
            ctk.CTkLabel(info_frame, text=title, font=("Segoe UI", 12, "bold"), wraplength=340, justify="left").pack(anchor="w")
            ctk.CTkLabel(info_frame, text=f"{artist} • @{user}", font=("Segoe UI", 10), text_color="#94a3b8").pack(anchor="w")

            btn_del = ctk.CTkButton(
                item_frame,
                text="❌",
                width=28,
                height=28,
                fg_color="transparent",
                hover_color="#7f1d1d",
                command=lambda i_id=item_id: self._remove_queue_item(i_id)
            )
            btn_del.grid(row=0, column=2, padx=6, pady=6)

    def _render_empty_queue(self):
        lbl = ctk.CTkLabel(
            self.queue_scroll,
            text="📭 La cola está vacía\nEscribe: !play <canción>",
            font=("Segoe UI", 12),
            text_color="#64748b",
            justify="center"
        )
        lbl.pack(pady=40)

    # --- 5. ACCIONES ---
    def _toggle_connect(self):
        username = self.entry_username.get().strip()
        if not self.is_connected:
            if not username:
                self.append_log("warning", "⚠️ Introduce tu usuario de TikTok arriba.")
                return

            # Guardar el usuario en la configuración para la próxima sesión
            if "tiktok" not in self.config:
                self.config["tiktok"] = {}
            self.config["tiktok"]["unique_id"] = username
            save_config(self.config)

            self._update_status_ui("CONNECTING", {})
            asyncio.run_coroutine_threadsafe(
                self.orchestrator.connect(username),
                self.async_loop
            )
        else:
            asyncio.run_coroutine_threadsafe(
                self.orchestrator.disconnect(),
                self.async_loop
            )

    def _on_toggle_command(self, key: str, badge: ctk.CTkLabel, desc_widget: Any, var: ctk.BooleanVar):
        """Activa o desactiva comandos del chat dinámicamente."""
        enabled = var.get()
        self.orchestrator.set_command_enabled(key, enabled)
        if enabled:
            badge.configure(text_color="#ffffff", fg_color="#2b384e")
            if isinstance(desc_widget, ctk.CTkOptionMenu):
                desc_widget.configure(state="normal")
            elif hasattr(desc_widget, "configure"):
                desc_widget.configure(text_color="#94a3b8")
        else:
            badge.configure(text_color="#64748b", fg_color="#1e293b")
            if isinstance(desc_widget, ctk.CTkOptionMenu):
                desc_widget.configure(state="disabled")
            elif hasattr(desc_widget, "configure"):
                desc_widget.configure(text_color="#475569")

    def _on_skip_permission_change(self, choice: str):
        """Cambia el nivel de permiso de !skip (Mods vs Todos)."""
        mode = "all" if "todo" in choice.lower() or "all" in choice.lower() else "mods"
        self.orchestrator.permissions.set_skip_permission(mode)

        if "permissions" not in self.config:
            self.config["permissions"] = {}
        self.config["permissions"]["skip_permission"] = mode
        save_config(self.config)

        txt = "🌍 Cualquier usuario (General)" if mode == "all" else "👥 Solo Moderadores y Streamer"
        self.append_log("admin", f"⚙️ Permiso de !skip actualizado a: {txt}")

    def _update_mode_selector_color(self, mode: str):
        """Aplica color Rojo para YouTube, Verde para Spotify y Amarillo para Local."""
        if mode == "youtube":
            self.mode_selector.configure(
                selected_color="#ef4444",
                selected_hover_color="#dc2626"
            )
        elif mode == "spotify":
            self.mode_selector.configure(
                selected_color="#1ed760",
                selected_hover_color="#16a34a"
            )
        else:  # local (amarillo explorador de archivos)
            self.mode_selector.configure(
                selected_color="#eab308",
                selected_hover_color="#ca8a04"
            )

    def _on_mode_change(self, value: str):
        if "YouTube" in value:
            mode = "youtube"
        elif "Spotify" in value:
            mode = "spotify"
        else:
            mode = "local"
        self._update_mode_selector_color(mode)
        self.orchestrator.set_player_mode(mode)
        self.config["player_mode"] = mode
        save_config(self.config)
        self._refresh_player_ui()

    def _on_play_pause(self):
        player = self.orchestrator.current_player
        if player.is_playing and not player.is_paused:
            player.pause()
        else:
            player.resume()
        self._refresh_player_ui()

    def _on_skip(self):
        self.orchestrator.current_player.skip()
        self._refresh_player_ui()

    def _on_volume_change(self, val: float):
        self.orchestrator.current_player.set_volume(val)

    def _on_add_manual_song(self):
        """Validación estricta del comando !play en la solicitud manual."""
        raw_text = self.entry_manual_song.get().strip()
        if not raw_text:
            return

        if not raw_text.lower().startswith("!play"):
            self.append_log("warning", "⚠️ Debes escribir el comando con '!play'. Ejemplo: !play awake wrld")
            return

        parts = raw_text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            self.append_log("warning", "⚠️ Falta el nombre de la canción. Ejemplo: !play awake wrld")
            return

        song_query = parts[1].strip()
        self.entry_manual_song.delete(0, "end")

        mode = self.orchestrator.player_mode
        if mode == "youtube":
            self.append_log("info", f"🔍 [!play] Buscando en YouTube: '{song_query}'...")
            threading.Thread(target=self._async_add_youtube_song, args=(song_query,), daemon=True).start()
        elif mode == "spotify":
            if not self.orchestrator.spotify_player.is_linked:
                self.append_log("warning", "⚠️ Spotify no está vinculado. Haz clic en '🔗 Vincular Spotify'.")
                return
            self.append_log("song", f"🎵 [!play] Spotify: '{song_query}'...")
            threading.Thread(target=self.orchestrator.spotify_player.search_and_play, args=(song_query,), daemon=True).start()
            self._refresh_player_ui()
        else:
            threading.Thread(target=self._async_add_local_song, args=(song_query,), daemon=True).start()

    def _async_add_youtube_song(self, query: str):
        track = self.orchestrator.youtube_player.search_track(query)
        if track:
            self.orchestrator.queue_manager.add(track, "Streamer (App)", "Streamer")
            self.orchestrator.log("song", f"🎵 [!play] '{track['title']}' encolada.")
            self.orchestrator._notify_queue_update()
            self.orchestrator._check_and_play_next()
        else:
            self.orchestrator.log("warning", f"❌ No se encontró en YouTube '{query}'")

    def _async_add_local_song(self, query: str):
        match, score = self.orchestrator.parser.find_best_match(query, self.orchestrator.local_player.indexed_tracks)
        if match and score >= 45:
            self.orchestrator.queue_manager.add(match, "Streamer (App)", "Streamer")
            self.orchestrator.log("song", f"🎵 [!play] Local: '{match['title']}' encolada.")
            self.orchestrator._notify_queue_update()
            self.orchestrator._check_and_play_next()
        else:
            self.orchestrator.log("warning", f"❌ No encontrada en biblioteca local '{query}'")

    def _remove_queue_item(self, item_id: str):
        self.orchestrator.remove_queue_item_by_id(item_id)
        self._refresh_queue_ui()

    def _on_clear_queue(self):
        count = self.orchestrator.clear_queue()
        self.append_log("admin", f"🗑️ Cola vaciada ({count} canciones eliminadas).")
        self._refresh_queue_ui()

    def _on_log_filter_change(self, filter_name: str):
        self.current_filter = filter_name
        self.logs_textbox.configure(state="normal")
        self.logs_textbox.delete("1.0", "end")
        self.logs_textbox.configure(state="disabled")
        for log in self.raw_logs:
            self._render_log_entry(log["level"], log["message"])

    def _clear_logs(self):
        self.raw_logs.clear()
        self.logs_textbox.configure(state="normal")
        self.logs_textbox.delete("1.0", "end")
        self.logs_textbox.configure(state="disabled")

    # --- 6. DIÁLOGO DE AJUSTES & GESTIÓN DE CACHÉ ---
    def _open_settings_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚙️ Ajustes & Gestión de Caché")
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="⚙️ Configuración & Caché de Audio", font=("Segoe UI", 15, "bold")).pack(padx=20, pady=(16, 8), anchor="w")

        stats = self.orchestrator.youtube_player.get_cache_stats()
        lbl_cache_info = ctk.CTkLabel(
            dialog,
            text=f"📁 Archivos en caché: {stats['count']}  ({stats['size_mb']} MB usados)",
            font=("Segoe UI", 12),
            text_color="#94a3b8"
        )
        lbl_cache_info.pack(padx=20, pady=4, anchor="w")

        lbl_desc = ctk.CTkLabel(
            dialog,
            text=" ATENCION: Las canciones se eliminan automáticamente del disco en cuanto\nterminan de sonar, manteniendo las canciones en cola protegidas\npara que comiencen al instante sin retrasos.",
            font=("Segoe UI", 11),
            text_color="#64748b",
            justify="left"
        )
        lbl_desc.pack(padx=20, pady=(0, 14), anchor="w")

        def clear_cache_action():
            deleted = self.orchestrator.youtube_player.clear_all_cache()
            new_stats = self.orchestrator.youtube_player.get_cache_stats()
            lbl_cache_info.configure(text=f"📁 Archivos en caché: {new_stats['count']}  ({new_stats['size_mb']} MB usados)")
            self.append_log("system", f"🧹 Caché vaciada: se eliminaron {deleted} archivos.")
            messagebox.showinfo("Caché", f"Se han eliminado {deleted} archivos de la caché.")

        btn_clear = ctk.CTkButton(
            dialog,
            text="🧹 Vaciar Caché Manualmente",
            command=clear_cache_action,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            font=("Segoe UI", 12, "bold")
        )
        btn_clear.pack(padx=20, pady=6, fill="x")

        # --- Sección de Actualizaciones ---
        sep = ctk.CTkFrame(dialog, height=1, fg_color="#334155")
        sep.pack(fill="x", padx=20, pady=(10, 6))

        ctk.CTkLabel(
            dialog,
            text=f"🚀 Actualizaciones  (Versión actual: {APP_VERSION})",
            font=("Segoe UI", 13, "bold")
        ).pack(padx=20, pady=(6, 4), anchor="w")

        btn_check_updates = ctk.CTkButton(
            dialog,
            text="🔍 Buscar Actualizaciones en GitHub",
            command=lambda: (
                dialog.destroy(),
                check_updates_background(self, silent=False, log_callback=self.append_log)
            ),
            fg_color="#1e40af",
            hover_color="#1d4ed8",
            font=("Segoe UI", 12, "bold")
        )
        btn_check_updates.pack(padx=20, pady=6, fill="x")

        btn_close = ctk.CTkButton(
            dialog,
            text="Cerrar",
            command=dialog.destroy,
            fg_color="#334155",
            hover_color="#475569"
        )
        btn_close.pack(padx=20, pady=(6, 16), fill="x")

    def _format_time(self, seconds: float) -> str:
        if seconds <= 0:
            return "00:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"
