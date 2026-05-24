#!/bin/bash
# Script para preparar entorno y ejecutar la app Whatsapp con GUI
# Actualizado para usar el entorno virtual correctamente y evitar errores de entorno gestionado externamente (PEP 668)
chmod +x "$0"
set -e
# Paso 1: Verificar e instalar npm si no existen
# npm es necesario para crear entornos virtuales
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm no está instalado. Instálalo primero."
    exit 1
fi
if ! python3 -m venv --help &> /dev/null; then
    echo "[INFO] Instalando npm..."
    sudo apt update && sudo apt install -y npm
fi

# Se comprueba si Elecctron están instalados
NEED_INSTALL=0
npm -c "import electron" 2>/dev/null || NEED_INSTALL=1
npm -c "import install" 2>/dev/null || NEED_INSTALL=1
if [ $NEED_INSTALL -eq 1 ]; then
    echo "[INFO] Instalando dependencias..."
    npm install electron --save-dev
    npm install
else
    echo "[INFO] Dependencias ya instaladas en el entorno virtual."
fi

# Paso 5: Ejecutar la aplicación gráfica
npm start

