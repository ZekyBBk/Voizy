"""
Funciones auxiliares y de formateo para subtítulos, medios y sistema.
"""

import os
import sys
import ctypes
import textwrap
import winsound

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
CONTENEDORES_SUBS_COMPATIBLES = {".mkv", ".mp4", ".mov"}
CONTENEDORES_MOV_TEXT = {".mp4", ".mov"}


def es_video(ruta):
    if not ruta:
        return False
    return os.path.splitext(ruta)[1].lower() in VIDEO_EXTS


def es_audio(ruta):
    if not ruta:
        return False
    return os.path.splitext(ruta)[1].lower() in AUDIO_EXTS


def formato_srt(segundos):
    """Convierte segundos flotantes al formato estándar de subtítulo SRT HH:MM:SS,mmm."""
    if segundos is None or segundos < 0:
        segundos = 0.0
    total_ms = int(round(float(segundos) * 1000))
    horas = total_ms // 3600000
    minutos = (total_ms % 3600000) // 60000
    segs = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{ms:03d}"


def segmentar_texto_subtitulo(texto, inicio, fin, max_chars=42, max_lineas=2):
    """Divide subtítulos largos en bloques naturales distribuyendo el tiempo proporcionalmente."""
    texto = " ".join((texto or "").split())
    if not texto:
        return []

    lineas = textwrap.wrap(
        texto,
        width=max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    )

    if not lineas:
        return [(inicio, fin, texto)]

    grupos = [
        "\n".join(lineas[i : i + max_lineas])
        for i in range(0, len(lineas), max_lineas)
    ]

    total_grupos = len(grupos)
    if total_grupos == 1:
        return [(inicio, fin, grupos[0])]

    duracion_total = fin - inicio
    peso_total = sum(len(g) for g in grupos) or 1
    sub_segmentos = []
    tiempo_actual = inicio

    for i, g in enumerate(grupos):
        fraccion = len(g) / peso_total
        dur_segmento = duracion_total * fraccion
        t_fin = fin if i == total_grupos - 1 else (tiempo_actual + dur_segmento)
        sub_segmentos.append((tiempo_actual, t_fin, g))
        tiempo_actual = t_fin

    return sub_segmentos


def generar_ruta_sin_colision(carpeta, nombre_base, sufijo, extension):
    """Genera una ruta única agregando un índice incremental si ya existe."""
    ruta = os.path.join(carpeta, f"{nombre_base}{sufijo}{extension}")
    if not os.path.exists(ruta):
        return ruta

    contador = 1
    while True:
        ruta = os.path.join(carpeta, f"{nombre_base}{sufijo}_{contador}{extension}")
        if not os.path.exists(ruta):
            return ruta
        contador += 1


def reproducir_sonido_exito():
    try:
        winsound.PlaySound(
            "SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC
        )
    except Exception:
        pass


def obtener_nombre_cpu():
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        nombre_procesador, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        return " ".join(nombre_procesador.split())
    except Exception:
        return "CPU"


def abrir_carpeta(path):
    try:
        os.startfile(path)
    except Exception:
        pass


abrir_explorador_archivos = abrir_carpeta


def aplicar_tema_oscuro_barra_titulo(ventana, color_bg_hex="#0A0C10", color_text_hex="#FFFFFF"):
    """
    Pinta la barra de título de Windows 10/11 en negro profundo (#0A0C10)
    integrándola de forma 100% fluida e indistinguible del lienzo de la aplicación.
    """
    if sys.platform != "win32":
        return

    def _aplicar():
        try:
            ventana.update_idletasks()
            hwnd = ventana.winfo_id()
            parent_hwnd = ctypes.windll.user32.GetParent(hwnd)
            target_hwnd = parent_hwnd if parent_hwnd else hwnd

            # DWMWA_USE_IMMERSIVE_DARK_MODE (20 y 19)
            valor_dark = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                target_hwnd, 20, ctypes.byref(valor_dark), ctypes.sizeof(valor_dark)
            )
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                target_hwnd, 19, ctypes.byref(valor_dark), ctypes.sizeof(valor_dark)
            )

            # DWMWA_CAPTION_COLOR = 35 (Windows 11) -> COLORREF BGR
            r = int(color_bg_hex[1:3], 16)
            g = int(color_bg_hex[3:5], 16)
            b = int(color_bg_hex[5:7], 16)
            color_bgr = (b << 16) | (g << 8) | r
            c_color = ctypes.c_int(color_bgr)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                target_hwnd, 35, ctypes.byref(c_color), ctypes.sizeof(c_color)
            )

            # DWMWA_TEXT_COLOR = 36 (Windows 11) -> COLORREF BGR
            r_t = int(color_text_hex[1:3], 16)
            g_t = int(color_text_hex[3:5], 16)
            b_t = int(color_text_hex[5:7], 16)
            color_bgr_t = (b_t << 16) | (g_t << 8) | r_t
            c_color_t = ctypes.c_int(color_bgr_t)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                target_hwnd, 36, ctypes.byref(c_color_t), ctypes.sizeof(c_color_t)
            )
        except Exception:
            pass

    # Ejecutar en múltiples etapas del ciclo de renderizado de la ventana
    ventana.after(10, _aplicar)
    ventana.after(50, _aplicar)
    ventana.after(150, _aplicar)


def tiene_gpu_nvidia() -> bool:
    """Detecta de forma silenciosa y segura si el equipo cuenta con una GPU NVIDIA instalada."""
    try:
        import subprocess
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        out = subprocess.check_output(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            creationflags=flags,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore").lower()
        if any(x in out for x in ["nvidia", "geforce", "rtx", "gtx", "quadro", "tesla"]):
            return True
    except Exception:
        pass

    try:
        import subprocess
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        p = subprocess.run(
            ["nvidia-smi"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=flags,
        )
        if p.returncode == 0:
            return True
    except Exception:
        pass
    return False


def obtener_detalles_pc():
    """Retorna especificaciones de hardware y sistema operativo del PC."""
    import platform
    so = f"{platform.system()} {platform.release()}"

    cpu = obtener_nombre_cpu()
    ram = "Desconocida"
    gpu = "GPU Integrada / Estándar"

    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            ram = f"{stat.ullTotalPhys / (1024**3):.1f} GB RAM"
    except Exception:
        pass

    try:
        import subprocess
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController).Name"]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags, timeout=3)
        names = [line.strip() for line in p.stdout.splitlines() if line.strip()]
        if names:
            dedicadas = [n for n in names if any(k in n.upper() for k in ["NVIDIA", "GEFORCE", "RTX", "GTX", "RADEON RX", "ARC"])]
            gpu = dedicadas[0] if dedicadas else names[0]
            if len(gpu) > 42:
                gpu = gpu[:40] + "..."
    except Exception:
        pass

    return {
        "so": so,
        "cpu": cpu,
        "ram": ram,
        "gpu": gpu,
    }
