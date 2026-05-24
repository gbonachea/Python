#!/bin/bash
# Script para preparar entorno y ejecutar la app Cleaner con GUI
set -e

# Asegurar permisos de ejecución para este script
chmod +x "$0"

# 1. Verificar e instalar python3-venv y python3-pip si no existen
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 no está instalado. Instálalo primero."
    exit 1
fi
if ! python3 -m venv --help &> /dev/null; then
    echo "[INFO] Instalando python3-venv..."
    sudo apt-get update && sudo apt-get install -y python3-venv
fi
if ! command -v pip3 &> /dev/null; then
    echo "[INFO] Instalando python3-pip..."
    sudo apt-get update && sudo apt-get install -y python3-pip
fi

# 2. Crear entorno virtual si no existe
echo "[INFO] Comprobando entorno virtual..."
if [ ! -d ".venv" ]; then
    echo "[INFO] Creando entorno virtual Python (.venv)"
    python3 -m venv .venv
fi

# 3. Activar entorno virtual
echo "[INFO] Activando entorno virtual..."
source .venv/bin/activate

# 4. Instalar dependencias solo si no están
NEED_INSTALL=0
python -c "import PyQt5" 2>/dev/null || NEED_INSTALL=1
python -c "import psutil" 2>/dev/null || NEED_INSTALL=1
if [ $NEED_INSTALL -eq 1 ]; then
    echo "[INFO] Instalando dependencias..."
    pip install --upgrade pip
    pip install PyQt5 psutil
else
    echo "[INFO] Dependencias ya instaladas."
fi

# 5. Ejecutar la aplicación gráfica
echo "[INFO] Iniciando la aplicación Cleaner (GUI)..."
python3 main.py
