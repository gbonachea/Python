#!/bin/bash

# Otorgar permisos de ejecución al propio script
chmod +x "$0"

# Verificar si python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "Instalando python3..."
    apt update && apt install -y python3
fi

# Verificar si pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "Instalando pip3..."
    apt install -y python3-pip
fi

# Verificar si ffmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo "Instalando ffmpeg..."
    apt install -y ffmpeg
fi

# Verificar si PyGObject está instalado
python3 -c "import gi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Instalando PyGObject..."
    pip3 install PyGObject
fi

# Ejecutar el programa principal
exec python3 "$(dirname "$0")/main.py"