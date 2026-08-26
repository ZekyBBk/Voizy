<p align="center">
  <img src="ui/assets/voizy_logo.png" alt="Voizy Logo" width="220" />
</p>

<h1 align="center">VOIZY STUDIO</h1>

<p align="center">
  <strong>Herramienta de escritorio ligera y 100% local para transcripción por IA, traducción multilingüe y generación de subtítulos sin depender de la nube.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Plataforma-Windows_10_%7C_11-101216?style=flat-square&logo=windows&logoColor=AAC90C" alt="Plataforma" />
  <img src="https://img.shields.io/badge/Motor_IA-Faster--Whisper-101216?style=flat-square&logoColor=AAC90C" alt="Whisper" />
  <img src="https://img.shields.io/badge/Aceleración-NVIDIA_CUDA_12-101216?style=flat-square&logo=nvidia&logoColor=AAC90C" alt="CUDA" />
  <img src="https://img.shields.io/badge/Versión-1.0.0-101216?style=flat-square&logoColor=AAC90C" alt="Versión" />
</p>

---

## 1. Instalar Git y Clonar

Si no tienes Git, abre **PowerShell** como Administrador y ejecuta:

```powershell
winget install --id Git.Git -e --source winget --silent
```

*(Cierra y vuelve a abrir la consola)* y clona el repositorio:

```powershell
git clone https://github.com/TU_USUARIO/Voizy.git C:\Voizy
```

---

## 2. Descripcion General

Voizy Studio automatiza el flujo completo de subtitulado profesional sin requerir configuraciones complejas ni instalaciones pesadas previas. Utiliza motores de inteligencia artificial Faster-Whisper optimizados con cuantización int8/float16, el motor multimedia FFmpeg y el acelerador oficial NVIDIA cuBLAS CUDA 12, permitiendo transcripciones de alta precisión y velocidad tanto en GPU dedicada como en CPU multinúcleo.

### Caracteristicas Principales

- **Reconocimiento de Voz Inteligente**: Integración de Whisper Large-V3 (máxima fidelidad) y Whisper Turbo (velocidad 4x).
- **Aceleracion por Hardware**: Soporte nativo para GPU NVIDIA mediante cuBLAS CUDA 12. Detección automática con respaldo continuo en CPU multihilo optimizado (AVX2).
- **Traduccion Multilingue Integrada**: Soporte para más de 10 idiomas internacionales con detección de idioma de origen automática.
- **Incrustacion sin Perdida de Calidad**: Muxing directo en contenedores MKV/MP4 mediante copia de flujo (`-c copy`), preservando la resolución, tasa de bits y audio original del vídeo.
- **Gestor de Motores IA y Binarios Desacoplado**: Descarga de modelos Whisper, FFmpeg y aceleradores CUDA bajo demanda directamente a `%LOCALAPPDATA%\Voizy`, manteniendo el repositorio y el ejecutable standalone ultra-ligeros (~35 MB).
- **Interfaz Dark Slate**: Experiencia de usuario limpia, centrada y optimizada en resolución fija, sin barras de desplazamiento innecesarias ni dependencias invasivas.

---

## 3. Requisitos del Sistema

- **Sistema Operativo**: Windows 10 o Windows 11 (64-bit).
- **Procesador**: CPU Intel o AMD compatible con instrucciones x86_64 (AVX2 recomendado).
- **Memoria RAM**: 4 GB minimo (8 GB o mas recomendado para modelos Large-V3).
- **Grafica (Opcional)**: Tarjeta grafica NVIDIA (GeForce GTX/RTX, Quadro o Tesla) para aceleración CUDA.
- **Software**: Git para Windows y Python 3.12 (instalado en el sistema o gestionado automáticamente por el compilador).

---

## 4. Compilacion y Generacion del Ejecutable Standalone

Voizy cuenta con un sistema de compilacion automatizado en un solo clic mediante **`Builder.exe`**.

### Metodo 1: Compilacion Grafica con Builder.exe (Recomendado)

1. Ejecuta el archivo `Builder.exe` ubicado en la raiz del proyecto.
2. Haz clic en **Compilar Voizy.exe**.
3. El compilador realizara automaticamente los siguientes pasos:
   - Deteccion del interprete de Python 3.12.
   - Creacion del entorno virtual `env/`.
   - Instalacion y actualizacion de dependencias base (`ctranslate2`, `faster-whisper`, `customtkinter`, `tkinterdnd2`, `deep-translator`, `pyinstaller`, `requests`, `huggingface_hub`, `Pillow`).
   - Empaquetado optimizado con PyInstaller mediante `tools/Voizy.spec`.
   - Ensamblado del ejecutable standalone ultra-rapido con launcher autocontenido en `tools/launcher.cs`.
4. Al finalizar, encontraras el ejecutable distribuible listo en tu Escritorio:
   - `Voizy.exe` (~35 MB)

### Metodo 2: Compilacion por Linea de Comandos

Tambien puedes compilar manualmente mediante el script por lotes incluido en `tools`:

```bat
tools\build.bat
```

---

## 5. Estructura del Repositorio

```text
Voizy/
├── Builder.exe                 # Compilador nativo para Windows
├── .gitignore                  # Exclusion de temporales, modelos pesados y entornos
├── README.md                   # Documentacion tecnica del proyecto
├── core/
│   ├── __init__.py
│   ├── config.py               # Mapeo de idiomas, modelos y preferencias
│   ├── main.py                 # Punto de entrada principal con supresion de consolas
│   ├── media.py                # Procesamiento y multiplexado con FFmpeg
│   ├── model_manager.py        # Gestor de descarga de Whisper, FFmpeg y CUDA
│   ├── transcriber.py          # Motor Faster-Whisper y generacion de SRT
│   └── translator.py           # Servicio de traduccion de subtitulos
├── ui/
│   ├── __init__.py
│   ├── assets/                 # Iconos y logotipos oficiales
│   ├── icons/                  # Recursos graficos auxiliares
│   ├── main_window.py          # Interfaz principal CustomTkinter
│   ├── modals.py               # Modales de confirmacion, informacion y gestor IA
│   └── theme.py                # Paleta corporativa Dark y Neon Lime
├── utils/
│   ├── __init__.py
│   ├── helpers.py              # Deteccion de hardware, formato de tiempo y cadenas
│   ├── logger.py               # Registro de eventos tecnicos en disco
│   └── paths.py                # Resolucion de rutas para entorno local y congelado
└── tools/
    ├── Voizy.spec              # Definicion de empaquetado para PyInstaller
    ├── build.bat               # Script CLI de automatizacion
    ├── builder.cs              # Codigo fuente C# del asistente de compilacion
    ├── builder.manifest        # Manifiesto de privilegios para Windows
    └── launcher.cs             # Lanzador ligero con extraccion rapida (<10ms)
```

---

## 6. Uso de la Aplicacion

1. **Seleccionar Archivo**: Arrastra tu archivo de vídeo o audio sobre la ventana o pulsa **Buscar**.
2. **Definir Opciones**:
   - Selecciona el **Idioma de subtítulos** deseado.
   - Elige el motor Whisper (**Large V3** para máxima precisión o **Turbo** para rapidez).
   - Marca las casillas de configuración (Subtítulos automáticos, Conversor MKV, Conservar `.srt`).
3. **Descargar Componentes**: Si es la primera vez que utilizas la app, pulsa en **MOTORES IA** para descargar FFmpeg, el modelo Whisper deseado o el acelerador CUDA para GPU NVIDIA.
4. **Procesar**: Pulsa **INICIAR PROCESAMIENTO**. Al finalizar, la carpeta de exportación se abrirá automáticamente con el resultado listo para reproducir.

---

## 7. Licencia

Proyecto desarrollado bajo licencia privada / MIT. Consulta los detalles de distribucion correspondientes en el repositorio.
