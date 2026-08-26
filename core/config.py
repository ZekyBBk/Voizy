"""
Gestión de configuración persistente y metadatos de modelos para Voizy Studio.
Implementa escrituras atómicas protegidas contra fallos de alimentación o cierres repentinos.
"""

import os
import json
import threading
from utils.paths import RUTA_BASE, RUTA_DATOS
from utils.logger import log_exception

FILE_CONFIG = os.path.join(RUTA_DATOS, "config.json")
_config_lock = threading.Lock()

MAPA_IDIOMAS = {
    "Español": "es",
    "Inglés": "en",
    "Francés": "fr",
    "Alemán": "de",
    "Italiano": "it",
    "Portugués": "pt",
    "Ruso": "ru",
    "Japonés": "ja",
    "Chino": "zh",
}

MAPA_MODELOS = {
    "Large V3 (Máxima Calidad y Precisión - Recomendado)": "large-v3",
    "Turbo (Rápido y Ligero - Buen equilibrio)": "turbo",
}

CARPETAS_MODELOS = {
    "turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
    "large-v3": "Systran/faster-whisper-large-v3",
}

REEMPLAZOS_GLOSARIO = {
    "g p t": "GPT",
    "chat gpt": "ChatGPT",
    "chatgpt": "ChatGPT",
    "open ai": "OpenAI",
    "openai": "OpenAI",
    "whisper": "Whisper",
    "voizy": "Voizy",
}


def _leer_config():
    """Lee el archivo config.json de forma segura."""
    if not os.path.exists(FILE_CONFIG):
        return {}
    try:
        with open(FILE_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _guardar_config(data):
    """Guarda el archivo config.json atómicamente."""
    with _config_lock:
        try:
            os.makedirs(os.path.dirname(FILE_CONFIG), exist_ok=True)
            temp_file = FILE_CONFIG + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            if os.path.exists(FILE_CONFIG):
                os.replace(temp_file, FILE_CONFIG)
            else:
                os.rename(temp_file, FILE_CONFIG)
        except Exception as e:
            log_exception("Error al guardar config.json", e)


cargar_configuracion = _leer_config
guardar_configuracion = _guardar_config


def obtener_ajustes_guardados():
    """Retorna los últimos ajustes guardados por el usuario."""
    cfg = _leer_config()
    return cfg.get("ultimo_proceso", {})


def guardar_ajustes_ultimo_proceso(
    idioma,
    modelo,
    activar_auto,
    convertir_mkv,
    conservar_srt,
):
    """Guarda las preferencias del usuario para futuras sesiones."""
    cfg = _leer_config()
    cfg["ultimo_proceso"] = {
        "idioma": idioma,
        "modelo": modelo,
        "activar_auto": activar_auto,
        "convertir_mkv": convertir_mkv,
        "conservar_srt": conservar_srt,
    }
    _guardar_config(cfg)


def obtener_modelos_meta():
    """Retorna la tabla de versiones y metadatos de modelos de HuggingFace."""
    cfg = _leer_config()
    return cfg.get("modelos_meta", {})


def obtener_meta_modelo(modelo_id):
    """Retorna los metadatos de un modelo específico."""
    metas = obtener_modelos_meta()
    return metas.get(modelo_id, {})


def guardar_meta_modelo(
    modelo_id,
    repo=None,
    revision_instalada=None,
    revision_remota_vista=None,
    auto_update=None,
):
    """Actualiza metadatos de versión y hash de un modelo."""
    cfg = _leer_config()
    if "modelos_meta" not in cfg:
        cfg["modelos_meta"] = {}

    m = cfg["modelos_meta"].get(modelo_id, {})
    if repo is not None:
        m["repo"] = repo
    if revision_instalada is not None:
        m["revision_instalada"] = revision_instalada
    if revision_remota_vista is not None:
        m["revision_remota_vista"] = revision_remota_vista
    if auto_update is not None:
        m["auto_update"] = auto_update

    cfg["modelos_meta"][modelo_id] = m
    _guardar_config(cfg)
