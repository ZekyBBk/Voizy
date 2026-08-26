"""
Motor de transcripción con Faster-Whisper, optimización de VRAM y generación de subtítulos SRT.
"""

import os
import time
import threading
import ctranslate2
from faster_whisper import WhisperModel

from utils.paths import RUTA_BASE
from utils.logger import log_info, log_exception
from utils.helpers import formato_srt, segmentar_texto_subtitulo
from core.translator import SubtitleTranslator
from core.model_manager import DIR_MODELOS


class AudioTranscriber:
    def __init__(self):
        self.modelo_cargado = None
        self.modelo_nombre_actual = None
        self.lock = threading.Lock()

    def cargar_modelo(self, modelo_id, on_status=None):
        """Carga o reutiliza en memoria el modelo Whisper especificado con aceleración CUDA o fallback automático a CPU."""
        ruta_local = os.path.join(DIR_MODELOS, modelo_id)
        if not os.path.exists(ruta_local):
            ruta_alt = os.path.join(RUTA_BASE, "models", modelo_id)
            if os.path.exists(ruta_alt):
                ruta_local = ruta_alt

        dispositivo = "cpu"
        tipo_calculo = "int8"

        try:
            if ctranslate2.get_cuda_device_count() > 0:
                dispositivo = "cuda"
                tipo_calculo = "float16"
        except Exception:
            dispositivo = "cpu"
            tipo_calculo = "int8"

        with self.lock:
            if (
                self.modelo_cargado is None
                or self.modelo_nombre_actual != modelo_id
            ):
                if on_status:
                    on_status(
                        f"Cargando motor IA ({dispositivo.upper()})..."
                    )

                if self.modelo_cargado is not None:
                    viejo = self.modelo_cargado
                    self.modelo_cargado = None
                    self.modelo_nombre_actual = None
                    del viejo

                log_info(
                    f"Cargando WhisperModel: {ruta_local} en {dispositivo} ({tipo_calculo})"
                )
                try:
                    self.modelo_cargado = WhisperModel(
                        ruta_local,
                        device=dispositivo,
                        compute_type=tipo_calculo,
                        cpu_threads=os.cpu_count() or 4,
                    )
                except Exception as ex_cuda:
                    if dispositivo == "cuda":
                        log_info(f"CUDA no disponible o faltan DLLs del sistema ({ex_cuda}), recurriendo a CPU multihilo...")
                        if on_status:
                            on_status("Cargando motor IA en CPU Multihilo (Optimizado AVX2)...")
                        self.modelo_cargado = WhisperModel(
                            ruta_local,
                            device="cpu",
                            compute_type="int8",
                            cpu_threads=os.cpu_count() or 4,
                        )
                    else:
                        raise ex_cuda

                self.modelo_nombre_actual = modelo_id

        return self.modelo_cargado

    def procesar_transcripcion(
        self,
        archivo_entrada,
        ruta_srt_salida,
        modelo_id,
        codigo_idioma_destino,
        cancel_event,
        progress_callback=None,
        status_callback=None,
    ):
        """
        Ejecuta la transcripción completa, traducción opcional y exportación a archivo SRT.
        """
        modelo = self.cargar_modelo(modelo_id, on_status=status_callback)

        if status_callback:
            status_callback("Iniciando transcripción inteligente...")

        segmentos, info = modelo.transcribe(
            archivo_entrada,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                threshold=0.5,
            ),
            word_timestamps=True,
            temperature=0,
            condition_on_previous_text=True,
            beam_size=5,
        )

        duracion_total = float(getattr(info, "duration", 0) or 0)
        tiempo_inicio = time.time()
        errores_traduccion = 0
        total_bloques = 0

        idioma_detectado = getattr(info, "language", None)
        traductor = None
        if (
            idioma_detectado
            and codigo_idioma_destino
            and idioma_detectado != codigo_idioma_destino
        ):
            traductor = SubtitleTranslator(
                target_lang=codigo_idioma_destino, source_lang="auto"
            )

        with open(ruta_srt_salida, "w", encoding="utf-8") as archivo_srt:
            contador = 1

            for segmento in segmentos:
                if cancel_event.is_set():
                    raise InterruptedError("Proceso cancelado por el usuario.")

                texto_original = (segmento.text or "").strip()
                if not texto_original:
                    continue

                texto_final = texto_original
                if traductor is not None:
                    texto_final, ok = traductor.traducir_texto(texto_original)
                    if not ok:
                        errores_traduccion += 1

                bloques = segmentar_texto_subtitulo(
                    texto_final,
                    segmento.start,
                    segmento.end,
                )

                for inicio_b, fin_b, texto_b in bloques:
                    archivo_srt.write(f"{contador}\n")
                    archivo_srt.write(
                        f"{formato_srt(inicio_b)} --> {formato_srt(fin_b)}\n"
                    )
                    archivo_srt.write(f"{texto_b}\n\n")
                    contador += 1
                    total_bloques += 1

                if duracion_total > 0 and progress_callback:
                    progreso_decimal = min(
                        float(segmento.end) / duracion_total, 1.0
                    )
                    progress_callback(progreso_decimal)

                tiempo_transcurrido = time.time() - tiempo_inicio
                if (
                    duracion_total > 0
                    and tiempo_transcurrido > 0
                    and segmento.end > 0
                    and status_callback
                ):
                    velocidad = segmento.end / tiempo_transcurrido
                    if velocidad > 0:
                        segundos_restantes = max(
                            0, duracion_total - segmento.end
                        )
                        eta_segundos = max(
                            0, int(segundos_restantes / velocidad)
                        )
                        minutos_eta = eta_segundos // 60
                        segs_eta = eta_segundos % 60

                        if minutos_eta > 0:
                            texto_eta = f"Transcribiendo... Tiempo restante: {minutos_eta}m {segs_eta}s"
                        else:
                            texto_eta = f"Transcribiendo... Tiempo restante: {segs_eta}s"

                        status_callback(texto_eta)

        if total_bloques == 0:
            raise Exception("No se detectó voz útil para generar subtítulos.")

        return {
            "total_bloques": total_bloques,
            "idioma_detectado": idioma_detectado,
            "errores_traduccion": errores_traduccion,
            "duracion_total": duracion_total,
        }
