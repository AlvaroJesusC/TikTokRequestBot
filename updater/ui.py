"""
Módulo de Interfaz Gráfica para el Sistema de Actualizaciones (CustomTkinter)
===========================================================================
Ventana modal moderna con visualización de changelog, barra de progreso
y descarga con reinicio automático.
"""

import sys
import threading
from typing import Dict, Any, Optional
from tkinter import messagebox

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from .version import APP_VERSION, APP_NAME
from .checker import check_for_updates, is_running_as_exe
from .installer import download_update, apply_update_and_restart, open_release_page_in_browser


class UpdateModalDialog(ctk.CTkToplevel):
    """Ventana modal moderna que informa sobre una nueva versión y permite instalarla."""

    def __init__(self, parent, update_info: Dict[str, Any]):
        super().__init__(parent)
        self.update_info = update_info
        self.is_downloading = False
        self._cancel_download = False

        self.title(f"🚀 Actualización Disponible - {APP_NAME}")
        self.geometry("540x480")
        self.minsize(500, 420)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#0f172a")

        # Centrar la ventana en pantalla
        self._center_window(parent)

        self._build_ui()

    def _center_window(self, parent):
        try:
            self.update_idletasks()
            pw = parent.winfo_width() if parent else 1000
            ph = parent.winfo_height() if parent else 700
            px = parent.winfo_rootx() if parent else 100
            py = parent.winfo_rooty() if parent else 100
            w, h = 540, 480
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _build_ui(self):
        # Header con gradiente/color
        header = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        header.pack(fill="x", padx=16, pady=(16, 8))

        lbl_icon = ctk.CTkLabel(header, text="✨", font=("Segoe UI Emoji", 26))
        lbl_icon.pack(side="left", padx=14, pady=10)

        header_text_frame = ctk.CTkFrame(header, fg_color="transparent")
        header_text_frame.pack(side="left", fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            header_text_frame,
            text=f"¡Nueva versión disponible: {self.update_info.get('latest_version', '')}!",
            font=("Segoe UI", 15, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w")

        v_current = self.update_info.get("current_version", APP_VERSION)
        v_latest = self.update_info.get("latest_version", "")
        ctk.CTkLabel(
            header_text_frame,
            text=f"Versión instalada: {v_current}  ➜  Última: {v_latest}",
            font=("Segoe UI", 11),
            text_color="#94a3b8"
        ).pack(anchor="w")

        # Card de Notas de la versión (Changelog)
        notes_frame = ctk.CTkFrame(self, fg_color="#131722", corner_radius=10)
        notes_frame.pack(fill="both", expand=True, padx=16, pady=6)

        ctk.CTkLabel(
            notes_frame,
            text="📋 Novedades y Cambios:",
            font=("Segoe UI", 12, "bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.txt_notes = ctk.CTkTextbox(
            notes_frame,
            fg_color="#0b0e14",
            text_color="#e2e8f0",
            font=("Segoe UI", 11),
            wrap="word",
            corner_radius=6
        )
        self.txt_notes.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        notes_body = self.update_info.get("release_notes", "").strip() or "Mejoras de rendimiento y correcciones de estabilidad."
        self.txt_notes.insert("1.0", notes_body)
        self.txt_notes.configure(state="disabled")

        # Barra de Descarga (inicialmente oculta/en 0)
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=16, pady=4)

        self.lbl_progress_status = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=("Segoe UI", 11),
            text_color="#94a3b8"
        )
        self.lbl_progress_status.pack(anchor="w", padx=2)

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            fg_color="#1e293b",
            progress_color="#38bdf8",
            height=10
        )
        self.progress_bar.set(0.0)

        # Botones de Acción
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(6, 16))

        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Recordar más tarde",
            fg_color="#334155",
            hover_color="#475569",
            command=self._on_close,
            width=130
        )
        self.btn_cancel.pack(side="left", padx=4)

        self.btn_github = ctk.CTkButton(
            btn_frame,
            text="🌐 Ver en GitHub",
            fg_color="#1e293b",
            hover_color="#334155",
            command=lambda: open_release_page_in_browser(self.update_info.get("html_url", "")),
            width=120
        )
        self.btn_github.pack(side="left", padx=4)

        download_url = self.update_info.get("download_url", "")
        if download_url and is_running_as_exe():
            btn_text = "⬇️ Actualizar y Reiniciar"
            btn_cmd = self._start_download_and_install
            btn_color = "#10b981"
            btn_hover = "#059669"
        else:
            btn_text = "⬇️ Descargar Nueva Versión"
            btn_cmd = lambda: open_release_page_in_browser(self.update_info.get("html_url", ""))
            btn_color = "#38bdf8"
            btn_hover = "#0284c7"

        self.btn_update = ctk.CTkButton(
            btn_frame,
            text=btn_text,
            fg_color=btn_color,
            hover_color=btn_hover,
            font=("Segoe UI", 12, "bold"),
            command=btn_cmd
        )
        self.btn_update.pack(side="right", padx=4, fill="x", expand=True)

    def _start_download_and_install(self):
        if self.is_downloading:
            return
        self.is_downloading = True
        self._cancel_download = False

        self.btn_update.configure(state="disabled", text="Descargando...")
        self.btn_cancel.configure(text="Cancelar")
        self.progress_bar.pack(fill="x", pady=(4, 0))
        self.lbl_progress_status.configure(text="Iniciando descarga...")

        download_url = self.update_info.get("download_url", "")
        threading.Thread(target=self._download_worker, args=(download_url,), daemon=True).start()

    def _download_worker(self, download_url: str):
        def on_progress(downloaded, total, percent):
            if total > 0:
                mb_down = downloaded / (1024 * 1024)
                mb_tot = total / (1024 * 1024)
                text = f"Descargando: {mb_down:.1f} MB / {mb_tot:.1f} MB ({int(percent * 100)}%)"
            else:
                text = f"Descargando: {downloaded / (1024 * 1024):.1f} MB..."

            self.after(0, lambda: self._update_progress_ui(percent, text))

        temp_path = download_update(
            download_url,
            progress_callback=on_progress,
            cancel_flag=lambda: self._cancel_download
        )

        if self._cancel_download:
            self.after(0, self._handle_download_cancelled)
            return

        if temp_path and temp_path.exists():
            self.after(0, lambda: self._handle_download_success(temp_path))
        else:
            self.after(0, self._handle_download_failed)

    def _update_progress_ui(self, percent: float, text: str):
        try:
            self.progress_bar.set(percent)
            self.lbl_progress_status.configure(text=text)
        except Exception:
            pass

    def _handle_download_success(self, temp_path):
        self.lbl_progress_status.configure(text="✅ Descarga completa. Reiniciando aplicación...", text_color="#10b981")
        self.after(1200, lambda: apply_update_and_restart(temp_path))

    def _handle_download_failed(self):
        self.is_downloading = False
        self.lbl_progress_status.configure(text="❌ Error en la descarga.", text_color="#ef4444")
        self.btn_update.configure(state="normal", text="Reintentar")
        self.btn_cancel.configure(text="Cerrar")
        messagebox.showerror(
            "Error de Actualización",
            "No se pudo completar la descarga. Puedes descargar la nueva versión manualmente desde GitHub."
        )

    def _handle_download_cancelled(self):
        self.is_downloading = False
        self.lbl_progress_status.configure(text="Descarga cancelada.", text_color="#94a3b8")
        self.btn_update.configure(state="normal", text="⬇️ Actualizar y Reiniciar")
        self.btn_cancel.configure(text="Recordar más tarde")

    def _on_close(self):
        if self.is_downloading:
            self._cancel_download = True
        self.destroy()


def check_updates_background(parent_window, silent: bool = True, log_callback=None):
    """
    Ejecuta la comprobación de actualizaciones en segundo plano.
    
    :param parent_window: Ventana principal (DesktopApp).
    :param silent: Si es True, solo muestra la ventana modal si hay una nueva versión.
                   Si es False, avisa también cuando ya se tiene la versión más reciente.
    :param log_callback: Función opcional para escribir al panel de logs del bot.
    """
    def worker():
        if log_callback and not silent:
            log_callback("system", "🔍 Comprobando actualizaciones en GitHub...")

        info = check_for_updates()

        if info.get("has_update"):
            if log_callback:
                log_callback("system", f"✨ ¡Nueva versión {info.get('latest_version')} disponible!")
            
            # Lanzar modal en el hilo principal de la UI
            parent_window.after(0, lambda: UpdateModalDialog(parent_window, info))
        else:
            if not silent:
                if info.get("error"):
                    err_msg = info.get("error")
                    if log_callback:
                        log_callback("warning", f"⚠️ Comprobación de versión: {err_msg}")
                    parent_window.after(0, lambda: messagebox.showwarning(
                        "Actualizaciones",
                        f"No se pudo consultar el repositorio:\n{err_msg}"
                    ))
                else:
                    if log_callback:
                        log_callback("system", f"✅ Estás al día (versión {APP_VERSION}).")
                    parent_window.after(0, lambda: messagebox.showinfo(
                        "TikTok LIVE SongBot",
                        f"🎉 ¡Tu aplicación está al día!\n\nVersión actual instalada: {APP_VERSION}"
                    ))

    threading.Thread(target=worker, daemon=True).start()
