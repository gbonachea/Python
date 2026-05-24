#!/bin/bash

# Otorgar permisos de ejecución al propio script
chmod +x "$0"

# Colores para los mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar si un paquete Python está instalado
check_python_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

# Función para instalar dependencias
install_dependencies() {
    echo -e "${YELLOW}Instalando dependencias...${NC}"
    
    # Verificar si pip está instalado
    if ! command -v pip3 &> /dev/null; then
        echo "Instalando pip3..."
        sudo apt-get update
        sudo apt-get install -y python3-pip
    fi
    
    # Instalar dependencias de Python
    pip3 install PyQt5 pygame mutagen
    
    echo -e "${GREEN}Dependencias instaladas correctamente${NC}"
}

# Verificar dependencias
dependencies_needed=false

# Verificar cada dependencia
for package in "PyQt5" "pygame" "mutagen"; do
    if ! check_python_package "$package"; then
        echo "Falta el paquete: $package"
        dependencies_needed=true
    fi
done

# Si faltan dependencias, instalarlas
if [ "$dependencies_needed" = true ]; then
    install_dependencies
fi

# Ejecutar el aplicativo
echo -e "${GREEN}Iniciando el reproductor...${NC}"
python3 reproductor.py