"""
Módulo de resolución de rutas y recursos portables para Voizy.
Gestiona el almacenamiento persistente en %LOCALAPPDATA%\\Voizy para modelos de IA,
configuraciones, binarios y registros, asegurando que nunca se pierdan entre compilaciones.
"""

import os
import sys
import shutil


def obtener_ruta_base():
    """Retorna la ruta base de ejecución de la aplicación."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(directorio_actual) in ["utils", "core", "ui"]:
        return os.path.dirname(directorio_actual)
    return directorio_actual


RUTA_BASE = obtener_ruta_base()


def obtener_ruta_datos():
    """Retorna la ruta permanente en %LOCALAPPDATA%\\Voizy."""
    local_app = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    voizy_data = os.path.join(local_app, "Voizy")
    os.makedirs(voizy_data, exist_ok=True)
    return voizy_data


RUTA_DATOS = obtener_ruta_datos()


def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, compatible con PyInstaller (_MEIPASS, ui/assets o raíz)."""
    base_meipass = getattr(sys, "_MEIPASS", None)
    if base_meipass:
        candidato = os.path.join(base_meipass, relative_path)
        if os.path.exists(candidato):
            return candidato
        candidato_assets = os.path.join(base_meipass, "ui", "assets", relative_path)
        if os.path.exists(candidato_assets):
            return candidato_assets

    candidato_local_assets = os.path.join(RUTA_BASE, "ui", "assets", relative_path)
    if os.path.exists(candidato_local_assets):
        return candidato_local_assets

    candidato_local = os.path.join(RUTA_BASE, relative_path)
    if os.path.exists(candidato_local):
        return candidato_local

    return os.path.join(RUTA_BASE, "ui", "assets", relative_path)


def obtener_ffmpeg_path():
    """Localiza el binario de FFmpeg en AppData/bin, ruta permanente, PATH del sistema o tools/."""
    candidatos = [
        os.path.join(RUTA_DATOS, "bin", "ffmpeg.exe"),
        os.path.join(RUTA_DATOS, "ffmpeg.exe"),
        shutil.which("ffmpeg.exe"),
        shutil.which("ffmpeg"),
        os.path.join(RUTA_BASE, "tools", "ffmpeg.exe"),
        os.path.join(RUTA_BASE, "ffmpeg.exe"),
        resource_path("ffmpeg.exe"),
    ]
    for c in candidatos:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    return None
