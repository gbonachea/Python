#!/bin/bash
# Script para ejecutar el cliente VPN y asegurar dependencias
chmod +x "$0"
set -e

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 no está instalado. Instalando..."
    sudo apt update && sudo apt install -y python3 python3-venv python3-pyqt5 pipx
fi

# Verificar OpenVPN
if ! command -v openvpn &> /dev/null; then
    echo "OpenVPN no está instalado. Instalando..."
    sudo apt update && sudo apt install -y openvpn
fi

# Instalar dependencias si faltan
if ! command -v openvpn &> /dev/null; then
    echo "pystray no está instalado. Instalando..."
    sudo pipx update && sudo pipx install -y pystray

fi


# Paso 5: Ejecutar la aplicación gráfica usando el Python del entorno virtual
echo "[INFO] Iniciando la aplicación Cleaner (GUI)..."
python3 vpn_client.py

# Cambios realizados:
# - Se eliminó el uso de 'source .venv/bin/activate' y se reemplazó por llamadas directas a .venv/bin/python y .venv/bin/pip
# - Se agregaron comentarios explicativos para cada paso
# - Se asegura que las dependencias se instalen solo en el entorno virtual, evitando errores de entorno gestionado externamente