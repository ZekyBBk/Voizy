"""
Ventanas modales, gestores y diálogos oscuros de confirmación para Voizy Studio.
Estilo profesional minimalista y limpio (sin emojis ni scrollbars innecesarios).
"""

import os
import sys
import threading
import customtkinter as ctk

from ui.theme import (
    COLOR_BG,
    COLOR_CARD,
    COLOR_CARD_BORDER,
    COLOR_INPUT_BG,
    COLOR_MARCA,
    COLOR_MARCA_HOVER,
    COLOR_MARCA_ACTIVE,
    COLOR_BTN_DARK,
    COLOR_BTN_DARK_HOVER,
    COLOR_BTN_DARK_BORDER,
    COLOR_ERROR,
    COLOR_AVISO,
    COLOR_OK,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    FONT_MAIN,
    NOMBRE_APP,
    VERSION_APP,
)
from utils.paths import resource_path, obtener_ffmpeg_path, RUTA_BASE, RUTA_DATOS
from utils.logger import log_info, log_exception
from utils.helpers import (
    abrir_explorador_archivos,
    obtener_nombre_cpu,
    obtener_detalles_pc,
    aplicar_tema_oscuro_barra_titulo,
)
from core.model_manager import (
    esta_instalado,
    esta_cuda_instalado,
    esta_ffmpeg_instalado,
    descargar_modelo_hf,
    descargar_acelerador_cuda,
    descargar_ffmpeg,
    hay_actualizacion_disponible,
    hay_actualizacion_cuda,
    INFO_MODELOS,
    DIR_MODELOS,
    DIR_CUDA,
    DIR_BIN,
)

try:
    import ctranslate2
except ImportError:
    ctranslate2 = None


def forzar_icono_modal(toplevel):
    """Aplica el icono corporativo voizy.ico al toplevel."""
    ruta_ico = resource_path("voizy.ico")
    if os.path.isfile(ruta_ico):
        try:
            toplevel.iconbitmap(ruta_ico)
        except Exception:
            pass


def _configurar_toplevel(modal, parent, titulo, ancho=500, alto=280):
    modal.title(titulo)
    modal.configure(fg_color=COLOR_BG)
    modal.resizable(False, False)
    modal.transient(parent)

    x = int((modal.winfo_screenwidth() / 2) - (ancho / 2))
    y = int((modal.winfo_screenheight() / 2) - (alto / 2))
    modal.geometry(f"{ancho}x{alto}+{x}+{y}")

    forzar_icono_modal(modal)
    aplicar_tema_oscuro_barra_titulo(modal, COLOR_BG, COLOR_TEXT)
    modal.grab_set()
    modal.focus_force()


def mostrar_modal_mensaje(parent, titulo, mensaje, tipo="info", on_close=None):
    """Modal oscuro para alertas, advertencias y confirmaciones simples."""
    modal = ctk.CTkToplevel(parent)
    parent._modal_activo = modal
    _configurar_toplevel(modal, parent, titulo, ancho=460, alto=230)

    color_titulo = COLOR_MARCA
    if tipo == "error":
        color_titulo = COLOR_ERROR
    elif tipo == "aviso":
        color_titulo = COLOR_AVISO

    card = ctk.CTkFrame(modal, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=12)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(
        card,
        text=titulo.upper(),
        font=(FONT_MAIN, 15, "bold"),
        text_color=color_titulo,
    ).pack(pady=(18, 8), padx=20, anchor="w")

    ctk.CTkLabel(
        card,
        text=mensaje,
        justify="left",
        wraplength=390,
        font=(FONT_MAIN, 12),
        text_color=COLOR_TEXT,
    ).pack(pady=(0, 16), padx=20, fill="x")

    def _cerrar():
        try:
            modal.grab_release()
            modal.destroy()
        except Exception:
            pass
        parent._modal_activo = None
        if on_close:
            on_close()

    modal.protocol("WM_DELETE_WINDOW", _cerrar)

    btn = ctk.CTkButton(
        card,
        text="Aceptar",
        command=_cerrar,
        fg_color=COLOR_MARCA,
        hover_color=COLOR_MARCA_HOVER,
        text_color="black",
        font=(FONT_MAIN, 12, "bold"),
        height=32,
        width=110,
        corner_radius=8,
    )
    btn.pack(side="bottom", anchor="e", padx=20, pady=(0, 16))


def mostrar_modal_aviso(parent, titulo, mensaje):
    mostrar_modal_mensaje(parent, titulo, mensaje, tipo="aviso")


def mostrar_modal_error(parent, titulo, mensaje, on_close=None):
    """Modal oscuro para errores con caja de texto completa y botón de copiar error."""
    modal = ctk.CTkToplevel(parent)
    parent._modal_activo = modal
    _configurar_toplevel(modal, parent, f"Error: {titulo}", ancho=560, alto=340)

    card = ctk.CTkFrame(modal, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=12)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(
        card,
        text="SE HA PRODUCIDO UN ERROR",
        font=(FONT_MAIN, 15, "bold"),
        text_color=COLOR_ERROR,
    ).pack(pady=(16, 6), padx=20, anchor="w")

    ctk.CTkLabel(
        card,
        text=titulo,
        font=(FONT_MAIN, 12, "bold"),
        text_color=COLOR_TEXT,
    ).pack(pady=(0, 8), padx=20, anchor="w")

    txt_error = ctk.CTkTextbox(
        card,
        fg_color=COLOR_INPUT_BG,
        border_color=COLOR_CARD_BORDER,
        border_width=1,
        text_color=COLOR_TEXT_DIM,
        font=("Consolas", 10),
        corner_radius=8,
        height=120,
    )
    txt_error.pack(fill="both", expand=True, padx=20, pady=(0, 12))
    txt_error.insert("1.0", mensaje)
    txt_error.configure(state="disabled")

    frame_btns = ctk.CTkFrame(card, fg_color="transparent")
    frame_btns.pack(side="bottom", fill="x", padx=20, pady=(0, 16))

    def _copiar():
        try:
            modal.clipboard_clear()
            modal.clipboard_append(mensaje)
            btn_copiar.configure(text="Copiado")
        except Exception:
            pass

    btn_copiar = ctk.CTkButton(
        frame_btns,
        text="Copiar Error",
        command=_copiar,
        fg_color=COLOR_BTN_DARK,
        hover_color=COLOR_BTN_DARK_HOVER,
        border_color=COLOR_BTN_DARK_BORDER,
        border_width=1,
        text_color=COLOR_TEXT,
        font=(FONT_MAIN, 11, "bold"),
        height=32,
        width=120,
        corner_radius=8,
    )
    btn_copiar.pack(side="left")

    def _cerrar():
        try:
            modal.grab_release()
            modal.destroy()
        except Exception:
            pass
        parent._modal_activo = None
        if on_close:
            on_close()

    modal.protocol("WM_DELETE_WINDOW", _cerrar)

    ctk.CTkButton(
        frame_btns,
        text="Cerrar",
        command=_cerrar,
        fg_color=COLOR_ERROR,
        hover_color="#DC2626",
        text_color="white",
        font=(FONT_MAIN, 11, "bold"),
        height=32,
        width=100,
        corner_radius=8,
    ).pack(side="right")


def mostrar_modal_confirmacion(parent, titulo, mensaje, on_confirm=None, on_cancel=None):
    """Modal oscuro de confirmación con dos botones claros (Aceptar / Cancelar)."""
    modal = ctk.CTkToplevel(parent)
    parent._modal_activo = modal
    _configurar_toplevel(modal, parent, titulo, ancho=480, alto=250)

    card = ctk.CTkFrame(modal, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=12)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(
        card,
        text=titulo.upper(),
        font=(FONT_MAIN, 14, "bold"),
        text_color=COLOR_MARCA,
    ).pack(pady=(16, 8), padx=20, anchor="w")

    ctk.CTkLabel(
        card,
        text=mensaje,
        justify="left",
        wraplength=390,
        font=(FONT_MAIN, 11),
        text_color=COLOR_TEXT,
    ).pack(pady=(0, 16), padx=20, fill="x")

    frame_btns = ctk.CTkFrame(card, fg_color="transparent")
    frame_btns.pack(side="bottom", fill="x", padx=20, pady=(0, 16))

    def _ejecutar_confirm():
        try:
            modal.grab_release()
            modal.destroy()
        except Exception:
            pass
        parent._modal_activo = None
        if on_confirm:
            on_confirm()

    def _ejecutar_cancel():
        try:
            modal.grab_release()
            modal.destroy()
        except Exception:
            pass
        parent._modal_activo = None
        if on_cancel:
            on_cancel()

    modal.protocol("WM_DELETE_WINDOW", _ejecutar_cancel)

    ctk.CTkButton(
        frame_btns,
        text="Cancelar",
        command=_ejecutar_cancel,
        fg_color=COLOR_BTN_DARK,
        hover_color=COLOR_BTN_DARK_HOVER,
        border_color=COLOR_BTN_DARK_BORDER,
        border_width=1,
        text_color=COLOR_TEXT,
        font=(FONT_MAIN, 11, "bold"),
        height=32,
        width=100,
        corner_radius=8,
    ).pack(side="right", padx=(8, 0))

    ctk.CTkButton(
        frame_btns,
        text="Aceptar",
        command=_ejecutar_confirm,
        fg_color=COLOR_MARCA,
        hover_color=COLOR_MARCA_HOVER,
        text_color="black",
        font=(FONT_MAIN, 11, "bold"),
        height=32,
        width=110,
        corner_radius=8,
    ).pack(side="right")


def mostrar_modal_exito(parent, ruta_carpeta, mensaje="Proceso completado con éxito.", on_reset=None):
    """Modal oscuro de éxito con acceso directo a la carpeta de salida."""
    modal = ctk.CTkToplevel(parent)
    parent._modal_activo = modal
    _configurar_toplevel(modal, parent, "Proceso Completado", ancho=480, alto=230)

    card = ctk.CTkFrame(modal, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=12)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(
        card,
        text="PROCESO COMPLETADO",
        font=(FONT_MAIN, 15, "bold"),
        text_color=COLOR_OK,
    ).pack(pady=(16, 6), padx=20, anchor="w")

    ctk.CTkLabel(
        card,
        text=mensaje,
        justify="left",
        wraplength=410,
        font=(FONT_MAIN, 11),
        text_color=COLOR_TEXT,
    ).pack(pady=(0, 14), padx=20, fill="x")

    frame_btns = ctk.CTkFrame(card, fg_color="transparent")
    frame_btns.pack(side="bottom", anchor="e", padx=20, pady=(0, 16))

    def abrir_y_cerrar():
        abrir_explorador_archivos(ruta_carpeta)
        cerrar()

    def cerrar():
        try:
            modal.grab_release()
            modal.destroy()
        except Exception:
            pass
        parent._modal_activo = None
        if on_reset:
            on_reset()

    modal.protocol("WM_DELETE_WINDOW", cerrar)

    ctk.CTkButton(
        frame_btns,
        text="Abrir Carpeta",
        command=abrir_y_cerrar,
        fg_color=COLOR_MARCA,
        hover_color=COLOR_MARCA_HOVER,
        text_color="black",
        font=(FONT_MAIN, 12, "bold"),
        height=32,
        width=135,
        corner_radius=8,
    ).pack(side="left", padx=6)

    ctk.CTkButton(
        frame_btns,
        text="Aceptar",
        command=cerrar,
        fg_color=COLOR_BTN_DARK,
        hover_color=COLOR_BTN_DARK_HOVER,
        border_color=COLOR_BTN_DARK_BORDER,
        border_width=1,
        text_color=COLOR_TEXT_DIM,
        font=(FONT_MAIN, 12, "bold"),
        height=32,
        width=100,
        corner_radius=8,
    ).pack(side="left", padx=6)


def cuda_disponible():
    try:
        if esta_cuda_instalado():
            import ctranslate2
            return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        pass
    return False


def mostrar_modal_info(parent):
    """Modal de especificaciones técnicas completas del PC y mantenimiento de datos."""
    modal = ctk.CTkToplevel(parent)
    parent._modal_activo = modal
    _configurar_toplevel(modal, parent, f"Acerca de {NOMBRE_APP}", ancho=580, alto=540)

    card = ctk.CTkFrame(modal, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=12)
    card.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(
        card,
        text="VOIZY STUDIO",
        font=(FONT_MAIN, 16, "bold"),
        text_color=COLOR_MARCA,
    ).pack(pady=(12, 2))

    ctk.CTkLabel(
        card,
        text=f"Versión {VERSION_APP} - Suite Profesional de Subtitulado Inteligente",
        font=(FONT_MAIN, 11),
        text_color=COLOR_TEXT_DIM,
    ).pack(pady=(0, 10))

    frame_specs = ctk.CTkFrame(card, fg_color=COLOR_INPUT_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=10)
    frame_specs.pack(fill="x", padx=16, pady=4)

    info_pc = obtener_detalles_pc()
    tiene_cuda = cuda_disponible()
    dispositivo_ia = "NVIDIA CUDA 12 Activo (Aceleración GPU)" if tiene_cuda else "Modo CPU Multihilo"
    ffmpeg_encontrado = obtener_ffmpeg_path()
    estado_ffmpeg = "Instalado y disponible" if ffmpeg_encontrado else "No descargado"

    specs = [
        ("Sistema Operativo", info_pc.get("so", "Windows 64-bit")),
        ("Procesador (CPU)", info_pc.get("cpu", "CPU Desconocida")),
        ("Memoria RAM", info_pc.get("ram", "RAM Desconocida")),
        ("Tarjeta Gráfica (GPU)", info_pc.get("gpu", "GPU Estándar")),
        ("Aceleración IA", dispositivo_ia),
        ("Motor de Transcripción", "Faster-Whisper (CTranslate2)"),
        ("Binario Multimedia", estado_ffmpeg),
    ]

    for etiqueta, valor in specs:
        fila = ctk.CTkFrame(frame_specs, fg_color="transparent")
        fila.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(fila, text=etiqueta + ":", font=(FONT_MAIN, 10, "bold"), text_color=COLOR_TEXT_DIM).pack(side="left")
        ctk.CTkLabel(fila, text=valor, font=(FONT_MAIN, 10), text_color=COLOR_TEXT, wraplength=340, justify="right").pack(side="right", padx=(8, 0))

    # Sección de Mantenimiento y Limpieza de Disco
    frame_clean = ctk.CTkFrame(card, fg_color=COLOR_INPUT_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
    frame_clean.pack(fill="x", padx=16, pady=(10, 4))

    ctk.CTkLabel(
        frame_clean,
        text="LIMPIEZA DE DATOS Y ESPACIO EN DISCO",
        font=(FONT_MAIN, 11, "bold"),
        text_color=COLOR_AVISO,
    ).pack(anchor="w", padx=14, pady=(8, 2))

    ctk.CTkLabel(
        frame_clean,
        text="Voizy guarda los modelos descargados, binarios y aceleradores en %LOCALAPPDATA%\\Voizy.\nPuedes eliminar estos archivos para liberar espacio en disco cuando lo desees.",
        font=(FONT_MAIN, 10),
        text_color=COLOR_TEXT_DIM,
        justify="left",
    ).pack(anchor="w", padx=14, pady=(0, 8))

    def _purgar_appdata():
        def _confirmado():
            try:
                import shutil
                if os.path.exists(RUTA_DATOS):
                    for item in os.listdir(RUTA_DATOS):
                        p = os.path.join(RUTA_DATOS, item)
                        try:
                            if os.path.isdir(p):
                                shutil.rmtree(p, ignore_errors=True)
                            else:
                                os.remove(p)
                        except Exception:
                            pass
                mostrar_modal_mensaje(
                    parent,
                    "Datos Eliminados",
                    "Se han eliminado los modelos de IA, aceleradores CUDA y archivos de AppData.\nEspacio en disco liberado correctamente.",
                )
            except Exception as e:
                mostrar_modal_error(parent, "Error", f"No se pudo limpiar AppData: {e}")

        mostrar_modal_confirmacion(
            modal,
            "Eliminar Datos Locales",
            "¿Estás seguro de que deseas eliminar permanentemente todos los modelos de IA, aceleradores CUDA, binarios y configuraciones en %LOCALAPPDATA%\\Voizy?\n\nEsta acción liberará espacio en disco.",
            on_confirm=_confirmado,
        )

    ctk.CTkButton(
        frame_clean,
        text="Liberar Espacio / Borrar todo AppData",
        command=_purgar_appdata,
        fg_color="#7F1D1D",
        hover_color="#DC2626",
        text_color="white",
        font=(FONT_MAIN, 11, "bold"),
        height=28,
        corner_radius=6,
    ).pack(anchor="w", padx=14, pady=(0, 8))

    def _cerrar():
        try:
            modal.grab_release()
            modal.destroy()
        except Exception:
            pass
        parent._modal_activo = None

    modal.protocol("WM_DELETE_WINDOW", _cerrar)

    ctk.CTkButton(
        card,
        text="Cerrar",
        command=_cerrar,
        fg_color=COLOR_MARCA,
        hover_color=COLOR_MARCA_HOVER,
        text_color="black",
        font=(FONT_MAIN, 12, "bold"),
        height=30,
        width=110,
        corner_radius=8,
    ).pack(pady=(6, 4))


class ModelManagerWindow(ctk.CTkToplevel):
    """Gestor de Modelos, Binarios Multimedia y Aceleradores de IA sin scrollbars innecesarios."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        parent._modal_activo = self
        _configurar_toplevel(self, parent, "Gestor de Motores IA", ancho=640, alto=610)

        self.descarga_activa = False
        self.botones = {}
        self.etiquetas_estado = {}

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            card,
            text="MOTORES Y ACELERADORES DE IA",
            font=(FONT_MAIN, 16, "bold"),
            text_color=COLOR_MARCA,
        ).pack(pady=(12, 2))

        ctk.CTkLabel(
            card,
            text="Gestión de descarga local de modelos Faster-Whisper, binarios y aceleración GPU.",
            font=(FONT_MAIN, 11),
            text_color=COLOR_TEXT_DIM,
        ).pack(pady=(0, 10))

        # Contenedor limpio sin scrollbars
        self.frame_lista = ctk.CTkFrame(
            card,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=10,
        )
        self.frame_lista.pack(fill="x", padx=16, pady=(4, 10))

        # Categorías y filas
        self._crear_seccion_titulo("BINARIOS Y ACELERADORES DE SISTEMA")
        self._crear_fila_ffmpeg()
        self._crear_fila_cuda()

        self._crear_seccion_titulo("RECONOCIMIENTO Y SUBTITULOS (WHISPER)")
        self._crear_fila("large-v3")
        self._crear_fila("turbo", es_ultimo=True)

        # Barra de progreso y estado dinámico
        self.frame_progreso = ctk.CTkFrame(card, fg_color="transparent")
        self.frame_progreso.pack(fill="x", padx=18, pady=(4, 6))

        self.lbl_progreso = ctk.CTkLabel(
            self.frame_progreso,
            text="",
            font=(FONT_MAIN, 10, "bold"),
            text_color=COLOR_AVISO,
        )
        self.lbl_progreso.pack(anchor="w", pady=(0, 2))

        self.progress_bar = ctk.CTkProgressBar(
            self.frame_progreso,
            fg_color=COLOR_INPUT_BG,
            progress_color=COLOR_MARCA,
            height=6,
            corner_radius=3,
        )
        self.progress_bar.set(0)

        def _cerrar():
            if self.descarga_activa:
                mostrar_modal_aviso(self, "Descarga en curso", "Espera a que finalice la descarga del componente antes de cerrar.")
                return
            try:
                self.grab_release()
                self.destroy()
            except Exception:
                pass
            parent._modal_activo = None

        self.protocol("WM_DELETE_WINDOW", _cerrar)

        ctk.CTkButton(
            card,
            text="Cerrar",
            command=_cerrar,
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            font=(FONT_MAIN, 12, "bold"),
            height=32,
            width=120,
            corner_radius=8,
        ).pack(side="bottom", pady=(6, 12))

    def _crear_seccion_titulo(self, texto):
        ctk.CTkLabel(
            self.frame_lista,
            text=texto,
            font=(FONT_MAIN, 10, "bold"),
            text_color=COLOR_MARCA,
        ).pack(anchor="w", padx=14, pady=(10, 4))

    def _crear_fila_ffmpeg(self):
        fila = ctk.CTkFrame(self.frame_lista, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
        fila.pack(fill="x", padx=10, pady=2)

        info_frame = ctk.CTkFrame(fila, fg_color="transparent")
        info_frame.pack(side="left", padx=12, pady=5, fill="x", expand=True)

        ctk.CTkLabel(info_frame, text="Motor Multimedia FFmpeg", font=(FONT_MAIN, 11, "bold"), text_color=COLOR_TEXT).pack(anchor="w")
        ctk.CTkLabel(info_frame, text="Procesamiento de vídeo y multiplexado de subtítulos MKV/MP4 (96 MB)", font=(FONT_MAIN, 9), text_color=COLOR_TEXT_DIM).pack(anchor="w")

        lbl_estado = ctk.CTkLabel(info_frame, text="", font=(FONT_MAIN, 9, "bold"), text_color=COLOR_OK)
        lbl_estado.pack(anchor="w")
        self.etiquetas_estado["ffmpeg"] = lbl_estado

        btn = ctk.CTkButton(
            fila,
            text="DESCARGAR",
            width=110,
            height=28,
            corner_radius=6,
            font=(FONT_MAIN, 10, "bold"),
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            command=self._descargar_ffmpeg_click,
        )
        btn.pack(side="right", padx=10, pady=5)
        self.botones["ffmpeg"] = btn
        self._actualizar_estado_ffmpeg()

    def _actualizar_estado_ffmpeg(self):
        btn = self.botones.get("ffmpeg")
        lbl = self.etiquetas_estado.get("ffmpeg")
        if not btn:
            return

        if esta_ffmpeg_instalado():
            btn.configure(text="INSTALADO", state="disabled", fg_color=COLOR_BTN_DARK, text_color=COLOR_TEXT_DIM)
            if lbl:
                lbl.configure(text="Instalado y disponible", text_color=COLOR_OK)
        else:
            btn.configure(text="DESCARGAR", state="normal", fg_color=COLOR_MARCA, hover_color=COLOR_MARCA_HOVER, text_color="black")
            if lbl:
                lbl.configure(text="No descargado (Requerido para procesar vídeo)", text_color=COLOR_AVISO)

    def _descargar_ffmpeg_click(self):
        if self.descarga_activa:
            return
        self.descarga_activa = True
        self.lbl_progreso.configure(text="Descargando motor oficial FFmpeg...", text_color=COLOR_MARCA)
        self.progress_bar.pack(fill="x", pady=(2, 6))
        self.progress_bar.set(0)

        def _worker():
            try:
                def cb(p, msg):
                    self.after(0, self._on_download_progress, p, msg)

                descargar_ffmpeg(progress_callback=cb)
                self.after(0, self._on_download_success, "ffmpeg")
            except Exception as e:
                self.after(0, self._on_download_error, "ffmpeg", str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _crear_fila_cuda(self):
        fila = ctk.CTkFrame(self.frame_lista, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
        fila.pack(fill="x", padx=10, pady=2)

        info_frame = ctk.CTkFrame(fila, fg_color="transparent")
        info_frame.pack(side="left", padx=12, pady=5, fill="x", expand=True)

        ctk.CTkLabel(info_frame, text="Acelerador NVIDIA CUDA 12 (cuBLAS)", font=(FONT_MAIN, 11, "bold"), text_color=COLOR_TEXT).pack(anchor="w")
        ctk.CTkLabel(info_frame, text="Acelera la transcripción y procesamiento hasta 10 veces en GPUs NVIDIA (120 MB)", font=(FONT_MAIN, 9), text_color=COLOR_TEXT_DIM).pack(anchor="w")

        lbl_estado = ctk.CTkLabel(info_frame, text="", font=(FONT_MAIN, 9, "bold"), text_color=COLOR_OK)
        lbl_estado.pack(anchor="w")
        self.etiquetas_estado["cuda"] = lbl_estado

        btn = ctk.CTkButton(
            fila,
            text="DESCARGAR",
            width=110,
            height=28,
            corner_radius=6,
            font=(FONT_MAIN, 10, "bold"),
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            command=self._descargar_cuda_click,
        )
        btn.pack(side="right", padx=10, pady=5)
        self.botones["cuda"] = btn
        self._actualizar_estado_cuda()

    def _actualizar_estado_cuda(self):
        btn = self.botones.get("cuda")
        lbl = self.etiquetas_estado.get("cuda")
        if not btn:
            return

        if esta_cuda_instalado():
            if hay_actualizacion_cuda():
                btn.configure(text="ACTUALIZAR", state="normal", fg_color=COLOR_AVISO, hover_color="#D97706", text_color="black")
                if lbl:
                    lbl.configure(text="Nueva versión disponible", text_color=COLOR_AVISO)
            else:
                btn.configure(text="INSTALADO", state="disabled", fg_color=COLOR_BTN_DARK, text_color=COLOR_TEXT_DIM)
                if lbl:
                    lbl.configure(text="Instalado y activo en GPU", text_color=COLOR_OK)
        else:
            btn.configure(text="DESCARGAR", state="normal", fg_color=COLOR_MARCA, hover_color=COLOR_MARCA_HOVER, text_color="black")
            if lbl:
                lbl.configure(text="No instalado", text_color=COLOR_TEXT_DIM)

    def _descargar_cuda_click(self):
        if self.descarga_activa:
            return
        self.descarga_activa = True
        self.lbl_progreso.configure(text="Descargando paquete de aceleración NVIDIA CUDA 12...", text_color=COLOR_MARCA)
        self.progress_bar.pack(fill="x", pady=(2, 6))
        self.progress_bar.set(0)

        def _worker():
            try:
                def cb(p, msg):
                    self.after(0, self._on_download_progress, p, msg)

                descargar_acelerador_cuda(progress_callback=cb)
                self.after(0, self._on_download_success, "cuda")
            except Exception as e:
                self.after(0, self._on_download_error, "cuda", str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _crear_fila(self, modelo_id, es_ultimo=False):
        info = INFO_MODELOS.get(modelo_id, {})
        fila = ctk.CTkFrame(self.frame_lista, fg_color=COLOR_CARD, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
        fila.pack(fill="x", padx=10, pady=(2, 10) if es_ultimo else 2)

        info_frame = ctk.CTkFrame(fila, fg_color="transparent")
        info_frame.pack(side="left", padx=12, pady=5, fill="x", expand=True)

        nombre_limpio = info.get("label", modelo_id).replace("🌟 ", "").replace("⚡ ", "")
        ctk.CTkLabel(info_frame, text=nombre_limpio, font=(FONT_MAIN, 11, "bold"), text_color=COLOR_TEXT).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"{info.get('descripcion', '')} ({info.get('size', '')})", font=(FONT_MAIN, 9), text_color=COLOR_TEXT_DIM).pack(anchor="w")

        lbl_estado = ctk.CTkLabel(info_frame, text="", font=(FONT_MAIN, 9, "bold"), text_color=COLOR_OK)
        lbl_estado.pack(anchor="w")
        self.etiquetas_estado[modelo_id] = lbl_estado

        btn = ctk.CTkButton(
            fila,
            text="DESCARGAR",
            width=110,
            height=28,
            corner_radius=6,
            font=(FONT_MAIN, 10, "bold"),
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            command=lambda m=modelo_id: self._descargar_click(m),
        )
        btn.pack(side="right", padx=10, pady=5)
        self.botones[modelo_id] = btn
        self._actualizar_estado(modelo_id)

    def _actualizar_estado(self, modelo_id):
        btn = self.botones.get(modelo_id)
        lbl = self.etiquetas_estado.get(modelo_id)
        if not btn:
            return

        if esta_instalado(modelo_id):
            if hay_actualizacion_disponible(modelo_id):
                btn.configure(text="ACTUALIZAR", state="normal", fg_color=COLOR_AVISO, hover_color="#D97706", text_color="black")
                if lbl:
                    lbl.configure(text="Nueva versión disponible", text_color=COLOR_AVISO)
            else:
                btn.configure(text="INSTALADO", state="disabled", fg_color=COLOR_BTN_DARK, text_color=COLOR_TEXT_DIM)
                if lbl:
                    lbl.configure(text="Instalado en local", text_color=COLOR_OK)
        else:
            btn.configure(text="DESCARGAR", state="normal", fg_color=COLOR_MARCA, hover_color=COLOR_MARCA_HOVER, text_color="black")
            if lbl:
                lbl.configure(text="No descargado", text_color=COLOR_TEXT_DIM)

    def _descargar_click(self, modelo_id):
        if self.descarga_activa:
            return
        self.descarga_activa = True
        self.lbl_progreso.configure(text=f"Descargando {modelo_id} desde HuggingFace...", text_color=COLOR_MARCA)
        self.progress_bar.pack(fill="x", pady=(2, 6))
        self.progress_bar.set(0)

        def _worker():
            try:
                def cb(p, msg):
                    self.after(0, self._on_download_progress, p, msg)

                descargar_modelo_hf(modelo_id, progress_callback=cb)
                self.after(0, self._on_download_success, modelo_id)
            except Exception as e:
                self.after(0, self._on_download_error, modelo_id, str(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_download_progress(self, p, msg):
        self.progress_bar.set(p)
        self.lbl_progreso.configure(text=f"{msg} ({int(p*100)}%)")

    def _on_download_success(self, componente_id):
        self.descarga_activa = False
        self.progress_bar.pack_forget()
        self.lbl_progreso.configure(text="Descarga e instalación completada con éxito.", text_color=COLOR_OK)
        if componente_id == "ffmpeg":
            self._actualizar_estado_ffmpeg()
        elif componente_id == "cuda":
            self._actualizar_estado_cuda()
            try:
                self.parent._actualizar_estado_hardware()
            except Exception:
                pass
        else:
            self._actualizar_estado(componente_id)

    def _on_download_error(self, componente_id, error_msg):
        self.descarga_activa = False
        self.progress_bar.pack_forget()
        self.lbl_progreso.configure(text=f"Error al descargar {componente_id}.", text_color=COLOR_ERROR)
        mostrar_modal_error(self, "Error de Descarga", error_msg)
