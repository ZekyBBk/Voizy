"""
Interfaz Gráfica Principal de Voizy Studio (Dark Modern & Neon Lime).
Diseño profesional y limpio sin emojis, con soporte para Whisper Large-V3 y Turbo,
traducción multilingüe, incrustación en MKV/MP4 y aceleración NVIDIA CUDA 12.
"""

import os
import sys
import threading
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    try:
        from TkinterDnD2 import TkinterDnD, DND_FILES
    except ImportError:
        import tkinterdnd2
        TkinterDnD = tkinterdnd2.TkinterDnD
        DND_FILES = tkinterdnd2.DND_FILES

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
from ui.modals import (
    mostrar_modal_exito,
    mostrar_modal_info,
    mostrar_modal_error,
    mostrar_modal_aviso,
    mostrar_modal_confirmacion,
    ModelManagerWindow,
    forzar_icono_modal,
)
from utils.paths import resource_path, obtener_ffmpeg_path, RUTA_BASE
from utils.logger import log_exception, log_info
from utils.helpers import (
    es_video,
    es_audio,
    generar_ruta_sin_colision,
    reproducir_sonido_exito,
    aplicar_tema_oscuro_barra_titulo,
    tiene_gpu_nvidia,
    CONTENEDORES_SUBS_COMPATIBLES,
)
from core.config import (
    MAPA_IDIOMAS,
    MAPA_MODELOS,
    obtener_ajustes_guardados,
    guardar_ajustes_ultimo_proceso,
)
from core.transcriber import AudioTranscriber
from core.media import MediaProcessor
from core.model_manager import esta_instalado, esta_cuda_instalado, INFO_MODELOS


class VoizyMainWindow(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(NOMBRE_APP)
        self.configure(fg_color=COLOR_BG)

        # Dimensiones optimizadas para ajuste perfecto
        ancho, alto = 840, 650
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, int((screen_w / 2) - (ancho / 2)))
        y = max(0, int((screen_h / 2) - (alto / 2) - 15))
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.resizable(False, False)

        ruta_icono = resource_path("voizy.ico")
        if os.path.isfile(ruta_icono):
            try:
                self.iconbitmap(ruta_icono)
            except Exception:
                pass

        aplicar_tema_oscuro_barra_titulo(self, COLOR_BG, COLOR_TEXT)

        self.transcriber = AudioTranscriber()
        self.media_processor = MediaProcessor()
        self.cancel_event = threading.Event()
        self.procesando = False
        self.ventana_modelos = None

        self.origen_var = ctk.StringVar()
        self.destino_var = ctk.StringVar()
        self.idioma_var = ctk.StringVar(value="Español")
        self.modelo_var = ctk.StringVar(value="Large V3 (Máxima Calidad y Precisión - Recomendado)")
        self.activar_auto_var = ctk.IntVar(value=1)
        self.convertir_mkv_var = ctk.IntVar(value=1)
        self.conservar_srt_var = ctk.IntVar(value=1)

        self._construir_ui()
        self._cargar_ajustes_guardados()
        self._actualizar_estado_hardware()

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._al_soltar_archivo)
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar_app)

        self.after(1500, self._iniciar_comprobacion_actualizaciones)

    def _actualizar_estado_hardware(self):
        """Actualiza el mensaje de estado de hardware (GPU NVIDIA CUDA / CPU)."""
        try:
            if esta_cuda_instalado():
                import ctranslate2
                if ctranslate2.get_cuda_device_count() > 0:
                    self.lbl_estado.configure(
                        text="Voizy Studio - Aceleración GPU NVIDIA CUDA activa",
                        text_color=COLOR_MARCA,
                    )
                    return
            if tiene_gpu_nvidia():
                self.lbl_estado.configure(
                    text="GPU NVIDIA detectada - Acelerador CUDA 12 disponible para instalar",
                    text_color=COLOR_AVISO,
                )
            else:
                self.lbl_estado.configure(
                    text="Voizy Studio - Modo CPU Multihilo",
                    text_color=COLOR_TEXT_DIM,
                )
        except Exception:
            self.lbl_estado.configure(
                text="Voizy Studio - Modo CPU Multihilo",
                text_color=COLOR_TEXT_DIM,
            )

    def _construir_ui(self):
        # -------------------------------------------------------------
        # 1. ENCABEZADO CON BOTONES SUPERIORES Y LOGO CENTRAL
        # -------------------------------------------------------------
        frame_superior = ctk.CTkFrame(self, fg_color="transparent")
        frame_superior.pack(pady=(8, 0), padx=30, fill="x")

        btn_box = ctk.CTkFrame(frame_superior, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="i",
            width=32,
            height=32,
            corner_radius=16,
            font=(FONT_MAIN, 15, "bold", "italic"),
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            command=lambda: mostrar_modal_info(self),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="MOTORES IA",
            fg_color=COLOR_BTN_DARK,
            hover_color=COLOR_BTN_DARK_HOVER,
            border_width=1,
            border_color=COLOR_MARCA,
            text_color=COLOR_MARCA,
            font=(FONT_MAIN, 11, "bold"),
            height=32,
            corner_radius=7,
            command=self._abrir_gestor_modelos,
        ).pack(side="left", padx=4)

        # Logo central de Voizy (Más grande y posicionado arriba)
        ruta_logo = resource_path("voizy_logo.png")
        if os.path.isfile(ruta_logo):
            try:
                img = Image.open(ruta_logo)
                w, h = img.size
                nh = 52
                nw = int((w / h) * nh)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(nw, nh))
                ctk.CTkLabel(self, image=ctk_img, text="").pack(pady=(0, 6))
            except Exception:
                ctk.CTkLabel(
                    self,
                    text="VOIZY STUDIO",
                    font=(FONT_MAIN, 28, "bold"),
                    text_color=COLOR_MARCA,
                ).pack(pady=(4, 4))
        else:
            ctk.CTkLabel(
                self,
                text="VOIZY STUDIO",
                font=(FONT_MAIN, 28, "bold"),
                text_color=COLOR_MARCA,
            ).pack(pady=(4, 4))

        # -------------------------------------------------------------
        # 2. RUTAS (ORIGEN Y DESTINO)
        # -------------------------------------------------------------
        frame_rutas = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12,
        )
        frame_rutas.pack(pady=4, padx=30, fill="x")

        # Origen
        fila_origen = ctk.CTkFrame(frame_rutas, fg_color="transparent")
        fila_origen.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(
            fila_origen,
            text="Origen:",
            width=70,
            anchor="w",
            font=(FONT_MAIN, 12, "bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left")
        ctk.CTkEntry(
            fila_origen,
            textvariable=self.origen_var,
            placeholder_text="Selecciona o arrastra tu archivo multimedia...",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            text_color=COLOR_TEXT,
            height=32,
            corner_radius=7,
        ).pack(side="left", fill="x", expand=True, padx=8)
        ctk.CTkButton(
            fila_origen,
            text="Buscar",
            command=self._buscar_origen,
            width=85,
            height=32,
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            font=(FONT_MAIN, 11, "bold"),
            corner_radius=7,
        ).pack(side="right")

        # Destino
        fila_dest = ctk.CTkFrame(frame_rutas, fg_color="transparent")
        fila_dest.pack(fill="x", padx=16, pady=(4, 10))

        ctk.CTkLabel(
            fila_dest,
            text="Destino:",
            width=70,
            anchor="w",
            font=(FONT_MAIN, 12, "bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left")
        ctk.CTkEntry(
            fila_dest,
            textvariable=self.destino_var,
            placeholder_text="Carpeta de exportación...",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            text_color=COLOR_TEXT,
            height=32,
            corner_radius=7,
        ).pack(side="left", fill="x", expand=True, padx=8)
        ctk.CTkButton(
            fila_dest,
            text="Elegir",
            command=self._buscar_destino,
            width=85,
            height=32,
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            font=(FONT_MAIN, 11, "bold"),
            corner_radius=7,
        ).pack(side="right")

        # -------------------------------------------------------------
        # 3. AJUSTES Y CONFIGURACIÓN
        # -------------------------------------------------------------
        frame_ajustes = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12,
        )
        frame_ajustes.pack(pady=4, padx=30, fill="x")
        frame_ajustes.grid_columnconfigure(0, weight=1)
        frame_ajustes.grid_columnconfigure(1, weight=1)

        # Fila 1: Idioma Subtítulos y Motor Whisper
        ctk.CTkLabel(
            frame_ajustes,
            text="Idioma subtítulos:",
            font=(FONT_MAIN, 12, "bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, pady=(10, 2), padx=20, sticky="w")

        ctk.CTkLabel(
            frame_ajustes,
            text="Motor Whisper:",
            font=(FONT_MAIN, 12, "bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=1, pady=(10, 2), padx=20, sticky="w")

        self.combo_idioma = ctk.CTkComboBox(
            frame_ajustes,
            values=list(MAPA_IDIOMAS.keys()),
            variable=self.idioma_var,
            state="readonly",
            height=32,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            button_color=COLOR_BTN_DARK,
            button_hover_color=COLOR_BTN_DARK_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_BTN_DARK_HOVER,
            dropdown_text_color=COLOR_TEXT,
            corner_radius=7,
        )
        self.combo_idioma.grid(row=1, column=0, pady=(0, 8), padx=20, sticky="ew")

        self.combo_modelo = ctk.CTkComboBox(
            frame_ajustes,
            values=list(MAPA_MODELOS.keys()),
            variable=self.modelo_var,
            state="readonly",
            height=32,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_CARD_BORDER,
            button_color=COLOR_BTN_DARK,
            button_hover_color=COLOR_BTN_DARK_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_BTN_DARK_HOVER,
            dropdown_text_color=COLOR_TEXT,
            corner_radius=7,
        )
        self.combo_modelo.grid(row=1, column=1, pady=(0, 8), padx=20, sticky="ew")

        # Fila 2: Checkboxes Verticales Centrados
        self.frame_checks = ctk.CTkFrame(frame_ajustes, fg_color="transparent")
        self.frame_checks.grid(row=2, column=0, columnspan=2, pady=(4, 12), padx=20, sticky="ew")

        self.frame_checks_center = ctk.CTkFrame(self.frame_checks, fg_color="transparent")
        self.frame_checks_center.pack(anchor="center")

        self.chk_auto = ctk.CTkCheckBox(
            self.frame_checks_center,
            text="Activar subtítulos automáticamente al reproducir",
            variable=self.activar_auto_var,
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            checkmark_color="black",
            text_color=COLOR_TEXT,
            font=(FONT_MAIN, 11),
        )
        self.chk_auto.pack(anchor="w", pady=2)

        self.chk_mkv = ctk.CTkCheckBox(
            self.frame_checks_center,
            text="Convertir a contenedor MKV (Máxima compatibilidad)",
            variable=self.convertir_mkv_var,
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            checkmark_color="black",
            text_color=COLOR_TEXT,
            font=(FONT_MAIN, 11),
        )
        self.chk_mkv.pack(anchor="w", pady=2)

        self.chk_srt = ctk.CTkCheckBox(
            self.frame_checks_center,
            text="Conservar archivo .srt independiente",
            variable=self.conservar_srt_var,
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            checkmark_color="black",
            text_color=COLOR_TEXT,
            font=(FONT_MAIN, 11),
        )
        self.chk_srt.pack(anchor="w", pady=2)

        # -------------------------------------------------------------
        # 4. PROGRESO Y ACCIONES
        # -------------------------------------------------------------
        frame_progreso = ctk.CTkFrame(
            self,
            fg_color=COLOR_CARD,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12,
        )
        frame_progreso.pack(pady=4, padx=30, fill="x")

        self.lbl_estado = ctk.CTkLabel(
            frame_progreso,
            text="Iniciando Voizy Studio...",
            font=(FONT_MAIN, 12, "bold"),
            text_color=COLOR_TEXT,
        )
        self.lbl_estado.pack(pady=(10, 2))

        self.progressbar = ctk.CTkProgressBar(
            frame_progreso,
            height=9,
            progress_color=COLOR_MARCA,
            fg_color=COLOR_INPUT_BG,
            corner_radius=5,
        )
        self.progressbar.set(0)
        self.progressbar.pack(fill="x", padx=25, pady=4)

        self.lbl_percent = ctk.CTkLabel(
            frame_progreso,
            text="0%",
            font=(FONT_MAIN, 12, "bold"),
            text_color=COLOR_MARCA,
        )
        self.lbl_percent.pack(pady=(0, 3))

        self.btn_procesar = ctk.CTkButton(
            frame_progreso,
            text="INICIAR PROCESAMIENTO",
            font=(FONT_MAIN, 14, "bold"),
            height=42,
            fg_color=COLOR_MARCA,
            hover_color=COLOR_MARCA_HOVER,
            text_color="black",
            corner_radius=9,
            command=self._iniciar_proceso,
        )
        self.btn_procesar.pack(fill="x", padx=25, pady=(3, 12))

        self.btn_cancelar = ctk.CTkButton(
            frame_progreso,
            text="CANCELAR OPERACION",
            font=(FONT_MAIN, 14, "bold"),
            height=42,
            fg_color=COLOR_ERROR,
            hover_color="#DC2626",
            text_color="white",
            corner_radius=9,
            command=self._cancelar_proceso,
        )

        # -------------------------------------------------------------
        # 5. PIE DE PÁGINA
        # -------------------------------------------------------------
        ctk.CTkLabel(
            self,
            text=f"VOIZY STUDIO v{VERSION_APP} - MOTOR FASTER-WHISPER & ACELERACIÓN GPU NVIDIA CUDA",
            font=(FONT_MAIN, 9, "bold"),
            text_color=COLOR_TEXT_DIM,
        ).pack(side="bottom", pady=(4, 8))

    def _buscar_origen(self):
        tipos = [
            ("Archivos multimedia", "*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.m4a *.flac"),
            ("Todos los archivos", "*.*"),
        ]
        ruta = filedialog.askopenfilename(filetypes=tipos)
        if ruta:
            self.origen_var.set(ruta)
            if not self.destino_var.get():
                self.destino_var.set(os.path.dirname(ruta))

    def _buscar_destino(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.destino_var.set(ruta)

    def _al_soltar_archivo(self, event):
        archivo = event.data.strip("{}")
        if os.path.isfile(archivo):
            self.origen_var.set(archivo)
            if not self.destino_var.get():
                self.destino_var.set(os.path.dirname(archivo))

    def _abrir_gestor_modelos(self):
        if self.ventana_modelos is None or not self.ventana_modelos.winfo_exists():
            self.ventana_modelos = ModelManagerWindow(self)
        else:
            self.ventana_modelos.lift()
            self.ventana_modelos.focus_force()

    def _iniciar_comprobacion_actualizaciones(self):
        def _worker():
            try:
                from core.model_manager import comprobar_todas_las_actualizaciones
                updates = comprobar_todas_las_actualizaciones()
                if updates:
                    self.after(0, self._notificar_actualizaciones_disponibles, updates)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _notificar_actualizaciones_disponibles(self, updates):
        items_texto = "\n".join([f"- {u['nombre']}" for u in updates])
        mensaje = f"Se han detectado nuevas versiones disponibles para:\n\n{items_texto}\n\n¿Deseas abrir el Gestor de Motores IA para actualizar ahora?"
        mostrar_modal_confirmacion(
            self,
            "Actualizaciones de IA Disponibles",
            mensaje,
            on_confirm=self._abrir_gestor_modelos,
        )

    def _cargar_ajustes_guardados(self):
        cfg = obtener_ajustes_guardados()
        if cfg:
            self.idioma_var.set(cfg.get("idioma", "Español"))
            self.modelo_var.set(cfg.get("modelo", "Large V3 (Máxima Calidad y Precisión - Recomendado)"))
            self.activar_auto_var.set(cfg.get("activar_auto", 1))
            self.convertir_mkv_var.set(cfg.get("convertir_mkv", 1))
            self.conservar_srt_var.set(cfg.get("conservar_srt", 1))

    def _guardar_ajustes_actuales(self):
        guardar_ajustes_ultimo_proceso(
            idioma=self.idioma_var.get(),
            modelo=self.modelo_var.get(),
            activar_auto=self.activar_auto_var.get(),
            convertir_mkv=self.convertir_mkv_var.get(),
            conservar_srt=self.conservar_srt_var.get(),
        )

    def _update_progress(self, p):
        p = max(0.0, min(1.0, float(p)))
        self.progressbar.set(p)
        self.lbl_percent.configure(text=f"{int(p * 100)}%")

    def _update_status(self, texto, color=COLOR_TEXT):
        self.lbl_estado.configure(text=texto, text_color=color)

    def _reset_ui_after_process(self):
        self.btn_cancelar.pack_forget()
        self.btn_procesar.pack(fill="x", padx=25, pady=(3, 12))
        self.procesando = False
        self._actualizar_estado_hardware()

    def _limpiar_campos(self):
        self.origen_var.set("")
        self.progressbar.set(0)
        self.lbl_percent.configure(text="0%")
        self._actualizar_estado_hardware()

    def _iniciar_proceso(self):
        archivo = self.origen_var.get().strip()
        destino = self.destino_var.get().strip()

        if not archivo or not os.path.isfile(archivo):
            self.lbl_estado.configure(
                text="Selecciona un archivo de vídeo o audio para comenzar.", text_color=COLOR_AVISO
            )
            mostrar_modal_aviso(
                self, "Archivo requerido", "Por favor, selecciona un archivo de vídeo o audio válido antes de iniciar el procesamiento."
            )
            return

        if not destino or not os.path.isdir(destino):
            destino = os.path.dirname(archivo)
            self.destino_var.set(destino)

        # Comprobar si el equipo tiene GPU NVIDIA y sugerir descarga de CUDA
        if tiene_gpu_nvidia() and not esta_cuda_instalado():
            def _ir_a_descargar_cuda():
                self._abrir_gestor_modelos()

            mostrar_modal_confirmacion(
                self,
                "GPU NVIDIA Detectada",
                "Se ha detectado una tarjeta gráfica NVIDIA en tu equipo, pero el acelerador NVIDIA CUDA 12 no está instalado todavía.\n\nInstalar CUDA te permitirá procesar hasta 10 veces más rápido por GPU.\n\n¿Deseas abrir el Gestor de Motores IA para descargarlo ahora?",
                on_confirm=_ir_a_descargar_cuda,
            )
            return

        modelo_texto = self.modelo_var.get()
        modelo_id = MAPA_MODELOS.get(modelo_texto, "large-v3")

        # Comprobar Whisper
        if not esta_instalado(modelo_id):
            self.lbl_estado.configure(
                text=f"El motor Whisper '{modelo_texto}' requiere descarga previa.", text_color=COLOR_AVISO
            )
            mostrar_modal_confirmacion(
                self,
                "Modelo no instalado",
                f"El motor de IA '{modelo_texto}' no está descargado en este equipo.\n\n¿Deseas abrir el Gestor de Modelos para descargarlo ahora?",
                on_confirm=self._abrir_gestor_modelos,
            )
            return

        ffmpeg_bin = obtener_ffmpeg_path()
        if not ffmpeg_bin:
            self.lbl_estado.configure(
                text="El motor multimedia FFmpeg requiere descarga previa.", text_color=COLOR_AVISO
            )
            def _ir_a_descargar_ffmpeg():
                self._abrir_gestor_modelos()

            mostrar_modal_confirmacion(
                self,
                "FFmpeg Requerido",
                "Para poder incrustar los subtítulos y procesar los archivos multimedia se requiere el motor FFmpeg.\n\n¿Deseas abrir el Gestor de Motores IA para descargarlo ahora automáticamente?",
                on_confirm=_ir_a_descargar_ffmpeg,
            )
            return

        self._guardar_ajustes_actuales()
        self.procesando = True
        self.cancel_event.clear()

        self.btn_procesar.pack_forget()
        self.btn_cancelar.pack(fill="x", padx=25, pady=(3, 12))
        self.progressbar.set(0)
        self.lbl_percent.configure(text="0%")
        self.lbl_estado.configure(
            text="Iniciando motor de procesamiento...", text_color=COLOR_TEXT
        )

        threading.Thread(
            target=self._worker_procesamiento_unificado,
            args=(archivo, destino, modelo_id, ffmpeg_bin),
            daemon=True,
        ).start()

    def _worker_procesamiento_unificado(self, archivo, carpeta_destino, modelo_id, ffmpeg_bin):
        """Flujo de trabajo unificado: Transcripción con Whisper + Traducción + Incrustación de Subtítulos."""
        input_video = es_video(archivo)
        input_audio = es_audio(archivo)

        codigo_idioma_subs = MAPA_IDIOMAS.get(self.idioma_var.get(), "es")
        idioma_subs_texto = self.idioma_var.get()

        nombre_base, ext_orig = os.path.splitext(os.path.basename(archivo))
        carpeta_export = os.path.join(carpeta_destino, "Voizy_Exportados")
        os.makedirs(carpeta_export, exist_ok=True)

        ruta_srt = generar_ruta_sin_colision(
            carpeta_export, nombre_base, f"_subs_{codigo_idioma_subs}", ".srt"
        )

        try:
            def on_progress(p):
                self.after(0, self._update_progress, p)

            def on_status(t):
                self.after(0, self._update_status, t, COLOR_TEXT)

            # 1. Transcripción y Subtitulado
            self.transcriber.procesar_transcripcion(
                archivo_entrada=archivo,
                ruta_srt_salida=ruta_srt,
                modelo_id=modelo_id,
                codigo_idioma_destino=codigo_idioma_subs,
                cancel_event=self.cancel_event,
                progress_callback=lambda p: on_progress(p * 0.92),
                status_callback=on_status,
            )

            if input_audio:
                self.after(0, self._update_progress, 1.0)
                self.after(0, self._update_status, "Transcripción completada al 100%", COLOR_OK)
                reproducir_sonido_exito()
                self.after(0, self._reset_ui_after_process)
                mostrar_modal_exito(
                    self,
                    carpeta_export,
                    "Transcripción de audio completada con éxito.\nArchivo .srt generado.",
                    on_reset=self._limpiar_campos,
                )
                return

            ext_salida = ".mkv" if self.convertir_mkv_var.get() == 1 else ext_orig.lower()
            if ext_salida not in CONTENEDORES_SUBS_COMPATIBLES:
                ext_salida = ".mkv"

            ruta_final = generar_ruta_sin_colision(
                carpeta_export, nombre_base, f"_{codigo_idioma_subs}", ext_salida
            )

            # 2. Muxing final (Vídeo original + subtítulos sin recodificación)
            on_status("Incrustando subtítulos en el archivo multimedia...")
            self.media_processor.incrustar_subtitulos(
                archivo_seleccionado=archivo,
                ruta_srt=ruta_srt,
                ruta_final=ruta_final,
                codigo_idioma=codigo_idioma_subs,
                idioma_seleccionado_texto=idioma_subs_texto,
                activar_auto=self.activar_auto_var.get(),
                ffmpeg_path=ffmpeg_bin,
                cancel_event=self.cancel_event,
            )

            if self.conservar_srt_var.get() == 0 and os.path.exists(ruta_srt):
                try:
                    os.remove(ruta_srt)
                except Exception:
                    pass

            self.after(0, self._update_progress, 1.0)
            self.after(0, self._update_status, "Subtitulado completado con éxito al 100%", COLOR_OK)
            reproducir_sonido_exito()
            self.after(0, self._reset_ui_after_process)

            mostrar_modal_exito(
                self,
                carpeta_export,
                "Subtitulado inteligente generado e incrustado con éxito.\nVídeo original preservado 1:1 sin pérdida de calidad.",
                on_reset=self._limpiar_campos,
            )

        except InterruptedError:
            self.after(
                0, self._update_status, "Proceso cancelado por el usuario.", COLOR_ERROR
            )
            self.after(0, self._reset_ui_after_process)
        except Exception as e:
            log_exception("Error en procesamiento", e)
            self.after(0, self._update_status, f"Error: {e}", COLOR_ERROR)
            self.after(0, self._reset_ui_after_process)
        finally:
            self.procesando = False

    def _cancelar_proceso(self):
        if self.procesando:
            self.cancel_event.set()
            self.media_processor.detener_proceso_actual()
            self.lbl_estado.configure(
                text="Cancelando proceso...", text_color=COLOR_AVISO
            )

    def _al_cerrar_app(self):
        if self.procesando:
            def _confirmar_salida():
                self.cancel_event.set()
                self.media_processor.detener_proceso_actual()
                self.destroy()

            mostrar_modal_confirmacion(
                self,
                "Salir de Voizy",
                "Hay una operación en curso. Si sales ahora, el proceso se cancelará.\n\n¿Deseas salir?",
                on_confirm=_confirmar_salida,
            )
            return

        self.destroy()

    def run(self):
        self.mainloop()
