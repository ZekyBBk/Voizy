"""
Sistema centralizado de logging para Voizy.
Almacena registros en %LOCALAPPDATA%\\Voizy\\logs para trazabilidad permanente.
"""

import os
import logging
from utils.paths import RUTA_DATOS

DIR_LOGS = os.path.join(RUTA_DATOS, "logs")
os.makedirs(DIR_LOGS, exist_ok=True)
FILE_LOG = os.path.join(DIR_LOGS, "voizy.log")

logging.basicConfig(
    filename=FILE_LOG,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)


def log_info(mensaje):
    logging.info(mensaje)


def log_warning(mensaje):
    logging.warning(mensaje)


def log_error(mensaje):
    logging.error(mensaje)


def log_exception(contexto, exc):
    logging.exception("%s: %s", contexto, exc)


def leer_ultimas_lineas_log(ruta=None, max_lineas=12):
    """Lee las últimas líneas de un archivo de log para diagnósticos de error."""
    target = ruta if ruta else FILE_LOG
    try:
        if not os.path.isfile(target):
            return ""
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            lineas = f.readlines()
        return "".join(lineas[-max_lineas:]).strip()
    except Exception:
        return ""
