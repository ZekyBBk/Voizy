@echo off
setlocal enabledelayedexpansion
title Voizy - Compilador de Builder Studio

cd /d "%~dp0"

set "CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" (
    set "CSC=C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)

echo [*] Compilando Builder.exe nativo C#...
"%CSC%" /nologo /target:winexe /win32icon:..\ui\assets\voizy.ico /win32manifest:builder.manifest /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll /out:"..\Builder.exe" builder.cs

if %errorlevel% neq 0 (
    echo [!] Error durante la compilacion de Builder.exe
    pause
    exit /b %errorlevel%
)

echo [OK] Builder.exe compilado con exito.
pause
