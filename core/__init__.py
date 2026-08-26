"""
Módulo core de procesamiento, configuración, modelos y subtitulado de Voizy Studio.
"""

from .config import (
    MAPA_IDIOMAS,
    MAPA_MODELOS,
    CARPETAS_MODELOS,
    cargar_configuracion,
    guardar_configuracion,
    obtener_ajustes_guardados,
    guardar_ajustes_ultimo_proceso,
)
from .transcriber import AudioTranscriber
from .translator import SubtitleTranslator
from .media import MediaProcessor
from .model_manager import (
    INFO_MODELOS,
    DIR_MODELOS,
    esta_instalado,
    descargar_modelo_huggingface,
    eliminar_modelo_local,
)
