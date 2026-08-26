"""
Punto de entrada principal de la aplicación Voizy Studio.
Inicializa variables de entorno, directorios de DLLs de CUDA y dependencias multimedia.
Garantiza ejecución sin consolas emergentes y soporte completo para multiprocessing congelado.
"""

import os
import sys
import multiprocessing

# Soporte fundamental para PyInstaller en Windows con multiprocessing (evita bucles infinitos)
multiprocessing.freeze_support()

# Asegurar que la raíz del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Voizy.Studio.App")
    except Exception:
        pass

from utils.paths import RUTA_DATOS, obtener_ffmpeg_path

# 1. Registrar directorios de DLLs nativas de CUDA 12 y binarios en Windows
app_dir = getattr(sys, "_MEIPASS", BASE_DIR)
if hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(app_dir)
    except Exception:
        pass

# Registrar carpeta permanente de acelerador CUDA en AppData
DIR_CUDA = os.path.join(RUTA_DATOS, "cuda")
if os.path.isdir(DIR_CUDA):
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(DIR_CUDA)
        except Exception:
            pass
    if DIR_CUDA not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{DIR_CUDA};{os.environ.get('PATH', '')}"

# En desarrollo local: añadir subcarpetas de nvidia
nv_dir = os.path.join(BASE_DIR, "env", "Lib", "site-packages", "nvidia")
if os.path.isdir(nv_dir):
    for sub in os.listdir(nv_dir):
        bin_path = os.path.join(nv_dir, sub, "bin")
        if os.path.isdir(bin_path):
            try:
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(bin_path)
                os.environ["PATH"] = f"{bin_path};{os.environ.get('PATH', '')}"
            except Exception:
                pass

if app_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{app_dir};{os.environ.get('PATH', '')}"

# 2. Configurar FFmpeg en PATH
ffmpeg_bin = obtener_ffmpeg_path()
if ffmpeg_bin and os.path.isfile(ffmpeg_bin):
    ffmpeg_dir = os.path.dirname(os.path.abspath(ffmpeg_bin))
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{ffmpeg_dir};{os.environ.get('PATH', '')}"

from ui.main_window import VoizyMainWindow


def main():
    app = VoizyMainWindow()
    app.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
