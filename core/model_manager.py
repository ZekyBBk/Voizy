"""
Gestor de descarga, verificación y actualización de modelos de IA, aceleradores CUDA y binarios multimedia desde HuggingFace/PyPI/Gyan para Voizy Studio.
Almacena y preserva los modelos en %LOCALAPPDATA%\\Voizy\\models, aceleradores en %LOCALAPPDATA%\\Voizy\\cuda y binarios en %LOCALAPPDATA%\\Voizy\\bin.
"""

import os
import shutil
import time
import zipfile
import requests
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import snapshot_download, HfApi

from utils.paths import RUTA_BASE, RUTA_DATOS
from utils.logger import log_exception, log_info, log_warning
from core.config import (
    CARPETAS_MODELOS,
    obtener_meta_modelo,
    guardar_meta_modelo,
    obtener_modelos_meta,
)

DIR_MODELOS = os.path.join(RUTA_DATOS, "models")
DIR_CUDA = os.path.join(RUTA_DATOS, "cuda")
DIR_BIN = os.path.join(RUTA_DATOS, "bin")
os.makedirs(DIR_MODELOS, exist_ok=True)
os.makedirs(DIR_CUDA, exist_ok=True)
os.makedirs(DIR_BIN, exist_ok=True)

INFO_MODELOS = {
    "large-v3": {
        "label": "Large V3 (Máxima Calidad - Recomendado)",
        "categoria": "whisper",
        "descripcion": "Máxima precisión en reconocimiento y subtítulos multilingües.",
        "repo": "Systran/faster-whisper-large-v3",
        "size": "3.0 GB",
        "archivos": [
            "config.json",
            "preprocessor_config.json",
            "tokenizer.json",
            "vocabulary.json",
            "model.bin",
        ],
    },
    "turbo": {
        "label": "Turbo (Rápido y Ligero - Buen equilibrio)",
        "categoria": "whisper",
        "descripcion": "Velocidad 4x superior con alta calidad de transcripción.",
        "repo": "deepdml/faster-whisper-large-v3-turbo-ct2",
        "size": "1.5 GB",
        "archivos": [
            "config.json",
            "preprocessor_config.json",
            "tokenizer.json",
            "vocabulary.json",
            "model.bin",
        ],
    },
}

hf_api = HfApi()


def esta_ffmpeg_instalado():
    """Verifica si el binario ffmpeg.exe está instalado y accesible."""
    from utils.paths import obtener_ffmpeg_path
    return obtener_ffmpeg_path() is not None


def descargar_ffmpeg(progress_callback=None):
    """
    Descarga el binario oficial FFmpeg release essentials para Windows
    y extrae ffmpeg.exe directamente en DIR_BIN (%LOCALAPPDATA%\\Voizy\\bin\\ffmpeg.exe).
    """
    os.makedirs(DIR_BIN, exist_ok=True)
    if progress_callback:
        progress_callback(0.05, "Iniciando conexión para descargar FFmpeg...")

    url_zip = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    tmp_zip = os.path.join(DIR_BIN, "ffmpeg_download.tmp")

    log_info(f"Descargando FFmpeg oficial desde {url_zip} a {tmp_zip}")
    try:
        with requests.get(url_zip, stream=True, timeout=30, headers={"User-Agent": "Voizy-App/1.0"}) as resp:
            resp.raise_for_status()
            total_bytes = int(resp.headers.get("content-length", 0))
            descargado = 0
            chunk_size = 2 * 1024 * 1024  # 2 MB

            with open(tmp_zip, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        descargado += len(chunk)
                        if total_bytes > 0 and progress_callback:
                            pct = (descargado / total_bytes)
                            mb_act = descargado / (1024 * 1024)
                            mb_tot = total_bytes / (1024 * 1024)
                            progress_callback(pct * 0.9, f"Descargando FFmpeg: {mb_act:.1f} MB / {mb_tot:.1f} MB ({int(pct*100)}%)")
    except Exception as e:
        log_warning(f"Fallo descarga desde Gyan.dev ({e}), intentando mirror BtbN...")
        url_mirror = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        with requests.get(url_mirror, stream=True, timeout=30, headers={"User-Agent": "Voizy-App/1.0"}) as resp:
            resp.raise_for_status()
            total_bytes = int(resp.headers.get("content-length", 0))
            descargado = 0
            with open(tmp_zip, "wb") as f:
                for chunk in resp.iter_content(chunk_size=2 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        descargado += len(chunk)
                        if total_bytes > 0 and progress_callback:
                            pct = (descargado / total_bytes)
                            mb_act = descargado / (1024 * 1024)
                            mb_tot = total_bytes / (1024 * 1024)
                            progress_callback(pct * 0.9, f"Descargando FFmpeg: {mb_act:.1f} MB / {mb_tot:.1f} MB ({int(pct*100)}%)")

    if progress_callback:
        progress_callback(0.92, "Extrayendo binario ffmpeg.exe...")

    destino_ffmpeg = os.path.join(DIR_BIN, "ffmpeg.exe")
    with zipfile.ZipFile(tmp_zip, "r") as z:
        for name in z.namelist():
            if name.endswith("ffmpeg.exe"):
                with z.open(name) as source, open(destino_ffmpeg, "wb") as target:
                    shutil.copyfileobj(source, target)
                break

    try:
        os.remove(tmp_zip)
    except Exception:
        pass

    if DIR_BIN not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{DIR_BIN};{os.environ.get('PATH', '')}"

    if progress_callback:
        progress_callback(1.0, "Motor Multimedia FFmpeg instalado con éxito.")

    log_info(f"FFmpeg instalado exitosamente en {destino_ffmpeg}")
    return destino_ffmpeg


def esta_cuda_instalado():
    """Verifica si las librerías CUDA de cuBLAS están instaladas en AppData o en el sistema."""
    cublas_dll = os.path.join(DIR_CUDA, "cublas64_12.dll")
    cublaslt_dll = os.path.join(DIR_CUDA, "cublasLt64_12.dll")
    if os.path.isfile(cublas_dll) and os.path.isfile(cublaslt_dll):
        return True
    local_nv = os.path.join(RUTA_BASE, "env", "Lib", "site-packages", "nvidia", "cublas", "bin")
    if os.path.isfile(os.path.join(local_nv, "cublas64_12.dll")) and os.path.isfile(os.path.join(local_nv, "cublasLt64_12.dll")):
        return True
    return False


def obtener_version_cuda_remota(timeout_seg=4):
    """Obtiene la versión más reciente de nvidia-cublas-cu12 desde PyPI."""
    try:
        url_json = "https://pypi.org/pypi/nvidia-cublas-cu12/json"
        r = requests.get(url_json, timeout=timeout_seg, headers={"User-Agent": "pip/24.0 (Voizy-App)"})
        if r.status_code == 200:
            return r.json().get("info", {}).get("version", "")
    except Exception:
        pass
    return ""


def hay_actualizacion_cuda():
    """Comprueba si hay una versión más nueva del acelerador CUDA."""
    if not esta_cuda_instalado():
        return False
    meta = obtener_meta_modelo("cuda")
    instalada = meta.get("revision_instalada", "")
    remota = meta.get("revision_remota_vista", "")
    if not remota:
        remota = obtener_version_cuda_remota(timeout_seg=3)
        if remota:
            guardar_meta_modelo("cuda", revision_remota_vista=remota)
    if instalada and remota and instalada != remota:
        return True
    return False


def descargar_acelerador_cuda(progress_callback=None):
    """
    Descarga el paquete oficial de aceleración NVIDIA CUDA 12 (cuBLAS)
    directamente desde PyPI y extrae cublas64_12.dll y cublasLt64_12.dll en DIR_CUDA.
    """
    os.makedirs(DIR_CUDA, exist_ok=True)
    if progress_callback:
        progress_callback(0.05, "Obteniendo URL oficial del acelerador NVIDIA CUDA 12...")

    wheel_url = "https://files.pythonhosted.org/packages/20/e2/fc9a0e985249d873150276d5afb02e39a66817fedbf1a385724393e505ed/nvidia_cublas_cu12-12.9.2.10-py3-none-win_amd64.whl"
    version_cuda = "12.9.2.10"

    try:
        url_json = "https://pypi.org/pypi/nvidia-cublas-cu12/json"
        r = requests.get(url_json, timeout=12, headers={"User-Agent": "pip/24.0 (Voizy-App)"})
        if r.status_code == 200:
            data = r.json()
            version_cuda = data.get("info", {}).get("version", version_cuda)
            for u in data.get("urls", []):
                if "win_amd64.whl" in u.get("filename", ""):
                    wheel_url = u.get("url")
                    break
    except Exception as e:
        log_warning(f"Error consultando PyPI JSON: {e}, usando URL oficial directa.")

    log_info(f"Descargando acelerador CUDA desde: {wheel_url}")
    if progress_callback:
        progress_callback(0.1, "Iniciando descarga de NVIDIA cuBLAS CUDA 12...")

    tmp_wheel = os.path.join(DIR_CUDA, "nvidia_cublas.tmp")
    with requests.get(wheel_url, stream=True, timeout=30, headers={"User-Agent": "pip/24.0 (Voizy-App)"}) as resp:
        resp.raise_for_status()
        total_bytes = int(resp.headers.get("content-length", 0))
        descargado = 0
        chunk_size = 2 * 1024 * 1024  # 2 MB

        with open(tmp_wheel, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    descargado += len(chunk)
                    if total_bytes > 0 and progress_callback:
                        pct = (descargado / total_bytes)
                        mb_act = descargado / (1024 * 1024)
                        mb_tot = total_bytes / (1024 * 1024)
                        progress_callback(pct * 0.9, f"Descargando CUDA 12: {mb_act:.1f} MB / {mb_tot:.1f} MB ({int(pct*100)}%)")

    if progress_callback:
        progress_callback(0.92, "Extrayendo librerías cublas64_12.dll y cublasLt64_12.dll...")

    with zipfile.ZipFile(tmp_wheel, "r") as z:
        for name in z.namelist():
            if name.endswith(".dll"):
                filename = os.path.basename(name)
                with z.open(name) as source, open(os.path.join(DIR_CUDA, filename), "wb") as target:
                    shutil.copyfileobj(source, target)

    try:
        os.remove(tmp_wheel)
    except Exception:
        pass

    guardar_meta_modelo("cuda", revision_instalada=version_cuda, revision_remota_vista=version_cuda)

    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(DIR_CUDA)
        except Exception:
            pass
    if DIR_CUDA not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{DIR_CUDA};{os.environ.get('PATH', '')}"

    if progress_callback:
        progress_callback(1.0, "Acelerador NVIDIA CUDA 12 instalado con éxito.")

    log_info("Acelerador NVIDIA CUDA 12 instalado y registrado en DIR_CUDA.")
    return DIR_CUDA


def esta_instalado(modelo_id):
    """Verifica si el modelo existe en el directorio permanente o local."""
    for base in [DIR_MODELOS, os.path.join(RUTA_BASE, "models")]:
        path = os.path.join(base, modelo_id)
        if os.path.isdir(path):
            archivos_encontrados = []
            for _, _, archivos in os.walk(path):
                archivos_encontrados.extend([a.lower() for a in archivos])

            if any("model.bin" in a or "model.safetensors" in a for a in archivos_encontrados):
                return True
    return False


def normalizar_revision(valor):
    if not valor:
        return ""
    return str(valor).strip()


def obtener_hash_remoto(repo_id, timeout_seg=5):
    """Obtiene el hash del commit remoto de HuggingFace con timeout."""
    def _fetch():
        info = hf_api.model_info(repo_id)
        return normalizar_revision(info.sha)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_fetch)
        try:
            return future.result(timeout=timeout_seg)
        except Exception as e:
            log_warning(f"No se pudo consultar hash de {repo_id}: {e}")
            return None


def hay_actualizacion_modelo(modelo_id):
    """Comprueba si un modelo instalado tiene una versión más nueva en HuggingFace."""
    if not esta_instalado(modelo_id):
        return False
    if modelo_id not in INFO_MODELOS:
        return False
    meta = obtener_meta_modelo(modelo_id)
    instalada = meta.get("revision_instalada", "")
    remota = meta.get("revision_remota_vista", "")
    if not remota:
        remota = obtener_hash_remoto(INFO_MODELOS[modelo_id]["repo"], timeout_seg=3) or ""
        if remota:
            guardar_meta_modelo(modelo_id, revision_remota_vista=remota)
    if instalada and remota and instalada != remota and instalada != "instalado_manual":
        return True
    return False


def comprobar_todas_las_actualizaciones():
    """Escanea todos los modelos y aceleradores instalados para detectar actualizaciones."""
    actualizaciones = []
    for mid, info in INFO_MODELOS.items():
        try:
            if esta_instalado(mid):
                repo = info["repo"]
                remota = obtener_hash_remoto(repo, timeout_seg=3)
                meta = obtener_meta_modelo(mid)
                instalada = meta.get("revision_instalada", "")
                if remota:
                    guardar_meta_modelo(mid, revision_remota_vista=remota)
                    if instalada and instalada != remota and instalada != "instalado_manual":
                        actualizaciones.append({
                            "id": mid,
                            "tipo": "modelo",
                            "nombre": info["label"],
                        })
        except Exception:
            pass

    try:
        if esta_cuda_instalado():
            remota_c = obtener_version_cuda_remota(timeout_seg=3)
            meta_c = obtener_meta_modelo("cuda")
            instalada_c = meta_c.get("revision_instalada", "")
            if remota_c:
                guardar_meta_modelo("cuda", revision_remota_vista=remota_c)
                if instalada_c and instalada_c != remota_c:
                    actualizaciones.append({
                        "id": "cuda",
                        "tipo": "cuda",
                        "nombre": "Acelerador NVIDIA CUDA 12",
                    })
    except Exception:
        pass

    return actualizaciones


def descargar_modelo_huggingface(modelo_id, progress_callback=None):
    """
    Descarga el modelo desde HuggingFace directamente a la carpeta permanente de modelos.
    Soporta callbacks de progreso: progress_callback(progreso_0_a_1, mensaje_estado)
    """
    if modelo_id not in INFO_MODELOS:
        raise ValueError(f"Modelo desconocido: {modelo_id}")

    repo = INFO_MODELOS[modelo_id]["repo"]
    archivos = INFO_MODELOS[modelo_id].get("archivos", [])
    destino = os.path.join(DIR_MODELOS, modelo_id)
    os.makedirs(destino, exist_ok=True)

    log_info(f"Iniciando descarga de {modelo_id} ({repo}) en {destino}")
    if progress_callback:
        progress_callback(0.05, f"Conectando con HuggingFace ({repo})...")

    descarga_exitosa = False
    if archivos:
        try:
            total_archivos = len(archivos)
            for idx, archivo in enumerate(archivos, 1):
                url = f"https://huggingface.co/{repo}/resolve/main/{archivo}"
                nombre_guardar = os.path.basename(archivo)
                ruta_destino = os.path.join(destino, nombre_guardar)

                if progress_callback:
                    progress_callback((idx - 1) / total_archivos, f"Descargando {nombre_guardar} ({idx}/{total_archivos})...")

                for intento in range(3):
                    try:
                        with requests.get(url, stream=True, timeout=30, headers={"User-Agent": "Voizy-App/1.0"}) as r:
                            r.raise_for_status()
                            total_bytes = int(r.headers.get("content-length", 0))
                            descargado = 0
                            chunk_size = 2 * 1024 * 1024  # 2 MB

                            with open(ruta_destino, "wb") as f:
                                for chunk in r.iter_content(chunk_size=chunk_size):
                                    if chunk:
                                        f.write(chunk)
                                        descargado += len(chunk)
                                        if total_bytes > 0 and progress_callback:
                                            pct_archivo = descargado / total_bytes
                                            pct_global = ((idx - 1) + pct_archivo) / total_archivos
                                            mb_act = descargado / (1024 * 1024)
                                            mb_tot = total_bytes / (1024 * 1024)
                                            progress_callback(pct_global * 0.95, f"Descargando {nombre_guardar}: {mb_act:.1f} MB / {mb_tot:.1f} MB ({int(pct_archivo*100)}%)")
                        break
                    except Exception as ex:
                        if intento == 2:
                            raise ex
                        time.sleep(1.5)
            descarga_exitosa = True
        except Exception as e:
            log_warning(f"Descarga directa falló para {modelo_id}: {e}, probando snapshot_download...")

    if not descarga_exitosa:
        if progress_callback:
            progress_callback(0.25, f"Descargando {INFO_MODELOS[modelo_id]['label']} con snapshot...")
        snapshot_download(
            repo_id=repo,
            local_dir=destino,
            local_dir_use_symlinks=False,
            resume_download=True,
        )

    if progress_callback:
        progress_callback(1.0, f"{INFO_MODELOS[modelo_id]['label']} descargado e instalado.")

    meta = obtener_meta_modelo(modelo_id)
    hash_remoto = obtener_hash_remoto(repo, timeout_seg=4)
    revision_guardar = hash_remoto if hash_remoto else (meta.get("revision_instalada") or "instalado_manual")

    guardar_meta_modelo(
        modelo_id,
        repo=repo,
        revision_instalada=revision_guardar,
        revision_remota_vista=hash_remoto or "",
        auto_update=meta.get("auto_update", False),
    )
    log_info(f"Modelo {modelo_id} verificado y registrado exitosamente en {destino}")
    return destino


def eliminar_modelo_local(modelo_id):
    """Elimina los archivos locales de un modelo."""
    for base in [DIR_MODELOS, os.path.join(RUTA_BASE, "models")]:
        destino = os.path.join(base, modelo_id)
        if os.path.exists(destino):
            shutil.rmtree(destino, ignore_errors=True)
    guardar_meta_modelo(
        modelo_id,
        revision_instalada="",
        revision_remota_vista="",
    )


descargar_modelo_hf = descargar_modelo_huggingface
hay_actualizacion_disponible = hay_actualizacion_modelo
