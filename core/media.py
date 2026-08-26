"""
Gestión de operaciones multimedia y subprocesos de FFmpeg para Voizy Studio.
"""

import os
import sys
import time
import subprocess
from utils.logger import log_exception, leer_ultimas_lineas_log
from utils.helpers import CONTENEDORES_MOV_TEXT
from utils.paths import RUTA_BASE


class MediaProcessor:
    def __init__(self):
        self.proceso_actual = None

    def detener_proceso_actual(self, timeout=2):
        """Detiene de forma segura y limpia el subproceso activo de FFmpeg."""
        proc = self.proceso_actual
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=timeout)
        except Exception as e:
            log_exception("Error al detener subproceso FFmpeg", e)
        finally:
            self.proceso_actual = None

    def incrustar_subtitulos(
        self,
        archivo_seleccionado,
        ruta_srt,
        ruta_final,
        codigo_idioma,
        idioma_seleccionado_texto,
        activar_auto,
        ffmpeg_path,
        cancel_event,
    ):
        """
        Empaqueta el vídeo con la pista de subtítulos sin recodificar vídeo ni audio (-c copy).
        """
        log_ffmpeg = os.path.join(RUTA_BASE, "logs", "ffmpeg_last.log")
        os.makedirs(os.path.dirname(log_ffmpeg), exist_ok=True)

        codec_subs = (
            "mov_text"
            if os.path.splitext(ruta_final)[1].lower() in CONTENEDORES_MOV_TEXT
            else "srt"
        )
        disposition_flag = "default" if bool(activar_auto) else "0"
        flags_ocultos = (
            subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        comando_ffmpeg = [
            ffmpeg_path,
            "-y",
            "-i",
            archivo_seleccionado,
            "-i",
            ruta_srt,
            "-map",
            "0:v?",
            "-map",
            "0:a?",
            "-map",
            "1:0",
            "-c",
            "copy",
            "-c:s",
            codec_subs,
            "-metadata:s:s:0",
            f"language={codigo_idioma}",
            "-metadata:s:s:0",
            f"title={idioma_seleccionado_texto}",
            "-disposition:s:0",
            disposition_flag,
            ruta_final,
        ]

        with open(log_ffmpeg, "w", encoding="utf-8", errors="ignore") as log_file:
            self.proceso_actual = subprocess.Popen(
                comando_ffmpeg,
                stdout=log_file,
                stderr=log_file,
                creationflags=flags_ocultos,
            )

            while self.proceso_actual.poll() is None:
                if cancel_event.is_set():
                    self.detener_proceso_actual()
                    if ruta_final and os.path.exists(ruta_final):
                        try:
                            os.remove(ruta_final)
                        except Exception:
                            pass
                    raise InterruptedError("Proceso cancelado por el usuario.")
                time.sleep(0.25)

        if self.proceso_actual and self.proceso_actual.returncode != 0:
            if ruta_final and os.path.exists(ruta_final):
                try:
                    os.remove(ruta_final)
                except Exception:
                    pass
            detalle = leer_ultimas_lineas_log(log_ffmpeg)
            raise Exception(
                "FFmpeg no pudo empaquetar el archivo final. "
                + (
                    f"Detalle técnico: {detalle}"
                    if detalle
                    else "Revisa el formato del archivo de entrada."
                )
            )
        self.proceso_actual = None
