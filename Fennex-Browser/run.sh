#!/bin/bash
# Script mejorado para ejecutar chrome_browser.py y pedir autorización solo si faltan dependencias
chmod +x "$0"
set -e

# Verifica dependencias de sistema
REQUIRED_PKGS=(python3-pyqt5 python3-pyqt5.qtwebengine python3-requests)
missing_system_pkgs=()
for pkg in "${REQUIRED_PKGS[@]}"; do
    dpkg -s "$pkg" &> /dev/null || missing_system_pkgs+=("$pkg")
done

# Verifica si zenity está instalado
if ! command -v zenity &> /dev/null; then
    echo "Instalando zenity..."
    sudo apt update && sudo apt install -y zenity || exit 1
fi

# Verifica dependencias de Python (PyQt5, PyQtWebEngine, requests)
missing_pip_pkgs=()
python3 -c "from PyQt5 import QtWidgets, QtWebEngineWidgets" 2>/dev/null || missing_pip_pkgs+=("PyQt5 PyQtWebEngine")
python3 -c "import requests" 2>/dev/null || missing_pip_pkgs+=("requests")

# Si todo está instalado, ejecuta directamente
if [ ${#missing_system_pkgs[@]} -eq 0 ] && [ ${#missing_pip_pkgs[@]} -eq 0 ]; then
    exec python3 /usr/lib/fennex/chrome_browser.py
else
    # Mostrar ventana de autorización solo si falta algo
    zenity --question --title="Instalar dependencias" --text="Faltan dependencias:\n${missing_system_pkgs[@]} ${missing_pip_pkgs[@]}\n¿Deseas instalarlas automáticamente?" || exit 1
    # Instala paquetes de sistema si faltan
    if [ ${#missing_system_pkgs[@]} -gt 0 ]; then
        sudo apt update
        sudo apt install -y ${missing_system_pkgs[@]}
    fi
    # Instala paquetes de pip si faltan
    if [[ "${missing_pip_pkgs[@]}" == *PyQt5* ]]; then
        pip3 install PyQt5 PyQtWebEngine
    fi
    if [[ "${missing_pip_pkgs[@]}" == *requests* ]]; then
        pip3 install requests
    fi
    exec python3 chrome_browser.py
fi
